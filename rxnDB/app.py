#######################################################
## .0.              Load Libraries               !!! ##
#######################################################
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Utilities !!
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
import os
import pandas as pd
import rxnDB.data.loader as db

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Plotting !!
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
from PIL import Image
import plotly.io as pio
import plotly.express as px
import rxnDB.visualize as vis
import plotly.graph_objects as go

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Shiny app !!
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
from rxnDB.ui import configure_ui
from shinywidgets import render_plotly
from shiny import Inputs, Outputs, Session
from shiny import App, reactive, render, ui

#######################################################
## .1.                 Init UI                   !!! ##
#######################################################
phases: list[str] = db.phases
init_phases: list[str] = ["Ky", "And", "Sil", "Ol", "Wd"]
app_ui: ui.page_sidebar = configure_ui(phases, init_phases)

#######################################################
## .2.              Server Logic                 !!! ##
#######################################################
def server(input: Inputs, output: Outputs, session: Session) -> None:
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Load rxnDB and filter by initial phases !!
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    df: pd.DataFrame = db.data
    df_init: pd.DataFrame = db.filter_data_by_rxn(df, init_phases, init_phases)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Keep track of reactive values !!
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    rxn_labels: reactive.Value[bool] = reactive.value(True)
    find_similar_rxns: reactive.Value[bool] = reactive.value(False)
    selected_row_ids: reactive.Value[list[int]] = reactive.value([])
    select_all_reactants: reactive.Value[bool] = reactive.value(False)
    select_all_products: reactive.Value[bool] = reactive.value(False)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Toggle reactive values (UI buttons) !!
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.show_rxn_labels)
    def show_rxn_labels() -> None:
        """
        Toggles rxn_labels
        """
        rxn_labels.set(not rxn_labels())

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.toggle_reactants)
    def toggle_reactants() -> None:
        """
        Toggles select_all_reactants
        """
        if select_all_reactants():
            ui.update_checkbox_group("reactants", selected=init_phases)
        else:
            ui.update_checkbox_group("reactants", selected=phases)

        select_all_reactants.set(not select_all_reactants())

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.toggle_products)
    def toggle_products() -> None:
        """
        Toggles select_all_products
        """
        if select_all_products():
            ui.update_checkbox_group("products", selected=init_phases)
        else:
            ui.update_checkbox_group("products", selected=phases)

        select_all_products.set(not select_all_products())

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.toggle_find_similar_rxns)
    def toggle_find_similar_rxns() -> None:
        """
        Toggles find_similar_rxns
        """
        find_similar_rxns.set(not find_similar_rxns())

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Filter rxnDB !!
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.calc
    def filter_df_for_datatable() -> pd.DataFrame:
        """
        Filters the DataTable by products and reactants (checked boxes only)
        """
        reactants: list[str] = input.reactants()
        products: list[str] = input.products()

        return db.filter_data_by_rxn(df, reactants, products)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.calc
    def filter_df_for_plotly() -> pd.DataFrame:
        """
        Filters the DataTable by reconciling checked boxes and DataTable selections
        """
        reactants: list[str] = input.reactants()
        products: list[str] = input.products()

        # Get the current selected IDs from the DataTable
        selected_rxn_ids: reactive.Value[list[int]] = selected_row_ids()

        # Find similar reactions button
        if not find_similar_rxns():
            if selected_rxn_ids and len(selected_rxn_ids) > 0:
                return db.filter_data_by_ids(df, selected_rxn_ids)
            else:
                return db.filter_data_by_rxn(df, reactants, products)

        # Reconcile DataTable selections and checked boxes
        if selected_rxn_ids and len(selected_rxn_ids) > 0:
            filtered_reactants: list[str] = df[df["id"].isin(selected_rxn_ids)][
                ["reactant1", "reactant2", "reactant3"]].values.flatten()
            filtered_reactants: pd.Series = pd.Series(filtered_reactants).dropna()

            filtered_products: list[str] = df[df["id"].isin(selected_rxn_ids)][
                ["product1", "product2", "product3"]].values.flatten()
            filtered_products: pd.Series = pd.Series(filtered_products).dropna()

            return db.filter_data_by_rxn(df, filtered_reactants, filtered_products)
        else:
            return db.filter_data_by_rxn(df, reactants, products)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Plotly widget (supergraph) !!
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @render_plotly
    def plotly() -> go.FigureWidget:
        """
        Render plotly
        """
        plot_df: pd.DataFrame = db.calculate_reaction_curves(df_init)

        fig: go.FigureWidget = vis.plot_reaction_lines(
            df=plot_df,
            rxn_ids=df_init["id"],
            dark_mode=False,
            color_palette="Alphabet"
        )

        return fig

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def update_plotly_labels() -> None:
        """
        Updates plotly (rxn labels only)
        """
        fig: go.FigureWidget = plotly.widget

        current_x_range: tuple[float, float] = fig.layout.xaxis.range
        current_y_range: tuple[float, float] = fig.layout.yaxis.range

        dark_mode: bool = input.mode() == "dark"
        show_labels: bool = rxn_labels()
        plot_df: pd.DataFrame = db.calculate_reaction_curves(filter_df_for_plotly())
        mp_df: pd.DataFrame = db.calculate_midpoints(filter_df_for_plotly())

        updated_fig: go.Figure = vis.plot_reaction_lines(
            df=plot_df,
            rxn_ids=filter_df_for_plotly()["id"],
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

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def update_plotly() -> None:
        """
        Updates plotly (except for rxn labels)
        """
        fig: go.FigureWidget = plotly.widget

        current_x_range: tuple[float, float] = fig.layout.xaxis.range
        current_y_range: tuple[float, float] = fig.layout.yaxis.range

        dark_mode: bool = input.mode() == "dark"
        plot_df: pd.DataFrame = db.calculate_reaction_curves(filter_df_for_plotly())

        updated_fig: go.Figure = vis.plot_reaction_lines(
            df=plot_df,
            rxn_ids=filter_df_for_plotly()["id"],
            dark_mode=dark_mode,
            color_palette="Alphabet"
        )

        updated_fig.layout.xaxis.range = current_x_range
        updated_fig.layout.yaxis.range = current_y_range

        fig.data: dict = ()
        fig.add_traces(updated_fig.data)

        fig.layout.update(updated_fig.layout)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.download_plotly)
    def save_figure() -> None:
        """
        Download the current plotly as png
        """
        fig: go.FigureWidget = plotly.widget

        filename: str = "rxndb-phase-diagram.png"
        dpi: int = 300
        width_px: int = int(3.5 * dpi)
        height_px: int = int(4 * dpi)

        show_download_message(filename)

        pio.write_image(fig, file=filename, width=width_px, height=height_px)

        with Image.open(filename) as img:
            img: Image.Image = img.convert("RGB")
            img.save(filename, dpi=(dpi, dpi))

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def show_download_message(filename) -> None:
        """
        Render download message
        """
        filepath: str = os.path.join(os.getcwd(), filename)
        m: ui.Tag = ui.modal(
            f"{filepath}",
            title="Downloading ...",
            easy_close=True,
            footer=None,
        )
        ui.modal_show(m)

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # DataTable widget (rxnDB) !!
    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @render.data_frame
    def datatable() -> render.DataTable:
        """
        Render DataTable
        """
        # Refresh table on clear selection
        _ = input.clear_selection()

        cols: list[str] = ["id", "formula", "rxn", "polynomial", "ref"]

        if input.reactants() != init_phases or input.products() != init_phases:
            data: pd.DataFrame = filter_df_for_datatable()[cols]
        else:
            data: pd.DataFrame = df_init[cols]

        return render.DataTable(data, height="98%", selection_mode="rows")

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.datatable_selected_rows)
    def update_selected_rows() -> None:
        """
        Update selected_rows when table selections change
        """
        indices: list[int] = input.datatable_selected_rows()

        if indices:
            if input.reactants() != init_phases or input.products() != init_phases:
                current_df: pd.DataFrame = filter_df_for_datatable()
            else:
                current_df: pd.DataFrame = df_init

            ids: list[int] = [current_df.iloc[i]["id"] for i in indices]

            selected_row_ids.set(ids)
        else:
            selected_row_ids.set([])

    #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.clear_selection)
    def clear_selected_rows() -> None:
        """
        Clears all DataTable selections
        """
        selected_row_ids.set([])

#######################################################
## .3.                Shiny App                  !!! ##
#######################################################
app: App = App(app_ui, server)
