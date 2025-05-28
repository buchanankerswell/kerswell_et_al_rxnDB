#######################################################
## .0. Load Libraries                            !!! ##
#######################################################
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go


#######################################################
## .1. Plotly                                    !!! ##
#######################################################
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@dataclass
class RxnDBPlotter:
    df: pd.DataFrame
    ids: list[str]
    dark_mode: bool = False
    font_size: float = 20

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def __post_init__(self):
        """"""
        if "rxn_color_key" not in self.df.columns:
            raise ValueError(
                "DataFrame must contain 'rxn_color_key' column. Did you use the processor's get_colors_for_filtered_df method?"
            )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def plot(self, temperature_units: str, pressure_units: str) -> go.Figure:
        """
        Plot reaction lines (phase diagram) using plotly.
        """
        required_cols = {
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
        }

        if not required_cols.issubset(self.df.columns):
            missing = required_cols - set(self.df.columns)
            raise ValueError(f"Missing required columns in DataFrame: {missing}")

        if temperature_units == "celcius":
            temperature_units_label = "˚C"
        elif temperature_units == "kelvin":
            temperature_units_label = "K"
        else:
            raise ValueError(f"Unknown temperature unit: {temperature_units}")

        if pressure_units == "gigapascal":
            pressure_units_label = "GPa"
        elif pressure_units == "kilobar":
            pressure_units_label = "kbar"
        else:
            raise ValueError(f"Unknown pressure unit: {pressure_units}")

        fig = go.Figure()

        hovertemplate = (
            "%{customdata[0]}<br>"
            "%{customdata[1]}<br>"
            f"(%{{x:.1f}} {temperature_units_label}, %{{y:.2f}} {pressure_units_label})<br>"
            "%{customdata[2]}<extra></extra>"
        )

        for rid in self.ids:
            d = self.df.query("unique_id == @rid")
            if d.empty:
                continue

            color = d["rxn_color_key"].iloc[0]
            plot_type = d["plot_type"].iloc[0]

            if plot_type == "curve":
                fig.add_trace(
                    go.Scatter(
                        x=d["T"],
                        y=d["P"],
                        mode="lines",
                        line=dict(width=2, color=color),
                        hovertemplate=hovertemplate,
                        customdata=np.stack(
                            (d["reaction"], d["unique_id"], d["type"]), axis=-1
                        ),
                    )
                )
            elif plot_type == "point":
                fig.add_trace(
                    go.Scatter(
                        x=d["T"],
                        y=d["P"],
                        mode="markers",
                        marker=dict(size=8, color=color),
                        error_x=dict(
                            type="data", array=d["T_uncertainty"], visible=True
                        ),
                        error_y=dict(
                            type="data", array=d["P_uncertainty"], visible=True
                        ),
                        hovertemplate=hovertemplate,
                        customdata=np.stack(
                            (d["reaction"], d["unique_id"], d["type"]), axis=-1
                        ),
                    )
                )

        layout_settings = self._configure_layout()

        fig.update_layout(
            xaxis_title=f"Temperature ({temperature_units_label})",
            yaxis_title=f"Pressure ({pressure_units_label})",
            showlegend=False,
            autosize=True,
            **layout_settings,
        )

        return fig

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _configure_layout(self) -> dict[str, Any]:
        """"""
        border_color = "#E5E5E5" if self.dark_mode else "black"
        grid_color = "#999999" if self.dark_mode else "#E5E5E5"
        tick_color = "#E5E5E5" if self.dark_mode else "black"
        label_color = "#E5E5E5" if self.dark_mode else "black"
        plot_bgcolor = "#1D1F21" if self.dark_mode else "#FFF"
        paper_bgcolor = "#1D1F21" if self.dark_mode else "#FFF"
        font_color = "#E5E5E5" if self.dark_mode else "black"
        legend_bgcolor = "#404040" if self.dark_mode else "#FFF"

        return {
            "template": "plotly_dark" if self.dark_mode else "plotly_white",
            "font": {"size": self.font_size, "color": font_color},
            "plot_bgcolor": plot_bgcolor,
            "paper_bgcolor": paper_bgcolor,
            "xaxis": {
                "gridcolor": grid_color,
                "title_font": {"color": label_color},
                "tickfont": {"color": tick_color},
                "showline": True,
                "linecolor": border_color,
                "linewidth": 2,
                "mirror": True,
                "constrain": "range",
            },
            "yaxis": {
                "gridcolor": grid_color,
                "title_font": {"color": label_color},
                "tickfont": {"color": tick_color},
                "showline": True,
                "linecolor": border_color,
                "linewidth": 2,
                "mirror": True,
                "constrain": "range",
            },
            "legend": {
                "font": {"color": font_color},
                "bgcolor": legend_bgcolor,
            },
        }
