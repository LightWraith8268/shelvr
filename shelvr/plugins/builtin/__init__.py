"""Built-in plugins shipped with Shelvr.

Each subdirectory is a plugin package with a plugin.toml and __init__.py
defining a Plugin subclass. The app factory discovers them alongside any
user-installed plugins under settings.plugin_dir.
"""

from __future__ import annotations
