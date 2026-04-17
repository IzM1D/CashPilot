from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import FadeTransition, SlideTransition

from db import delete_category_from_db, get_db
from screens import RecordScreen
from ui_widgets import RootWidget


class MainApp(App):
    last_transition = "down"
    mode = "record"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.last_entry_point = None

    def build(self):
        Builder.load_file("main.kv")
        return RootWidget()

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
        screen.ids.category_widget.show_categories()

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
        self.root.ids.sm.get_screen("history").load_history()
