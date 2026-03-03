"""MindEase PRO — Application Entry Point"""
import os
import sys

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, socketio
from config import Config

app = create_app()

if __name__ == "__main__":
    config = Config()
    print(f"🧠 MindEase PRO v{config.VERSION} starting on port {config.PORT}...")
    print("   Loading AI models (this may take a minute on first run)...")
    socketio.run(
        app,
        host="0.0.0.0",
        port=config.PORT,
        debug=config.DEBUG,
        use_reloader=False,
        log_output=True,
    )
