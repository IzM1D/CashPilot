from kivy.config import Config
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '800')
Config.write()
import sqlite3
from decimal import Decimal
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition, FadeTransition
from kivy.properties import ListProperty, ObjectProperty, StringProperty
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.metrics import dp
from kivy.uix.floatlayout import FloatLayout
from datetime import datetime, timezone, timedelta


def rgba_from_hex(hex_color):
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16) / 255
    g = int(hex_color[2:4], 16) / 255
    b = int(hex_color[4:6], 16) / 255
    return (r, g, b, 1)

DB_NAME = "data.db"

moscow_time = datetime.now(timezone(timedelta(hours=3)))

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
                    color TEXT DEFAULT '#ff0000'
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
    cur.execute("SELECT id, name, color FROM categories ORDER BY id;")
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

class CategoriesWidget(FloatLayout):
    output = ListProperty([])
    color_rgba = ListProperty([1,1,1,1])

    def on_output(self, instance, value):
        # попытка найти RecycleView в self.ids
        rv = self.ids.get("rv")
        if not rv:
            # ещё не создан — ничего не делаем (show_categories попробует снова)
            return
        rv.data = [
            {"text": f"{cid}. {name}", "category_id": cid}
            for cid, name in get_categories()
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
        # показываем порядковый номер (i+1) в тексте, но сохраняем реальный category_id
        data = []
        for i, (cid, name, color_hex) in enumerate(rows):
            display_text = f"{i+1}. {name}"
            data.append({
                "text": display_text,
                "category_id": cid,
                "color_rgba": rgba_from_hex(color_hex)
            })



        rv = self.ids.get("rv")
        if rv:
            rv.data = data
        else:
            # запасной путь — используем output
            self.output = [f"{i+1}. {name}" for i, (_, name) in enumerate(rows)]

class CategoryButton(FloatLayout):
    category_id = 0
    text = StringProperty("")
    color_rgba = ListProperty([1, 1, 1, 1])



# --- Приложение Kivy ---
class MainApp(App):
    last_transition = "down"  # по умолчанию

    def build(self):
        return RootWidget()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_entry_point = None

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

        # Запоминаем направление
        if transition_type.startswith("slide_"):
            self.last_transition = transition_type.replace("slide_", "")

        # Определяем тип перехода
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
        # если вход был через "операции" — хотим slide_right
        if self.last_entry_point == "history":
            direction = "slide_left"
        # если вход был через "запись операции" — хотим slide_left
        elif self.last_entry_point == "record":
            direction = "slide_right"
        else:
            direction = "slide_left"

        self.go_to("main", direction)


    def delete_category(self, category_id):
        delete_category_from_db(category_id)

        # после удаления обновляем список категорий
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
            # Открываем экран записи операции
            record = sm.get_screen("record")
            record.category_id = cat_id
            record.category_name = cat_name
            self.go_to("record", "slide_left")

        else:
            # Открываем экран истории операций
            history = sm.get_screen("history")
            history.category_id = cat_id
            history.category_name = cat_name
            history.load_history()
            self.go_to("history", "slide_right")


class CategoryScreen(Screen):
    def on_enter(self):
        if 'category_widget' in self.ids:
            self.ids.category_widget.show_categories()


class RootWidget(FloatLayout):
    pass

class MainScreen(Screen):
    pass

class AddCategoryScreen(Screen):
    selected_color = "#ff5555"
    def add_category(self):
        name = self.ids.category_input.text.strip()
        msg = self.ids.msg_label

        # поле пустое
        if not name:
            msg.text = "Ошибка: имя категории пустое"
            msg.color = (1, 0, 0, 1)   # красный
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
            msg.color = (1, 0, 0, 1)   # красный
            msg.halign = "center"
            msg.valign = "middle"
            msg.text_size = msg.size

        else:
            cur.execute("INSERT INTO categories (name, color) VALUES (?, ?)", (name, self.selected_color))
            conn.commit()
            msg.text = f"Категория '{short_name}' добавлена"
            msg.color = (0, 1, 0, 1)   # зелёный
            msg.halign = "center"
            msg.valign = "middle"
            msg.text_size = msg.size


        cur.close()
        conn.close()

        # очищаем поле
        self.ids.category_input.text = ""

        # очищаем поле
        self.ids.category_input.text = ""

    def on_enter(self):
        colors = [
            "#ff5555", "#55ff55", "#5555ff",
            "#ffcc00", "#ff8800", "#00cccc",
        ]

        grid = self.ids.color_grid
        grid.clear_widgets()

        for hex_color in colors:
            r = int(hex_color[1:3], 16) / 255
            g = int(hex_color[3:5], 16) / 255
            b = int(hex_color[5:7], 16) / 255

            btn = Button(
                background_normal="",
                background_color=(r, g, b, 1),
                size_hint=(None, None),
                size=(50, 50),
                on_release=lambda instance, c=hex_color: self.set_color(c)
            )

            grid.add_widget(btn)

    def set_color(self, color_hex):
        self.selected_color = color_hex
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


class RecordScreen(Screen):
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
        cur.execute(
            "INSERT INTO operations(category_id, amount_cents, type, created_at) VALUES (?, ?, ?, ?)",
            (self.category_id, amount_cents, type_op, moscow_time.isoformat(sep=" "))
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


    def on_enter(self):
        # Активируем кнопку "Доход"
        self.ids.income.state = "down"


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
        box = self.ids.history_box
        box.clear_widgets()

        conn, cur = get_db()
        cur.execute("""
            SELECT id, amount_cents, type, created_at
            FROM operations
            WHERE category_id=?
            ORDER BY created_at DESC
        """, (self.category_id,))
        rows = cur.fetchall()
        cur.close()
        conn.close()

        if not rows:
            box.add_widget(Label(
                text="Операций пока нет",
                color=(0, 0, 0, 1),
                font_size=20,
                size_hint_y=None,
                height=40
            ))
            return

        app = App.get_running_app()

        for op_id, amount, type_op, dt in rows:

            # текст
            sign = "-" if amount < 0 else "+"
            rub = abs(amount) // 100
            kop = abs(amount) % 100

            full_text = f"{dt} | {type_op.capitalize()} {sign}{rub}.{kop:02d}₽"
            short_text = f"{sign}{rub}.{kop:02d}₽"

            # ---- строка операции ----
            row = FloatLayout(size_hint_y=None, height=dp(50))

            # ---- основная кнопка ----
            btn = Button(
                text=short_text,
                color=(1, 1, 1, 1),
                size_hint=(0.85, None),   # как у категорий
                height=dp(50),            # как у категорий
                pos_hint={"x": 0}         # ровно как у CategoryButton
            )
            btn.bind(on_release=lambda instance, t=full_text: self.show_operation_detail(t))
            row.add_widget(btn)

            # ---- кнопка удаления (как в категориях) ----
            del_btn = Button(
                size_hint=(0.23, 1),
                pos_hint={"right": 1.1},
                background_normal='',
                background_color=(156/255, 156/255, 156/255, 1)
            )
            del_btn.bind(on_release=lambda instance, id=op_id: self.delete_operation(id))
            row.add_widget(del_btn)

            box.add_widget(row)

    def delete_operation(self, op_id):
        conn, cur = get_db()
        cur.execute("DELETE FROM operations WHERE id=?", (op_id,))
        conn.commit()
        cur.close()
        conn.close()

        self.load_history()


class OperationDetailScreen(Screen):
    operation_text = StringProperty("")



if __name__ == "__main__":
    init_db()
    MainApp().run()
