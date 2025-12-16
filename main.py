__version__ = '1.0'
from kivy.config import Config
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '800')
Config.write()

import sqlite3
import io
from decimal import Decimal
from datetime import datetime, timezone, timedelta

# matplotlib + kivy image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from kivy.core.image import Image as CoreImage
from kivy.clock import Clock

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition, FadeTransition
from kivy.properties import ListProperty, ObjectProperty, StringProperty, NumericProperty
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.utils import get_color_from_hex as HEX
from kivy.uix.image import Image
import numpy as np
import matplotlib.patheffects as pe

DB_NAME = "data.db"

CATEGORY_COLORS = [
    "#9AA0A6", "#1F1F1F",
    "#7A4A2E", "#D64545", "#E67E22", "#F1C40F",
    "#A3CB38", "#2ECC71", "#48C9B0",
    "#3498DB", "#8E44AD", "#C0398E",
]

# --- Работа с базой данных ---
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()
    return conn, cur

def init_db():
    conn, cur = get_db()

    cur.execute("""CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    color TEXT DEFAULT '#1F1F1F'
                  );""")
    cur.execute("""CREATE TABLE IF NOT EXISTS operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category_id INTEGER REFERENCES categories(id) ON DELETE CASCADE,
                    amount_cents INTEGER,
                    type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                  );""")
    conn.commit()
    cur.close()
    conn.close()


