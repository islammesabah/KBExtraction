"""
Flask application factory.

Why an app factory?
-------------------
- Keeps global state minimal.
- Enables clean modular route registration via Blueprints.
- Makes testing easier (create_app(test_config=...)).
"""

from __future__ import annotations

from pathlib import Path
from flask import Flask
from dotenv import load_dotenv

# from ui.routes import register_blueprints
from ..routes import register_blueprints

def create_app() -> Flask:
    """
    Create and configure the Flask application.

    Returns
    -------
    Flask
        Configured Flask app instance.2dq 
    """
    # Load .env once at startup (repo root)
    REPO_ROOT = Path(__file__).resolve().parents[2]
    # parents[2] because: ui/ui_app/factory.py → go up to ui/ (1) → repo root (2)
    env_path = REPO_ROOT / ".env"
    load_dotenv(dotenv_path=env_path)

    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )

    # Register modular routes (Blueprints)
    register_blueprints(app)

    return app