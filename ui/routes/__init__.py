"""
Blueprint registration.

This module exposes one function `register_blueprints(app)` that keeps
all blueprint wiring in one place.
"""

from __future__ import annotations

from flask import Flask, render_template

from .graph_routes import graph_bp
from .pipeline_routes import pipeline_bp
# from .verify_routes import verify_bp

def register_blueprints(app: Flask) -> None:
    """
    Register all UI Blueprints on the Flask app.

    Parameters
    ----------
    app:
        Flask application instance.
    """
    @app.route('/')
    def index():
        return render_template('index.html')
    
    app.register_blueprint(graph_bp, url_prefix="/api/graph")
    app.register_blueprint(pipeline_bp, url_prefix="/api/pipeline")
    # app.register_blueprint(verify_bp)