def get_categories():
    conn, cur = get_db()
    cur.execute("SELECT id, name, color FROM categories ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return rows

def delete_category_from_db(category_id):
    conn, cur = get_db()
    cur.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    cur.close()
    conn.close()

# ---------------------------
# PieChart widget (matplotlib -> texture)
# ---------------------------
class PieChart(Image):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def draw(self, data, dpi=120, size_px=320):
        total = sum([v for _, v, _ in data])
        # подготовим фигуру
        fig, ax = plt.subplots(figsize=(size_px/ dpi, size_px/ dpi), dpi=dpi)
        fig.patch.set_alpha(0)  # прозрачный фон

        if total <= 0 or len(data) == 0:
            # пустой / нулевые данные — рисуем серый круг и текст
            sizes = [1]
            colors = ['#DDDDDD']
            wedges, _ = ax.pie(sizes, colors=colors, startangle=90, counterclock=False,
                               wedgeprops={'linewidth':0})
            ax.set(aspect="equal")
            ax.text(0, 0, "Нет\nдоходов", ha='center', va='center', fontsize=14)
        else:
            labels = []
            sizes = []
            colors = []
            for lbl, val, hexc in data:
                if val > 0:
                    labels.append(lbl)
                    sizes.append(val)
                    colors.append(hexc if hexc else '#1F1F1F')

            def autopct(pct):
                return ('{:.1f}%'.format(pct)) if pct > 0.5 else ''

            wedges, texts, autotexts = ax.pie(
                sizes,
                labels=None,
                colors=colors,
                startangle=90,
                counterclock=False,
                autopct=autopct,
                pctdistance=0.75,
                wedgeprops={'linewidth':0}
            )
            ax.set(aspect="equal")

            # Внутренние подписи (при желании можно расположить легенду)
            # Сделаем легенду справа с именами + суммы в рублях
            legend_labels = []
            for (lbl, val, _) in zip(labels, sizes, colors):
                # но здесь zip неправильно — ниже пересоздадим из data
                pass
            # Создадим легенду из исходных списков:
            legend_labels = [f"{labels[i]} — {sizes[i]/100:.2f}₽" for i in range(len(labels))]
            ax.legend(wedges, legend_labels, loc="center left", bbox_to_anchor=(1, 0.5), fontsize=8)

            # увеличим размер процентов
            for t in autotexts:
                t.set_fontsize(9)
                t.set_color('white')
                t.set_weight('bold')

        # Сохранение в buffer и установка текстуры
        buf = io.BytesIO()
        plt.savefig(buf, format='png', transparent=True, bbox_inches='tight', pad_inches=0)
        plt.close(fig)
        buf.seek(0)
        self.texture = CoreImage(buf, ext='png').texture

# ---------------------------
# Существующие классы приложения
# ---------------------------
class CategoriesWidget(FloatLayout):
    output = ListProperty([])

    def on_output(self, instance, value):
        # попытка найти RecycleView в self.ids
        rv = self.ids.get("rv")
        if not rv:
            # ещё не создан — ничего не делаем (show_categories попробует снова)
            return
        rv.data = [
            {"text": f"{cid}. {name}", "category_id": cid, "bg_color": HEX(color)}
            for cid, name, color in get_categories()
        ]


    def show_categories(self):
        rows = get_categories()

        # функция для правильного склонения слова "категория"
        def pluralize_category(n):
            if 11 <= n % 100 <= 14:
                return "категорий"
            last = n % 10
            if last == 1:
                return "категория"
            elif last in (2, 3, 4):
                return "категории"
            else:
                return "категорий"

        # обновляем текст-инфо
        info = self.ids.get("info_label")
        if info:
            if len(rows) == 0:
                info.text = "У вас нет категорий"
            else:
                count = len(rows)
                info.text = f"У вас {count} {pluralize_category(count)}"

        # формируем данные для RecycleView:
        data = []
        for i, (cid, name, color_hex) in enumerate(rows):
            display_text = f"{i+1}. {name}"
            data.append({
                "text": display_text,
                "category_id": cid,
                "bg_color": HEX(color_hex)
            })

        rv = self.ids.get("rv")
        if rv:
            rv.data = data
        else:
            # запасной путь — используем output
            self.output = [f"{i+1}. {name}" for i, (_, name) in enumerate(rows)]

class PieAnimatedChart(Image):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.progress = 0
        self.fps = 1 / 120
        self.speed = 0.1
        self.values = []
        self.colors = []
        self.labels = []
        self._anim_event = None

    def start(self, values, colors, labels):
        # сохраняем данные
        self.values = values
        self.colors = colors
        self.labels = labels

        # сбрасываем анимацию
        self.progress = 0
        if self._anim_event:
            self._anim_event.cancel()

        # запуск анимации
        self._anim_event = Clock.schedule_interval(self._update, self.fps)

    def _update(self, dt):
        if self.progress >= 1:
            self.progress = 1
            self._draw(self.progress)
            return False  # стоп анимации

        self._draw(self.progress)
        self.progress += self.speed

    def _draw(self, progress):
        if not self.values:
            return

        fig, ax = plt.subplots(figsize=(3.2, 3.2), dpi=100)
        fig.patch.set_alpha(0)

        total = sum(self.values)
        if total == 0:
            plt.close(fig)
            return

        # масштабируем значениями прогресса
        scaled = [(v / total) * progress for v in self.values]

        # гарантируем, что сектор не исчезает полностью
        safe_scaled = [max(v, 0.0001) for v in scaled]

        # добавляем ПРОЗРАЧНЫЙ остаток — ОТВЕЧАЕТ ЗА АНИМАЦИЮ
        remainder = max(0, 1 - progress)
        sizes = safe_scaled + [remainder]
        colors = list(self.colors) + [(0, 0, 0, 0)]
        labels = list(self.labels) + [""]

        wedges, _ = ax.pie(
            sizes,
            colors=colors,
            startangle=90,
            counterclock=False,
            labels=None,
            wedgeprops={'linewidth': 0}
        )

        # --- подписи из второго варианта ---
        for i, w in enumerate(wedges[:-1]):  # последний — прозрачный сектор
            theta1, theta2 = w.theta1, w.theta2
            theta_mid = (theta1 + theta2) / 2
            ang = np.deg2rad(theta_mid)

            r = 0.65
            x = r * np.cos(ang)
            y = r * np.sin(ang)

            # название категории
            ax.text(
                x, y + 0.07, self.labels[i],
                ha='center', va='center',
                fontsize=9, color='white', weight='bold',
                path_effects=[pe.withStroke(linewidth=1, foreground="black")]
            )

            # процент от полного массива (как во втором варианте)
            pct = f"{100 * self.values[i] / total:.1f}%"
            ax.text(
                x, y - 0.08, pct,
                ha='center', va='center',
                fontsize=10, color='white', weight='bold',
                path_effects=[pe.withStroke(linewidth=1, foreground="black")]
            )

        ax.set(aspect='equal')

        buf = io.BytesIO()
        plt.savefig(
            buf, format='png',
            transparent=True,
            bbox_inches='tight',
            pad_inches=0
        )
        plt.close(fig)

        buf.seek(0)
        self.texture = CoreImage(buf, ext='png').texture




class MainApp(App):
    last_transition = "down"  # по умолчанию

    def build(self):
        # загрузим kv из файла main.kv (если есть)
        Builder.load_file("main.kv")
        return RootWidget()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_entry_point = None

    # --- навигация (без изменений) ---
    def open_category_screen(self, category_id, category_name, direction="left"):
        sm = self.root.ids.sm
        if f"cat_{category_id}" in sm.screen_names:
            sm.transition = SlideTransition(direction=direction, duration=0.4)
            sm.current = f"cat_{category_id}"
            return
        new_screen = RecordScreen(name=f"cat_{category_id}")
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
            "right": "left"
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

    mode = "record"  # "record" или "history"

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

class AddCategoryScreen(Screen):
    selected_color = "#1F1F1F"
    def on_enter(self):
        grid = self.ids.get("color_grid")
        if not grid:
            return
        grid.clear_widgets()
        for col in CATEGORY_COLORS:
            btn = Button(
                background_normal="",
                background_color=HEX(col),
                on_release=lambda b, c=col: self.select_color(c)
            )
            grid.add_widget(btn)

    def select_color(self, color):
        self.selected_color = color
        print("Выбран цвет:", color)

    from kivy.clock import Clock

    def add_category(self):
        name = self.ids.category_input.text.strip()
        msg = self.ids.msg_label

        def clear_msg(dt):
            msg.text = ""

        if not name:
            msg.text = "Ошибка: имя категории пустое"
            msg.color = (1, 0, 0, 1)
            msg.halign = "center"
            msg.valign = "middle"
            msg.text_size = msg.size
            Clock.schedule_once(clear_msg, 3)  # текст исчезнет через 3 секунды
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
            Clock.schedule_once(clear_msg, 3)
        else:
            cur.execute(
                "INSERT INTO categories (name, color) VALUES (?, ?)",
                (name, self.selected_color)
            )
            conn.commit()
            msg.text = f"Категория '{short_name}' добавлена"
            msg.color = (0, 1, 0, 1)
            msg.halign = "center"
            msg.valign = "middle"
            msg.text_size = msg.size
            Clock.schedule_once(clear_msg, 3)

        cur.close()
        conn.close()
        self.ids.category_input.text = ""

class CategoryButton(FloatLayout):
    category_id = NumericProperty(0)
    text = StringProperty("")
    bg_color = ListProperty([0,0,0,1])

class RootWidget(FloatLayout):
    pass

class MainScreen(Screen):

    def on_enter(self):
        Clock.schedule_once(self.animate_chart, 0)

    def animate_chart(self, dt):
        conn, cur = get_db()

        # --- Доходы ---
        cur.execute("""
            SELECT c.name, c.color,
                   COALESCE(SUM(CASE WHEN o.type='доход' THEN o.amount_cents ELSE 0 END), 0)
            FROM categories c
            LEFT JOIN operations o ON o.category_id = c.id
            GROUP BY c.id
        """)
        income_rows = cur.fetchall()

        income_rows = [r for r in income_rows if r[2] > 0]

        # --- Расходы ---
        cur.execute("""
            SELECT c.name, c.color,
                   COALESCE(SUM(CASE WHEN o.type='расход' THEN -o.amount_cents ELSE 0 END), 0)
            FROM categories c
            LEFT JOIN operations o ON o.category_id = c.id
            GROUP BY c.id
        """)
        expense_rows = cur.fetchall()

        expense_rows = [r for r in expense_rows if r[2] > 0]

        conn.close()

        # --- Анимация доходов ---
        income_chart = self.ids.get("pie_chart_income")
        income_label = self.ids.get("label_income")

        if income_rows:
            # показываем диаграмму
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
            # скрываем диаграмму
            if income_chart:
                income_chart.opacity = 0
                income_chart.disabled = True

            if income_label:
                income_label.opacity = 0



        # --- Анимация расходов ---
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
        from kivy.uix.label import Label
        from kivy.uix.scrollview import ScrollView
        from kivy.uix.boxlayout import BoxLayout

        layout = self.ids.operations_layout
        layout.clear_widgets()

        if not self.category_id:
            layout.add_widget(Label(text="Ошибка: нет категории"))
            return

        conn, cur = get_db()
        cur.execute("""
            SELECT amount_cents, type, created_at 
            FROM operations 
            WHERE category_id=? 
            ORDER BY created_at DESC
        """, (self.category_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            layout.add_widget(Label(
                text="Операций пока нет",
                color=(0, 0, 0, 1),
                font_size=18
            ))
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
                    height=30
                )
            )

class CategoryScreen(Screen):
    def on_enter(self):
        self.ids.category_widget.show_categories()

class RecordScreen(Screen):
    def reset_buttons(self):
        self.ids.income.state = "normal"
        self.ids.expense.state = "normal"
        self.ids.income.state = "down"

    error_label = None
    success_label = None
    category_id = None
    category_name = None

    def add_operation(self):
        # Удаляем старые сообщения
        if self.error_label:
            self.remove_widget(self.error_label)
            self.error_label = None

        if self.success_label:
            self.remove_widget(self.success_label)
            self.success_label = None

        # 1. Получаем сумму
        amount_text = self.ids.operation.text.strip()

        if not amount_text:
            self.error_label = Label(
                text="Введите сумму",
                color=(1, 0, 0, 1),
                font_size='24sp',
                size_hint=(None, None),
                size=(self.ids.operation.width, 30),
                pos_hint={"center_x": 0.5, "center_y": 0.6}
            )
            self.add_widget(self.error_label)
            return

        # 2. Пробуем конвертировать в число
        try:
            amount_cents = int(Decimal(amount_text) * 100)
        except:
            self.error_label = Label(
                text="Ошибка: введите число",
                color=(1, 0, 0, 1),
                font_size='24sp',
                size_hint=(None, None),
                size=(self.ids.operation.width, 30),
                pos_hint={"center_x": 0.5, "center_y": 0.6}
            )
            self.add_widget(self.error_label)
            return

        # 3. Определяем тип операции
        if self.ids.income.state == "down":
            type_op = "доход"
        else:
            type_op = "расход"
            amount_cents = -abs(amount_cents)

        # 4. Записываем в БД с московским временем
        conn, cur = get_db()
        current_time = datetime.now(timezone(timedelta(hours=3)))

        cur.execute(
            "INSERT INTO operations(category_id, amount_cents, type, created_at) VALUES (?, ?, ?, ?)",
            (self.category_id, amount_cents, type_op, current_time.strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        cur.close()
        conn.close()

        # 5. Показываем зелёное сообщение
        self.success_label = Label(
            text=f"{type_op.capitalize()} добавлен",
            color=(0, 1, 0, 1),
            font_size='24sp',
            size_hint=(None, None),
            size=(self.ids.operation.width + 50, 30),
            pos_hint={"center_x": 0.5, "center_y": 0.6}
        )
        self.add_widget(self.success_label)

        # 6. Чистим поле
        self.ids.operation.text = ""

        self.reset_buttons()

    def on_enter(self):
        # Активируем кнопку "Доход"
        self.ids.income.state = "down"
        self.reset_buttons()

    def send_text(self):
        text = self.ids.operation.text.strip()

        # Удаляем старые сообщения, если есть
        if self.error_label:
            self.remove_widget(self.error_label)
            self.error_label = None
        if self.success_label:
            self.remove_widget(self.success_label)
            self.success_label = None

        if not text:
            # Показываем красное сообщение об ошибке
            self.error_label = Label(
                text="Поле не должно быть пустым",
                color=(1, 0, 0, 1),  # красный
                font_size='24sp',
                size_hint=(None, None),
                size=(self.ids.operation.width, 30),
                pos_hint={"center_x": 0.5, "center_y": 0.6}
            )
            self.add_widget(self.error_label)
            return

        # Очищаем поле ввода
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
        cur.execute("""
            SELECT id, amount_cents, type, created_at
            FROM operations
            WHERE category_id=?
            ORDER BY created_at DESC
        """, (self.category_id,))
        rows = cur.fetchall()
        conn.close()

        data = []

        for op_id, amount, type_op, dt in rows:
            sign = "-" if amount < 0 else "+"
            rub = abs(amount) // 100
            kop = abs(amount) % 100

            full = f"{dt} | {type_op.capitalize()} {sign}{rub}.{kop:02d}₽"
            short = f"{sign}{rub}.{kop:02d}₽"

            data.append({
                "op_id": op_id,
                "full_text": full,
                "short_text": short
            })

        rv.data = data

class OperationDetailScreen(Screen):
    operation_text = StringProperty("")

if __name__ == "__main__":
    init_db()
    MainApp().run()
