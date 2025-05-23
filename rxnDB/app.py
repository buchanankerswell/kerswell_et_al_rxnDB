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

    _rv_group_display_modes = reactive.value({})

    _rv_ui_initialized = reactive.value(False)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Helper functions for phase selection management
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _convert_phase_abbrevs_to_selected_boxes(
        phases: set[str], display_mode: str, boxes: list[str]
    ) -> set[str]:
        """Convert phase abbreviations to the current display boxes."""
        if not phases:
            return set()

        selections = set()
        if display_mode == "abbreviation":
            selections = phases.intersection(boxes)
        elif display_mode == "name":
            for abbrev in phases:
                name = set(processor.get_phase_name_from_abbrev(abbrev))
                selections.update(name.intersection(boxes))
        elif display_mode == "formula":
            for abbrev in phases:
                formula = set(processor.get_phase_formula_from_abbrev(abbrev))
                selections.update(formula.intersection(boxes))

        return selections

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _convert_selected_boxes_to_phase_abbrevs(
        selections: list[str], display_mode: str
    ) -> set[str]:
        """Convert selected boxes back to phase abbreviations."""
        if not selections:
            return set()

        abbrevs = set()
        for box in selections:
            if display_mode == "abbreviation":
                abbrevs.add(box)
            elif display_mode == "name":
                abbrev = processor.get_phase_abbrev_from_name(box)
                if abbrev:
                    abbrevs.update(abbrev)
            elif display_mode == "formula":
                abbrev = processor.get_phase_abbrev_from_formula(box)
                if abbrev:
                    abbrevs.update(abbrev)

        return abbrevs

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Initialization
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def _re_initialize_once() -> None:
        """Initialize app state once at startup."""
        if not _rv_ui_initialized():
            _re_initialize_group_defaults()
            _rv_ui_initialized.set(True)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _re_initialize_group_defaults() -> None:
        """Initialize default values for groups if not already set."""
        checkbox_groups = processor.get_all_group_names()
        current_display_modes = _rv_group_display_modes().copy()

        changed = False
        for group in checkbox_groups:
            if group not in current_display_modes:
                current_display_modes[group] = "name"
                changed = True

        if changed:
            _rv_group_display_modes.set(current_display_modes)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Reactive UI components
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @output(id="phase_selector_ui")
    @render.ui
    def phase_selector() -> ui.Tag:
        """Generate phase selector UI (only re-renders on initialization)."""
        if not _rv_ui_initialized():
            return ui.div("Loading ...")

        # Get phase groups
        checkbox_groups = processor.get_all_group_names()
        if not checkbox_groups:
            return ui.div("No phase groups available ...")

        # Isolate reactive state values to avoid re-rendering the entire UI
        # Let UI event handlers update individual components when state changes
        with reactive.isolate():
            current_display_modes = _rv_group_display_modes()
            current_phases = _rv_selected_phase_abbrevs()

        # Initialize UI components for each phase group
        ui_elements = []
        for group in checkbox_groups:
            # Stable UI IDs
            group_id = processor.get_group_id(group)
            id_radio = f"mode_{group_id}"
            id_boxes = f"boxes_{group_id}"

            # Get selections
            display_mode = current_display_modes.get(group)
            boxes = processor.get_grouped_phases(group, display_mode)
            selections = _convert_phase_abbrevs_to_selected_boxes(
                current_phases, display_mode, boxes
            )

            # Build UI components
            display_mode_ui = ui.input_radio_buttons(
                id_radio,
                "Display Mode",
                choices=["abbreviation", "name", "formula"],
                selected=display_mode,
                inline=False,
            )

            popover_icon = ui.span(
                icon_svg("gear"),
                class_="sidebar-popover-icon",
            )

            popover_ui = ui.popover(
                popover_icon,
                ui.div(
                    display_mode_ui,
                    class_="sidebar-popover-radio-btns",
                ),
                title=f"{group} Settings",
                placement="top",
            )

            checkbox_group_ui = ui.input_checkbox_group(
                id_boxes,
                None,
                choices=sorted(list(boxes)),
                selected=list(selections),
            )

            popover_container = ui.div(popover_ui, class_="sidebar-popover-container")
            panel_container = ui.div(
                checkbox_group_ui, popover_container, class_="sidebar-panel-container"
            )

            ui_elements.append(
                ui.accordion_panel(
                    group,
                    panel_container,
                    value=group,
                )
            )

        return ui.accordion(*ui_elements, id="accordion", open=False)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # UI event handlers
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def _handle_display_mode_changes():
        """Handle display mode changes and updates UI components."""
        if not _rv_ui_initialized():
            return

        # Get phase groups
        checkbox_groups = processor.get_all_group_names()

        # Get reactive state values
        current_display_modes = _rv_group_display_modes().copy()

        # Isolate reactive state values to avoid re-rendering
        with reactive.isolate():
            current_selected_phase_abbrevs = _rv_selected_phase_abbrevs()

        # Check for state change and update individual UI components
        display_mode_state_change = False
        for group in checkbox_groups:
            group_id = processor.get_group_id(group)
            id_radio = f"mode_{group_id}"

            new_display_mode = input[id_radio]()

            if new_display_mode is not None:
                if current_display_modes.get(group) != new_display_mode:
                    current_display_modes[group] = new_display_mode
                    display_mode_state_change = True

                    new_boxes = processor.get_grouped_phases(group, new_display_mode)
                    new_selections = _convert_phase_abbrevs_to_selected_boxes(
                        current_selected_phase_abbrevs, new_display_mode, new_boxes
                    )

                    ui.update_checkbox_group(
                        id=f"boxes_{group_id}",
                        choices=sorted(list(new_boxes)),
                        selected=list(new_selections),
                    )

        if display_mode_state_change:
            _rv_group_display_modes.set(current_display_modes)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def _handle_phase_selections():
        """
        Handle phase selection changes from checkbox groups and update the
        central _rv_selected_phase_abbrevs state.
        """
        if not _rv_ui_initialized():
            return

        # Get phase groups
        checkbox_groups = processor.get_all_group_names()

        # Get reactive state values
        with reactive.isolate():
            current_display_modes = _rv_group_display_modes()

        # Check for state change and update central list of selected phases
        newly_selected_phase_abbrevs = set()
        for group in checkbox_groups:
            group_id = processor.get_group_id(group)
            id_boxes = f"boxes_{group_id}"

            selected_boxes = input[id_boxes]()

            if selected_boxes is not None:
                display_mode = current_display_modes.get(group, "name")

                phase_abbrevs = _convert_selected_boxes_to_phase_abbrevs(
                    list(selected_boxes), display_mode
                )
                newly_selected_phase_abbrevs.update(phase_abbrevs)

        # Update the central reactive value if the set of selected abbreviations has changed
        if newly_selected_phase_abbrevs != _rv_selected_phase_abbrevs():
            _rv_selected_phase_abbrevs.set(newly_selected_phase_abbrevs)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Global toggle event listeners
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
    # Table selection event listeners (unchanged)
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
    # Reactive calculations for data filtering (unchanged)
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
