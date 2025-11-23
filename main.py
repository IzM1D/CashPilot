# -------------------------
# KIVY: basic config
# -------------------------
from kivy.config import Config

# фиксируем размер окна (как у тебя было)
Config.set("graphics", "width", "360")
Config.set("graphics", "height", "800")
Config.write()

# -------------------------
# Imports
# -------------------------
import io
import sqlite3
from decimal import Decimal
from datetime import datetime, timezone, timedelta

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.utils import get_color_from_hex as HEX

from kivy.uix.image import Image
from kivy.core.image import Image as CoreImage
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import (
    ScreenManager,
    Screen,
    SlideTransition,
    FadeTransition,
)
from kivy.properties import (
    ListProperty,
    ObjectProperty,
    StringProperty,
    NumericProperty,
)
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.garden.matplotlib import FigureCanvasKivyAgg
from kivy.uix.widget import Widget

# -------------------------
# Constants
# -------------------------
DB_NAME = "data.db"

CATEGORY_COLORS = [
    "#808080",
    "#000000",
    "#8B4513",
    "#FF0000",
    "#FFA500",
    "#FFFF00",
    "#00FF00",
    "#008000",
    "#00FFFF",
    "#0000FF",
    "#800080",
    "#FF00FF",
]

# -------------------------
# Database helpers
# -------------------------


def get_db():
    """
    Open a sqlite3 connection with foreign keys on and return (conn, cursor).
    Caller is responsible for closing both.
    """
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()
    return conn, cur


def init_db():
    """Create required tables if they don't exist yet."""
    conn, cur = get_db()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            color TEXT DEFAULT '#000000'
        );
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
            amount_cents INTEGER,
            type TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )

    conn.commit()
    cur.close()
    conn.close()


