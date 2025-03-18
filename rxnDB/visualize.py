import pandas as pd
import plotly.express as px
from rxnDB.utils import app_dir
import plotly.graph_objects as go

def configure_layout(dark_mode: bool, font_size: float=20) -> dict:
    """
    Returns a dictionary of layout settings for Plotly figures.
    """
    border_color: str = "#E5E5E5" if dark_mode else "black"
    grid_color: str = "#999999" if dark_mode else "#E5E5E5"
    tick_color: str = "#E5E5E5" if dark_mode else "black"
    label_color: str = "#E5E5E5" if dark_mode else "black"

    return {
        "template": "plotly_dark" if dark_mode else "plotly_white",
        "font": {"size": font_size, "color": "#E5E5E5" if dark_mode else "black"},
        "plot_bgcolor": "#404040" if dark_mode else "white",
        "paper_bgcolor": "#303030" if dark_mode else "white",
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
            "font": {"color": "#E5E5E5" if dark_mode else "black"},
            "bgcolor": "#404040" if dark_mode else "white",
        }
    }

def plot_reaction_lines(df: pd.DataFrame, mp: pd.DataFrame, rxn_ids: list,
                        dark_mode: bool, font_size: float=20) -> go.Figure:
    """
    Plots the reaction lines and midpoints (as scatter points) on a phase diagram using Plotly.
    """
    # Create a figure object
    fig = go.Figure()

    # Tooltip template
    hovertemplate = (
        "Rxn: %{text}<extra></extra><br>"
        "T: %{x:.1f} ˚C<br>"
        "P: %{y:.2f} GPa<br>"
    )

    # Plot reaction lines
    for id in rxn_ids:
        d = df.query(f"id == {id}")
        fig.add_trace(go.Scatter(
            x=d["T (˚C)"],
            y=d["P (GPa)"],
            mode="lines",
            line=dict(width=2),
            hovertemplate=hovertemplate,
            text=d["Rxn"]
        ))

    # Add text labels to midpoints
    annotations = [
        dict(x=row["T (˚C)"], y=row["P (GPa)"], text=row["id"], showarrow=True, arrowhead=2)
        for _, row in mp.iterrows()
    ]
    fig.update_layout(annotations=annotations)

    # Update layout
    layout_settings = configure_layout(dark_mode, font_size)
    fig.update_layout(
        xaxis_title="Temperature (˚C)",
        yaxis_title="Pressure (GPa)",
        showlegend=False,
        **layout_settings
    )

    return fig
