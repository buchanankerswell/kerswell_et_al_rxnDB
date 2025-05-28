#######################################################
## .0. Load Libraries                            !!! ##
#######################################################
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from ruamel.yaml import YAML

from rxnDB.utils import app_dir


#######################################################
## .1. HP11Preprocessor                        !!! ##
#######################################################
@dataclass
class HP11Preprocessor:
    in_data: Path
    out_dir: Path

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __post_init__(self) -> None:
        """"""
        if not self.in_data.exists():
            raise FileNotFoundError(f"Could not find {self.in_data}!")

        self.yaml = YAML()
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml.default_flow_style = False
        self.yaml.allow_unicode = True
        self.yaml.explicit_start = True

        self.out_dir.mkdir(parents=True, exist_ok=True)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def preprocess(self) -> None:
        """"""
        raw_text = self.in_data.read_text()
        data_entries = self._split_into_entries(raw_text)

        for i, entry in enumerate(data_entries):
            print(f"Processing HP11 entry {i + 1} ...", end="\r", flush=True)

            rxn_data = self._process_entry(entry)
            in_data = self.out_dir / f"hp11-{i + 1:03}.yml"

            with open(in_data, "w") as file:
                self.yaml.dump(rxn_data, file)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def _split_into_entries(text: str) -> list[str]:
        """"""
        entries = re.split(r"(?=\n\s*\d+\))", text)
        return [e.strip() for e in entries if e.strip()]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _process_entry(self, entry: str) -> dict[str, Any]:
        """"""
        lines = entry.splitlines()
        header = lines[0].strip()
        data_lines = lines[2:]

        index, reaction, citation = self._split_reaction_and_citation(header)
        reactants, products = self._split_reaction(reaction)

        rxn_data = self._parse_data_lines(data_lines)
        rounded_data = cast(dict[str, Any], self._round_data(rxn_data))

        data_type = (
            "phase_boundary"
            if all(x == 0.0 for x in rounded_data["ln_K"]["mid"])
            else "calibration"
        )

        def to_point_block(
            mid: list[float | None], half_range: list[float | None]
        ) -> dict:
            return {
                "value": [v if v is not None else None for v in mid],
                "uncertainty": [u if u is not None else None for u in half_range],
            }

        out_dict = {
            "reactants": {p: None for p in reactants},
            "products": {p: None for p in products},
            "data": {
                "type": data_type,
                "units": {"T": "C", "P": "kbar"},
                "points": {
                    "T": to_point_block(
                        rounded_data["T"]["mid"], rounded_data["T"]["half_range"]
                    ),
                    "P": to_point_block(
                        rounded_data["P"]["mid"], rounded_data["P"]["half_range"]
                    ),
                    "lnK": to_point_block(
                        rounded_data["ln_K"]["mid"], rounded_data["ln_K"]["half_range"]
                    ),
                },
            },
            "metadata": {
                "unique_id": f"hp11-{int(index):03}",
                "reference": citation,
                "method": None,
                "comments": None,
            },
        }

        return out_dict

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def _round_data(
        data: dict[str, dict[str, list[float]]], decimals: int = 3
    ) -> dict[str, Any]:
        """"""
        return {
            k: {subk: [round(x, decimals) for x in v] for subk, v in subv.items()}
            for k, subv in data.items()
        }

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _split_reaction_and_citation(
        self, header: str
    ) -> tuple[str, str, dict[str, Any]]:
        """"""
        match = re.match(r"(\d+)\)\s+(.*)", header)

        if not match:
            raise ValueError(f"Invalid header: {header}")

        index, rest = match.groups()

        depth: int = 0
        for i in range(len(rest) - 1, -1, -1):
            if rest[i] == ")":
                depth += 1
            elif rest[i] == "(":
                depth -= 1
                if depth == 0:
                    reaction: str = rest[:i].strip().replace("=", "=>")
                    citation: str = rest[i + 1 : -1].strip()

                    return (
                        index,
                        reaction,
                        self._split_citations(citation),
                    )

        return index, rest.strip().replace("=", "=>"), {}

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def _split_reaction(reaction: str) -> tuple[list[str], list[str]]:
        """"""
        if "=>" not in reaction:
            raise ValueError(f"Invalid reaction: {reaction}")

        reactants, products = reaction.split("=>")

        def strip_digits(s: str) -> str:
            return re.sub(r"^\d+", "", s.strip())

        return [strip_digits(r) for r in reactants.split("+")], [
            strip_digits(p) for p in products.split("+")
        ]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def _split_citations(citation_text: str) -> dict[str, Any]:
        parts: list[str] = re.split(r";\s*", citation_text)

        all_authors, years = [], []
        for part in parts:
            match = re.match(r"(.+?)(?:,|\s)(\d{4})$", part.strip())
            if match:
                raw_authors = (
                    match.group(1).replace("et al.,", "et al.").strip().rstrip(",")
                )

                if "et al." in raw_authors:
                    split_authors = [raw_authors]
                else:
                    split_authors = re.split(r"\s*(?:&| and )\s*", raw_authors)

                all_authors.extend([a.strip() for a in split_authors])
                years.append(int(match.group(2)))
            else:
                all_authors.append(part.strip())
                years.append(None)

        return {
            "short_cite": citation_text,
            "authors": all_authors,
            "year": years if len(years) > 1 else years[0],
        }

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def _parse_data_lines(data_lines: list[str]) -> dict[str, Any]:
        """"""

        def to_float(s: str) -> float | None:
            """"""
            s = s.strip()
            return float(s) if s and s != "-" else None

        def mid_half(
            a: float | None, b: float | None
        ) -> tuple[float | None, float | None]:
            """"""
            if a is None and b is None:
                return None, None
            if a is None:
                return b, None
            if b is None:
                return a, None
            return (a + b) / 2, abs(b - a) / 2

        parsed: list[list[float | None]] = []
        for line in data_lines:
            tokens: list[str] = line.split()

            if not tokens or to_float(tokens[0]) is None:
                continue

            parsed.append([to_float(tok) for tok in tokens[:7]])

        if not parsed:
            return {"ln_K": [], "x_CO2": [], "P": [], "T": []}

        lnK_mid, lnK_range = [], []
        xCO2_mid, xCO2_range = [], []
        P_mid, P_range = [], []
        T_mid, T_range = [], []

        for row in parsed:
            m, r = mid_half(row[0], row[1])
            lnK_mid.append(m)
            lnK_range.append(r)

            m, r = mid_half(row[2], row[2])
            xCO2_mid.append(m)
            xCO2_range.append(r)

            m, r = mid_half(row[3], row[4])
            P_mid.append(m)
            P_range.append(r)

            m, r = mid_half(row[5], row[6])
            T_mid.append(m)
            T_range.append(r)

        return {
            "ln_K": {"mid": lnK_mid, "half_range": lnK_range},
            "x_CO2": {"mid": xCO2_mid, "half_range": xCO2_range},
            "P": {"mid": P_mid, "half_range": P_range},
            "T": {"mid": T_mid, "half_range": T_range},
        }


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def main():
    """"""
    in_data = app_dir / "data" / "sets" / "hp11-raw.txt"
    out_dir = app_dir / "data" / "sets" / "hp11"

    hp11_db = HP11Preprocessor(in_data, out_dir)
    hp11_db.preprocess()

    print("\nDatasets preprocessed!")


if __name__ == "__main__":
    main()
