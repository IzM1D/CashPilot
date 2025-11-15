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
from kivy.properties import ListProperty, ObjectProperty
from kivy.uix.label import Label


DB_NAME = "data.db"

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
                    name TEXT UNIQUE
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
    cur.execute("SELECT id, name FROM categories ORDER BY id;")
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return rows

class CategoriesWidget(FloatLayout):
    output = ListProperty([])

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
        print("get_categories returned:", rows)

        # установка текста в зависимости от количества категорий
        info = self.ids.get("info_label")
        if info:
            if len(rows) == 0:
                info.text = "У вас нет категорий"
            else:
                info.text = f"У вас {len(rows)} категори(й)"  # можно улучшить склонение

        data = [{"text": f"{cid}. {name}", "category_id": cid} for cid, name in rows]

        rv = self.ids.get("rv")
        if rv:
            rv.data = data
            print("rv.data set, length:", len(rv.data))
        else:
            self.output = [f"{cid}. {name}" for cid, name in rows]



# --- Приложение Kivy ---
class MainApp(App):
    last_transition = "up"  # по умолчанию

    def build(self):
        return RootWidget()

    def open_category_screen(self, category_id, category_name, direction="left"):
        print(f"Открыта категория {category_id}: {category_name}")

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

class CategoryScreen(Screen):
    def on_enter(self):
        if 'category_widget' in self.ids:
            self.ids.category_widget.show_categories()


class RootWidget(FloatLayout):
    pass

class MainScreen(Screen):
    pass

class OperationScreen(Screen):
    category_id = None
    category_name = None

    def on_enter(self):
        print(f"Экран категории {self.category_id} ({self.category_name})")
        # Тут можно добавить логику — загрузку операций, суммы и т.д.


class RecordScreen(Screen):
    error_label = None  # для ошибок
    success_label = None  # для успешного сообщения

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
                font_size='16sp',
                size_hint=(None, None),
                size=(self.ids.operation.width, 30),
                pos=(self.ids.operation.x, self.ids.operation.y - 35)
            )
            self.add_widget(self.error_label)
            return

        # Если текст есть — выводим успешное сообщение
        self.success_label = Label(
            text=f"Операция '{text}' успешно добавлена в категорию",
            color=(0, 1, 0, 1),  # зелёный
            font_size='16sp',
            size_hint=(None, None),
            size=(self.ids.operation.width + 50, 30),
            pos=(self.ids.operation.x, self.ids.operation.y - 35)
        )
        self.add_widget(self.success_label)

        # Очищаем поле ввода
        self.ids.operation.text = ""
if __name__ == "__main__":
    init_db()
    MainApp().run()
