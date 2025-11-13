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

    def show_categories(self):
        rows = get_categories()
        self.output = [f"{cid}. {name}" for cid, name in rows]


# --- Приложение Kivy ---
class MainApp(App):
    last_transition = "up"  # по умолчанию

    def build(self):
        return RootWidget()

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
    pass

class RecordScreen(Screen):
    def send_text(self):
        text = self.ids.operation.text

if __name__ == "__main__":
    init_db()
    MainApp().run()
