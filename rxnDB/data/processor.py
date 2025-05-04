#######################################################
## .0. Load Libraries                            !!! ##
#######################################################
from dataclasses import dataclass, field

import pandas as pd
import plotly.express as px


#######################################################
## .1. RxnDBProcessor                            !!! ##
#######################################################
@dataclass
class RxnDBProcessor:
    df: pd.DataFrame
    allow_empty: bool = False
    color_palette: str = "Alphabet"
    _original_df: pd.DataFrame = field(init=False, repr=False)
    _reactant_lookup: dict[str, set[str]] = field(init=False, repr=False)
    _product_lookup: dict[str, set[str]] = field(init=False, repr=False)
    _rxn_groups: dict[str, int] = field(init=False, repr=False, default_factory=dict)
    _color_map: dict[str, str] = field(init=False, repr=False, default_factory=dict)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __post_init__(self) -> None:
        """Initialize the processor and validate the DataFrame."""
        if not isinstance(self.df, pd.DataFrame):
            raise TypeError("Input 'df' must be a pandas DataFrame.")
        if not self.allow_empty and self.df.empty:
            raise ValueError("RxnDB dataframe cannot be empty unless allow_empty=True")

        required_cols = [
            "id",
            "reactants",
            "products",
            "type",
            "plot_type",
            "rxn",
            "ref",
        ]
        missing = [col for col in required_cols if col not in self.df.columns]

        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        self._original_df = self.df

        self._precompute_phase_info()
        self._build_color_map()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _precompute_phase_info(self) -> None:
        """Pre-compute phase information for faster filtering."""
        self._reactant_lookup = {}
        self._product_lookup = {}

        for _, row in self.df.iterrows():
            rxn_id = row["id"]

            # Add to reactant lookup
            for reactant in row["reactants"]:
                if pd.notna(reactant) and isinstance(reactant, str):
                    if reactant not in self._reactant_lookup:
                        self._reactant_lookup[reactant] = set()
                    self._reactant_lookup[reactant].add(rxn_id)

            # Add to product lookup
            for product in row["products"]:
                if pd.notna(product) and isinstance(product, str):
                    if product not in self._product_lookup:
                        self._product_lookup[product] = set()
                    self._product_lookup[product].add(rxn_id)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _build_rxn_groups(self, method: str = "or"):
        """
        Group reactions based on shared reactants AND products.
        Assigns each reaction ID to a group number.
        """
        self._rxn_groups = {}
        group_counter = 0
        processed_ids = set()

        for rxn_id in self._original_df["id"].unique():
            if rxn_id in processed_ids:
                continue

            row = self._original_df[self._original_df["id"] == rxn_id].iloc[0]
            reactants = row.get("reactants", [])
            products = row.get("products", [])

            if not isinstance(reactants, list) or not isinstance(products, list):
                continue

            if not reactants or not products:
                continue

            # Forward direction
            f_reactant_ids = self._get_ids_for_phases(reactants, self._reactant_lookup)
            f_product_ids = self._get_ids_for_phases(products, self._product_lookup)

            # Reverse direction
            r_reactant_ids = self._get_ids_for_phases(reactants, self._product_lookup)
            r_product_ids = self._get_ids_for_phases(products, self._reactant_lookup)

            if method == "and":
                matching_ids = f_reactant_ids.intersection(f_product_ids).union(
                    r_reactant_ids.intersection(r_product_ids)
                )
            else:  # "or"
                matching_ids = f_reactant_ids.union(f_product_ids).union(
                    r_reactant_ids.union(r_product_ids)
                )

            if matching_ids:
                for match_id in matching_ids:
                    self._rxn_groups[match_id] = group_counter
                    processed_ids.add(match_id)
                self._rxn_groups[rxn_id] = group_counter
                processed_ids.add(rxn_id)
                group_counter += 1

        for rxn_id in self._original_df["id"].unique():
            if rxn_id not in processed_ids:
                self._rxn_groups[rxn_id] = group_counter
                group_counter += 1

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _build_color_map(self):
        """
        Build a color map for reaction groups.
        Assigns a color to each unique group number.
        """
        # Build reaction groups first if they don't exist
        if not self._rxn_groups:
            self._build_rxn_groups()

        # Get unique group numbers
        unique_groups = set(self._rxn_groups.values())

        # Get color palette
        palette = self._get_color_palette()

        # Assign colors to groups
        self._color_map = {
            str(group): palette[i % len(palette)]
            for i, group in enumerate(sorted(unique_groups))
        }
        print(self._color_map)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _get_color_palette(self) -> list[str]:
        """Get a color palette based on the specified name."""
        if self.color_palette in dir(px.colors.qualitative):
            return getattr(px.colors.qualitative, self.color_palette)
        elif self.color_palette.lower() in px.colors.named_colorscales():
            return [color[1] for color in px.colors.get_colorscale(self.color_palette)]
        else:
            print(
                f"'{self.color_palette}' is not a valid palette, using default 'Set1'."
            )
            return px.colors.qualitative.Set1

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_color_for_reaction(self, reaction_id: str) -> str:
        """
        Get the color for a specific reaction ID.
        Returns black (#000000) as fallback if no color is found.
        """
        if reaction_id not in self._rxn_groups:
            return "#000000"

        group = self._rxn_groups[reaction_id]
        return self._color_map.get(str(group), "#000000")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_colors_for_filtered_df(self, filtered_df: pd.DataFrame) -> pd.DataFrame:
        """
        Add color information to a filtered dataframe.
        Returns a copy of the dataframe with 'rxn_color_key' column added.
        """
        df_copy = filtered_df.copy()

        # Add group column for debugging/reference
        df_copy["rxn_group"] = df_copy["id"].map(lambda x: self._rxn_groups.get(x, -1))

        # Add color column
        df_copy["rxn_color_key"] = df_copy["id"].map(
            lambda x: self.get_color_for_reaction(x)
        )

        return df_copy

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
        self, reactants: list[str], products: list[str], method: str = "and"
    ) -> pd.DataFrame:
        """
        Filter by reactants and/or products.
        - If both reactants and products are provided, returns reactions matching criteria (intersection or union).
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
            # Forward direction
            f_reactant_ids = self._get_ids_for_phases(reactants, self._reactant_lookup)
            f_product_ids = self._get_ids_for_phases(products, self._product_lookup)

            # Reverse direction (reactants <=> products)
            r_reactant_ids = self._get_ids_for_phases(reactants, self._product_lookup)
            r_product_ids = self._get_ids_for_phases(products, self._reactant_lookup)

            if not f_reactant_ids:
                return pd.DataFrame(columns=self._original_df.columns)

            if not f_product_ids:
                return pd.DataFrame(columns=self._original_df.columns)

            if method == "and":
                matching_ids = f_reactant_ids.intersection(f_product_ids).union(
                    r_reactant_ids.intersection(r_product_ids)
                )
            else:  # "or"
                matching_ids = (
                    f_reactant_ids.union(f_product_ids)
                    .union(r_reactant_ids)
                    .union(r_product_ids)
                )

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

        unique_reactants = sorted(list(set(all_reactants)))
        unique_products = sorted(list(set(all_products)))

        return unique_reactants, unique_products


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def main():
    """"""
    from rxnDB.data.loader import RxnDBLoader
    from rxnDB.utils import app_dir

    filepath = app_dir / "data" / "cache" / "rxnDB.parquet"
    rxnDB: pd.DataFrame = RxnDBLoader.load_parquet(filepath)
    processor: RxnDBProcessor = RxnDBProcessor(rxnDB)
    all_phases = processor.get_unique_phases()
    print(all_phases)


if __name__ == "__main__":
    main()
