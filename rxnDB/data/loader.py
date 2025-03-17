import pandas as pd

def load_data(filepath):
    """Load CSV data into a pandas DataFrame."""
    return pd.read_csv(filepath)
