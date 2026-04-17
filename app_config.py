from kivy.config import Config

Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '800')
Config.write()

DB_NAME = "data.db"

CATEGORY_COLORS = [
    "#9AA0A6", "#1F1F1F",
    "#7A4A2E", "#D64545", "#E67E22", "#F1C40F",
    "#A3CB38", "#2ECC71", "#48C9B0",
    "#3498DB", "#8E44AD", "#C0398E",
]
