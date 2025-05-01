#######################################################
## .0.              Load Libraries               !!! ##
#######################################################
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from ruamel.yaml import YAML

from rxnDB.utils import app_dir


#######################################################
## .1.                   RxnDB                   !!! ##
#######################################################
@dataclass
class RxnDBLoader:
    in_dir: Path

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __post_init__(self):
        self.yaml = YAML()
        if not self.in_dir.exists():
            raise FileNotFoundError(f"Directory {self.in_dir} not found!")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def load_all(self) -> pd.DataFrame:
        """Load and concatenate all YAML entries in the directory into a single DataFrame."""
        dfs = [
            self.load_entry(filepath) for filepath in sorted(self.in_dir.glob("*.yml"))
        ]
        return pd.concat(dfs, ignore_index=True)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def load_entry(self, filepath: Path) -> pd.DataFrame:
        """Load a single YAML file and convert it into a DataFrame."""
        parsed_yml = self._read_yml(filepath)

        data = parsed_yml["data"]
        metadata = parsed_yml["metadata"]

        n_rows = len(data["ln_K"]["mid"])
        rows = [
            {
                "id": parsed_yml["id"],
                "type": parsed_yml["type"],
                "rxn": parsed_yml["rxn"],
                "products": self._convert_to_str_list(parsed_yml["products"]),
                "reactants": self._convert_to_str_list(parsed_yml["reactants"]),
                "ln_K_mid": data["ln_K"]["mid"][i],
                "ln_K_half_range": data["ln_K"]["half_range"][i],
                "x_CO2_mid": data["x_CO2"]["mid"][i],
                "x_CO2_half_range": data["x_CO2"]["half_range"][i],
                "P": data["P"]["mid"][i],
                "P_half_range": data["P"]["half_range"][i],
                "T": data["T"]["mid"][i],
                "T_half_range": data["T"]["half_range"][i],
                "ref": metadata["ref"]["short_cite"],
            }
            for i in range(n_rows)
        ]

        return pd.DataFrame(rows)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _read_yml(self, filepath: Path) -> dict[str, Any]:
        """Read and parse a YAML file."""
        with open(filepath, "r") as file:
            return self.yaml.load(file)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _convert_to_str_list(self, data: Any) -> list[str]:
        """Ensure that the data is converted to a list of strings"""
        if isinstance(data, list):
            return [str(item).lower() for item in data]
        elif isinstance(data, str):
            return [data.lower()]
        else:
            return [str(data).lower()]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def main():
    hp11_in_data = app_dir / "data" / "sets" / "preprocessed" / "hp11_data"
    hp11_loader = RxnDBLoader(hp11_in_data)

    jimmy_in_data = app_dir / "data" / "sets" / "preprocessed" / "jimmy_data"
    jimmy_loader = RxnDBLoader(jimmy_in_data)

    hp11_data = hp11_loader.load_entry(hp11_in_data / "hp11-001.yml")
    jimmy_data = jimmy_loader.load_entry(jimmy_in_data / "jimmy-001.yml")

    # hp11_data = hp11_loader.load_all()
    # jimmy_data = jimmy_loader.load_all()

    print(hp11_data)
    print(hp11_data.info())
    print(jimmy_data)
    print(jimmy_data.info())


if __name__ == "__main__":
    main()
