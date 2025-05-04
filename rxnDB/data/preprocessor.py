#######################################################
## .0. Load Libraries                            !!! ##
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
## .1. CSVPreprocessor                           !!! ##
#######################################################
@dataclass
class CSVPreprocessor:
    filepath: Path
    out_dir: Path
    unique_tag: str

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __post_init__(self) -> None:
        """"""
        if not self.filepath.exists():
            raise FileNotFoundError(f"Could not find {self.filepath}!")

        self.yaml = YAML()
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml.default_flow_style = False
        self.yaml.allow_unicode = True
        self.yaml.explicit_start = True

        self.out_dir.mkdir(parents=True, exist_ok=True)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def preprocess(self) -> None:
        """"""
        df = pd.read_csv(self.filepath)

        for i, (_, entry) in enumerate(df.iterrows()):
            print(
                f"Processing {self.unique_tag} entry {i + 1} ...",
                end="\r",
                flush=True,
            )

            rxn_data = self._process_entry(entry)
            filepath = self.out_dir / f"{self.unique_tag}-{i + 1:03}.yml"

            with open(filepath, "w") as file:
                self.yaml.dump(rxn_data, file)

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

        reactants = self._standardize_abbreviations(reactants)
        products = self._standardize_abbreviations(products)

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
    @classmethod
    def _standardize_abbreviations(cls, phases: list[str]) -> list[str]:
        """"""
        return [ABBREV_MAP.get(p, p) for p in phases]

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
        row: pd.Series, nsteps: int = 30
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
## .2. HP11Preprocessor                        !!! ##
#######################################################
@dataclass
class HP11Preprocessor:
    filepath: Path
    out_dir: Path

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __post_init__(self) -> None:
        """"""
        if not self.filepath.exists():
            raise FileNotFoundError(f"Could not find {self.filepath}!")

        self.yaml = YAML()
        self.yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml.default_flow_style = False
        self.yaml.allow_unicode = True
        self.yaml.explicit_start = True

        self.out_dir.mkdir(parents=True, exist_ok=True)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def preprocess(self) -> None:
        """"""
        raw_text = self.filepath.read_text()
        data_entries = self._split_into_entries(raw_text)

        for i, entry in enumerate(data_entries):
            print(f"Processing HP11 entry {i + 1} ...", end="\r", flush=True)

            rxn_data = self._process_entry(entry)
            filepath = self.out_dir / f"hp11-{i + 1:03}.yml"

            with open(filepath, "w") as file:
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

        reactants = self._standardize_abbreviations(reactants)
        products = self._standardize_abbreviations(products)

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
    @classmethod
    def _standardize_abbreviations(cls, phases: list[str]) -> list[str]:
        """"""
        return [ABBREV_MAP.get(p, p) for p in phases]

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

        return [strip_digits(r).lower() for r in reactants.split("+")], [
            strip_digits(p).lower() for p in products.split("+")
        ]

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @staticmethod
    def _split_citations(citation_text: str) -> dict[str, Any]:
        """"""
        parts: list[str] = re.split(r";\s*", citation_text)

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
# Constants
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
ABBREV_MAP: dict[str, str] = {
    "al": "aluminum",
    "smul": "aluminosilicate",
    "amul": "aluminosilicate",
    "ky": "aluminosilicate",
    "and": "aluminosilicate",
    "sil": "aluminosilicate",
    "sill": "aluminosilicate",
    "anth": "amphibole",
    "cumm": "amphibole",
    "fanth": "amphibole",
    "fact": "amphibole",
    "fgl": "amphibole",
    "gl": "amphibole",
    "grun": "amphibole",
    "parg": "amphibole",
    "rieb": "amphibole",
    "tr": "amphibole",
    "ts": "amphibole",
    "bdy": "baddeleyite",
    "ba i": "barium",
    "ba ii": "barium",
    "bi i": "bismuth",
    "bi ii": "bismuth",
    "bi iii": "bismuth",
    "bi v": "bismuth",
    "ann": "biotite",
    "east": "biotite",
    "phl": "biotite",
    "mnbi": "biotite",
    "naph": "biotite",
    "br": "brucite",
    "arag": "carbonate",
    "arg": "carbonate",
    "cav": "carbonate",
    "cc": "carbonate",
    "mag": "carbonate",
    "mgst": "carbonate",
    "rhc": "carbonate",
    "sid": "carbonate",
    "spu": "carbonate",
    "ty": "carbonate",
    "fcar": "carpholite",
    "mcar": "carpholite",
    "fcel": "celadonite",
    "chl": "chlorite",
    "clin": "chlorite",
    "daph": "chlorite",
    "mnchl": "chlorite",
    "fsud": "chlorite",
    "sud": "chlorite",
    "chum": "clinohumite",
    "cpx": "clinopyroxene",
    "acm": "clinopyroxene",
    "cats": "clinopyroxene",
    "cen": "clinopyroxene",
    "di": "clinopyroxene",
    "hed": "clinopyroxene",
    "hen": "clinopyroxene",
    "jd": "clinopyroxene",
    "kos": "clinopyroxene",
    "mgts": "clinopyroxene",
    "crd": "cordierite",
    "cg": "cordierite",
    "cgh": "cordierite",
    "hcrd": "cordierite",
    "fcrd": "cordierite",
    "mncrd": "cordierite",
    "mctd": "chloritoid",
    "fctd": "chloritoid",
    "mnctd": "chloritoid",
    "kao": "clay",
    "kcm": "clay",
    "cu": "copper",
    "cup": "copper",
    "ten": "copper",
    "deer": "deerite",
    "pha": "DHMS",
    "diam": "diamond",
    "dsp": "diaspore",
    "dol": "dolomite",
    "ank": "dolomite",
    "caes": "epidote",
    "cz": "epidote",
    "ep": "epidote",
    "fep": "epidote",
    "jgd": "epidote",
    "zo": "epidote",
    "kls": "feldspathoid",
    "lc": "feldspathoid",
    "ne": "feldspathoid",
    "nl": "feldspathoid",
    "sdl": "feldspathoid",
    "alm": "garnet",
    "py": "garnet",
    "gr": "garnet",
    "andr": "garnet",
    "spss": "garnet",
    "gt": "garnet",
    "maj": "garnet",
    "mcor": "garnet",
    "mgmj": "garnet",
    "geh": "gehlenite",
    "ge": "germanium",
    "gth": "goethite",
    "au": "gold",
    "gph": "graphite",
    "hlt": "salt",
    "syv": "salt",
    "cor": "hematite",
    "esk": "hematite",
    "hem": "hematite",
    "h2": "hydrogen",
    "h2s": "hydrogen sulfide",
    "fe": "iron",
    "fe-e": "iron",
    "tro": "iron-sulfide",
    "trov": "iron-sulfide",
    "trot": "iron-sulfide",
    "lot": "iron-sulfide",
    "pyr": "iron-sulfide",
    "ak": "ilmenite",
    "fak": "ilmenite",
    "mak": "ilmenite",
    "ilm": "ilmenite",
    "geik": "ilmenite",
    "pnt": "ilmenite",
    "hol": "k-feldspar",
    "san": "k-feldspar",
    "law": "lawsonite",
    "merw": "merwinite",
    "hltl": "melt",
    "abl": "melt",
    "anl": "melt",
    "corl": "melt",
    "dil": "melt",
    "enl": "melt",
    "fal": "melt",
    "fol": "melt",
    "kspl": "melt",
    "lcl": "melt",
    "liml": "melt",
    "nel": "melt",
    "perl": "melt",
    "ql": "melt",
    "syvl": "melt",
    "wol": "melt",
    "wal": "melt",
    "cel": "mica",
    "ma": "mica",
    "pa": "mica",
    "mu": "muscovite",
    "musc": "muscovite",
    "glt": "muscovite",
    "ni": "nickel",
    "nio": "nickel",
    "ol": "olivine",
    "lar": "olivine",
    "lrn": "olivine",
    "fa": "olivine",
    "fo": "olivine",
    "mont": "olivine",
    "teph": "olivine",
    "opx": "orthopyroxene",
    "en": "orthopyroxene",
    "oen": "orthopyroxene",
    "fs": "orthopyroxene",
    "pren": "orthopyroxene",
    "osm1": "osumilite",
    "osm2": "osumilite",
    "fosm": "osumilite",
    "o2": "oxygen",
    "pb": "lead",
    "apbo2": "lead",
    "mt": "magnetite",
    "bn": "periclase",
    "per": "periclase",
    "pc": "periclase",
    "fper": "periclase",
    "mang": "periclase",
    "ab": "plagioclase",
    "abh": "plagioclase",
    "an": "plagioclase",
    "plg": "plagioclase",
    "pre": "prehnite",
    "fpre": "prehnite",
    "pv": "perovskite",
    "fpv": "perovskite",
    "mpv": "perovskite",
    "apv": "perovskite",
    "capv": "perovskite",
    "cpv": "perovskite",
    "mgpv": "perovskite",
    "ppv": "perovskite",
    "pt": "platinum",
    "pump": "pumpellyite",
    "pmt": "pumpellyite",
    "fpm": "pumpellyite",
    "mpm": "pumpellyite",
    "prl": "pyrophyllite",
    "pxmn": "pyroxene",
    "rhod": "pyroxene",
    "pyx": "pyroxenoid",
    "rnk": "rankinite",
    "rw": "ringwoodite",
    "mrw": "ringwoodite",
    "frw": "ringwoodite",
    "rt": "rutile",
    "ru": "rutile",
    "me": "scapolite",
    "ag": "silver",
    "st": "staurolite",
    "fst": "staurolite",
    "mst": "staurolite",
    "mnst": "staurolite",
    "ames": "serpentine",
    "atg": "serpentine",
    "chr": "serpentine",
    "liz": "serpentine",
    "serp": "serpentine",
    "knor": "spinel",
    "sp": "spinel",
    "spr4": "spinel",
    "spr5": "spinel",
    "fspr": "spinel",
    "herc": "spinel",
    "mft": "spinel",
    "picr": "spinel",
    "usp": "spinel",
    "fstp": "stilpnomelane",
    "mstp": "stilpnomelane",
    "s2": "sulfide",
    "fta": "talc",
    "ta": "talc",
    "tats": "talc",
    "minn": "talc",
    "minm": "talc",
    "tap": "talc",
    "sph": "titanite",
    "tit": "titanite",
    "tpz": "topaz",
    "wad": "wadsleyite",
    "wd": "wadsleyite",
    "wa": "wadsleyite",
    "wds": "wadsleyite",
    "fwd": "wadsleyite",
    "mwd": "wadsleyite",
    "h2o": "water",
    "h2ol": "water",
    "pswo": "wollastonite",
    "wo": "wollastonite",
    "coe": "silica",
    "crst": "silica",
    "qtz": "silica",
    "q": "silica",
    "stv": "silica",
    "cstn": "silica",
    "trd": "silica",
    "vsv": "vesuvianite",
    "heu": "zeolite",
    "lmt": "zeolite",
    "stlb": "zeolite",
    "wrk": "zeolite",
    "zn": "zinc",
    "zrc": "zircon",
}


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def main():
    """"""
    raw_data_dir = app_dir / "data" / "sets" / "raw"
    preprocessed_data_dir = app_dir / "data" / "sets" / "preprocessed"

    in_data = raw_data_dir / "jimmy-rxn-db.csv"
    out_dir = preprocessed_data_dir / "jimmy_data"
    jimmy_db = CSVPreprocessor(in_data, out_dir, "jimmy")
    jimmy_db.preprocess()

    in_data = raw_data_dir / "hp11-rxn-db.txt"
    out_dir = preprocessed_data_dir / "hp11_data"
    hp11_db = HP11Preprocessor(in_data, out_dir)
    hp11_db.preprocess()

    print("\nDatasets preprocessed!")


if __name__ == "__main__":
    main()
