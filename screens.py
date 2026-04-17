from decimal import Decimal

from kivy.app import App
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import Screen
from kivy.utils import get_color_from_hex as HEX

from config import CATEGORY_COLORS
from db import (
    add_category,
    add_operation,
    category_exists,
    get_chart_rows,
    get_operations_by_category,
)


class AddCategoryScreen(Screen):
    selected_color = "#1F1F1F"

    def on_enter(self):
        grid = self.ids.get("color_grid")
        if not grid:
            return
        grid.clear_widgets()

        for color in CATEGORY_COLORS:
            btn = Button(
                background_normal="",
                background_color=HEX(color),
                on_release=lambda _btn, c=color: self.select_color(c),
            )
            grid.add_widget(btn)

    def select_color(self, color):
        self.selected_color = color

    def add_category(self):
        name = self.ids.category_input.text.strip()
        msg = self.ids.msg_label

        def clear_msg(_dt):
            msg.text = ""

        if not name:
            msg.text = "Ошибка: имя категории пустое"
            msg.color = (1, 0, 0, 1)
            msg.halign = "center"
            msg.valign = "middle"
            msg.text_size = msg.size
            Clock.schedule_once(clear_msg, 3)
            return

        short_name = name[:13] + "..." if len(name) > 13 else name

        if category_exists(name):
            msg.text = f"Ошибка: категория '{short_name}' уже существует"
            msg.color = (1, 0, 0, 1)
            msg.halign = "center"
            msg.valign = "middle"
            msg.text_size = msg.size
            Clock.schedule_once(clear_msg, 3)
        else:
            add_category(name, self.selected_color)
            msg.text = f"Категория '{short_name}' добавлена"
            msg.color = (0, 1, 0, 1)
            msg.halign = "center"
            msg.valign = "middle"
            msg.text_size = msg.size
            Clock.schedule_once(clear_msg, 3)

        self.ids.category_input.text = ""


class MainScreen(Screen):
    def on_enter(self):
        Clock.schedule_once(self.animate_chart, 0)

    def animate_chart(self, _dt):
        income_rows, expense_rows = get_chart_rows()

        income_chart = self.ids.get("pie_chart_income")
        income_label = self.ids.get("label_income")
        if income_rows:
            if income_chart:
                income_chart.opacity = 1
                income_chart.disabled = False
                labels = [r[0] for r in income_rows]
                colors = [r[1] for r in income_rows]
                values = [r[2] for r in income_rows]
                income_chart.start(values, colors, labels)
            if income_label:
                income_label.opacity = 1
        else:
            if income_chart:
                income_chart.opacity = 0
                income_chart.disabled = True
            if income_label:
                income_label.opacity = 0

        expense_chart = self.ids.get("pie_chart_expense")
        expense_label = self.ids.get("label_expense")
        if expense_rows:
            if expense_chart:
                expense_chart.opacity = 1
                expense_chart.disabled = False
                labels = [r[0] for r in expense_rows]
                colors = [r[1] for r in expense_rows]
                values = [r[2] for r in expense_rows]
                expense_chart.start(values, colors, labels)
            if expense_label:
                expense_label.opacity = 1
        else:
            if expense_chart:
                expense_chart.opacity = 0
                expense_chart.disabled = True
            if expense_label:
                expense_label.opacity = 0


class OperationScreen(Screen):
    category_id = None
    category_name = None

    def on_pre_enter(self):
        self.show_operations()

    def show_operations(self):
        layout = self.ids.operations_layout
        layout.clear_widgets()

        if not self.category_id:
            layout.add_widget(Label(text="Ошибка: нет категории"))
            return

        rows = get_operations_by_category(self.category_id)
        if not rows:
            layout.add_widget(Label(text="Операций пока нет", color=(0, 0, 0, 1), font_size=18))
            return

        for _, amount, type_op, dt in rows:
            sign = "-" if amount < 0 else "+"
            rub = abs(amount) // 100
            kop = abs(amount) % 100
            text = f"{dt} | {type_op.capitalize()} {sign}{rub}.{kop:02d}₽"
            layout.add_widget(
                Label(text=text, color=(0, 0, 0, 1), font_size=16, size_hint_y=None, height=30)
            )


