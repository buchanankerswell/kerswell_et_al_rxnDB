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
    _rv_toggle_similar_reactions = reactive.value("off")

    _rv_selected_chemical_system = reactive.value(["Al", "O", "Si"])
    _rv_selected_phase_abbrevs = reactive.value(set())
    _rv_selected_table_columns = reactive.value(
        ["unique_id", "reaction", "type", "reference"]
    )
    _rv_selected_table_rows = reactive.value([])

    _rv_selected_temperature_units = reactive.value("celcius")
    _rv_selected_pressure_units = reactive.value("gigapascal")

    _rv_group_display_modes = reactive.value({})

    _rv_ui_initialized = reactive.value(False)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Initialization
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def _re_initialize_once() -> None:
        """Initialize app state once at startup."""
        if not _rv_ui_initialized():
            _re_initialize_defaults()
            _rv_ui_initialized.set(True)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def _re_initialize_defaults() -> None:
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
    # Reactive UI components
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @render.ui
    def sidebar_chemical_system_ui() -> ui.Tag:
        """Render sidebar chemical sytem UI."""
        if not _rv_ui_initialized():
            return ui.div("Loading ...")

        components = processor.get_all_chemical_components()

        with reactive.isolate():
            selected_chemical_system = _rv_selected_chemical_system()

        return ui.input_selectize(
            "selected_chemical_system",
            "Filter by chemical system",
            choices={element: element for element in sorted(components)},
            selected=list(selected_chemical_system),
            multiple=True,
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @render.ui
    def sidebar_checkbox_ui() -> ui.Tag:
        """Render sidebar checkbox UI."""
        if not _rv_ui_initialized():
            return ui.div("Loading ...")

        checkbox_groups = processor.get_all_group_names()
        if not checkbox_groups:
            return ui.div("No phase groups available ...")

        with reactive.isolate():
            current_display_modes = _rv_group_display_modes()
            current_phases = _rv_selected_phase_abbrevs()
            current_chemical_system = _rv_selected_chemical_system()

        ui_elements = []
        for group in checkbox_groups:
            # Stable UI IDs
            group_id = processor.get_group_id(group)
            id_radio = f"mode_{group_id}"
            id_boxes = f"boxes_{group_id}"

            display_mode = current_display_modes.get(group, "name")
            boxes = processor.get_grouped_phases(
                group, current_chemical_system, display_mode
            )
            selections = _convert_phase_abbrevs_to_selected_boxes(
                current_phases, display_mode, boxes
            )

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
                choices=sorted(boxes),
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

        return ui.accordion(*ui_elements, id="accordion")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @render.ui
    def table_column_selector_ui():
        """Generate table column selector UI (only re-renders on initialization)."""
        if not _rv_ui_initialized():
            return

        columns = processor.data.columns

        return (
            ui.input_selectize(
                "select_table_columns",
                "Select table columns",
                {col: col for col in columns},
                multiple=True,
            ),
        )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # UI event handlers
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def _handle_sidebar_ui_changes():
        """Handle sidebar UI changes."""
        if not _rv_ui_initialized():
            return

        checkbox_groups = processor.get_all_group_names()
        current_display_modes = _rv_group_display_modes().copy()
        current_chemical_system = _rv_selected_chemical_system().copy()

        with reactive.isolate():
            current_selected_phase_abbrevs = _rv_selected_phase_abbrevs()

        new_chemical_system = list(input["selected_chemical_system"]())

        chemical_system_state_change = False
        if new_chemical_system is not None:
            if current_chemical_system != new_chemical_system:
                current_chemical_system = new_chemical_system
                chemical_system_state_change = True

        display_mode_state_change = False
        for group in checkbox_groups:
            group_id = processor.get_group_id(group)
            id_radio = f"mode_{group_id}"

            new_display_mode = input[id_radio]()

            if new_display_mode is not None:
                if current_display_modes.get(group) != new_display_mode:
                    current_display_modes[group] = new_display_mode
                    display_mode_state_change = True

            new_boxes = processor.get_grouped_phases(
                group, new_chemical_system, new_display_mode
            )
            new_selections = _convert_phase_abbrevs_to_selected_boxes(
                current_selected_phase_abbrevs, new_display_mode, new_boxes
            )

            ui.update_checkbox_group(
                id=f"boxes_{group_id}",
                choices=sorted(new_boxes),
                selected=list(new_selections),
            )

        if display_mode_state_change:
            _rv_group_display_modes.set(current_display_modes)
        if chemical_system_state_change:
            _rv_selected_chemical_system.set(current_chemical_system)

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
    def _re_toggle_similar_reactions() -> None:
        """Toggles similar reactions mode."""
        if not _rv_ui_initialized():
            return

        if _rv_toggle_similar_reactions() == "off":
            _rv_toggle_similar_reactions.set("or")
        elif _rv_toggle_similar_reactions() == "or":
            _rv_toggle_similar_reactions.set("and")
        else:
            _rv_toggle_similar_reactions.set("off")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.toggle_data_type)
    def _re_toggle_data_type() -> None:
        """Toggles data type mode."""
        if not _rv_ui_initialized():
            return

        if _rv_toggle_data_type() == "all":
            _rv_toggle_data_type.set("curves")
        elif _rv_toggle_data_type() == "curves":
            _rv_toggle_data_type.set("points")
        else:
            _rv_toggle_data_type.set("all")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.clear_table_row_selection)
    def _re_clear_table_row_selections() -> None:
        """Clears table selections."""
        if not _rv_ui_initialized():
            return

        _rv_selected_table_rows.set([])

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def _re_update_pressure_units():
        """Updates selected pressure units and stores the previous value."""
        if not _rv_ui_initialized():
            return

        selected_pressure_units = input.select_pressure_units()
        if (
            selected_pressure_units
            and selected_pressure_units != _rv_selected_pressure_units()
        ):
            _rv_selected_pressure_units.set(selected_pressure_units)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def _re_update_temperature_units():
        """Updates selected temperature units and stores the previous value."""
        if not _rv_ui_initialized():
            return

        selected_temperature_units = input.select_temperature_units()

        if (
            selected_temperature_units
            and selected_temperature_units != _rv_selected_temperature_units()
        ):
            _rv_selected_temperature_units.set(selected_temperature_units)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def _update_chemical_system():
        """Handle chemical system changes."""
        if not _rv_ui_initialized():
            return

        selected_chemical_system = list(input.selected_chemical_system())

        if selected_chemical_system:
            _rv_selected_chemical_system.set(selected_chemical_system)
        else:
            _rv_selected_chemical_system.set([])

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Table selection event listeners
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def _re_update_table_column_selections() -> None:
        """Updates selected table columns."""
        if not _rv_ui_initialized():
            return

        selected_columns = input.select_table_columns()

        if selected_columns:
            _rv_selected_table_columns.set(list(selected_columns))
        else:
            _rv_selected_table_columns.set(
                ["unique_id", "reaction", "type", "reference"]
            )

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    @reactive.event(input.table_selected_rows)
    def _re_update_table_row_selections() -> None:
        """Updates selected table rows."""
        if not _rv_ui_initialized():
            return

        indices = input.table_selected_rows()

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
        selected_columns = _rv_selected_table_columns()

        array_columns = [
            "T",
            "P",
            "T_uncertainty",
            "P_uncertainty",
            "lnK",
            "lnk_uncertainty",
        ]

        if not df.empty:
            if any(col in selected_columns for col in array_columns):
                return df[selected_columns].round(2).reset_index(drop=True)
            else:
                return (
                    df[selected_columns]
                    .drop_duplicates(subset="unique_id")
                    .reset_index(drop=True)
                )
        else:
            return pd.DataFrame(columns=selected_columns)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.calc
    def rc_get_plotly_data() -> pd.DataFrame:
        """Get data for Plotly widget."""
        df = rc_get_filtered_data()
        selected_table_rows = _rv_selected_table_rows()
        find_similar_mode = _rv_toggle_similar_reactions()
        data_plot_type = _rv_toggle_data_type()

        if selected_table_rows:
            if find_similar_mode != "off":
                reactants = processor.get_reactant_abbrevs_from_ids(selected_table_rows)
                products = processor.get_product_abbrevs_from_ids(selected_table_rows)

                if reactants or products:
                    df = processor.filter_by_reactants_and_product_abbrevs(
                        list(reactants),
                        list(products),
                        method=str(find_similar_mode),
                    )
                    df = convert_units(df)
                else:
                    df = pd.DataFrame(columns=df.columns)
            else:
                df = df[df["unique_id"].isin(selected_table_rows)]

        if data_plot_type == "all":
            return df
        elif data_plot_type == "points":
            return (
                df[df["plot_type"] == "point"]
                if "plot_type" in df.columns
                else pd.DataFrame(columns=df.columns)
            )
        elif data_plot_type == "curves":
            return (
                df[df["plot_type"] == "curve"]
                if "plot_type" in df.columns
                else pd.DataFrame(columns=df.columns)
            )
        else:
            return pd.DataFrame(columns=df.columns)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def convert_units(df: pd.DataFrame) -> pd.DataFrame:
        """"""
        with reactive.isolate():
            current_temperature_units = _rv_selected_temperature_units()
            current_pressure_units = _rv_selected_pressure_units()

        if current_temperature_units == "celcius":
            df = pd.DataFrame(df.apply(processor.convert_T_to_celcius, axis=1))
        elif current_temperature_units == "kelvin":
            df = pd.DataFrame(df.apply(processor.convert_T_to_kelvin, axis=1))

        if current_pressure_units == "gigapascal":
            df = pd.DataFrame(df.apply(processor.convert_P_to_gigapascal, axis=1))
        elif current_pressure_units == "kilobar":
            df = pd.DataFrame(df.apply(processor.convert_P_to_kbar, axis=1))

        return df

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.calc
    def rc_get_filtered_data() -> pd.DataFrame:
        """Initial filtering based on selected phases and plot type."""
        phases = _rv_selected_phase_abbrevs()

        if phases:
            df = processor.filter_by_reactants_and_product_abbrevs(
                list(phases), list(phases)
            )
        else:
            df = pd.DataFrame(columns=processor.data.columns)
            _ = input.clear_table_row_selection()

        return convert_units(df)

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    # Render and update widgets
    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @render.data_frame
    def table() -> render.DataTable:
        """Render table."""
        _ = input.clear_table_row_selection()
        df = rc_get_table_data()

        return render.DataTable(df, height="98%", selection_mode="rows")

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @output
    @render_plotly
    def plotly() -> go.FigureWidget:
        """Render plotly."""
        if not _rv_ui_initialized():
            return go.FigureWidget()

        print("Rendering plot ...")
        with reactive.isolate():
            df = rc_get_plotly_data()
            current_temperature_units = _rv_selected_temperature_units()
            current_pressure_units = _rv_selected_pressure_units()
            current_dark_mode = input.dark_mode() == "dark"

        df = processor.add_color_keys(df)
        uids = []
        if not df.empty and "unique_id" in df.columns:
            uids = df["unique_id"].unique().tolist()

        plotter = RxnDBPlotter(df, uids, current_dark_mode)
        fig = plotter.plot(current_temperature_units, current_pressure_units)

        # Create and return the widget
        widget = go.FigureWidget(fig)

        return widget

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @reactive.effect
    def _update_plotly_data() -> None:
        """Update plotly widget data without re-rendering."""
        if not _rv_ui_initialized():
            return

        widget = plotly.widget
        if widget is None:
            return

        print("Updating plot ...")
        df = rc_get_plotly_data()
        current_temperature_units = _rv_selected_temperature_units()
        current_pressure_units = _rv_selected_pressure_units()
        current_dark_mode = input.dark_mode() == "dark"

        df = processor.add_color_keys(df.copy())
        uids = []
        if not df.empty and "unique_id" in df.columns:
            uids = df["unique_id"].unique().tolist()

        plotter = RxnDBPlotter(df, uids, current_dark_mode)
        fig = plotter.plot(current_temperature_units, current_pressure_units)

        # Update widget in place using batch_update to prevent flickering
        with widget.batch_update():
            widget.data = ()
            widget.add_traces(fig.data)
            widget.layout.update(fig.layout)  # type: ignore

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @render.text
    def plot_settings() -> str:
        """Show plot settings info"""
        data_type = f"Data type: {_rv_toggle_data_type()}\n"
        similar_reactions = f"Similar rxns: {_rv_toggle_similar_reactions()}\n"
        table_selections = f"Table selections:\n{'\n'.join(_rv_selected_table_rows()) if _rv_selected_table_rows() else 'None'}"

        info = data_type + similar_reactions + table_selections

        return info


#######################################################
## .5. Shiny App                                 !!! ##
#######################################################
app: App = App(app_ui, server)
