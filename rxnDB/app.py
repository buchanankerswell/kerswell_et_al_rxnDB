#######################################################
## .0.              Load Libraries               !!! ##
#######################################################
import os

import pandas as pd
import plotly.graph_objects as go
from shiny import App, Inputs, Outputs, Session, reactive, render, ui
from shinywidgets import render_plotly

import rxnDB.visualize as vis
from rxnDB.data.loader import RxnDBLoader
from rxnDB.data.processor import RxnDBProcessor
from rxnDB.ui import configure_ui
from rxnDB.utils import app_dir

#######################################################
## .1.                Init Data                  !!! ##
#######################################################
hp11_loader = RxnDBLoader(app_dir / "data" / "sets" / "preprocessed" / "hp11_data")
jimmy_loader = RxnDBLoader(app_dir / "data" / "sets" / "preprocessed" / "jimmy_data")

hp11_data: pd.DataFrame = hp11_loader.load_all()
jimmy_data: pd.DataFrame = jimmy_loader.load_all()

rxnDB = pd.concat([hp11_data, jimmy_data], ignore_index=True)
processor = RxnDBProcessor(rxnDB)

#######################################################
## .2.                 Init UI                   !!! ##
#######################################################
all_phases: list[str] = processor.get_unique_phases()
init_phases: list[str] = ["ky", "and", "sil", "ol", "wd"]
app_ui: ui.Tag = configure_ui(all_phases, init_phases)