class CategoryScreen(Screen):
    def on_enter(self):
        self.ids.category_widget.show_categories()


class RecordScreen(Screen):
    error_label = None
    success_label = None
    category_id = None
    category_name = None

    def reset_buttons(self):
        self.ids.income.state = "normal"
        self.ids.expense.state = "normal"
        self.ids.income.state = "down"

    def add_operation(self):
        if self.error_label:
            self.remove_widget(self.error_label)
            self.error_label = None
        if self.success_label:
            self.remove_widget(self.success_label)
            self.success_label = None

        amount_text = self.ids.operation.text.strip()
        if not amount_text:
            self.error_label = Label(
                text="Введите сумму",
                color=(1, 0, 0, 1),
                font_size="24sp",
                size_hint=(None, None),
                size=(self.ids.operation.width, 30),
                pos_hint={"center_x": 0.5, "center_y": 0.6},
            )
            self.add_widget(self.error_label)
            return

        try:
            amount_cents = int(Decimal(amount_text) * 100)
        except Exception:
            self.error_label = Label(
                text="Ошибка: введите число",
                color=(1, 0, 0, 1),
                font_size="24sp",
                size_hint=(None, None),
                size=(self.ids.operation.width, 30),
                pos_hint={"center_x": 0.5, "center_y": 0.6},
            )
            self.add_widget(self.error_label)
            return

        if self.ids.income.state == "down":
            op_type = "доход"
        else:
            op_type = "расход"
            amount_cents = -abs(amount_cents)

        add_operation(self.category_id, amount_cents, op_type)

        self.success_label = Label(
            text=f"{op_type.capitalize()} добавлен",
            color=(0, 1, 0, 1),
            font_size="24sp",
            size_hint=(None, None),
            size=(self.ids.operation.width + 50, 30),
            pos_hint={"center_x": 0.5, "center_y": 0.6},
        )
        self.add_widget(self.success_label)
        self.ids.operation.text = ""
        self.reset_buttons()

    def on_enter(self):
        self.ids.income.state = "down"
        self.reset_buttons()

    def send_text(self):
        text = self.ids.operation.text.strip()

        if self.error_label:
            self.remove_widget(self.error_label)
            self.error_label = None
        if self.success_label:
            self.remove_widget(self.success_label)
            self.success_label = None

        if not text:
            self.error_label = Label(
                text="Поле не должно быть пустым",
                color=(1, 0, 0, 1),
                font_size="24sp",
                size_hint=(None, None),
                size=(self.ids.operation.width, 30),
                pos_hint={"center_x": 0.5, "center_y": 0.6},
            )
            self.add_widget(self.error_label)
            return

        self.ids.operation.text = ""


class HistoryScreen(Screen):
    category_id = None
    category_name = None

    def show_operation_detail(self, full_text):
        app = App.get_running_app()
        sm = app.root.ids.sm
        screen = sm.get_screen("operation_detail")
        screen.operation_text = full_text
        app.go_to("operation_detail", "slide_right")

    def load_history(self):
        rv = self.ids.history_rv
        rows = get_operations_by_category(self.category_id)

        data = []
        for op_id, amount, type_op, dt in rows:
            sign = "-" if amount < 0 else "+"
            rub = abs(amount) // 100
            kop = abs(amount) % 100
            full = f"{dt} | {type_op.capitalize()} {sign}{rub}.{kop:02d}₽"
            short = f"{sign}{rub}.{kop:02d}₽"
            data.append({"op_id": op_id, "full_text": full, "short_text": short})

        rv.data = data


class OperationDetailScreen(Screen):
    operation_text = StringProperty("")
