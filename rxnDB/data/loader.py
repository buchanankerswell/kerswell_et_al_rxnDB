import numpy as np
import pandas as pd
from rxnDB.utils import app_dir

def load_data(filename: str="rxns.csv") -> pd.DataFrame:
    """
    Loads the data from a CSV file located in the 'data' directory of the application.

    This function reads a CSV file containing reaction data and returns it as a
    pandas DataFrame.  The file is expected to be located in the 'data' subdirectory
    within the application directory.

    Args:
        filename (str, optional): The name of the CSV file to load. Defaults to "rxns.csv".

    Returns:
        pd.DataFrame: The loaded data as a pandas DataFrame.

    Raises:
        FileNotFoundError: If the specified file is not found in the 'data' directory.
    """
    # Construct the full file path for the data file
    filepath: Path = app_dir / "data" / filename

    # Check if the file exists, and raise an error if not
    if not filepath.exists():
        raise FileNotFoundError(f"File {filepath} not found!")

    return pd.read_csv(filepath)

def filter_data(df: pd.DataFrame, reactants: list[str], products: list[str],
                ignore_rxn_ids: list[int]=[45, 73, 74]):
    """
    Filter the dataframe based on the given reactants, products, and exclusion of
    specific reaction IDs. Also, filters out rows where 'b' is NaN.

    This function applies several filters to the input dataframe, including filtering
    by reactant and product phases, excluding specific reaction IDs, and removing rows
    with NaN values in the 'b' column. It also generates a polynomial representation
    of the reactions for each row.

    Args:
        df (pd.DataFrame): The input DataFrame containing reaction data.
        reactants (list[str]): A list of reactants to filter by.
        products (list[str]): A list of products to filter by.
        ignore_rxn_ids (list[int], optional): A list of reaction IDs to exclude from the
                                              results. Defaults to [45, 73, 74].

    Returns:
        pd.DataFrame: The filtered DataFrame with a 'polynomial' column added.
    """
    # Create a mask for the reactants
    reactant_mask: pd.Series = (
        df["reactant1"].isin(reactants) |
        df["reactant2"].isin(reactants) |
        df["reactant3"].isin(reactants)
    )

    # Create a mask for the products
    product_mask: pd.Series = (
        df["product1"].isin(products) |
        df["product2"].isin(products) |
        df["product3"].isin(products)
    )

    equal_range_mask: pd.Series = (df["pmin"] != df["pmax"]) & (df["tmin"] != df["tmax"])

    # Apply the reactant and product filters to the dataframe
    df_filtered: pd.DataFrame = df[reactant_mask & product_mask & equal_range_mask].copy()

    # Exclude specific reaction IDs
    df_filtered = df_filtered[~df_filtered["id"].isin(ignore_rxn_ids)]

    # Exclude rows where 'b' is NaN
    df_filtered = df_filtered[df_filtered["b"].notna()]

    # Terms for creating the polynomial
    terms: list[str] = ["t1", "t2", "t3", "t4", "b"]

    def create_poly(row: pd.Series) -> str:
        """
        Creates a polynomial string for the given row.
        """
        poly_parts: list[str] = []
        for i, term in enumerate(terms):
            if term in df_filtered.columns and pd.notna(row[term]):
                if term != "b":
                    if i == 0:
                        poly_parts.append(f"{row[term]}x")
                    else:
                        poly_parts.append(f"{row[term]}x^{i+1}")
                else:
                    poly_parts.append(f"{row[term]}")
        return "y = " + " + ".join(poly_parts) if poly_parts else "y = 0"

    # Create the polynomial for each row
    df_filtered["polynomial"] = df_filtered.apply(create_poly, axis=1)

    return df_filtered

def get_unique_phases(df: pd.DataFrame) -> list[str]:
    """
    Get a sorted list of unique chemical phases (reactants + products)
    from the given dataframe.

    This function extracts the unique chemical phases from the reactant and product columns
    of the input DataFrame, removes any duplicates, and returns the sorted list of phases.

    Args:
        df (pd.DataFrame): The input DataFrame containing reaction data.

    Returns:
        list[str]: A sorted list of unique chemical phases.
    """
    # Combine reactants, ensuring each unique phase is captured
    reacts: list[str] = pd.concat(
        [df["reactant1"], df["reactant2"], df["reactant3"]]).unique().tolist()

    # Combine products, ensuring each unique phase is captured
    prods: list[str] = pd.concat(
        [df["product1"], df["product2"], df["product3"]]).unique().tolist()

    # Combine the reactant and product phases and remove duplicates
    all_phases: list[str] = list(set(reacts + prods))

    # Filter out any NaN values
    all_phases = [compound for compound in all_phases if pd.notna(compound)]

    # Sort the phases alphabetically
    all_phases.sort()

    # Remove "Triple Point" phase from the list
    all_phases = [c for c in all_phases if c != "Triple Point"]

    return all_phases

def get_reaction_line_and_midpoint_dfs(df: pd.DataFrame, nsteps: int=1000) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calculate the reaction curves and midpoints for each row in the DataFrame.

    This function computes reaction curves by calculating pressure as a function of
    temperature using the polynomial terms for each reaction in the input DataFrame. It
    also calculates the midpoints for each reaction and returns two DataFrames: one with
    the reaction curves and another with the midpoints.

    Args:
        df (pd.DataFrame): The input DataFrame containing reaction data.
        nsteps (int, optional): The number of temperature steps to calculate.
                                Defaults to 1000.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: A tuple containing two DataFrames: one with the
        reaction curves and another with the midpoints for each reaction.
    """
    # Initialize lists to store reaction curve data and midpoints
    rxn_curves: list[dict] = []
    midpoints: list[dict] = []

    # Iterate through each row in the DataFrame to calculate the reaction curves and midpoints
    for _, row in df.iterrows():
        # Generate a range of temperatures between tmin and tmax
        Ts: np.array = np.linspace(row["tmin"], row["tmax"], int(nsteps))

        # Initialize pressure as the base value from column 'b'
        Ps: np.ndarray = np.full_like(Ts, row["b"])

        # Terms to use in the polynomial equation for calculating pressure
        terms: list[str] = ["t1", "t2", "t3", "t4"]

        # Calculate the pressure for each temperature step using the polynomial terms
        for i, term in enumerate(terms, start=1):
            t: float = row[term]
            if pd.notna(t):
                Ps += t * Ts**i

        # Append the calculated reaction curve points to rxn_curves list
        for t, p in zip(Ts, Ps):
            rxn_curves.append({"T (˚C)": t, "P (GPa)": p, "Rxn": row["rxn"],
                               "id": row["id"]})

        # Calculate the midpoint for the temperature and pressure
        midpoint_T: float = np.mean(Ts)
        midpoint_P: float = row["b"]
        for i, term in enumerate(terms, start=1):
            t: float = row[term]
            if pd.notna(t):
                midpoint_P += t * midpoint_T**i

        # Append the midpoint values to midpoints list
        midpoints.append({"T (˚C)": midpoint_T, "P (GPa)": midpoint_P, "Rxn": row["rxn"],
                         "id": row["id"]})

    # Convert lists to DataFrames and add rxn id column
    plot_df: pd.DataFrame = pd.DataFrame(rxn_curves)
    if not plot_df.empty:
        plot_df["id"] = pd.Categorical(plot_df["id"])

    mp_df: pd.DataFrame = pd.DataFrame(midpoints)
    if not mp_df.empty:
        mp_df["id"] = pd.Categorical(mp_df["id"])

    return plot_df, mp_df

data: pd.DataFrame = load_data()
phases: list[str] = get_unique_phases(data)

