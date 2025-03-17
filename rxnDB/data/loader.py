import pandas as pd
from pathlib import Path

# Define the app directory 'rxnDB/'
app_dir = Path(__file__).resolve().parent.parent

def load_data(filename="rxns.csv"):
    """
    """
    filepath = app_dir / "data" / filename
    if not filepath.exists():
        raise FileNotFoundError(f"File {filepath} not found!")

    return pd.read_csv(filepath)
