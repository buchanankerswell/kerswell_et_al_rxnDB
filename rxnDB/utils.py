import logging
from pathlib import Path

app_dir: Path = Path(__file__).resolve().parent

def setup_logging():
    """
    """
    logging.basicConfig(level=logging.INFO)
