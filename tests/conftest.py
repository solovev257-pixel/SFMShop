"""Автотесты используют тестовые настройки и не читают локальный .env."""
import os

os.environ["SFMShop_ENV_FILE"] = ""
