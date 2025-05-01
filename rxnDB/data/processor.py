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
    _original_df: pd.DataFrame = field(init=False)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __post_init__(self):
        if self.df.empty:
            raise ValueError("RxnDB dataframe empty!")

        required_cols = ["id", "reactants", "products", "type"]
        missing = [col for col in required_cols if col not in self.df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        self._original_df = self.df.copy()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def reset(self) -> "RxnDBProcessor":
        """"""
        return RxnDBProcessor(df=self._original_df.copy())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def filter_by_ids(self, ids: list[str]) -> "RxnDBProcessor":
        """"""
        mask = self.df["id"].isin(ids)
        return RxnDBProcessor(df=self.df[mask].copy())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def filter_by_reactants(self, phases: list[str]) -> "RxnDBProcessor":
        """"""
        mask = self.df["reactants"].apply(lambda x: any(phase in x for phase in phases))
        return RxnDBProcessor(df=self.df[mask].copy())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def filter_by_products(self, phases: list[str]) -> "RxnDBProcessor":
        """"""
        mask = self.df["products"].apply(lambda x: any(phase in x for phase in phases))
        return RxnDBProcessor(df=self.df[mask].copy())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def remove_point_data(self) -> "RxnDBProcessor":
        """"""
        mask = self.df["type"] != "point"
        return RxnDBProcessor(df=self.df[mask].copy())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def remove_calibration_curves(self) -> "RxnDBProcessor":
        """"""
        mask = self.df["type"] != "calibration_curve"
        return RxnDBProcessor(df=self.df[mask].copy())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def remove_reaction_curves(self) -> "RxnDBProcessor":
        """"""
        mask = self.df["type"] != "reaction_curve"
        return RxnDBProcessor(df=self.df[mask].copy())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def _strip_coefficients(phases: list[str]) -> list[str]:
        return [re.sub(r"^\d+", "", phase) for phase in phases]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def get_unique_phases(self) -> list[str]:
        """Get a sorted list of unique phase names from reactants and products"""
        all_phases = []

        for col in ["reactants", "products"]:
            for entry in self.df[col]:
                if isinstance(entry, list):
                    all_phases.extend(entry)

        # Remove leading digits using regex
        clean_phases = [
            re.sub(r"^\d+", "", phase) for phase in all_phases if pd.notna(phase)
        ]

        # Get unique, sorted list
        return sorted(set(clean_phases))


def main():
    """"""
