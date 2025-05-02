#######################################################
## .0.              Load Libraries               !!! ##
#######################################################
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


#######################################################
## .1.                 Plotly                    !!! ##
#######################################################
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def plot_reaction_lines(
    df: pd.DataFrame,
    ids: list,
    dark_mode: bool,
    font_size: float = 20,
    color_palette: str = "Set1",
) -> go.Figure:
    """
    Plot reaction lines (phase diagram) using plotly
    """
    required_columns = {
        "id",
        "rxn",
        "plot_type",
        "T",
        "P",
        "T_half_range",
        "P_half_range",
    }
    if not required_columns.issubset(df.columns):
        missing = required_columns - set(df.columns)
        raise ValueError(f"Missing required columns in DataFrame: {missing}")

    missing_ids = [rid for rid in ids if rid not in df["id"].unique()]
    if missing_ids:
        print(f"Warning: These ids were not found in the DataFrame: {missing_ids}")

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
    for i, id in enumerate(ids):
        d: pd.DataFrame = df.query(f"id == '{id}'")

        if d.empty:
            continue

        plot_type = d["plot_type"].iloc[0]

        if plot_type == "curve":
            fig.add_trace(
                go.Scatter(
                    x=d["T"],
                    y=d["P"],
                    mode="lines",
                    line=dict(width=2, color=palette[i % len(palette)]),
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
                    marker=dict(size=8, color="black"),
                    error_x=dict(type="data", array=d["T_half_range"], visible=True),
                    error_y=dict(type="data", array=d["P_half_range"], visible=True),
                    hovertemplate=hovertemplate,
                    customdata=np.stack((d["id"], d["rxn"]), axis=-1),
                )
            )

    # Update layout
    layout_settings: dict = configure_layout(dark_mode, font_size)
    fig.update_layout(
        xaxis_title="Temperature (˚C)",
        yaxis_title="Pressure (GPa)",
        showlegend=False,
        autosize=True,
        **layout_settings,
    )

    return fig


#######################################################
## .2.             Helper Functions              !!! ##
#######################################################
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def add_reaction_labels(fig: go.Figure, mp: pd.DataFrame) -> None:
    """
    Adds labels at midpoints of each reaction curves
    """
    annotations: list[dict] = [
        dict(
            x=row["T"],
            y=row["P"],
            text=row["id"],
            showarrow=True,
            arrowhead=2,
        )
        for _, row in mp.iterrows()
    ]
    fig.update_layout(annotations=annotations)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def calculate_rxn_curve_midpoints(df: pd.DataFrame) -> pd.DataFrame:
    """
    Extracts the midpoint of each PT curve in the input DataFrame
    """
    midpoints = []

    for rxn_id, group in df.groupby("id"):
        group_sorted = group.sort_values("T").reset_index(drop=True)
        group_sorted = group_sorted.dropna(subset=["T", "P"])
        n = len(group_sorted)

        if n == 0:
            continue
        elif n % 2 == 1:
            # Odd number of points: take the middle
            midpoint_row = group_sorted.iloc[n // 2]
            T_mid = midpoint_row["T"]
            P_mid = midpoint_row["P"]
        else:
            # Even number of points: average the two central points
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
def configure_layout(dark_mode: bool, font_size: float = 20) -> dict:
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
