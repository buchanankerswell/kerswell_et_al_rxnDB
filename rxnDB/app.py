#######################################################
## .0. Load Libraries                            !!! ##
#######################################################
import pandas as pd
import plotly.graph_objects as go
from faicons import icon_svg
from shiny import App, Inputs, Outputs, Session, reactive, render, ui
from shinywidgets import render_plotly

from rxnDB.data.loader import RxnDBLoader
from rxnDB.data.processor import RxnDBProcessor
from rxnDB.ui import configure_ui
from rxnDB.utils import app_dir
from rxnDB.visualize import RxnDBPlotter

#######################################################
## .1. Init Data                                 !!! ##
#######################################################
try:
    in_data = app_dir / "data" / "cache" / "rxnDB.parquet"
    rxnDB_df = RxnDBLoader.load_parquet(in_data)
    processor = RxnDBProcessor(rxnDB_df)
except FileNotFoundError:
    raise FileNotFoundError(f"Error: Data file not found at {in_data.name}!")
except Exception as e:
    raise RuntimeError(f"Error loading or processing data: {e}!")

#######################################################
## .2. Init UI                                   !!! ##
#######################################################
try:
    app_ui: ui.Tag = configure_ui()
except Exception as e:
    raise RuntimeError(f"Error loading shinyapp UI: {e}!")