#######################################################
## .3.              Server Logic                 !!! ##
#######################################################
def server(input: Inputs, output: Outputs, session: Session) -> None:
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Keep track of reactive values !!
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    rxn_labels: reactive.Value[bool] = reactive.value(True)
    find_similar_rxns: reactive.Value[bool] = reactive.value(False)
    selected_row_ids: reactive.Value[list[str]] = reactive.value([])
    select_all_reactants: reactive.Value[bool] = reactive.value(False)
    select_all_products: reactive.Value[bool] = reactive.value(False)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Toggle reactive values (UI buttons) !!
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.show_rxn_labels)
    def show_rxn_labels() -> None:
        """
        Toggles rxn_labels
        """
        rxn_labels.set(not rxn_labels())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.toggle_reactants)
    def toggle_reactants() -> None:
        """
        Toggles select_all_reactants
        """
        if select_all_reactants():
            ui.update_checkbox_group("reactants", selected=init_phases)
        else:
            ui.update_checkbox_group("reactants", selected=all_phases)

        select_all_reactants.set(not select_all_reactants())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.toggle_products)
    def toggle_products() -> None:
        """
        Toggles select_all_products
        """
        if select_all_products():
            ui.update_checkbox_group("products", selected=init_phases)
        else:
            ui.update_checkbox_group("products", selected=all_phases)

        select_all_products.set(not select_all_products())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.toggle_find_similar_rxns)
    def toggle_find_similar_rxns() -> None:
        """
        Toggles find_similar_rxns
        """
        find_similar_rxns.set(not find_similar_rxns())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Filter rxnDB !!
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.calc
    def filter_reactants_and_products() -> RxnDBProcessor:
        return processor.filter_by_reactants(input.reactants()).filter_by_products(
            input.products()
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.calc
    def filter_datatable() -> pd.DataFrame:
        """
        Filters the DataTable by products and reactants (checked boxes only)
        """
        return filter_reactants_and_products().df.drop_duplicates(subset="id")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.calc
    def filter_plotly() -> pd.DataFrame:
        """
        Filters the DataTable by reconciling checked boxes and DataTable selections
        """
        base_filter: RxnDBProcessor = filter_reactants_and_products()
        selected_rxns: list[str] = selected_row_ids()

        if not find_similar_rxns():
            if selected_rxns:
                return base_filter.filter_by_ids(selected_rxns).df
            return base_filter.df

        # Reconcile DataTable selections and checked boxes
        # if find similar rxns button is toggled on
        if selected_rxns:
            filtered_reactants: list[str] = (
                base_filter.filter_by_ids(selected_rxns)
                .df["reactants"]
                .dropna()
                .tolist()
            )

            filtered_products: list[str] = (
                base_filter.filter_by_ids(selected_rxns)
                .df["products"]
                .dropna()
                .tolist()
            )

            return (
                processor.filter_by_reactants(filtered_reactants)
                .filter_by_products(filtered_products)
                .df
            )
        else:
            return base_filter.df

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Plotly widget (supergraph) !!
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @render_plotly
    def plotly() -> go.FigureWidget:
        """
        Render plotly
        """
        init_df: pd.DataFrame = processor.reset().df

        fig: go.FigureWidget = go.FigureWidget(
            vis.plot_reaction_lines(
                df=init_df,
                rxn_ids=init_df["id"].tolist(),
                dark_mode=False,
                color_palette="Alphabet",
            )
        )

        return fig

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def update_plotly_labels() -> None:
        """
        Updates plotly (rxn labels only)
        """
        assert plotly.widget is not None
        fig: go.FigureWidget = plotly.widget

        current_x_range: tuple[float, float] = fig.layout.xaxis.range  # type: ignore
        current_y_range: tuple[float, float] = fig.layout.yaxis.range  # type: ignore

        dark_mode: bool = input.mode() == "dark"
        show_labels: bool = rxn_labels()
        plot_df: pd.DataFrame = filter_plotly()
        mp_df: pd.DataFrame = vis.calculate_rxn_curve_midpoints(filter_plotly())

        updated_fig: go.Figure = vis.plot_reaction_lines(
            df=plot_df,
            rxn_ids=plot_df["id"].tolist(),
            dark_mode=dark_mode,
            color_palette="Alphabet",
        )

        updated_fig.layout.xaxis.range = current_x_range  # type: ignore
        updated_fig.layout.yaxis.range = current_y_range  # type: ignore

        if show_labels:
            vis.add_reaction_labels(updated_fig, mp_df)
            fig.layout.annotations = updated_fig.layout.annotations  # type: ignore
        else:
            fig.layout.annotations = ()  # type: ignore

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def update_plotly() -> None:
        """
        Updates plotly (except for rxn labels)
        """
        assert plotly.widget is not None
        fig: go.FigureWidget = plotly.widget

        current_x_range: tuple[float, float] = fig.layout.xaxis.range  # type: ignore
        current_y_range: tuple[float, float] = fig.layout.yaxis.range  # type: ignore

        dark_mode: bool = input.mode() == "dark"
        plot_df: pd.DataFrame = filter_plotly()

        updated_fig: go.Figure = vis.plot_reaction_lines(
            df=plot_df,
            rxn_ids=plot_df["id"].tolist(),
            dark_mode=dark_mode,
            color_palette="Alphabet",
        )

        updated_fig.layout.xaxis.range = current_x_range  # type: ignore
        updated_fig.layout.yaxis.range = current_y_range  # type: ignore

        fig.data = ()
        fig.add_traces(updated_fig.data)

        fig.layout.update(updated_fig.layout)  # type: ignore

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
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

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # DataTable widget (rxnDB) !!
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @render.data_frame
    def datatable() -> render.DataTable:
        """
        Render DataTable
        """
        init_df: pd.DataFrame = processor.reset().df

        # Refresh table on clear selection
        _ = input.clear_selection()

        cols: list[str] = ["id", "rxn", "ref"]

        if input.reactants() != init_phases or input.products() != init_phases:
            data: pd.DataFrame = filter_datatable()[cols]
        else:
            data: pd.DataFrame = init_df[cols]

        return render.DataTable(data, height="98%", selection_mode="rows")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.datatable_selected_rows)
    def update_selected_rows() -> None:
        """
        Update selected_rows when table selections change
        """
        init_df: pd.DataFrame = processor.reset().df
        indices: list[int] = input.datatable_selected_rows()

        if indices:
            if input.reactants() != init_phases or input.products() != init_phases:
                current_df: pd.DataFrame = filter_datatable()
            else:
                current_df: pd.DataFrame = init_df

            ids: list[str] = [current_df.iloc[i]["id"] for i in indices]

            selected_row_ids.set(ids)
        else:
            selected_row_ids.set([])

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.clear_selection)
    def clear_selected_rows() -> None:
        """
        Clears all DataTable selections
        """
        selected_row_ids.set([])


#######################################################
## .4.                Shiny App                  !!! ##
#######################################################
app: App = App(app_ui, server)
