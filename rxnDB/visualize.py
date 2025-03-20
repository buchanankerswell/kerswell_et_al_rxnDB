#######################################################
## .0.              Load Libraries               !!! ##
#######################################################
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Utilities !!
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import numpy as np
import pandas as pd
from rxnDB.utils import app_dir

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Plotting !!
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import plotly.express as px
import plotly.graph_objects as go

#######################################################
## .1.                 Plotly                    !!! ##
#######################################################
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def plot_reaction_lines(df: pd.DataFrame, rxn_ids: list, dark_mode: bool,
                        font_size: float=20, color_palette: str="Set1") -> go.Figure:
    """
    Plot reaction lines (phase diagram) using plotly
    """
    fig = go.Figure()

    # Tooltip template
    hovertemplate: str = (
        "ID: %{customdata[0]}<br>"
        "Rxn: %{customdata[1]}<extra></extra><br>"
        "T: %{x:.1f} ˚C<br>"
        "P: %{y:.2f} GPa<br>"
    )

    palette: list[str] = get_color_palette(color_palette)

    # Plot reaction lines
    for id in rxn_ids:
        d: pd.DataFrame = df.query(f"id == {id}")
        fig.add_trace(go.Scatter(
            x=d["T (˚C)"],
            y=d["P (GPa)"],
            mode="lines",
            line=dict(width=2, color=palette[id % len(palette)]),
            hovertemplate=hovertemplate,
            customdata=np.stack((d["id"], d["Rxn"]), axis=-1)
        ))

    # Update layout
    layout_settings: dict = configure_layout(dark_mode, font_size)
    fig.update_layout(
        xaxis_title="Temperature (˚C)",
        yaxis_title="Pressure (GPa)",
        showlegend=False,
        autosize=True,
        **layout_settings
    )

    return fig

#######################################################
## .2.             Helper Functions              !!! ##
#######################################################
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def add_reaction_labels(fig: go.Figure, mp: pd.DataFrame) -> None:
    """
    Adds labels at midpoints of each reaction curves
    """
    annotations: list[dict] = [
        dict(x=row["T (˚C)"], y=row["P (GPa)"], text=row["id"], showarrow=True, arrowhead=2)
        for _, row in mp.iterrows()
    ]
    fig.update_layout(annotations=annotations)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def configure_layout(dark_mode: bool, font_size: float=20) -> dict:
    """
    Configure plotly style (theme)
    """
    border_color: str = "#E5E5E5" if dark_mode else "black"
    grid_color: str = "#999999" if dark_mode else "#E5E5E5"
    tick_color: str = "#E5E5E5" if dark_mode else "black"
    label_color: str = "#E5E5E5" if dark_mode else "black"
    plot_bgcolor: str = "#1D1F21" if dark_mode else "#FFF"
    paper_bgcolor: str = "#1D1F21" if dark_mode else "#FFF"
    font_color: str = "#E5E5E5" if dark_mode else "black"
    legend_bgcolor: str = "#404040" if dark_mode else "#FFF"

    return {
        "template": "plotly_dark" if dark_mode else "plotly_white",
        "font": {"size": font_size, "color": font_color},
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
            "mirror": True
        },
        "yaxis": {
            "range": (-0.5, 19),
            "gridcolor": grid_color,
            "title_font": {"color": label_color},
            "tickfont": {"color": tick_color},
            "showline": True,
            "linecolor": border_color,
            "linewidth": 2,
            "mirror": True
        },
        "legend": {
            "font": {"color": font_color},
            "bgcolor": legend_bgcolor,
        }
    }

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def get_color_palette(color_palette: str) -> list[str]:
    """
    Get color palette
    """
    if color_palette in dir(px.colors.qualitative):
        return getattr(px.colors.qualitative, color_palette)
    elif color_palette.lower() in px.colors.named_colorscales():
        return [color[1] for color in px.colors.get_colorscale(color_palette)]
    else:
        print(f"'{color_palette}' is not a valid palette, using default 'Set1'.")
        return px.colors.qualitative.Set1
