"""Web application package for Glassbox."""

from glassbox.web.app import create_app
from glassbox.web.server import run_server

__all__ = ["create_app", "run_server"]
