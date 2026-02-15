"""
UI entrypoint.

This file intentionally stays tiny:
- It imports the Flask app factory.
- It starts the dev server.

All actual route logic lives in ui/routes/.
"""

from .ui_app.factory import create_app

app = create_app()

if __name__ == "__main__":
    # Dev run only. For cluster usage we already do port forwarding.
    app.run(host="127.0.0.1", port=5002, debug=True)
