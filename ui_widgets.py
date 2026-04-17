from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.uix.floatlayout import FloatLayout
from kivy.utils import get_color_from_hex as HEX

from db import get_categories


class CategoriesWidget(FloatLayout):
    output = ListProperty([])

    def on_output(self, instance, value):
        rv = self.ids.get("rv")
        if not rv:
            return
        rv.data = [
            {"text": f"{cid}. {name}", "category_id": cid, "bg_color": HEX(color)}
            for cid, name, color in get_categories()
        ]

    @staticmethod
    def _pluralize_category(count):
        if 11 <= count % 100 <= 14:
            return "категорий"
        last = count % 10
        if last == 1:
            return "категория"
        if last in (2, 3, 4):
            return "категории"
        return "категорий"

    def show_categories(self):
        rows = get_categories()
        info = self.ids.get("info_label")
        if info:
            if len(rows) == 0:
                info.text = "У вас нет категорий"
            else:
                count = len(rows)
                info.text = f"У вас {count} {self._pluralize_category(count)}"

        data = [
            {"text": f"{i + 1}. {name}", "category_id": cid, "bg_color": HEX(color_hex)}
            for i, (cid, name, color_hex) in enumerate(rows)
        ]

        rv = self.ids.get("rv")
        if rv:
            rv.data = data
        else:
            self.output = [f"{i + 1}. {name}" for i, (_, name, _) in enumerate(rows)]


class CategoryButton(FloatLayout):
    category_id = NumericProperty(0)
    text = StringProperty("")
    bg_color = ListProperty([0, 0, 0, 1])


class RootWidget(FloatLayout):
    pass
