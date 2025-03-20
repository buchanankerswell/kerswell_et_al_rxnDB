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
    df_init: pd.DataFrame = db.filter_data_by_rxn(df, init_phases, init_phases)

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
        Toggles the selection state of selected_all_reactants
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
        Toggles the selection state of selected_all_products
        """
        if selected_all_products():
            ui.update_checkbox_group("products", selected=init_phases)
        else:
            ui.update_checkbox_group("products", selected=phases)

        selected_all_products.set(not selected_all_products())

    # Keeps track of the rows selected in the DataTable
    selected_row_ids: reactive.Value[list[int]] = reactive.value([])

    @reactive.effect
    @reactive.event(input.clear_selection)
    def clear_selected_rows() -> None:
        """
        Clears all selections using a button
        """
        selected_row_ids.set([])

    find_similar_rxns: reactive.Value[bool] = reactive.value(False)

    @reactive.effect
    @reactive.event(input.toggle_find_similar_rxns)
    def toggle_find_similar_rxns() -> None:
        """
        Toggles the selection state of find_similar_rxns
        """
        find_similar_rxns.set(not find_similar_rxns())

    @reactive.effect
    @reactive.event(input.datatable_selected_rows)
    def update_selected_rows() -> None:
        """
        Update the selected_rows reactive value when table selections change
        """
        selected_indices: list[int] = input.datatable_selected_rows()

        if selected_indices:
            if input.reactants() != init_phases or input.products() != init_phases:
                current_table_data: pd.DataFrame = filter_df_datatable()
            else:
                current_table_data: pd.DataFrame = df_init

            # Extract selected row rxn "id" values
            selected_ids: list[int] = [
                current_table_data.iloc[i]["id"] for i in selected_indices]

            selected_row_ids.set(selected_ids)
        else:
            selected_row_ids.set([])

    @reactive.calc
    def filter_df_datatable() -> pd.DataFrame:
        """
        Filters the DataTable for the DataTable.
        Products and reactants are slected from the checked boxes only
        """
        reactants_checks: list[str] = input.reactants()
        products_checks: list[str] = input.products()

        return db.filter_data_by_rxn(df, reactants_checks, products_checks)

    @reactive.calc
    def filter_df_plotly() -> pd.DataFrame:
        """
        Filters the DataTable for the plotly.
        Products and reactants are reconciled between the checked boxes and DataTable
        """
        reactants_checks: list[str] = input.reactants()
        products_checks: list[str] = input.products()

        # Get the current selected IDs from the reactive value
        current_selected_ids = selected_row_ids()

        if not find_similar_rxns():
            if current_selected_ids and len(current_selected_ids) > 0:
                return db.filter_data_by_ids(df, current_selected_ids)
            else:
                # No table selections, just filter based on checkboxes
                return db.filter_data_by_rxn(df, reactants_checks, products_checks)

        if current_selected_ids and len(current_selected_ids) > 0:
            # Filter reactants and products from the selected rows
            filtered_reactants = df[df["id"].isin(current_selected_ids)][
                ["reactant1", "reactant2", "reactant3"]].values.flatten()
            filtered_reactants = pd.Series(filtered_reactants).dropna()

            filtered_products = df[df["id"].isin(current_selected_ids)][
                ["product1", "product2", "product3"]].values.flatten()
            filtered_products = pd.Series(filtered_products).dropna()

            return db.filter_data_by_rxn(df, filtered_reactants, filtered_products)
        else:
            # No table selections, just filter based on checkboxes
            return db.filter_data_by_rxn(df, reactants_checks, products_checks)

    @reactive.calc
    def filter_df_similar_plotly() -> pd.DataFrame:
        """
        Filters the DataTable for the plotly.
        Products and reactants are reconciled between the checked boxes and DataTable
        """
        reactants_checks: list[str] = input.reactants()
        products_checks: list[str] = input.products()

        # Get the current selected IDs from the reactive value
        current_selected_ids = selected_row_ids()

        if current_selected_ids and len(current_selected_ids) > 0:
            # Filter reactants and products from the selected rows
            filtered_reactants = df[df["id"].isin(current_selected_ids)][
                ["reactant1", "reactant2", "reactant3"]].values.flatten()
            filtered_reactants = pd.Series(filtered_reactants).dropna()

            filtered_products = df[df["id"].isin(current_selected_ids)][
                ["product1", "product2", "product3"]].values.flatten()
            filtered_products = pd.Series(filtered_products).dropna()

            return db.filter_data_by_rxn(df, filtered_reactants, filtered_products)
        else:
            # No table selections, just filter based on checkboxes
            return db.filter_data_by_rxn(df, reactants_checks, products_checks)

    @render_plotly
    def plotly() -> go.FigureWidget:
        """
        Renders a plot of reaction lines and labels
        """
        # Get reaction lines and midpoints
        plot_df: pd.DataFrame = db.calculate_reaction_curves(df_init)

        # Draw Supergraph
        fig: go.FigureWidget = vis.plot_reaction_lines(
            df=plot_df,
            rxn_ids=df_init["id"],
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
        plot_df = db.calculate_reaction_curves(filter_df_plotly())
        mp_df = db.calculate_midpoints(filter_df_plotly())

        updated_fig = vis.plot_reaction_lines(
            df=plot_df,
            rxn_ids=filter_df_plotly()["id"],
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
        plot_df = db.calculate_reaction_curves(filter_df_plotly())

        updated_fig = vis.plot_reaction_lines(
            df=plot_df,
            rxn_ids=filter_df_plotly()["id"],
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
    def datatable() -> render.DataTable:
        """
        Renders a DataTable of filtered reaction data
        """
        # Refresh table on clear selection
        _ = input.clear_selection()

        cols: list[str] = ["id", "formula", "rxn", "polynomial", "ref"]

        if input.reactants() != init_phases or input.products() != init_phases:
            # Use filtered data when user has made selections
            data: pd.DataFrame = filter_df_datatable()[cols]
        else:
            # Use initial filtered data
            data: pd.DataFrame = df_init[cols]

        return render.DataTable(data, height="98%", selection_mode="rows")

# Create the Shiny app
app: App = App(app_ui, server)
