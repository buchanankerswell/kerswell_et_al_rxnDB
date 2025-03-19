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

    # Keeps track of plot labels on/off
    plot_labels = reactive.value(True)

    @reactive.effect
    @reactive.event(input.show_plot_labels)
    def show_plot_labels() -> None:
        """
        Toggles the selection state of plot labels in the UI.

        When called, this function will turn onn/off the plot labels by toggling the
        state of the `plot_labels` flag.

        Returns:
            None
        """
        plot_labels.set(not plot_labels())

    # Keeps track of whether all reactants or products are selected
    selected_all_reactants = reactive.value(False)
    selected_all_products = reactive.value(False)

    @reactive.effect
    @reactive.event(input.toggle_reactants)
    def toggle_reactants() -> None:
        """
        Toggles the selection state of all reactants in the UI.

        When called, this function will either select all phases as reactants
        or reset the selection based on the current state. It updates the
        checkbox group for reactants in the UI and toggles the state of the
        `selected_all_reactants` flag.

        Returns:
            None
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
        Toggles the selection state of all products in the UI.

        When called, this function will either select all phases as products
        or reset the selection based on the current state. It updates the
        checkbox group for products in the UI and toggles the state of the
        `selected_all_products` flag.

        Returns:
            None
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
        Filters the reaction database based on selected reactants and products.

        This function retrieves the current selections for reactants and products
        from the UI and filters the dataset accordingly. It returns a DataFrame
        containing the filtered data that matches the selected reactants and products.

        Returns:
            pd.DataFrame: The filtered reaction data.
        """
        reactants: list[str] = input.reactants()
        products: list[str] = input.products()

        return db.filter_data(df, reactants, products)

    @render_widget
    def visualize_rxns() -> go.FigureWidget:
        """
        Renders a plot of reaction lines and labels.

        This function generates a plot based on the filtered reaction data,
        displaying reaction lines and midpoints. It adjusts the plot styling
        based on the current mode (light or dark) and returns a Plotly
        FigureWidget for rendering in the UI.

        Returns:
            go.FigureWidget: The Plotly figure displaying reaction lines and labels.
        """
        # Configure plotting styles
        dark_mode: bool = input.mode() == "dark"
        show_labels = plot_labels()

        # Get reaction lines and midpoints
        plot_df, mp_df = db.get_reaction_line_and_midpoint_dfs(filtered_df())

        # Draw Supergraph
        fig = plot_reaction_lines(plot_df, mp_df, filtered_df()["id"], dark_mode,
                                  color_palette="Alphabet", show_labels=show_labels)

        return fig

    @render.data_frame
    def rxns_db() -> render.DataTable:
        """
        Renders a DataTable of filtered reaction data.

        This function generates a table of filtered reaction data, selecting
        specific columns to display. It renders the table with a height of 98%
        to fit the available space in the UI.

        Returns:
            render.DataTable: The rendered DataTable of filtered reaction data.
        """
        # Select columns for table
        cols: list[str] = ["id", "formula", "rxn", "polynomial", "ref"]

        return render.DataTable(filtered_df()[cols], height="98%")

# Create the Shiny app
app: App = App(app_ui, server)
