import numpy as np
import pandas as pd
import plotly.express as px
from rxnDB.utils import app_dir
import plotly.graph_objects as go

def plot_reaction_lines(df: pd.DataFrame, mp: pd.DataFrame, rxn_ids: list,
                        dark_mode: bool, font_size: float=20,
                        color_palette: str="Set1", show_labels: bool=True) -> go.Figure:
    """
    Plots the reaction lines on a phase diagram using Plotly.

    This function creates a Plotly figure displaying the reaction lines
    for a given set of reactions and their corresponding labels on
    a phase diagram. The figure is customized based on the provided
    dark mode setting and font size.

    Args:
        df (pd.DataFrame): DataFrame containing the reaction data for plotting.
        mp (pd.DataFrame): DataFrame containing the midpoints for each reaction for labelling.
        rxn_ids (list): A list of reaction IDs to be plotted.
        dark_mode (bool): If True, the plot will be configured for dark mode.
        font_size (float, optional): The font size for axis labels and titles. Defaults to 20.
        color_palette (str or list, optional): Name of a Plotly color scale. Defaults to Set1.
        show_labels (bool): If True, the reaction lines will show labels for their IDs.

    Returns:
        go.Figure: A Plotly figure containing the reaction lines and midpoint scatter points.
    """
    # Create a figure object
    fig = go.Figure()

    # Tooltip template
    hovertemplate: str = (
        "ID: %{customdata[0]}<br>"
        "Rxn: %{customdata[1]}<extra></extra><br>"
        "T: %{x:.1f} ˚C<br>"
        "P: %{y:.2f} GPa<br>"
    )

    # Get color palette
    palette = get_color_palette(color_palette)

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

    # Add text labels to midpoints
    if show_labels:
        annotations = [dict(x=row["T (˚C)"], y=row["P (GPa)"], text=row["id"],
                            showarrow=True, arrowhead=2) for _, row in mp.iterrows()]
        fig.update_layout(annotations=annotations)

    # Update layout
    layout_settings = configure_layout(dark_mode, font_size)
    fig.update_layout(
        xaxis_title="Temperature (˚C)",
        yaxis_title="Pressure (GPa)",
        showlegend=False,
        autosize=True,
        **layout_settings
    )

    return fig

def configure_layout(dark_mode: bool, font_size: float=20) -> dict:
    """
    Returns a dictionary of layout settings for Plotly figures.

    This function configures the layout of a Plotly figure, including
    axis properties, background colors, font styles, and grid lines.
    The layout is dynamically adjusted based on the dark mode setting
    and font size provided.

    Args:
        dark_mode (bool): If True, the layout will be configured for dark mode.
        font_size (float, optional): The font size for axis labels and titles. Defaults to 20.

    Returns:
        dict: A dictionary containing the layout configuration for the Plotly figure.
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

def get_color_palette(color_palette: str) -> list[str]:
    """
    Returns a list of colors based on the specified color palette.

    Args:
        color_palette (str): The name of the color palette to use.

    Returns:
        list[str]: A list of color hex codes.
    """
    if color_palette in dir(px.colors.qualitative):
        return getattr(px.colors.qualitative, color_palette)
    elif color_palette.lower() in px.colors.named_colorscales():
        return [color[1] for color in px.colors.get_colorscale(color_palette)]
    else:
        print(f"'{color_palette}' is not a valid palette, using default 'Set1'.")
        return px.colors.qualitative.Set1
