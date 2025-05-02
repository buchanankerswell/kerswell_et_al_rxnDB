#######################################################
## .0.              Load Libraries               !!! ##
#######################################################
import re
from dataclasses import dataclass, field

import pandas as pd


#######################################################
## .1.                   RxnDB                   !!! ##
#######################################################
@dataclass
class RxnDBProcessor:
    df: pd.DataFrame
    allow_empty: bool = False
    _original_df: pd.DataFrame = field(init=False, repr=False)
    _reactant_lookup: dict[str, set[str]] = field(init=False, repr=False)
    _product_lookup: dict[str, set[str]] = field(init=False, repr=False)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __post_init__(self):
        """Initialize the processor and validate the DataFrame."""
        if not isinstance(self.df, pd.DataFrame):
            raise TypeError("Input 'df' must be a pandas DataFrame.")
        if not self.allow_empty and self.df.empty:
            raise ValueError("RxnDB dataframe cannot be empty unless allow_empty=True")

        required_cols = ["id", "reactants", "products", "type", "rxn", "ref"]
        missing = [col for col in required_cols if col not in self.df.columns]

        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Store original data reference (no copy needed)
        self._original_df = self.df

        # Pre-compute phase information for faster filtering
        self._precompute_phase_info()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _precompute_phase_info(self):
        """Pre-compute phase information for faster filtering."""
        self._reactant_lookup = {}
        self._product_lookup = {}

        self.df["reactants"] = self.df["reactants"].apply(
            lambda x: x if isinstance(x, list) else []
        )
        self.df["products"] = self.df["products"].apply(
            lambda x: x if isinstance(x, list) else []
        )

        for _, row in self.df.iterrows():
            rxn_id = row["id"]

            # Add to reactant lookup
            for reactant in row["reactants"]:
                if pd.notna(reactant) and isinstance(reactant, str):
                    clean_reactant = self.strip_coefficients([reactant])[0]
                    if clean_reactant:
                        if clean_reactant not in self._reactant_lookup:
                            self._reactant_lookup[clean_reactant] = set()
                        self._reactant_lookup[clean_reactant].add(rxn_id)

            # Add to product lookup
            for product in row["products"]:
                if pd.notna(product) and isinstance(product, str):
                    clean_product = self.strip_coefficients([product])[0]
                    if clean_product:
                        if clean_product not in self._product_lookup:
                            self._product_lookup[clean_product] = set()
                        self._product_lookup[clean_product].add(rxn_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def filter_by_ids(self, ids: list[str]) -> pd.DataFrame:
        """Filter dataframe by reaction IDs."""
        if not ids:
            return self._original_df

        return self._original_df[self._original_df["id"].isin(ids)]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _get_ids_for_phases(
        self, phases: list[str], lookup: dict[str, set[str]]
    ) -> set[str]:
        """Helper to get all unique IDs matching any phase in the list."""
        if not phases:
            return set()

        matching_ids = set()
        for phase in phases:
            matching_ids.update(lookup.get(phase, set()))

        return matching_ids

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def filter_by_reactants(self, phases: list[str]) -> pd.DataFrame:
        """Filter dataframe by reactant phases (union logic)."""
        if not phases:
            return self._original_df

        matching_ids = self._get_ids_for_phases(phases, self._reactant_lookup)

        if not matching_ids:
            return pd.DataFrame(columns=self._original_df.columns)

        return self._original_df[self._original_df["id"].isin(matching_ids)]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def filter_by_products(self, phases: list[str]) -> pd.DataFrame:
        """Filter dataframe by product phases (union logic)."""
        if not phases:
            return self._original_df

        matching_ids = self._get_ids_for_phases(phases, self._product_lookup)

        if not matching_ids:
            return pd.DataFrame(columns=self._original_df.columns)

        return self._original_df[self._original_df["id"].isin(matching_ids)]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def filter_by_reactants_and_products(
        self, reactants: list[str], products: list[str]
    ) -> pd.DataFrame:
        """
        Filter by reactants and/or products.
        - If both reactants and products are provided, returns reactions matching BOTH criteria (intersection of IDs).
        - If only reactants are provided, returns reactions matching ANY of the reactants (union).
        - If only products are provided, returns reactions matching ANY of the products (union).
        - If neither is provided, returns the original dataframe.
        """
        if not reactants and not products:
            return self._original_df

        if reactants and not products:
            return self.filter_by_reactants(reactants)

        if not reactants and products:
            return self.filter_by_products(products)

        if reactants and products:
            reactant_ids = self._get_ids_for_phases(reactants, self._reactant_lookup)

            if not reactant_ids:
                return pd.DataFrame(columns=self._original_df.columns)

            product_ids = self._get_ids_for_phases(products, self._product_lookup)

            if not product_ids:
                return pd.DataFrame(columns=self._original_df.columns)

            matching_ids = reactant_ids.intersection(product_ids)

            if not matching_ids:
                return pd.DataFrame(columns=self._original_df.columns)

            return self._original_df[self._original_df["id"].isin(matching_ids)]

        return pd.DataFrame(columns=self._original_df.columns)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def filter_by_type(self, types: list[str]) -> pd.DataFrame:
        """Filter by specific types of data."""
        if not types:
            return self._original_df

        return self._original_df[self._original_df["type"].isin(types)]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def strip_coefficients(phases: list[str]) -> list[str]:
        """Remove leading coefficients (e.g., '2H2O' -> 'H2O') from phase names."""
        cleaned = []

        for phase in phases:
            if isinstance(phase, str):
                cleaned.append(re.sub(r"^\d+\s*", "", phase).strip())

        return [p for p in cleaned if p]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_unique_phases(self) -> list[str]:
        """Get a sorted list of unique phase names from reactants and products."""
        all_phases = set(self._reactant_lookup.keys()) | set(
            self._product_lookup.keys()
        )

        return sorted(list(all_phases))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_phases_for_ids(self, ids: list[str]) -> tuple[list[str], list[str]]:
        """Get unique reactants and products associated with a list of reaction IDs."""
        if not ids:
            return [], []

        subset_df = self._original_df[self._original_df["id"].isin(ids)]

        all_reactants = subset_df["reactants"].explode().dropna().unique().tolist()
        all_products = subset_df["products"].explode().dropna().unique().tolist()

        unique_reactants = sorted(list(set(self.strip_coefficients(all_reactants))))
        unique_products = sorted(list(set(self.strip_coefficients(all_products))))

        return unique_reactants, unique_products


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def main():
    """"""
    from rxnDB.data.loader import RxnDBLoader
    from rxnDB.utils import app_dir

    data_path = app_dir / "data" / "cache" / "rxnDB.parquet"
    rxnDB: pd.DataFrame = RxnDBLoader.load_parquet(data_path)
    processor: RxnDBProcessor = RxnDBProcessor(rxnDB)

    print("Original DF:")
    print(processor._original_df)
    print("\nUnique Phases:", processor.get_unique_phases())

    print("\nFilter ky as reactant:")
    print(processor.filter_by_reactants(["ky"]))

    print("\nFilter sil as product:")
    print(processor.filter_by_products(["sil"]))

    print("\nFilter ky as reactant AND and as product:")
    print(processor.filter_by_reactants_and_products(["ky"], ["and"]))

    print("\nFilter ky OR and as reactant:")
    print(processor.filter_by_reactants_and_products(["ky", "and"], []))

    print("\nFilter H2O as reactant:")
    print(processor.filter_by_reactants(["H2O"]))

    print("\nGet phases for R1, R4:")
    reacts, prods = processor.get_phases_for_ids(
        ["jimmy-001", "jimmy-005", "jimmy-047", "jimmy-027"]
    )
    print(f"Reactants: {reacts}, Products: {prods}")


if __name__ == "__main__":
    main()
