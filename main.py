__version__ = "1.0"

# Импорт экранов/виджетов/графиков нужен для регистрации классов в Kivy Factory.
from app import MainApp
from charts import PieAnimatedChart, PieChart  # noqa: F401
from config import configure_window
from db import init_db
from screens import (  # noqa: F401
    AddCategoryScreen,
    CategoryScreen,
    HistoryScreen,
    MainScreen,
    OperationDetailScreen,
    OperationScreen,
    RecordScreen,
)
from ui_widgets import CategoriesWidget, CategoryButton, RootWidget  # noqa: F401


if __name__ == "__main__":
    configure_window()
    init_db()
    MainApp().run()
