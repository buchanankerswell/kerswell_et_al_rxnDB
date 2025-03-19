import re
import sphinx_rtd_theme
from sphinx.locale import _
import revitron_sphinx_theme
from importlib.metadata import version as get_version

project = "rxnDB"
slug = re.sub(r"\W+", "-", project.lower())
version = get_version("rxnDB")
release = get_version("rxnDB")
copyright = "2025, Buchanan Kerswell"
author = "Buchanan Kerswell"
copyright = "<a href='https://buchanankerswell.com'>Buchanan Kerswell</a>"
language = "en"

extensions = [
    "autoapi.extension",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.mathjax",
    "sphinx.ext.viewcode",
    "sphinxcontrib.httpdomain",
    "revitron_sphinx_theme"
]

autoapi_dirs = ["../rxnDB"]
autodoc_default_options = {"autosummary": True}

templates_path = ["_templates"]
source_suffix = ".rst"
exclude_patterns = []
locale_dirs = ["locale/"]
gettext_compact = False

master_doc = "index"
suppress_warnings = ["image.nonlocal_uri"]

intersphinx_mapping = {
    "rtd": ("https://docs.readthedocs.io/en/latest/", None),
    "sphinx": ("http://www.sphinx-doc.org/en/stable/", None),
}

#html_theme = "sphinx_rtd_theme"
html_theme = "revitron_sphinx_theme"
html_static_path = ["_static"]

html_theme_options = {
}

html_theme_options = {
    "color_scheme": "light",
    "collapse_navigation": False,
    "navigation_depth": 4,
    "github_url": "https://github.com/buchanankerswell/kerswell_et_al_rxnDB",
}

html_logo = "rxndb-logo.svg"
html_title = "rxnDB"
html_show_sourcelink = True
htmlhelp_basename = slug

html_context = {
    "landing_page": {
        "menu": [
            {"title": "Installation", "url": "installation.html"},
            {"title": "Usage", "url": "installation.html"},
            {"title": "GitHub", "url": "https://github.com/buchanankerswell/kerswell_et_al_rxnDB"}
        ]
    }
}
