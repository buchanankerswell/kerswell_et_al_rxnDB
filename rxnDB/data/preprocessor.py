#######################################################
## .0.              Load Libraries               !!! ##
#######################################################
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import numpy as np
import pandas as pd
from ruamel.yaml import YAML

from rxnDB.utils import app_dir


#######################################################
## .1.              CSVPreprocessor              !!! ##
#######################################################
@dataclass
class CSVPreprocessor:
    filepath: Path
    output_dir: Path
    db_id: str

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __post_init__(self):
        if not self.filepath.exists():
            raise FileNotFoundError(f"Could not find {self.filepath}!")

        self.yaml = YAML()
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml.default_flow_style = False
        self.yaml.allow_unicode = True
        self.yaml.explicit_start = True

        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def preprocess(self) -> None:
        """"""
        df = pd.read_csv(self.filepath)

        for i, (_, entry) in enumerate(df.iterrows()):
            print(f"Processing {self.db_id} CSV row {i + 1} ...", end="\r", flush=True)
            rxn_data = self._process_entry(entry)
            out_file = self.output_dir / f"{self.db_id}-{i + 1:03}.yml"
            with open(out_file, "w") as file:
                self.yaml.dump(rxn_data, file)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def _abbrev_map() -> dict[str, str]:
        """"""
        return {
            "sil": "sil",
            "sill": "sil",
            "wd": "wad",
            "wa": "wad",
            "wds": "wad",
        }

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @classmethod
    def _normalize_abbreviations(cls, phases: list[str]) -> list[str]:
        """"""
        abbrev_map = cls._abbrev_map()
        return [abbrev_map.get(p, p) for p in phases]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @classmethod
    def _normalize_rxn_string(cls, rxn: str) -> str:
        """"""
        abbrev_map = cls._abbrev_map()

        pattern = re.compile(
            r"\b(\d*)(?=("
            + "|".join(re.escape(k) for k in abbrev_map.keys())
            + r"))\w+\b"
        )

        def replacer(match):
            coeff = match.group(1)
            phase = match.group(0)[len(coeff) :]
            norm_phase = abbrev_map.get(phase, phase)
            return f"{coeff}{norm_phase}"

        return pattern.sub(replacer, rxn)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _process_entry(self, entry: pd.Series) -> dict[str, Any]:
        """"""
        reactants = [
            entry[f"reactant{i}"].lower()
            for i in range(1, 4)
            if pd.notna(entry.get(f"reactant{i}", None))
        ]

        products = [
            entry[f"product{i}"].lower()
            for i in range(1, 4)
            if pd.notna(entry.get(f"product{i}", None))
        ]

        reactants = self._normalize_abbreviations(reactants)
        products = self._normalize_abbreviations(products)

        if not reactants and any("melt" in p for p in products):
            if pd.notna(entry.get("formula", None)):
                reactants = [entry["formula"].lower()]

        reaction = (
            re.sub(
                r"\s*\+\s*", " + ", re.sub(r"\s*=>\s*", " => ", entry["rxn"].lower())
            )
            if pd.notna(entry["rxn"]) and entry["rxn"].lower() != "melt"
            else f"{' + '.join(reactants)} => {' + '.join(products)}"
        )

        reaction = self._normalize_rxn_string(reaction)

        rxn_data = self._process_polynomial(entry)
        rounded_data = cast(dict[str, Any], self._round_data(rxn_data))

        yml_out = {
            "name": f"jimmy-{entry['id']:03}",
            "source": "jimmy",
            "type": "phase_boundary",
            "plot_type": "curve",
            "rxn": reaction,
            "reactants": reactants,
            "products": products,
            "data": rounded_data,
            "metadata": self._build_metadata(entry),
        }

        return yml_out

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
    @staticmethod
    def _process_polynomial(
        row: pd.Series, nsteps: int = 100
    ) -> dict[str, dict[str, list[float]]]:
        """"""
        Ts = np.linspace(row["tmin"], row["tmax"], nsteps)
        Ps = np.full_like(Ts, row["b"])

        for i, term in enumerate(["t1", "t2", "t3", "t4"], start=1):
            coeff = row.get(term, 0.0)
            if pd.notna(coeff):
                Ps += coeff * Ts**i

        return {
            "P": {"mid": Ps.tolist(), "half_range": [0.0] * nsteps},
            "T": {"mid": Ts.tolist(), "half_range": [0.0] * nsteps},
            "ln_K": {"mid": [0.0] * nsteps, "half_range": [0.0] * nsteps},
            "x_CO2": {"mid": [0.0] * nsteps, "half_range": [0.0] * nsteps},
        }

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def _build_metadata(entry: pd.Series) -> dict[str, Any]:
        """"""
        ref = {
            k: entry[k]
            for k in ["doi", "authors", "year", "title", "journal", "volume", "pages"]
            if k in entry and pd.notna(entry[k])
        }

        authors = (
            entry["authors"].replace(";", ",")
            if pd.notna(entry["authors"])
            else "Unknown"
        )

        year = str(entry["year"]) if pd.notna(entry["year"]) else "n.d."
        ref["short_cite"] = f"{authors}, {year}"

        polynomial = {
            "rxn_polynomial": {
                k: float(entry[k]) if pd.notna(entry[k]) else None
                for k in ["b", "t1", "t2", "t3", "t4", "pmin", "pmax", "tmin", "tmax"]
            }
        }

        extra = {
            k: entry[k]
            for k in ["calibration_confidence", "data_constraint_confidence", "misc"]
            if k in entry and pd.notna(entry[k])
        }

        return {"ref": ref, **extra, **polynomial}


