#######################################################
## .0. Load Libraries                            !!! ##
#######################################################
from dataclasses import dataclass, field

import pandas as pd
import plotly.express as px

from rxnDB.data.mapping import MINERAL_ABBREV_MAP as MAP


#######################################################
## .1. RxnDBProcessor                            !!! ##
#######################################################
@dataclass
class RxnDBProcessor:
    df: pd.DataFrame
    allow_empty: bool = False
    color_palette: str = "Alphabet"
    _original_df: pd.DataFrame = field(init=False, repr=False)
    _uid_to_reactant_abbrevs_lookup: dict[str, set[str]] = field(init=False, repr=False)
    _uid_to_product_abbrevs_lookup: dict[str, set[str]] = field(init=False, repr=False)
    _phase_name_to_abbrev_lookup: dict[str, set[str]] = field(init=False, repr=False)
    _phase_group_to_abbrev_lookup: dict[str, set[str]] = field(init=False, repr=False)
    _phase_formula_to_abbrev_lookup: dict[str, set[str]] = field(init=False, repr=False)
    _abbrev_to_phase_name_lookup: dict[str, set[str]] = field(init=False, repr=False)
    _abbrev_to_phase_group_lookup: dict[str, set[str]] = field(init=False, repr=False)
    _abbrev_to_phase_formula_lookup: dict[str, set[str]] = field(init=False, repr=False)
    _grouped_phases_by_mode: dict[str, dict[str, set[str]]] = field(
        init=False, repr=False
    )
    _reaction_groups: dict[str, int] = field(
        init=False, repr=False, default_factory=dict
    )
    _color_map: dict[str, str] = field(init=False, repr=False, default_factory=dict)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __post_init__(self) -> None:
        """Initialize the processor and validate the DataFrame."""
        if not isinstance(self.df, pd.DataFrame):
            raise TypeError("Input 'df' must be a pandas DataFrame.")
        if not self.allow_empty and self.df.empty:
            raise ValueError("RxnDB dataframe cannot be empty unless allow_empty=True")

        required_cols = [
            "unique_id",
            "reaction",
            "reaction_names",
            "reactants",
            "reactant_names",
            "reactant_groups",
            "reactant_formulas",
            "products",
            "product_names",
            "product_groups",
            "product_formulas",
            "type",
            "units_P",
            "units_T",
            "T",
            "T_uncertainty",
            "P",
            "P_uncertainty",
            "plot_type",
            "reference",
        ]

        missing = [col for col in required_cols if col not in self.df.columns]

        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        self._original_df = self.df.copy()
        self._precompute_phase_info()
        self._build_color_map()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _precompute_phase_info(self) -> None:
        """Pre-compute phase information for faster filtering."""
        self._phase_name_to_abbrev_lookup = {}
        self._phase_group_to_abbrev_lookup = {}
        self._phase_formula_to_abbrev_lookup = {}

        self._abbrev_to_phase_name_lookup = {}
        self._abbrev_to_phase_group_lookup = {}
        self._abbrev_to_phase_formula_lookup = {}

        self._grouped_phases = {
            "abbreviation": {},
            "common name": {},
        }

        self._grouped_phases_with_formulas = {
            "abbreviation": {},
            "common name": {},
        }

        group_order = [
            "Aluminosilicates",
            "Silica minerals",
            "High-P phases",
            "Garnets & olivines",
            "Other orthosilicates",
            "Pyroxenes & pyroxenoids",
            "Amphibole",
            "Other chain silicates",
            "Feldspars & feldspathoid",
            "Other framework silicates",
            "Chlorites",
            "Micas",
            "Other sheet silicates",
            "Cyclosilicates",
            "Sorosilicates",
            "Carbonates",
            "Oxides",
            "Hydroxides",
            "Halides & sulphides",
            "Elements",
            "Gas species",
            "Melt species",
        ]
        group_rank = {name: i for i, name in enumerate(group_order)}
        self._group_rank = group_rank

        for abbrev, info in MAP.items():
            name = info["name"]
            group = info["group"]
            formula = info["formula"]

            if name not in self._phase_name_to_abbrev_lookup:
                self._phase_name_to_abbrev_lookup[name] = set()
            self._phase_name_to_abbrev_lookup[name].add(abbrev)

            if group not in self._phase_group_to_abbrev_lookup:
                self._phase_group_to_abbrev_lookup[group] = set()
            self._phase_group_to_abbrev_lookup[group].add(abbrev)

            if formula not in self._phase_formula_to_abbrev_lookup:
                self._phase_formula_to_abbrev_lookup[formula] = set()
            self._phase_formula_to_abbrev_lookup[formula].add(abbrev)

            if abbrev not in self._abbrev_to_phase_name_lookup:
                self._abbrev_to_phase_name_lookup[abbrev] = set()
            self._abbrev_to_phase_name_lookup[abbrev].add(name)

            if abbrev not in self._abbrev_to_phase_group_lookup:
                self._abbrev_to_phase_group_lookup[abbrev] = set()
            self._abbrev_to_phase_group_lookup[abbrev].add(group)

            if abbrev not in self._abbrev_to_phase_formula_lookup:
                self._abbrev_to_phase_formula_lookup[abbrev] = set()
            self._abbrev_to_phase_formula_lookup[abbrev].add(formula)

            for mode, label in {
                "abbreviation": abbrev,
                "common name": name,
            }.items():
                if group not in self._grouped_phases[mode]:
                    self._grouped_phases[mode][group] = set()
                self._grouped_phases[mode][group].add(label)

                if group not in self._grouped_phases_with_formulas[mode]:
                    self._grouped_phases_with_formulas[mode][group] = set()
                self._grouped_phases_with_formulas[mode][group].add(
                    f"{label} ({formula})"
                )

        self._uid_to_reactant_abbrevs_lookup = {}
        self._uid_to_product_abbrevs_lookup = {}

        for _, row in self._original_df.iterrows():
            uid = row["unique_id"]

            for reactant in row["reactants"]:
                if pd.notna(reactant) and isinstance(reactant, str):
                    if reactant not in self._uid_to_reactant_abbrevs_lookup:
                        self._uid_to_reactant_abbrevs_lookup[reactant] = set()
                    self._uid_to_reactant_abbrevs_lookup[reactant].add(uid)

            for product in row["products"]:
                if pd.notna(product) and isinstance(product, str):
                    if product not in self._uid_to_product_abbrevs_lookup:
                        self._uid_to_product_abbrevs_lookup[product] = set()
                    self._uid_to_product_abbrevs_lookup[product].add(uid)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def filter_by_reactants_and_product_abbrevs(
        self,
        reactant_abbrevs: list[str],
        product_abbrevs: list[str],
        method: str = "and",
    ) -> pd.DataFrame:
        """
        Filter by reactant_abbrevs and/or product_abbrevs.
        - If both reactants and products are provided, returns reactions matching criteria (intersection or union).
        - If only reactants are provided, returns reactions matching ANY of the reactants (union).
        - If only products are provided, returns reactions matching ANY of the products (union).
        - If neither is provided, returns the original dataframe.
        """
        if not reactant_abbrevs and not product_abbrevs:
            return pd.DataFrame(columns=self._original_df.columns)

        if reactant_abbrevs and not product_abbrevs:
            return self.filter_by_reactant_abbrevs(reactant_abbrevs)

        if not reactant_abbrevs and product_abbrevs:
            return self.filter_by_product_abbrevs(product_abbrevs)

        if reactant_abbrevs and product_abbrevs:
            f_reactant_ids = self.get_unique_ids_from_phase_abbrevs(
                reactant_abbrevs, self._uid_to_reactant_abbrevs_lookup
            )
            f_product_ids = self.get_unique_ids_from_phase_abbrevs(
                product_abbrevs, self._uid_to_product_abbrevs_lookup
            )

            r_reactant_ids = self.get_unique_ids_from_phase_abbrevs(
                reactant_abbrevs, self._uid_to_product_abbrevs_lookup
            )
            r_product_ids = self.get_unique_ids_from_phase_abbrevs(
                product_abbrevs, self._uid_to_reactant_abbrevs_lookup
            )

            if not f_reactant_ids:
                return pd.DataFrame(columns=self._original_df.columns)

            if not f_product_ids:
                return pd.DataFrame(columns=self._original_df.columns)

            if method == "and":
                matching_ids = f_reactant_ids.intersection(f_product_ids).union(
                    r_reactant_ids.intersection(r_product_ids)
                )
            else:
                matching_ids = (
                    f_reactant_ids.union(f_product_ids)
                    .union(r_reactant_ids)
                    .union(r_product_ids)
                )

            if not matching_ids:
                return pd.DataFrame(columns=self._original_df.columns)

            return self._original_df[self._original_df["unique_id"].isin(matching_ids)]

        return pd.DataFrame(columns=self._original_df.columns)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def filter_by_reactant_abbrevs(self, phase_abbrevs: list[str]) -> pd.DataFrame:
        """Filter dataframe by reactant phase_abbrevs (union logic)."""
        if not phase_abbrevs:
            return self._original_df

        matching_ids = self.get_unique_ids_from_phase_abbrevs(
            phase_abbrevs, self._uid_to_reactant_abbrevs_lookup
        )

        if not matching_ids:
            return pd.DataFrame(columns=self._original_df.columns)

        return self._original_df[self._original_df["unique_id"].isin(matching_ids)]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def filter_by_product_abbrevs(self, phase_abbrevs: list[str]) -> pd.DataFrame:
        """Filter dataframe by product phase_abbrevs (union logic)."""
        if not phase_abbrevs:
            return self._original_df

        matching_ids = self.get_unique_ids_from_phase_abbrevs(
            phase_abbrevs, self._uid_to_product_abbrevs_lookup
        )

        if not matching_ids:
            return pd.DataFrame(columns=self._original_df.columns)

        return self._original_df[self._original_df["unique_id"].isin(matching_ids)]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def filter_by_ids(self, unique_ids: list[str]) -> pd.DataFrame:
        """Filter dataframe by unique IDs."""
        if not unique_ids:
            return self._original_df

        return self._original_df[self._original_df["unique_id"].isin(unique_ids)]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def filter_by_type(self, types: list[str]) -> pd.DataFrame:
        """Filter by specific types of data."""
        if not types:
            return self._original_df

        return self._original_df[self._original_df["type"].isin(types)]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_unique_ids_from_phase_abbrevs(
        self, phase_abbrevs: list[str], lookup: dict[str, set[str]]
    ) -> set[str]:
        """Get all unique IDs matching any phase in the list."""
        if not phase_abbrevs:
            return set()

        matching_ids = set()
        for phase in phase_abbrevs:
            matching_ids.update(lookup.get(phase, set()))

        return matching_ids

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_reactant_abbrevs_from_ids(self, unique_ids: list[str]) -> list[str]:
        """Get unique reactants associated with a list of reaction IDs."""
        if not unique_ids:
            return []

        reactant_abbrevs = {
            reactant
            for reactant, uids in self._uid_to_reactant_abbrevs_lookup.items()
            if uids.intersection(unique_ids)
        }

        return sorted(reactant_abbrevs)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_product_abbrevs_from_ids(self, unique_ids: list[str]) -> list[str]:
        """Get unique products associated with a list of reaction IDs."""
        if not unique_ids:
            return []

        product_abbrevs = {
            product
            for product, uids in self._uid_to_product_abbrevs_lookup.items()
            if uids.intersection(unique_ids)
        }

        return sorted(product_abbrevs)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_phase_abbrev_from_name(self, name: str) -> list[str]:
        """"""
        return sorted(list(self._phase_name_to_abbrev_lookup.get(name, set())))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_phase_abbrev_from_group(self, group: str) -> list[str]:
        """"""
        return sorted(list(self._phase_group_to_abbrev_lookup.get(group, set())))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_phase_abbrev_from_formula(self, formula: str) -> list[str]:
        """"""
        return sorted(list(self._phase_formula_to_abbrev_lookup.get(formula, set())))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_phase_name_from_abbrev(self, abbrev: str) -> str:
        """Get the common name of a phase from its abbreviation."""
        return str(self._abbrev_to_phase_name_lookup.get(abbrev, ""))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_phase_formula_from_abbrev(self, abbrev: str) -> str:
        """Get the chemical formula of a phase from its abbreviation."""
        return str(self._abbrev_to_phase_formula_lookup.get(abbrev, ""))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_phase_group_from_abbrev(self, abbrev: str) -> str:
        """Get the mineral group of a phase from its abbreviation."""
        return str(self._abbrev_to_phase_group_lookup.get(abbrev, ""))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_phase_info_from_abbrev(self, abbrev: str) -> dict:
        """Get all information about a phase from its abbreviation."""
        if abbrev not in self._abbrev_to_phase_name_lookup:
            return {}

        return {
            "abbreviation": abbrev,
            "name": self._abbrev_to_phase_name_lookup.get(abbrev, ""),
            "formula": self._abbrev_to_phase_formula_lookup.get(abbrev, ""),
            "group": self._abbrev_to_phase_group_lookup.get(abbrev, ""),
        }

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_all_phase_info(self) -> dict:
        """Get a dictionary of all phases with their complete information."""
        all_phases = {}

        for abbrev in self._abbrev_to_phase_name_lookup:
            all_phases[abbrev] = self.get_phase_info_from_abbrev(abbrev)

        return all_phases

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_reactant_info_from_unique_id(self, unique_id: str) -> list[dict]:
        """Get information about all reactants for a specific reaction ID."""
        if unique_id not in self._original_df["unique_id"].values:
            return []

        row = self._original_df[self._original_df["unique_id"] == unique_id].iloc[0]
        reactants = row.get("reactants", [])

        if not isinstance(reactants, list):
            return []

        return [
            self.get_phase_info_from_abbrev(abbrev)
            for abbrev in reactants
            if abbrev in self._abbrev_to_phase_name_lookup
        ]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_product_info_from_unique_id(self, unique_id: str) -> list[dict]:
        """Get information about all products for a specific reaction ID."""
        if unique_id not in self._original_df["unique_id"].values:
            return []

        row = self._original_df[self._original_df["unique_id"] == unique_id].iloc[0]
        products = row.get("products", [])

        if not isinstance(products, list):
            return []

        return [
            self.get_phase_info_from_abbrev(abbrev)
            for abbrev in products
            if abbrev in self._abbrev_to_phase_name_lookup
        ]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_reaction_info_from_unique_id(self, unique_id: str) -> dict:
        """Get comprehensive information about all phases in a reaction."""
        return {
            "reactants": self.get_reactant_info_from_unique_id(unique_id),
            "products": self.get_product_info_from_unique_id(unique_id),
        }

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_all_group_names(self) -> list[str]:
        """Get all groups names."""
        return list(self._group_rank.keys())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_all_grouped_phases(
        self, display_mode: str, show_formula: bool
    ) -> dict[str, list[str]]:
        """Get all checkbox group phases based on the display mode."""
        grouped = (
            self._grouped_phases_with_formulas.get(display_mode)
            if show_formula
            else self._grouped_phases.get(display_mode)
        )

        if not grouped:
            raise ValueError(f"Invalid display_mode: {display_mode!r}")

        return {
            k: list(grouped[k])
            for k in sorted(
                grouped, key=lambda g: self._group_rank.get(g, float("inf"))
            )
        }

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_grouped_phases(
        self, group: str, display_mode: str, show_formula: bool
    ) -> list[str]:
        """Get individual checkbox group phases based on the display mode."""
        grouped = (
            self._grouped_phases_with_formulas.get(display_mode)
            if show_formula
            else self._grouped_phases.get(display_mode)
        )

        if not grouped:
            raise ValueError(f"Invalid display_mode: {display_mode!r}")

        return sorted(grouped.get(group, []))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _build_reaction_groups(self, method: str = "or"):
        """
        Group reactions based on shared reactant_abbrevs AND product_abbrevs.
        Assigns each unique ID to a group number.
        """
        self._reaction_groups = {}
        group_counter = 0
        processed_ids = set()

        for uid in self._original_df["unique_id"].unique():
            if uid in processed_ids:
                continue

            row = self._original_df[self._original_df["unique_id"] == uid].iloc[0]
            reactant_abbrevs = row.get("reactants", [])
            product_abbrevs = row.get("products", [])

            if not isinstance(reactant_abbrevs, list) or not isinstance(
                product_abbrevs, list
            ):
                continue

            if not reactant_abbrevs or not product_abbrevs:
                continue

            f_reactant_ids = self.get_unique_ids_from_phase_abbrevs(
                reactant_abbrevs, self._uid_to_reactant_abbrevs_lookup
            )
            f_product_ids = self.get_unique_ids_from_phase_abbrevs(
                product_abbrevs, self._uid_to_product_abbrevs_lookup
            )

            r_reactant_ids = self.get_unique_ids_from_phase_abbrevs(
                reactant_abbrevs, self._uid_to_product_abbrevs_lookup
            )
            r_product_ids = self.get_unique_ids_from_phase_abbrevs(
                product_abbrevs, self._uid_to_reactant_abbrevs_lookup
            )

            if method == "and":
                matching_ids = f_reactant_ids.intersection(f_product_ids).union(
                    r_reactant_ids.intersection(r_product_ids)
                )
            else:
                matching_ids = f_reactant_ids.union(f_product_ids).union(
                    r_reactant_ids.union(r_product_ids)
                )

            if matching_ids:
                for match_id in matching_ids:
                    self._reaction_groups[match_id] = group_counter
                    processed_ids.add(match_id)
                self._reaction_groups[uid] = group_counter
                processed_ids.add(uid)
                group_counter += 1

        for uid in self._original_df["unique_id"].unique():
            if uid not in processed_ids:
                self._reaction_groups[uid] = group_counter
                group_counter += 1

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _build_color_map(self):
        """
        Build a color map for reaction groups.
        Assigns a color to each unique group number.
        """
        if not self._reaction_groups:
            self._build_reaction_groups()

        unique_groups = set(self._reaction_groups.values())
        palette = self._get_color_palette()

        self._color_map = {
            str(group): palette[i % len(palette)]
            for i, group in enumerate(sorted(unique_groups))
        }

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
    def _get_color_from_reaction(self, unique_id: str) -> str:
        """Get the color for a specific unique ID."""
        if unique_id not in self._reaction_groups:
            return "#000000"

        group = self._reaction_groups[unique_id]
        return self._color_map.get(str(group), "#000000")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def add_color_keys(self, filtered_df: pd.DataFrame) -> pd.DataFrame:
        """Add color information to a filtered dataframe."""
        df_copy = filtered_df.copy()
        df_copy["rxn_group"] = df_copy["unique_id"].map(
            lambda x: self._reaction_groups.get(x, -1)
        )
        df_copy["rxn_color_key"] = df_copy["unique_id"].map(
            lambda x: self._get_color_from_reaction(x)
        )

        return df_copy

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def get_group_id(group_name: str) -> str:
        """Reformats group id for in compatible format for shiny UI IDs."""
        return (
            group_name.lower().replace(" ", "_").replace("&", "and").replace("-", "_")
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @property
    def phases(self) -> list[str]:
        """Get a sorted list of unique phase names from reactants and products."""
        all_phases = set(self._uid_to_reactant_abbrevs_lookup.keys()) | set(
            self._uid_to_product_abbrevs_lookup.keys()
        )

        return sorted(list(all_phases))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @property
    def data(self) -> pd.DataFrame:
        """"""
        return self._original_df


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def main():
    """"""
    from rxnDB.data.loader import RxnDBLoader
    from rxnDB.utils import app_dir

    filepath = app_dir / "data" / "cache" / "rxnDB.parquet"
    rxnDB: pd.DataFrame = RxnDBLoader.load_parquet(filepath)
    processor: RxnDBProcessor = RxnDBProcessor(rxnDB)
    all_phases = processor.phases
    print(all_phases)


if __name__ == "__main__":
    main()
