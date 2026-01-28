from src.config import settings

__version__ = settings.app.version
__app_name__ = settings.app.app_name

__all__ = [
    "__version__",
    "__app_name__",
    "settings",
]
