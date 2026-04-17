__version__ = '1.0'

# Важно: импорты ниже регистрируют все custom-классы для main.kv.
import app_config  # noqa: F401
from app import MainApp
from chart_widgets import PieAnimatedChart, PieChart  # noqa: F401
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
    init_db()
    MainApp().run()
