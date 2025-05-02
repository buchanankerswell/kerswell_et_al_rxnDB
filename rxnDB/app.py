#######################################################
## .0.              Load Libraries               !!! ##
#######################################################
from typing import Literal

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
## .1. Init Data                                 !!! ##
#######################################################
try:
    filepath = app_dir / "data" / "cache" / "rxnDB.parquet"
    rxnDB_df: pd.DataFrame = RxnDBLoader.load_parquet(filepath)
    processor: RxnDBProcessor = RxnDBProcessor(rxnDB_df)
except FileNotFoundError:
    raise FileNotFoundError(f"Error: Data file not found at {filepath}!")
except Exception as e:
    raise RuntimeError(f"Error loading or processing data: {e}!")

#######################################################
## .2. Init UI                                   !!! ##
#######################################################
try:
    all_phases: list[str] = processor.get_unique_phases()
    init_phases: list[str] = [p for p in ["ky", "and", "sil"] if p in all_phases]

    if not init_phases and all_phases:
        init_phases = all_phases[: min(3, len(all_phases))]

    app_ui: ui.Tag = configure_ui(all_phases, init_phases)
except Exception as e:
    raise RuntimeError(f"Error loading shinyapp UI: {e}!")


#######################################################
## .3. Server Logic                              !!! ##
#######################################################
def server(input: Inputs, output: Outputs, session: Session) -> None:
    """"""
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Reactive state values
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    rxn_labels = reactive.value(True)
    find_similar_rxns: reactive.Value[Literal["or"] | Literal["and"] | bool] = (
        reactive.value(False)
    )
    selected_row_ids = reactive.value([])
    select_all_reactants = reactive.value(False)
    select_all_products = reactive.value(False)
    _selected_row_indices = reactive.value(None)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Event listeners for UI buttons / toggles
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.show_rxn_labels)
    def _() -> None:
        """Toggles rxn_labels"""
        rxn_labels.set(not rxn_labels())

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.toggle_reactants)
    def _() -> None:
        """Toggles select_all_reactants"""
        current_state = not select_all_reactants()
        select_all_reactants.set(current_state)

        if current_state:
            ui.update_checkbox_group("reactants", selected=all_phases)
        else:
            ui.update_checkbox_group("reactants", selected=init_phases)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.toggle_products)
    def _() -> None:
        """Toggles select_all_products"""
        current_state = not select_all_products()
        select_all_products.set(current_state)

        if current_state:
            ui.update_checkbox_group("products", selected=all_phases)
        else:
            ui.update_checkbox_group("products", selected=init_phases)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.toggle_find_similar_rxns)
    def _() -> None:
        """Cycles find_similar_rxns through False → 'or' → 'and' → False"""
        current = find_similar_rxns()
        if current is False:
            find_similar_rxns.set("or")
        elif current == "or":
            find_similar_rxns.set("and")
        else:
            find_similar_rxns.set(False)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.clear_selection)
    def _() -> None:
        """Clears all DataTable selections"""
        selected_row_ids.set([])
        _selected_row_indices.set(None)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Calculate base filtered data once
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.calc
    def base_filtered_data() -> pd.DataFrame:
        """Initial filtering based only on selected reactants/products."""
        reactants = input.reactants()
        products = input.products()

        return processor.filter_by_reactants_and_products(reactants, products)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Reactive calculation for DataTable data
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.calc
    def get_datatable_data() -> pd.DataFrame:
        """Get filtered data for DataTable."""
        filtered_df = base_filtered_data()

        if not filtered_df.empty:
            return (
                filtered_df[["id", "name", "rxn", "type", "ref"]]
                .drop_duplicates(subset="id")
                .reset_index(drop=True)
            )
        else:
            return pd.DataFrame(columns=["id", "name", "rxn", "type", "ref"])

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Effect to update selected_row_ids based on DataTable selection indices
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.datatable_selected_rows)
    def _update_selected_ids_from_indices() -> None:
        """Updates the selected_row_ids list based on the indices selected in the DataTable."""
        indices = input.datatable_selected_rows()
        _selected_row_indices.set(indices)

        if indices:
            current_table_df = get_datatable_data()
            if not current_table_df.empty and max(indices) < len(current_table_df):
                ids = current_table_df.iloc[list(indices)]["id"].tolist()
                selected_row_ids.set(ids)
            else:
                selected_row_ids.set([])
        else:
            selected_row_ids.set([])

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Reactive calculation for Plotly data
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.calc
    def get_plotly_data() -> pd.DataFrame:
        """Get filtered data for Plotly."""
        filtered_df = base_filtered_data()

        selected_ids = selected_row_ids()
        find_similar = find_similar_rxns()

        if selected_ids:
            if find_similar:
                selected_reactants, selected_products = processor.get_phases_for_ids(
                    selected_ids
                )
                if selected_reactants or selected_products:
                    return processor.filter_by_reactants_and_products(
                        selected_reactants,
                        selected_products,
                        method=str(find_similar),
                    )
                else:
                    return pd.DataFrame(columns=processor._original_df.columns)

            else:
                return filtered_df[filtered_df["id"].isin(selected_ids)]
        else:
            return filtered_df

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Plotly widget (supergraph)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @render_plotly
    def plotly() -> go.FigureWidget:
        """Render plotly"""
        try:
            initial_plot_df = processor.filter_by_reactants_and_products(
                init_phases, init_phases
            )
            if initial_plot_df.empty:
                initial_plot_df = processor.df.head(3)
            ids_to_plot = initial_plot_df["id"].unique().tolist()

        except Exception:
            initial_plot_df = processor.df.head(3)
            ids_to_plot = initial_plot_df["id"].unique().tolist()

        fig = go.FigureWidget(
            vis.plot_reaction_lines(
                df=initial_plot_df,
                ids=ids_to_plot,
                dark_mode=False,
                color_palette="Alphabet",
            )
        )
        return fig

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Plotly update effect
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def update_plotly() -> None:
        """Updates plotly figure widget efficiently based on filtered data and settings."""
        widget = plotly.widget
        if widget is None:
            return

        current_x_range = getattr(getattr(widget.layout, "xaxis", None), "range", None)
        current_y_range = getattr(getattr(widget.layout, "yaxis", None), "range", None)

        plot_df = get_plotly_data()

        dark_mode = input.mode() == "dark"
        show_labels = rxn_labels()

        updated_fig = vis.plot_reaction_lines(
            df=plot_df,
            ids=plot_df["id"].unique().tolist(),
            dark_mode=dark_mode,
            color_palette="Alphabet",
        )

        if current_x_range is not None:
            updated_fig.layout.xaxis.range = current_x_range  # type: ignore
        if current_y_range is not None:
            updated_fig.layout.yaxis.range = current_y_range  # type: ignore

        with widget.batch_update():
            widget.data = ()
            widget.add_traces(updated_fig.data)
            widget.layout.update(updated_fig.layout)  # type: ignore

            if show_labels and not plot_df.empty:
                try:
                    mp_df = vis.calculate_rxn_curve_midpoints(plot_df)
                    temp_fig = go.Figure()
                    vis.add_reaction_labels(temp_fig, mp_df)
                    widget.layout.annotations = temp_fig.layout.annotations  # type: ignore
                except Exception as e:
                    print(f"Error adding reaction labels: {e}")
            else:
                widget.layout.annotations = ()  # type: ignore

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # DataTable widget (rxnDB)
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @render.data_frame
    def datatable() -> render.DataTable:
        """Render DataTable with current filtered/formatted data."""
        _ = input.clear_selection()

        data = get_datatable_data()

        return render.DataTable(
            data,
            height="98%",
            selection_mode="rows",
        )


#######################################################
## .4.                Shiny App                  !!! ##
#######################################################
app: App = App(app_ui, server)
