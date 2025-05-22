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
    _rv_group_show_formulas = reactive.value({})

    _rv_formula_click_counts = reactive.value({})

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Helper functions for phase selection management
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _convert_abbrevs_to_selected_boxes(
        phases: set[str], display_mode: str, boxes: list[str]
    ) -> list[str]:
        """Convert phase abbreviations to the current display boxes."""
        if not phases:
            return []

        selections = set()
        if display_mode == "abbreviation":
            selections = phases.intersection(boxes)
        elif display_mode == "common name":
            for abbrev in phases:
                names = processor._abbrev_to_phase_name_lookup.get(abbrev, set())
                selections.update(names.intersection(boxes))

        return sorted(list(selections))

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _convert_selected_boxes_to_abbrevs(
        selections: list[str], display_mode: str
    ) -> set[str]:
        """Convert selected boxes back to phase abbreviations."""
        if not selections:
            return set()

        abbrevs = set()
        for box in selections:
            if display_mode == "abbreviation":
                abbrevs.add(box)
            elif display_mode == "common name":
                abbrev = processor.get_phase_abbrev_from_name(box)
                if abbrev:
                    abbrevs.update(abbrev)

        return abbrevs

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _initialize_group_defaults() -> None:
        """Initialize default values for groups if not already set."""
        checkbox_groups = processor.get_all_group_names()
        current_modes = _rv_group_display_modes().copy()
        current_formulas = _rv_group_show_formulas().copy()
        current_clicks = _rv_formula_click_counts().copy()

        changed = False

        for group in checkbox_groups:
            if group not in current_modes:
                current_modes[group] = "abbreviation"
                changed = True
            if group not in current_formulas:
                current_formulas[group] = False
                changed = True
            if group not in current_clicks:
                current_clicks[group] = 0
                changed = True

        if changed:
            _rv_group_display_modes.set(current_modes)
            _rv_group_show_formulas.set(current_formulas)
            _rv_formula_click_counts.set(current_clicks)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Reactive UI components
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @output
    @render.ui
    def phase_selector() -> ui.Tag:
        """Generate phase selector UI with individual group panels."""
        _initialize_group_defaults()

        checkbox_groups = processor.get_all_group_names()

        if not checkbox_groups:
            return ui.div("No phase groups available.")

        ui_elements = []
        phases = _rv_selected_phase_abbrevs()
        display_modes = _rv_group_display_modes()
        show_formulas_dict = _rv_group_show_formulas()

        for group in checkbox_groups:
            display_mode = display_modes.get(group, "abbreviation")
            show_formulas = show_formulas_dict.get(group, False)

            id_radio = f"mode_{processor.get_group_id(group)}"
            id_boxes = f"boxes_{processor.get_group_id(group)}"
            id_formulas = f"formulas_{processor.get_group_id(group)}"

            boxes = processor.get_grouped_phases(group, display_mode, show_formulas)
            selections = _convert_abbrevs_to_selected_boxes(phases, display_mode, boxes)

            display_mode_ui = ui.input_radio_buttons(
                id_radio,
                "Display Mode",
                choices=["abbreviation", "common name"],
                selected=display_mode,
                inline=True,
            )

            formula_button_text = "Hide Formulas" if show_formulas else "Show Formulas"
            formula_toggle_ui = ui.input_action_button(
                id_formulas,
                formula_button_text,
                class_="popover-btn",
            )

            popover_icon = ui.span(
                icon_svg("gear"),
                class_="sidebar-popover-icon",
            )

            popover_ui = ui.popover(
                popover_icon,
                ui.div(
                    display_mode_ui,
                    ui.hr(),
                    formula_toggle_ui,
                ),
                title=f"{group} Settings",
                placement="top",
            )

            checkbox_group_ui = ui.input_checkbox_group(
                id_boxes,
                None,
                choices=sorted(boxes),
                selected=selections,
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

        if not ui_elements:
            return ui.div("No UI elements to display.")

        return ui.accordion(*ui_elements, id="acc")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Event listeners for display modes
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def _update_display_modes():
        """Update display modes when radio buttons change."""
        checkbox_groups = processor.get_all_group_names()
        current_modes = _rv_group_display_modes().copy()
        changes_made = False

        for group in checkbox_groups:
            id_radio = f"mode_{processor.get_group_id(group)}"

            if hasattr(input, id_radio):
                input_obj = getattr(input, id_radio)
                if input_obj is not None:
                    new_mode = input_obj()
                    if new_mode and new_mode in {"abbreviation", "common name"}:
                        if current_modes.get(group) != new_mode:
                            current_modes[group] = new_mode
                            changes_made = True

        if changes_made:
            _rv_group_display_modes.set(current_modes)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Event listeners for formula toggles
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def _update_formula_toggles():
        """Update formula display settings when buttons are clicked."""
        checkbox_groups = processor.get_all_group_names()
        current_formulas = _rv_group_show_formulas().copy()
        current_clicks = _rv_formula_click_counts().copy()
        changes_made = False

        for group in checkbox_groups:
            id_formulas = f"formulas_{processor.get_group_id(group)}"

            if hasattr(input, id_formulas):
                input_obj = getattr(input, id_formulas)
                if input_obj is not None:
                    click_count = input_obj()
                    previous_count = current_clicks.get(group, 0)

                    if click_count and click_count > previous_count:
                        current_state = current_formulas.get(group, False)
                        current_formulas[group] = not current_state
                        current_clicks[group] = click_count
                        changes_made = True

        if changes_made:
            _rv_group_show_formulas.set(current_formulas)
            _rv_formula_click_counts.set(current_clicks)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Event listener for phase selections
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def _update_phase_selections():
        """Update selected phases when checkboxes change."""
        checkbox_groups = processor.get_all_group_names()
        display_modes = _rv_group_display_modes()

        if not checkbox_groups:
            if _rv_selected_phase_abbrevs():
                _rv_selected_phase_abbrevs.set(set())
            return

        new_selection = set()
        for group in checkbox_groups:
            display_mode = display_modes.get(group, "abbreviation")
            id_boxes = f"boxes_{processor.get_group_id(group)}"

            if hasattr(input, id_boxes):
                input_value_object = getattr(input, id_boxes)
                if input_value_object is not None:
                    selected_items = input_value_object()
                    if selected_items:
                        abbrevs = _convert_selected_boxes_to_abbrevs(
                            selected_items, display_mode
                        )
                        new_selection.update(abbrevs)

        if new_selection != _rv_selected_phase_abbrevs():
            _rv_selected_phase_abbrevs.set(new_selection)

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

    @reactive.effect
    @reactive.event(input.clear_selection)
    def _() -> None:
        """Clears table selections."""
        _rv_selected_table_rows.set([])
        _rv_selected_row_indices.set(None)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Table selection event listeners
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
