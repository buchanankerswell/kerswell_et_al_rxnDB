#######################################################
## .0. Load Libraries                            !!! ##
#######################################################
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from ruamel.yaml import YAML

from rxnDB.data.mapping import MINERAL_ABBREV_MAP
from rxnDB.utils import app_dir


#######################################################
## .1. RxnDB                                     !!! ##
#######################################################
@dataclass
class RxnDBLoader:
    in_dir: Path

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __post_init__(self) -> None:
        """"""
        if not self.in_dir.exists():
            raise FileNotFoundError(f"Directory {self.in_dir} not found!")

        self.yaml = YAML()

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def load_all(self) -> pd.DataFrame:
        """Load and concatenate all YAML entries in the directory into a single DataFrame."""
        in_paths: list[Path] = sorted(self.in_dir.glob("*.yml"))
        dfs: list[pd.DataFrame] = [self.load_entry(path) for path in in_paths]

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FutureWarning)
            return pd.concat(dfs, ignore_index=True)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def load_entry(self, filepath: Path) -> pd.DataFrame:
        """Load a single YAML file and convert it into a DataFrame."""
        print(f"Loading {filepath.name} ...", end="\r", flush=True)
        parsed_yml = self._read_yml(filepath)

        reactants: list[str] = self._convert_to_str_list(
            parsed_yml.get("reactants", {})
        )
        products: list[str] = self._convert_to_str_list(parsed_yml.get("products", {}))

        reactant_names: list[str] = []
        reactant_groups: list[str] = []
        reactant_formulas: list[str] = []

        product_names: list[str] = []
        product_groups: list[str] = []
        product_formulas: list[str] = []

        for reactant in reactants:
            if reactant in MINERAL_ABBREV_MAP:
                mineral_info = MINERAL_ABBREV_MAP[reactant]
                reactant_names.append(mineral_info["name"])
                reactant_groups.append(mineral_info["group"])
                reactant_formulas.append(mineral_info["formula"])
            else:
                print(f" !! Warning: phase {reactant} not in map!")
                reactant_names.append(reactant)
                reactant_groups.append("")
                reactant_formulas.append("")

        for product in products:
            if product in MINERAL_ABBREV_MAP:
                mineral_info = MINERAL_ABBREV_MAP[product]
                product_names.append(mineral_info["name"])
                product_groups.append(mineral_info["group"])
                product_formulas.append(mineral_info["formula"])
            else:
                print(f" !! Warning: phase {product} not in map!")
                product_names.append(product)
                product_groups.append("")
                product_formulas.append("")

        reaction = "+".join(reactants) + "<=>" + "+".join(products)
        reaction_names = "+".join(reactant_names) + "<=>" + "+".join(product_names)

        data = parsed_yml.get("data", {})
        data_type = data.get("type")
        units_T = data.get("units", {}).get("T")
        units_P = data.get("units", {}).get("P")

        metadata = parsed_yml.get("metadata", {})
        unique_id = metadata.get("unique_id")
        method = metadata.get("method", {})
        method_name = method.get("name") if method else None
        calib = method.get("calibration") if method else {}
        calib_P = calib.get("P") if calib else None
        calib_T = calib.get("T") if calib else None
        reference = metadata.get("reference").get("short_cite")
        comments = metadata.get("comments")

        rows = []

        points = data.get("points", {})
        curve = data.get("boundary_curve", {}).get("polynomial")

        if points:
            T_vals = points.get("T", {}).get("value", [None])
            T_uncs = points.get("T", {}).get("uncertainty", [None])
            P_vals = points.get("P", {}).get("value", [None])
            P_uncs = points.get("P", {}).get("uncertainty", [None])
            lnK_vals = points.get("lnK", {}).get("value", [None])
            lnK_uncs = points.get("lnK", {}).get("uncertainty", [None])

            n_rows = max(len(T_vals), len(P_vals))
            for i in range(n_rows):
                rows.append(
                    {
                        "unique_id": unique_id,
                        "reaction": reaction,
                        "reaction_names": reaction_names,
                        "reactants": reactants,
                        "reactant_names": reactant_names,
                        "reactant_groups": reactant_groups,
                        "reactant_formulas": reactant_formulas,
                        "products": products,
                        "product_names": product_names,
                        "product_groups": product_groups,
                        "product_formulas": product_formulas,
                        "type": data_type,
                        "units_T": units_T,
                        "units_P": units_P,
                        "T": T_vals[i] if i < len(T_vals) else np.nan,
                        "T_uncertainty": T_uncs[i] if i < len(T_uncs) else np.nan,
                        "P": P_vals[i] if i < len(P_vals) else np.nan,
                        "P_uncertainty": P_uncs[i] if i < len(P_uncs) else np.nan,
                        "lnK": lnK_vals[i] if i < len(lnK_vals) else np.nan,
                        "lnK_uncertainty": lnK_uncs[i] if i < len(lnK_uncs) else np.nan,
                        "plot_type": "point",
                        "reference": reference,
                        "method": method_name,
                        "calib_P": calib_P,
                        "calib_T": calib_T,
                        "comments": comments,
                    }
                )

        elif curve:
            intercept = curve.get("intercept", 0.0)
            x1 = curve.get("x1", 0.0)
            x2 = curve.get("x2", 0.0)
            x3 = curve.get("x3", 0.0)

            limits = data.get("boundary_curve", {}).get("limits", {})
            T_min = limits.get("T_min")
            T_max = limits.get("T_max")
            P_min = limits.get("P_min")
            P_max = limits.get("P_max")

            T_vals = np.linspace(T_min, T_max, num=20)

            for T in T_vals:
                P = intercept + x1 * T + x2 * T**2 + x3 * T**3

                if (P_min is not None and P < P_min) or (
                    P_max is not None and P > P_max
                ):
                    T = np.nan
                    P = np.nan

                rows.append(
                    {
                        "unique_id": unique_id,
                        "reaction": reaction,
                        "reaction_names": reaction_names,
                        "reactants": reactants,
                        "reactant_names": reactant_names,
                        "reactant_groups": reactant_groups,
                        "reactant_formulas": reactant_formulas,
                        "products": products,
                        "product_names": product_names,
                        "product_groups": product_groups,
                        "product_formulas": product_formulas,
                        "type": data_type,
                        "units_T": units_T,
                        "units_P": units_P,
                        "T": T,
                        "T_uncertainty": np.nan,
                        "P": P,
                        "P_uncertainty": np.nan,
                        "lnK": np.nan,
                        "lnK_uncertainty": np.nan,
                        "plot_type": "curve",
                        "reference": reference,
                        "method": method_name,
                        "calib_P": calib_P,
                        "calib_T": calib_T,
                        "comments": comments,
                    }
                )

        else:
            print(f"  No point or curve data found in {filepath.name}!")

        df = pd.DataFrame(rows)

        if "comments" in df.columns:
            df["comments"] = df["comments"].fillna("").astype(str)

        return df

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def save_as_parquet(df: pd.DataFrame, filepath: Path) -> None:
        """Save a DataFrame as a compressed Parquet file."""
        filepath.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(filepath, index=False)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def load_parquet(filepath: Path) -> pd.DataFrame:
        """Load a DataFrame from a Parquet file."""
        print(f"Loading data from {filepath.name} ...")
        return pd.read_parquet(filepath)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _read_yml(self, filepath: Path) -> dict[str, Any]:
        """Read and parse a YAML file."""
        with open(filepath, "r") as file:
            return self.yaml.load(file)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _convert_to_str_list(self, data: Any) -> list[str]:
        """Ensure that the data is converted to a list of strings"""
        if isinstance(data, list):
            return [str(item) for item in data]
        elif isinstance(data, str):
            return [data]
        elif isinstance(data, dict):
            return [str(k) for k, _ in data.items()]
        else:
            return [str(data)]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def main():
    """"""
    jimmy_loader = RxnDBLoader(app_dir / "data" / "sets" / "jimmy")
    jimmy_data = jimmy_loader.load_all()

    hp11_loader = RxnDBLoader(app_dir / "data" / "sets" / "hp11")
    hp11_data = hp11_loader.load_all()

    # kbar --> GPa
    hp11_data["P"] *= 0.1
    hp11_data["P_uncertainty"] *= 0.1

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        rxnDB = pd.concat([hp11_data, jimmy_data], ignore_index=True)

    out_data = app_dir / "data" / "cache" / "rxnDB.parquet"
    RxnDBLoader.save_as_parquet(rxnDB, app_dir / "data" / "cache" / "rxnDB.parquet")

    print("\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print(f"Data saved to {out_data.name}!")
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    print("Summary:")
    print(rxnDB.info())


if __name__ == "__main__":
    main()
