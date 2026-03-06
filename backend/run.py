"""MindEase PRO — Application Entry Point"""
import os
import sys

# Disable TensorFlow / Flax backends in transformers to avoid Keras 3 conflicts.
# Must be set before any transformers import occurs.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("USE_FLAX", "0")
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

# Ensure backend directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, socketio
from config import Config

app = create_app()

if __name__ == "__main__":
    config = Config()
    # Use stdout with UTF-8 to avoid Windows cp1252 emoji encoding errors
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print(f"[MindEase PRO] v{config.VERSION} starting on port {config.PORT}...")
    print("   Loading AI models (this may take a minute on first run)...")
    socketio.run(
        app,
        host="0.0.0.0",
        port=config.PORT,
        debug=config.DEBUG,
        use_reloader=False,
        log_output=True,
    )
