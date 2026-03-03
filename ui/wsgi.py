# optional production entrypoint
# ui/wsgi.py
from ui.ui_app.factory import create_app

app = create_app()
