#######################################################
## .0.              Load Libraries               !!! ##
#######################################################
from dataclasses import dataclass

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


#######################################################
## .1.                 Plotly                    !!! ##
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
        """Initialize the plotter with the dataframe that should already contain color information."""
        # Verify necessary color information is present
        if "rxn_color_key" not in self.df.columns:
            raise ValueError(
                "DataFrame must contain 'rxn_color_key' column. Did you use the processor's get_colors_for_filtered_df method?"
            )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def plot(self) -> go.Figure:
        """
        Plot reaction lines (phase diagram) using plotly.
        """
        required_columns = {
            "id",
            "rxn",
            "plot_type",
            "T",
            "P",
            "T_half_range",
            "P_half_range",
            "rxn_color_key",
        }

        if not required_columns.issubset(self.df.columns):
            missing = required_columns - set(self.df.columns)
            raise ValueError(f"Missing required columns in DataFrame: {missing}")

        fig = go.Figure()

        hovertemplate = (
            "ID: %{customdata[0]}<br>"
            "Rxn: %{customdata[1]}<extra></extra><br>"
            "T: %{x:.1f} ˚C<br>"
            "P: %{y:.2f} GPa<br>"
        )

        for rid in self.ids:
            d = self.df.query("id == @rid")
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
                        customdata=np.stack((d["id"], d["rxn"]), axis=-1),
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
                            type="data", array=d["T_half_range"], visible=True
                        ),
                        error_y=dict(
                            type="data", array=d["P_half_range"], visible=True
                        ),
                        hovertemplate=hovertemplate,
                        customdata=np.stack((d["id"], d["rxn"]), axis=-1),
                    )
                )

        layout_settings = self._configure_layout()
        fig.update_layout(
            xaxis_title="Temperature (˚C)",
            yaxis_title="Pressure (GPa)",
            showlegend=False,
            autosize=True,
            **layout_settings,
        )
        return fig

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _get_color_palette(self) -> list[str]:
        """"""
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
    def _configure_layout(self) -> dict:
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
                "range": (0, 1650),
                "gridcolor": grid_color,
                "title_font": {"color": label_color},
                "tickfont": {"color": tick_color},
                "showline": True,
                "linecolor": border_color,
                "linewidth": 2,
                "mirror": True,
            },
            "yaxis": {
                "range": (-0.5, 19),
                "gridcolor": grid_color,
                "title_font": {"color": label_color},
                "tickfont": {"color": tick_color},
                "showline": True,
                "linecolor": border_color,
                "linewidth": 2,
                "mirror": True,
            },
            "legend": {
                "font": {"color": font_color},
                "bgcolor": legend_bgcolor,
            },
        }

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def calculate_midpoints(self) -> pd.DataFrame:
        """
        Extracts the midpoint of each PT curve in the input DataFrame
        """
        midpoints = []

        for rxn_id, group in self.df.groupby("id"):
            group_sorted = group.sort_values("T").reset_index(drop=True)
            group_sorted = group_sorted.dropna(subset=["T", "P"])
            n = len(group_sorted)

            if n == 0:
                continue
            elif n % 2 == 1:
                midpoint_row = group_sorted.iloc[n // 2]
                T_mid = midpoint_row["T"]
                P_mid = midpoint_row["P"]
            else:
                row1 = group_sorted.iloc[n // 2 - 1]
                row2 = group_sorted.iloc[n // 2]
                T_mid = (row1["T"] + row2["T"]) / 2
                P_mid = (row1["P"] + row2["P"]) / 2

            midpoints.append(
                {
                    "T": T_mid,
                    "P": P_mid,
                    "rxn": group_sorted["rxn"].iloc[0],
                    "id": rxn_id,
                }
            )

        return pd.DataFrame(midpoints)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def add_labels(self, fig: go.Figure, midpoints_df: pd.DataFrame) -> None:
        """
        Adds labels at midpoints of each reaction curve
        """
        annotations = [
            dict(
                x=row["T"],
                y=row["P"],
                text=row["id"],
                showarrow=True,
                arrowhead=2,
            )
            for _, row in midpoints_df.iterrows()
        ]
        fig.update_layout(annotations=annotations)