#######################################################
## .4. Server Logic                              !!! ##
#######################################################
def server(input: Inputs, output: Outputs, session: Session) -> None:
    """Server logic."""

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Reactive state values
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    _rv_toggle_data_type = reactive.value("all")
    _rv_toggle_similar_reactions = reactive.value(False)

    _rv_selected_table_rows = reactive.value([])
    _rv_selected_row_indices = reactive.value(None)
    _rv_selected_phase_abbrevs = reactive.value(set())

    _rv_updating_ui = reactive.value(False)
    _rv_previous_display_mode = reactive.value(None)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Reactive UI components
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @output
    @render.ui
    def phase_selector() -> ui.Tag:
        """Generate phase selector UI based on current display mode."""
        display_mode = input.name_display_mode()
        checkbox_groups = processor.get_checkbox_group_items(display_mode)

        if not checkbox_groups:
            return ui.div("No phase groups available for current display mode.")

        phases = _rv_selected_phase_abbrevs()

        ui_elements = []
        for group, boxes in checkbox_groups.items():
            group_id = processor.get_group_id(group, display_mode)
            selections = _convert_abbrevs_to_display(phases, display_mode, boxes)

            ui_elements.append(
                ui.panel_well(
                    ui.tags.h5(group),
                    ui.popover(
                        ui.span(
                            icon_svg("gear"),
                            class_="sidebar-popover-gear-icon",
                        ),
                        ui.input_action_button(
                            f"btn_{group_id}",
                            "Dummy",
                            class_="popover-btn",
                        ),
                        title=f"{group} settings",
                    ),
                    ui.input_checkbox_group(
                        group_id,
                        None,
                        choices=sorted(boxes),
                        selected=selections,
                    ),
                )
            )

        return ui.div(*ui_elements)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Helper functions for phase selection management
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _convert_abbrevs_to_display(
        phases: set[str], display_mode: str, boxes: list[str]
    ) -> list[str]:
        """Convert a set of phase abbreviations to the current display format."""
        if not phases:
            return []

        selections = set()
        if display_mode == "abbreviation":
            selections = phases.intersection(boxes)
        elif display_mode == "common name":
            for abbrev in phases:
                names = processor._abbrev_to_phase_name_lookup.get(abbrev, set())
                selections.update(names.intersection(boxes))
        elif display_mode == "formula":
            for abbrev in phases:
                formulas = processor._abbrev_to_phase_formula_lookup.get(abbrev, set())
                selections.update(formulas.intersection(boxes))

        return sorted(list(selections))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    #  UI event listeners
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.toggle_similar_reactions)
    def _() -> None:
        """Toggles show similar reactions mode."""
        if _rv_toggle_similar_reactions() is False:
            _rv_toggle_similar_reactions.set("or")
        elif _rv_toggle_similar_reactions() == "or":
            _rv_toggle_similar_reactions.set("and")
        else:
            _rv_toggle_similar_reactions.set(False)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.toggle_data_type)
    def _() -> None:
        """Toggles data type mode."""
        if _rv_toggle_data_type() == "all":
            _rv_toggle_data_type.set("curves")
        elif _rv_toggle_data_type() == "curves":
            _rv_toggle_data_type.set("points")
        else:
            _rv_toggle_data_type.set("all")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.clear_selection)
    def _() -> None:
        """Clears table selections."""
        _rv_selected_table_rows.set([])
        _rv_selected_row_indices.set(None)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.name_display_mode)
    def _():
        """Updates display_mode."""
        current_mode = input.name_display_mode()
        _rv_previous_display_mode.set(current_mode)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def _() -> None:
        """Updates _rv_selected_phase_abbrevs."""
        if _rv_updating_ui.get():
            return

        display_mode = input.name_display_mode()
        checkbox_groups = processor.get_checkbox_group_items(display_mode)

        if not checkbox_groups:
            if _rv_selected_phase_abbrevs.get() != set():
                _rv_selected_phase_abbrevs.set(set())
            return

        new_selection = set()
        for group in checkbox_groups.keys():
            group_id = processor.get_group_id(group, display_mode)

            input_value_object = getattr(input, group_id, None)

            if input_value_object is None:
                continue

            selected_items = input_value_object()

            if selected_items is None:
                continue

            for val in selected_items:
                if display_mode == "abbreviation":
                    new_selection.add(val)
                elif display_mode == "common name":
                    abbrevs = processor.get_phase_abbrev_from_name(val)
                    if abbrevs:
                        new_selection.update(abbrevs)
                elif display_mode == "formula":
                    abbrevs = processor.get_phase_abbrev_from_formula(val)
                    if abbrevs:
                        new_selection.update(abbrevs)

        if new_selection != _rv_selected_phase_abbrevs.get():
            _rv_selected_phase_abbrevs.set(new_selection)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Data filtering event listeners
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.table_selected_rows)
    def _() -> None:
        """Updates the _rv_selected_table_rows list based on the indices selected in the table."""
        indices = input.table_selected_rows()
        _rv_selected_row_indices.set(indices)
        if indices:
            current_table_df = rc_get_table_data()
            if not current_table_df.empty:
                valid_indices = [i for i in indices if i < len(current_table_df)]
                if valid_indices:
                    ids = current_table_df.iloc[valid_indices]["unique_id"].tolist()
                    _rv_selected_table_rows.set(ids)
                else:
                    _rv_selected_table_rows.set([])
            else:
                _rv_selected_table_rows.set([])
        else:
            _rv_selected_table_rows.set([])

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Reactive calculations for data filtering
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.calc
    def rc_get_table_data() -> pd.DataFrame:
        """Get data for table widget."""
        df = rc_get_filtered_data()

        if not df.empty:
            return (
                df[["unique_id", "reaction", "type"]]
                .drop_duplicates(subset="unique_id")
                .reset_index(drop=True)
            )
        else:
            return pd.DataFrame(columns=["unique_id", "reaction", "type"])

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.calc
    def rc_get_plotly_data() -> pd.DataFrame:
        """Get data for Plotly widget."""
        df = rc_get_filtered_data()
        selected_ids = _rv_selected_table_rows()
        find_similar_mode = _rv_toggle_similar_reactions()

        if selected_ids:
            if find_similar_mode:
                reactants = processor.get_reactant_abbrevs_from_ids(selected_ids)
                products = processor.get_product_abbrevs_from_ids(selected_ids)

                if reactants or products:
                    return processor.filter_by_reactants_and_product_abbrevs(
                        list(reactants),
                        list(products),
                        method=str(find_similar_mode),
                    )
                else:
                    return pd.DataFrame(columns=df.columns)
            else:
                return df[df["unique_id"].isin(selected_ids)]
        else:
            return df

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.calc
    def rc_get_filtered_data() -> pd.DataFrame:
        """Initial filtering based on selected phases and plot type."""
        phases = _rv_selected_phase_abbrevs()
        data_type = _rv_toggle_data_type()

        if phases:
            df = processor.filter_by_reactants_and_product_abbrevs(phases, phases)
        else:
            df = pd.DataFrame(columns=processor.data.columns)

        if data_type == "all":
            return df
        elif data_type == "points":
            return (
                df[df["plot_type"] == "point"]
                if "plot_type" in df.columns
                else pd.DataFrame(columns=df.columns)
            )
        elif data_type == "curves":
            return (
                df[df["plot_type"] == "curve"]
                if "plot_type" in df.columns
                else pd.DataFrame(columns=df.columns)
            )

        return df

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Render and update widgets
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @render.data_frame
    def table() -> render.DataTable:
        """Render table with current filtered/formatted data."""
        _ = input.clear_selection()
        df = rc_get_table_data()

        return render.DataTable(df, height="98%", selection_mode="rows")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @output
    @render_plotly
    def plotly() -> go.FigureWidget:
        """Render plotly"""
        dark_mode = False

        df = pd.DataFrame(columns=processor.data.columns)
        uids = df["unique_id"].unique().tolist()
        df = processor.add_color_keys(df)

        plotter = RxnDBPlotter(df, uids, dark_mode)
        fig = go.FigureWidget(plotter.plot())

        return fig

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def update_plotly() -> None:
        """Updates plotly figure widget efficiently based on filtered data and settings."""
        widget = plotly.widget

        if widget is None:
            return

        current_x_range = getattr(getattr(widget.layout, "xaxis", None), "range", None)
        current_y_range = getattr(getattr(widget.layout, "yaxis", None), "range", None)

        dark_mode = input.dark_mode() == "dark"

        df = rc_get_plotly_data()
        df = processor.add_color_keys(df)
        uids = df["unique_id"].unique().tolist()

        plotter = RxnDBPlotter(df, uids, dark_mode)

        updated_fig = go.FigureWidget(plotter.plot())

        if current_x_range is not None:
            updated_fig.layout.xaxis.range = current_x_range  # type: ignore
        if current_y_range is not None:
            updated_fig.layout.yaxis.range = current_y_range  # type: ignore

        with widget.batch_update():
            widget.data = ()
            widget.add_traces(updated_fig.data)
            widget.layout.update(updated_fig.layout)  # type: ignore


#######################################################
## .5. Shiny App                                 !!! ##
#######################################################
app: App = App(app_ui, server)
