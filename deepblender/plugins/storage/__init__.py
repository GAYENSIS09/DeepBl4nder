"""Storage plugins : stockage, Git, cache Redis."""

from deepblender.plugins.storage.storage import StoragePlugin
from deepblender.plugins.storage.git import GitPlugin
from deepblender.plugins.storage.cache import CachePlugin

__all__ = ["StoragePlugin", "GitPlugin", "CachePlugin"]
