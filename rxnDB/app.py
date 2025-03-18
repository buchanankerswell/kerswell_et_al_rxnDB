import pandas as pd
import plotly.express as px
import rxnDB.data.loader as db
import plotly.graph_objects as go
from rxnDB.ui import configure_ui
from shinywidgets import render_widget
from shiny import Inputs, Outputs, Session
from shiny import App, reactive, render, ui
from rxnDB.visualize import plot_reaction_lines

# Get unique phases and set initial selection
phases: list[str] = db.phases
init_phases: list[str] = ["Ky", "And", "Sil", "Ol", "Wd"]

# Configure UI
app_ui = configure_ui(phases, init_phases)

# Server logic (reactivity)
def server(input: Inputs, output: Outputs, session: Session) -> None:
    df: pd.DataFrame = db.data

    # Keeps track of whether all reactants or products are selected
    selected_all_reactants = reactive.value(False)
    selected_all_products = reactive.value(False)

    @reactive.effect
    @reactive.event(input.toggle_reactants)
    def toggle_reactants() -> None:
        """
        Toggles all reactants on/off
        """
        if selected_all_reactants():
            ui.update_checkbox_group("reactants", selected=init_phases)
        else:
            ui.update_checkbox_group("reactants", selected=phases)

        # Toggle the state of selected_all_reactants
        selected_all_reactants.set(not selected_all_reactants())

    @reactive.effect
    @reactive.event(input.toggle_products)
    def toggle_products() -> None:
        """
        Toggles all products on/off
        """
        if selected_all_products():
            ui.update_checkbox_group("products", selected=init_phases)
        else:
            ui.update_checkbox_group("products", selected=phases)

        # Toggle the state of selected_all_products
        selected_all_products.set(not selected_all_products())

    @reactive.calc
    def filtered_df() -> pd.DataFrame:
        """
        Filters the rxnDB as reactants and/or products are selected
        """
        reactants: list[str] = input.reactants()
        products: list[str] = input.products()

        return db.filter_data(df, reactants, products)

    @render_widget
    def visualize_rxns() -> go.FigureWidget:
        """
        Renders reaction lines and labels plot
        """
        # Configure plotting styles
        dark_mode: bool = input.mode() == "dark"

        # Get reaction lines and midpoints
        plot_df, mp_df = db.get_reaction_line_and_midpoint_dfs(filtered_df())

        # Draw Supergraph
        fig = plot_reaction_lines(plot_df, mp_df, filtered_df()["id"], dark_mode)

        return fig

    @render.data_frame
    def rxns_db() -> render.DataTable:
        """
        Renders the DataTable.
        """
        # Select columns for table
        cols: list[str] = ["id", "formula", "rxn", "polynomial", "ref"]

        return render.DataTable(filtered_df()[cols], height="98%")

app: App = App(app_ui, server)
