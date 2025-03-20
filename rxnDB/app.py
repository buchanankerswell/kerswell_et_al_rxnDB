import os
import pandas as pd
from PIL import Image
import plotly.io as pio
import plotly.express as px
import rxnDB.visualize as vis
import rxnDB.data.loader as db
import plotly.graph_objects as go
from rxnDB.ui import configure_ui
from shinywidgets import render_plotly
from shiny import Inputs, Outputs, Session
from shiny import App, reactive, render, ui

# Get unique phases from database
phases: list[str] = db.phases
init_phases: list[str] = ["Ky", "And", "Sil", "Ol", "Wd"]

# Configure UI with initial selection of rxnDB phases
app_ui = configure_ui(phases, init_phases)

# Server logic (reactivity)
def server(input: Inputs, output: Outputs, session: Session) -> None:
    df: pd.DataFrame = db.data
    df_filt: pd.DataFrame = db.filter_data(df, init_phases, init_phases)

    # Keeps track of plot labels on/off
    labels: reactive.Value[bool] = reactive.value(True)

    @reactive.effect
    @reactive.event(input.show_plot_labels)
    def show_plot_labels() -> None:
        """
        Toggles the selection state of plot labels in the UI
        """
        labels.set(not labels())

    # Keeps track of whether all reactants or products are selected
    selected_all_reactants: reactive.Value[bool] = reactive.value(False)
    selected_all_products: reactive.Value[bool] = reactive.value(False)

    @reactive.effect
    @reactive.event(input.toggle_reactants)
    def toggle_reactants() -> None:
        """
        Toggles the selection state of all reactants in the UI
        """
        if selected_all_reactants():
            ui.update_checkbox_group("reactants", selected=init_phases)
        else:
            ui.update_checkbox_group("reactants", selected=phases)

        selected_all_reactants.set(not selected_all_reactants())

    @reactive.effect
    @reactive.event(input.toggle_products)
    def toggle_products() -> None:
        """
        Toggles the selection state of all products in the UI
        """
        if selected_all_products():
            ui.update_checkbox_group("products", selected=init_phases)
        else:
            ui.update_checkbox_group("products", selected=phases)

        selected_all_products.set(not selected_all_products())

    @reactive.calc
    def filtered_df() -> pd.DataFrame:
        """
        Filters the reaction database based on selected reactants and products
        """
        reactants: list[str] = input.reactants()
        products: list[str] = input.products()

        return db.filter_data(df, reactants, products)

    @render_plotly
    def plotly() -> go.FigureWidget:
        """
        Renders a plot of reaction lines and labels
        """
        # Get reaction lines and midpoints
        plot_df: pd.DataFrame = db.calculate_reaction_curves(df_filt)

        # Draw Supergraph
        fig: go.FigureWidget = vis.plot_reaction_lines(
            df=plot_df,
            rxn_ids=df_filt["id"],
            dark_mode=False,
            color_palette="Alphabet"
        )

        return fig

    @reactive.effect
    def update_plotly_labels() -> None:
        """
        Updates the plotly figure (labels only)
        """
        fig = plotly.widget

        current_x_range = fig.layout.xaxis.range
        current_y_range = fig.layout.yaxis.range

        dark_mode: bool = input.mode() == "dark"
        show_labels: bool = labels()
        plot_df = db.calculate_reaction_curves(filtered_df())
        mp_df = db.calculate_midpoints(filtered_df())

        updated_fig = vis.plot_reaction_lines(
            df=plot_df,
            rxn_ids=filtered_df()["id"],
            dark_mode=dark_mode,
            color_palette="Alphabet"
        )
        updated_fig.layout.xaxis.range = current_x_range
        updated_fig.layout.yaxis.range = current_y_range

        if show_labels:
            vis.add_reaction_labels(updated_fig, mp_df)
            fig.layout.annotations = updated_fig.layout.annotations
        else:
            fig.layout.annotations = ()

    @reactive.effect
    def update_plotly() -> None:
        """
        Updates the plotly figure (expect for labels)
        """
        fig = plotly.widget

        current_x_range = fig.layout.xaxis.range
        current_y_range = fig.layout.yaxis.range

        dark_mode: bool = input.mode() == "dark"
        plot_df = db.calculate_reaction_curves(filtered_df())

        updated_fig = vis.plot_reaction_lines(
            df=plot_df,
            rxn_ids=filtered_df()["id"],
            dark_mode=dark_mode,
            color_palette="Alphabet"
        )
        updated_fig.layout.xaxis.range = current_x_range
        updated_fig.layout.yaxis.range = current_y_range

        fig.data = ()
        fig.add_traces(updated_fig.data)

        fig.layout.update(updated_fig.layout)

    @reactive.effect
    @reactive.event(input.download_plotly)
    def save_figure() -> None:
        """
        Save the current Plotly figure as an image when the button is clicked
        """
        fig = plotly.widget

        filename: str = "rxndb-phase-diagram.png"
        dpi: int = 300
        width_px: int = int(3.5 * dpi)
        height_px: int = int(4 * dpi)

        show_download_message(filename)

        pio.write_image(fig, file=filename, width=width_px, height=height_px)

        with Image.open(filename) as img:
            img = img.convert("RGB")
            img.save(filename, dpi=(dpi, dpi))

    def show_download_message(filename) -> None:
        """
        Render download message
        """
        filepath: str = os.path.join(os.getcwd(), filename)
        m = ui.modal(
            f"{filepath}",
            title="Downloading ...",
            easy_close=True,
            footer=None,
        )
        ui.modal_show(m)


    @render.data_frame
    def database() -> render.DataTable:
        """
        Renders a DataTable of filtered reaction data
        """
        cols: list[str] = ["id", "formula", "rxn", "polynomial", "ref"]
        return render.DataTable(filtered_df()[cols], height="98%")

# Create the Shiny app
app: App = App(app_ui, server)