#######################################################
## .2.             HP11DBPreprocessor            !!! ##
#######################################################
@dataclass
class HP11DBPreprocessor:
    filepath: Path
    output_dir: Path

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __post_init__(self):
        if not self.filepath.exists():
            raise FileNotFoundError(f"Could not find {self.filepath}!")

        self.yaml = YAML()
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml.default_flow_style = False
        self.yaml.allow_unicode = True
        self.yaml.explicit_start = True

        self.output_dir.mkdir(parents=True, exist_ok=True)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def preprocess(self) -> None:
        """"""
        text = self.filepath.read_text()
        entries = self._split_into_entries(text)

        for i, entry in enumerate(entries):
            print(f"Processing HP11 data entry {i + 1} ...", end="\r", flush=True)
            rxn_data = self._process_entry(entry)
            out_file = self.output_dir / f"hp11-{i + 1:03}.yml"
            with open(out_file, "w") as file:
                self.yaml.dump(rxn_data, file)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def _split_into_entries(text: str) -> list[str]:
        """"""
        entries = re.split(r"(?=\n\s*\d+\))", text)
        return [e.strip() for e in entries if e.strip()]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @classmethod
    def _abbrev_map(cls) -> dict[str, str]:
        """"""
        return {
            "sil": "sil",
            "sill": "sil",
            "wd": "wad",
            "wa": "wad",
            "wds": "wad",
        }

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @classmethod
    def _normalize_rxn_string(cls, rxn: str) -> str:
        """"""
        abbrev_map = cls._abbrev_map()
        pattern = re.compile(
            r"\b(\d*)(?=(" + "|".join(re.escape(k) for k in abbrev_map) + r"))\w+\b"
        )

        def replacer(match):
            coeff = match.group(1)
            phase = match.group(0)[len(coeff) :]
            return f"{coeff}{abbrev_map.get(phase, phase)}"

        return pattern.sub(replacer, rxn)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _process_entry(self, entry: str) -> dict[str, Any]:
        """"""
        lines = entry.splitlines()
        header = lines[0].strip()
        data_lines = lines[2:]

        index, reaction, citation = self._split_reaction_and_citation(header)
        reaction = self._normalize_rxn_string(reaction.lower())

        reactants, products = self._split_reaction(reaction)

        rxn_data = self._parse_data_lines(data_lines)
        rounded_data = cast(dict[str, Any], self._round_data(rxn_data))

        data_type = (
            "phase_boundary"
            if all(x == 0.0 for x in rounded_data["ln_K"]["mid"])
            else "rxn_calibration"
        )

        yml_out = {
            "name": f"hp11-{int(index):03}",
            "source": "hp11",
            "type": data_type,
            "plot_type": "point",
            "rxn": reaction,
            "reactants": reactants,
            "products": products,
            "data": rounded_data,
            "metadata": self._build_metadata(citation),
        }

        return yml_out

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
    @staticmethod
    def _split_reaction_and_citation(header: str) -> tuple[str, str, dict[str, Any]]:
        """"""
        match = re.match(r"(\d+)\)\s+(.*)", header)

        if not match:
            raise ValueError(f"Invalid header: {header}")

        index, rest = match.groups()

        depth = 0
        for i in range(len(rest) - 1, -1, -1):
            if rest[i] == ")":
                depth += 1
            elif rest[i] == "(":
                depth -= 1
                if depth == 0:
                    reaction = rest[:i].strip().replace("=", "=>")
                    citation = rest[i + 1 : -1].strip()
                    return (
                        index,
                        reaction,
                        HP11DBPreprocessor._split_citations(citation),
                    )
        return index, rest.strip().replace("=", "=>"), {}

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def _split_reaction(reaction: str) -> tuple[list[str], list[str]]:
        """"""
        if "=>" not in reaction:
            raise ValueError(f"Invalid reaction: {reaction}")
        reactants, products = reaction.split("=>")

        return [r.strip() for r in reactants.split("+")], [
            p.strip() for p in products.split("+")
        ]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def _split_citations(citation_text: str) -> dict[str, Any]:
        """"""
        parts = re.split(r";\s*", citation_text)
        authors, years = [], []
        for part in parts:
            match = re.match(r"(.+?)(?:,|\s)(\d{4})$", part.strip())
            if match:
                name = (
                    match.group(1)
                    .replace(" and ", " & ")
                    .replace("et al.,", "et al.")
                    .strip()
                )
                authors.append(name)
                years.append(match.group(2))
            else:
                authors.append(part.strip())
                years.append(None)

        return {
            "short_cite": citation_text,
            "authors": authors if len(authors) > 1 else authors[0],
            "year": years if len(years) > 1 else years[0],
        }

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def _parse_data_lines(data_lines: list[str]) -> dict[str, Any]:
        """"""

        def to_float(s: str) -> float | None:
            s = s.strip()
            return float(s) if s and s != "-" else None

        def mid_half(
            a: float | None, b: float | None
        ) -> tuple[float | None, float | None]:
            if a is None and b is None:
                return None, None
            if a is None:
                return b, None
            if b is None:
                return a, None
            return (a + b) / 2, abs(b - a) / 2

        parsed = []
        for line in data_lines:
            tokens = line.split()
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
    @staticmethod
    def _build_metadata(citation: dict[str, Any]) -> dict[str, Any]:
        """"""
        metadata = {"ref": {"short_cite": citation.get("short_cite", "")}}
        authors, years = citation.get("authors"), citation.get("year")

        if isinstance(authors, list) and isinstance(years, list):
            for i, (a, y) in enumerate(zip(authors, years), 1):
                metadata["ref"][f"ref{i}"] = {"authors": a, "year": y}
        elif authors and years:
            metadata["ref"]["ref1"] = {"authors": authors, "year": years}

        return metadata


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def main():
    """"""
    data_dir = app_dir / "data" / "sets"

    in_data = data_dir / "raw" / "jimmy-rxn-db.csv"
    out_dir = data_dir / "preprocessed" / "jimmy_data"
    jimmy_db = CSVPreprocessor(in_data, out_dir, "jimmy")
    jimmy_db.preprocess()

    in_data = data_dir / "raw" / "hp11-rxn-db.txt"
    out_dir = data_dir / "preprocessed" / "hp11_data"
    hp11_db = HP11DBPreprocessor(in_data, out_dir)
    hp11_db.preprocess()

    print("\nDatasets preprocessed!")


if __name__ == "__main__":
    main()