def get_categories():
    """Return list of (id, name, color) ordered by id."""
    conn, cur = get_db()
    cur.execute("SELECT id, name, color FROM categories ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def delete_category_from_db(category_id):
    """Delete category by id (cascades to operations thanks to FK)."""
    conn, cur = get_db()
    cur.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    cur.close()
    conn.close()


# -------------------------
# PieChart widget (matplotlib -> texture)
# -------------------------

class PieChart(Widget):
    """
    Статичная диаграмма через FigureCanvasKivyAgg.
    draw(values, labels, colors) — values должны быть list/array чисел (не кортежи).
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # создаём фигуру и ось один раз
        self.fig, self.ax = plt.subplots(figsize=(3, 3))
        self.ax.set_aspect('equal')
        self.canvas_widget = FigureCanvasKivyAgg(self.fig)
        # добавляем холст как child widget
        self.add_widget(self.canvas_widget)

    def draw(self, values, labels=None, colors=None):
        """
        values: list/np.array чисел (например, суммы в копейках или уже в рублях)
        labels: list строк (тот же порядок)
        colors: list hex строк или matplotlib colors
        """
        # нормализация
        if values is None:
            values = []
        values = np.array(values, dtype=float)

        self.ax.clear()
        self.ax.set_aspect('equal')

        if values.size == 0 or values.sum() == 0:
            # пустая диаграмма
            self.ax.pie([1], colors=["#DDDDDD"])
        else:
            # удаляем нулевые элементы, чтобы легенда/пороги работали корректно
            positive_mask = values > 0
            v = values[positive_mask]
            labs = None
            cols = None
            if labels is not None:
                labs = [labels[i] for i, m in enumerate(positive_mask) if m]
            if colors is not None:
                cols = [colors[i] for i, m in enumerate(positive_mask) if m]
            self.ax.pie(v, labels=labs, colors=cols, startangle=90, counterclock=False,
                        autopct=lambda pct: ("{:.1f}%".format(pct) if pct > 0.5 else ""), pctdistance=0.75)

        # обновляем холст
        self.canvas_widget.draw()

    def clear(self):
        """Очищает график."""
        self.ax.clear()
        self.canvas_widget.draw()

# -------------------------
# UI Widgets / Screens
# -------------------------


class CategoriesWidget(FloatLayout):
    """
    Widget that manages category list (used inside CategoryScreen).
    Exposes `output` for fallback textual output.
    """
    output = ListProperty([])

    def on_output(self, instance, value):
        rv = self.ids.get("rv")
        if not rv:
            return
        rv.data = [
            {"text": f"{cid}. {name}", "category_id": cid, "bg_color": HEX(color)}
            for cid, name, color in get_categories()
        ]

    def show_categories(self):
        rows = get_categories()

        def pluralize_category(n: int) -> str:
            """Return correct Russian plural for 'категория'."""
            if 11 <= n % 100 <= 14:
                return "категорий"
            last = n % 10
            if last == 1:
                return "категория"
            if last in (2, 3, 4):
                return "категории"
            return "категорий"

        info = self.ids.get("info_label")
        if info:
            if len(rows) == 0:
                info.text = "У вас нет категорий"
            else:
                count = len(rows)
                info.text = f"У вас {count} {pluralize_category(count)}"

        data = []
        for i, (cid, name, color_hex) in enumerate(rows):
            display_text = f"{i + 1}. {name}"
            data.append({"text": display_text, "category_id": cid, "bg_color": HEX(color_hex)})

        rv = self.ids.get("rv")
        if rv:
            rv.data = data
        else:
            self.output = [f"{i+1}. {name}" for i, (_, name) in enumerate(rows)]


class RootWidget(FloatLayout):
    """Root layout returned from Builder (main.kv)."""
    pass


class MainApp(App):
    """
    Основной класс приложения.
    Навигация, режимы и публичные методы для экранов.
    """
    last_transition = "down"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_entry_point = None

    def build(self):
        # загружаем KV (если есть) и возвращаем корневой виджет
        Builder.load_file("main.kv")
        return RootWidget()

    # -------------------------
    # Navigation helpers
    # -------------------------
    def open_category_screen(self, category_id, category_name, direction="left"):
        sm = self.root.ids.sm
        screen_name = f"cat_{category_id}"
        if screen_name in sm.screen_names:
            sm.transition = SlideTransition(direction=direction, duration=0.4)
            sm.current = screen_name
            return

        new_screen = RecordScreen(name=screen_name)
        new_screen.category_id = category_id
        new_screen.category_name = category_name
        sm.add_widget(new_screen)
        sm.transition = SlideTransition(direction=direction, duration=0.4)
        sm.current = new_screen.name

    def go_to(self, screen_name, transition_type="slide_up"):
        sm = self.root.ids.sm
        if transition_type.startswith("slide_"):
            self.last_transition = transition_type.replace("slide_", "")
        if transition_type == "fade":
            sm.transition = FadeTransition(duration=0.4)
        elif transition_type == "slide_up":
            sm.transition = SlideTransition(direction="up", duration=0.4)
        elif transition_type == "slide_down":
            sm.transition = SlideTransition(direction="down", duration=0.4)
        elif transition_type == "slide_left":
            sm.transition = SlideTransition(direction="left", duration=0.4)
        elif transition_type == "slide_right":
            sm.transition = SlideTransition(direction="right", duration=0.4)
        sm.current = screen_name

    def go_back(self, screen_name):
        sm = self.root.ids.sm
        opposite = {
            "up": "down",
            "down": "up",
            "left": "right",
            "right": "left",
        }.get(self.last_transition, "up")
        sm.transition = SlideTransition(direction=opposite, duration=0.4)
        sm.current = screen_name

    def go_back_from_categories(self):
        if self.last_entry_point == "history":
            direction = "slide_left"
        elif self.last_entry_point == "record":
            direction = "slide_right"
        else:
            direction = "slide_left"
        self.go_to("main", direction)

    def delete_category(self, category_id):
        delete_category_from_db(category_id)
        screen = self.root.ids.sm.get_screen("categories")
        widget = screen.ids.category_widget
        widget.show_categories()

    # mode: 'record' or 'history'
    mode = "record"

    def open_categories_for_record(self):
        self.mode = "record"
        self.last_entry_point = "record"
        self.go_to("categories", "slide_left")

    def open_categories_for_history(self):
        self.mode = "history"
        self.last_entry_point = "history"
        self.go_to("categories", "slide_right")

    def category_selected(self, cat_id, cat_name):
        sm = self.root.ids.sm
        if self.mode == "record":
            record = sm.get_screen("record")
            record.category_id = cat_id
            record.category_name = cat_name
            self.go_to("record", "slide_left")
        else:
            history = sm.get_screen("history")
            history.category_id = cat_id
            history.category_name = cat_name
            history.load_history()
            self.go_to("history", "slide_right")

    def open_operation_detail(self, full_text):
        sm = self.root.ids.sm
        screen = sm.get_screen("operation_detail")
        screen.operation_text = full_text
        self.go_to("operation_detail", "slide_right")

    def delete_operation(self, op_id):
        conn, cur = get_db()
        cur.execute("DELETE FROM operations WHERE id=?", (op_id,))
        conn.commit()
        conn.close()
        screen = self.root.ids.sm.get_screen("history")
        screen.load_history()
        App.get_running_app().root.ids.sm.get_screen("main").refresh()


# -------------------------
# Screens
# -------------------------


class AddCategoryScreen(Screen):
    """Экран добавления категории — кнопки цветов создаются динамически."""
    selected_color = "#000000"

    def on_enter(self):
        grid = self.ids.get("color_grid")
        if not grid:
            return
        grid.clear_widgets()
        for col in CATEGORY_COLORS:
            btn = Button(background_normal="", background_color=HEX(col),
                         on_release=lambda b, c=col: self.select_color(c))
            grid.add_widget(btn)

    def select_color(self, color):
        self.selected_color = color
        print("Выбран цвет:", color)

    def add_category(self):
        name = self.ids.category_input.text.strip()
        msg = self.ids.msg_label

        if not name:
            msg.text = "Ошибка: имя категории пустое"
            msg.color = (1, 0, 0, 1)
            msg.halign = "center"
            msg.valign = "middle"
            msg.text_size = msg.size
            return

        short_name = name[:13] + "..." if len(name) > 13 else name
        conn, cur = get_db()
        cur.execute("SELECT id FROM categories WHERE name = ?", (name,))
        exists = cur.fetchone()
        if exists:
            msg.text = f"Ошибка: категория '{short_name}' уже существует"
            msg.color = (1, 0, 0, 1)
            msg.halign = "center"
            msg.valign = "middle"
            msg.text_size = msg.size
        else:
            cur.execute("INSERT INTO categories (name, color) VALUES (?, ?)", (name, self.selected_color))
            conn.commit()
            msg.text = f"Категория '{short_name}' добавлена"
            msg.color = (0, 1, 0, 1)
            msg.halign = "center"
            msg.valign = "middle"
            msg.text_size = msg.size
        cur.close()
        conn.close()
        self.ids.category_input.text = ""


class CategoryButton(FloatLayout):
    """Простой контейнер для кнопки категории (viewclass в RecycleView)."""
    category_id = NumericProperty(0)
    text = StringProperty("")
    bg_color = ListProperty([0, 0, 0, 1])


class PieAnimatedChart(PieChart):
    """
    Лёгкая анимация: плавно интерполируем значения, вызывая draw для промежуточных значений.
    Методы:
        animate(values, labels, colors, duration=0.6)
        clear()
    """

    def animate(self, values, labels=None, colors=None, duration=0.6):
        # подготовка
        if values is None:
            values = []
        values = np.array(values, dtype=float)
        steps = max(6, int(30 * (duration / 0.6)))  # минимум 6 шагов
        self._anim_step = 0
        self._anim_steps = steps
        self._anim_values = values
        self._anim_labels = labels
        self._anim_colors = colors

        # отменим предыдущую анимацию, если есть
        try:
            Clock.unschedule(self._anim_callback)
        except Exception:
            pass

        def _tick(dt):
            self._anim_step += 1
            t = self._anim_step / self._anim_steps
            t = min(1.0, t)
            interp = self._anim_values * t
            # рисуем интерполированные значения
            super().draw(interp, self._anim_labels, self._anim_colors)
            if self._anim_step >= self._anim_steps:
                # завершили
                try:
                    Clock.unschedule(self._anim_callback)
                except Exception:
                    pass
                return False
            return True

        # расписать callback и старт
        self._anim_callback = Clock.schedule_interval(_tick, duration / steps)

    # clear() унаследован от PieChart



# -------------------------
# More screens
# -------------------------


class MainScreen(Screen):
    """
    Главный экран: обновляет баланс/операции и запускает анимацию диаграмм.
    """

    def refresh(self):
        """
        Полное обновление экрана: баланс, список операций и диаграммы.
        """
        if hasattr(self, "update_balance"):
            self.update_balance()
        if hasattr(self, "load_operations"):
            self.load_operations()

        # обновляем диаграммы в следующем кадре
        Clock.schedule_once(self.animate_chart, 0)

    def animate_chart(self, dt):
        conn, cur = get_db()

        # доходы
        cur.execute(
            """
            SELECT c.name, c.color,
                   COALESCE(SUM(CASE WHEN o.type='доход' THEN o.amount_cents END), 0)
            FROM categories c
            LEFT JOIN operations o ON o.category_id = c.id
            GROUP BY c.id
            """
        )
        income_rows = [r for r in cur.fetchall() if r[2] > 0]

        # расходы
        cur.execute(
            """
            SELECT c.name, c.color,
                   COALESCE(SUM(CASE WHEN o.type='расход' THEN -o.amount_cents END), 0)
            FROM categories c
            LEFT JOIN operations o ON o.category_id = c.id
            GROUP BY c.id
            """
        )
        expense_rows = [r for r in cur.fetchall() if r[2] > 0]

        conn.close()

        # показываем/скрываем лейблы
        self.ids.income_label.opacity = 1 if income_rows else 0
        self.ids.expense_label.opacity = 1 if expense_rows else 0

        # доходы — анимация
        chart_inc = self.ids.pie_income
        if income_rows:
            labels = [r[0] for r in income_rows]
            colors = [r[1] for r in income_rows]
            values = [r[2] for r in income_rows]
            # у нас animate(values, labels, colors)
            chart_inc.animate(values, labels, colors)
        else:
            chart_inc.clear()

        # расходы — анимация
        chart_exp = self.ids.pie_expense
        if expense_rows:
            labels = [r[0] for r in expense_rows]
            colors = [r[1] for r in expense_rows]
            values = [r[2] for r in expense_rows]
            chart_exp.animate(values, labels, colors)
        else:
            chart_exp.clear()


    def update_pie(self):
        """
        Нарисовать статичную круговую диаграмму (только доходы).
        """
        conn, cur = get_db()
        cur.execute(
            """
            SELECT c.id, c.name, c.color, IFNULL(SUM(o.amount_cents), 0) as sum_cents
            FROM categories c
            LEFT JOIN operations o ON o.category_id = c.id AND o.type = 'доход'
            GROUP BY c.id, c.name, c.color
            ORDER BY c.id
            """
        )
        rows = cur.fetchall()
        conn.close()

        values = []
        labels = []
        colors = []
        for cid, name, color_hex, sum_cents in rows:
            val = sum_cents or 0
            values.append(float(val))
            labels.append(name)
            colors.append(color_hex or "#000000")


        pie_widget = None
        try:
            pie_widget = self.ids.pie_chart
        except Exception:
            pie_widget = None

        if not pie_widget:
            pie_widget = PieChart(size_hint=(None, None), size=(280, 280))
            pie_widget.id = "pie_chart"
            container = self.children[0] if self.children else None
            if container:
                container.add_widget(pie_widget)

        pie_widget.draw(values, labels, colors)


class OperationScreen(Screen):
    category_id = None
    category_name = None

    def on_pre_enter(self):
        self.show_operations()

    def show_operations(self):
        # локальные быстрые импорты UI-компонентов (как в оригинале)
        from kivy.uix.label import Label

        layout = self.ids.operations_layout
        layout.clear_widgets()

        if not self.category_id:
            layout.add_widget(Label(text="Ошибка: нет категории"))
            return

        conn, cur = get_db()
        cur.execute(
            """
            SELECT amount_cents, type, created_at
            FROM operations
            WHERE category_id=?
            ORDER BY created_at DESC
            """,
            (self.category_id,),
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            layout.add_widget(
                Label(text="Операций пока нет", color=(0, 0, 0, 1), font_size=18)
            )
            return

        for amount, type_op, dt in rows:
            sign = "-" if amount < 0 else "+"
            rub = abs(amount) // 100
            kop = abs(amount) % 100
            text = f"{dt} | {type_op.capitalize()} {sign}{rub}.{kop:02d}₽"

            layout.add_widget(
                Label(
                    text=text,
                    color=(0, 0, 0, 1),
                    font_size=16,
                    size_hint_y=None,
                    height=30,
                )
            )


class CategoryScreen(Screen):
    def on_enter(self):
        self.ids.category_widget.show_categories()


class RecordScreen(Screen):
    """Экран записи операции."""
    error_label = None
    success_label = None
    category_id = None
    category_name = None

    def reset_buttons(self):
        self.ids.income.state = "normal"
        self.ids.expense.state = "normal"
        self.ids.income.state = "down"

    def add_operation(self):
        # удаляем старые сообщения
        if self.error_label:
            try:
                self.remove_widget(self.error_label)
            except Exception:
                pass
            self.error_label = None

        if self.success_label:
            try:
                self.remove_widget(self.success_label)
            except Exception:
                pass
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
            type_op = "доход"
        else:
            type_op = "расход"
            amount_cents = -abs(amount_cents)

        conn, cur = get_db()
        current_time = datetime.now(timezone(timedelta(hours=3)))
        cur.execute(
            "INSERT INTO operations(category_id, amount_cents, type, created_at) VALUES (?, ?, ?, ?)",
            (self.category_id, amount_cents, type_op, current_time.strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        cur.close()
        conn.close()

        # обновим главный экран
        try:
            self.manager.get_screen("main").refresh()
        except Exception:
            pass

        self.success_label = Label(
            text=f"{type_op.capitalize()} добавлен",
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
            try:
                self.remove_widget(self.error_label)
            except Exception:
                pass
            self.error_label = None

        if self.success_label:
            try:
                self.remove_widget(self.success_label)
            except Exception:
                pass
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

        conn, cur = get_db()
        cur.execute(
            """
            SELECT id, amount_cents, type, created_at
            FROM operations
            WHERE category_id=?
            ORDER BY created_at DESC
            """,
            (self.category_id,),
        )
        rows = cur.fetchall()
        conn.close()

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


# -------------------------
# Entrypoint
# -------------------------
if __name__ == "__main__":
    init_db()
    MainApp().run()
