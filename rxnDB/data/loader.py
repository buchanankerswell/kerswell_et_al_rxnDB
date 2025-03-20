#######################################################
## .0.              Load Libraries               !!! ##
#######################################################
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Utilities !!
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import numpy as np
import pandas as pd
from rxnDB.utils import app_dir

#######################################################
## .1.                  rxnDB                    !!! ##
#######################################################
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def load_data(filename: str="rxns.csv") -> pd.DataFrame:
    """
    Loads rxnDB from csv file
    """
    filepath: Path = app_dir / "data" / filename
    if not filepath.exists():
        raise FileNotFoundError(f"File {filepath} not found!")

    return pd.read_csv(filepath)

#######################################################
## .2.             Helper Functions              !!! ##
#######################################################
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def filter_data_by_ids(df: pd.DataFrame, ids: list[int],
                       ignore_rxn_ids: list[int]=[45, 73, 74]) -> pd.DataFrame:
    """
    Filter the database by rxn ids
    """
    id_mask: pd.Series = (df["id"].isin(ids))
    df_filtered: pd.DataFrame = df[id_mask].copy()
    df_filtered = df_filtered[~df_filtered["id"].isin(ignore_rxn_ids)]
    df_filtered = df_filtered[df_filtered["b"].notna()]

    terms: list[str] = ["t1", "t2", "t3", "t4", "b"]
    def create_poly(row: pd.Series) -> str:
        """
        Creates a polynomial string
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

    df_filtered["polynomial"] = df_filtered.apply(create_poly, axis=1)

    return df_filtered

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def filter_data_by_rxn(df: pd.DataFrame, reactants: list[str], products: list[str],
                       ignore_rxn_ids: list[int]=[45, 73, 74]):
    """
    Filter the database by reactants and products
    """
    reactant_mask: pd.Series = (
        df["reactant1"].isin(reactants) |
        df["reactant2"].isin(reactants) |
        df["reactant3"].isin(reactants)
    )
    product_mask: pd.Series = (
        df["product1"].isin(products) |
        df["product2"].isin(products) |
        df["product3"].isin(products)
    )
    equal_range_mask: pd.Series = (df["pmin"] != df["pmax"]) & (df["tmin"] != df["tmax"])
    df_filtered: pd.DataFrame = df[reactant_mask & product_mask & equal_range_mask].copy()
    df_filtered = df_filtered[~df_filtered["id"].isin(ignore_rxn_ids)]
    df_filtered = df_filtered[df_filtered["b"].notna()]

    terms: list[str] = ["t1", "t2", "t3", "t4", "b"]
    def create_poly(row: pd.Series) -> str:
        """
        Creates a polynomial string
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

    df_filtered["polynomial"] = df_filtered.apply(create_poly, axis=1)

    return df_filtered

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def get_unique_phases(df: pd.DataFrame) -> list[str]:
    """
    Get a sorted list of unique phases
    """
    reactants: list[str] = pd.concat(
        [df["reactant1"], df["reactant2"], df["reactant3"]]
    ).unique().tolist()

    products: list[str] = pd.concat(
        [df["product1"], df["product2"], df["product3"]]
    ).unique().tolist()

    all_phases: list[str] = list(set(reactants + products))
    all_phases = [compound for compound in all_phases if pd.notna(compound)]
    all_phases.sort()
    all_phases = [c for c in all_phases if c != "Triple Point"]

    return all_phases

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def calculate_reaction_curves(df: pd.DataFrame, nsteps: int=1000) -> pd.DataFrame:
    """
    Calculate reaction curves
    """
    rxn_curves: list[dict] = []

    # Iterate through each row in the DataFrame to calculate the reaction curves
    for _, row in df.iterrows():
        Ts: np.array = np.linspace(row["tmin"], row["tmax"], int(nsteps))
        Ps: np.ndarray = np.full_like(Ts, row["b"])

        terms: list[str] = ["t1", "t2", "t3", "t4"]
        for i, term in enumerate(terms, start=1):
            t: float = row[term]
            if pd.notna(t):
                Ps += t * Ts**i

        for t, p in zip(Ts, Ps):
            rxn_curves.append({"T (˚C)": t, "P (GPa)": p, "Rxn": row["rxn"],
                               "id": row["id"]})

    plot_df: pd.DataFrame = pd.DataFrame(rxn_curves)
    if not plot_df.empty:
        plot_df["id"] = pd.Categorical(plot_df["id"])

    return plot_df

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def calculate_midpoints(df: pd.DataFrame, nsteps: int=1000) -> pd.DataFrame:
    """
    Calculate the reaction curve midpoints
    """
    midpoints: list[dict] = []

    # Iterate through each row in the DataFrame to calculate the midpoints
    for _, row in df.iterrows():
        Ts: np.array = np.linspace(row["tmin"], row["tmax"], int(nsteps))
        midpoint_P: float = row["b"]
        terms: list[str] = ["t1", "t2", "t3", "t4"]
        midpoint_T: float = np.mean(Ts)

        for i, term in enumerate(terms, start=1):
            t: float = row[term]
            if pd.notna(t):
                midpoint_P += t * midpoint_T**i

        midpoints.append({"T (˚C)": midpoint_T, "P (GPa)": midpoint_P, "Rxn": row["rxn"],
                         "id": row["id"]})

    mp_df: pd.DataFrame = pd.DataFrame(midpoints)
    if not mp_df.empty:
        mp_df["id"] = pd.Categorical(mp_df["id"])

    return mp_df

#######################################################
## .3.            Module Attributes              !!! ##
#######################################################
data: pd.DataFrame = load_data()
phases: list[str] = get_unique_phases(data)
