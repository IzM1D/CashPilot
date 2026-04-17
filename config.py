from kivy.config import Config

APP_VERSION = "1.0"
DB_NAME = "data.db"

CATEGORY_COLORS = [
    "#9AA0A6", "#1F1F1F",
    "#7A4A2E", "#D64545", "#E67E22", "#F1C40F",
    "#A3CB38", "#2ECC71", "#48C9B0",
    "#3498DB", "#8E44AD", "#C0398E",
]


def configure_window(width: int = 360, height: int = 800) -> None:
    Config.set("graphics", "width", str(width))
    Config.set("graphics", "height", str(height))
    Config.write()
