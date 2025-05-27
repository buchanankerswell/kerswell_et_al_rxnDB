#######################################################
## .0. Load Libraries                            !!! ##
#######################################################
from shiny import ui
from shinywidgets import output_widget

from rxnDB.utils import app_dir


#######################################################
## .1. Shiny App UI                              !!! ##
#######################################################
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def configure_ui() -> ui.Tag:
    """
    Configures the Shiny app user interface
    """
    return ui.page_sidebar(
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Sidebar !!
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        ui.sidebar(
            ui.output_ui("sidebar_chemical_system_ui"),
            ui.output_ui("sidebar_checkbox_ui"),
            title="Phases",
            width=300,
            open={"desktop": "open", "mobile": "closed"},
        ),
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Custom CSS !!
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        ui.head_content(ui.include_css(app_dir / "styles.css")),
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Plotly and Table !!
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        ui.navset_card_pill(
            ui.nav_panel(
                "Visualization",
                ui.layout_sidebar(
                    ui.sidebar(
                        ui.tooltip(
                            ui.input_action_button(
                                "toggle_data_type",
                                "Toggle Data Type",
                                class_="popover-btn",
                            ),
                            "Show points, curves, or both",
                        ),
                        ui.tooltip(
                            ui.input_action_button(
                                "toggle_similar_reactions",
                                "Toggle Similar Reactions",
                                class_="popover-btn",
                            ),
                            "Find similar rxn sets by intersection or union (for table selections)",
                        ),
                        ui.input_selectize(
                            "select_temperature_units",
                            "Select temperature units",
                            {"celcius": "celcius", "kelvin": "kelvin"},
                        ),
                        ui.input_selectize(
                            "select_pressure_units",
                            "Select pressure units",
                            {"gigapascal": "gigapascal", "kilobar": "kilobar"},
                        ),
                        ui.output_text_verbatim("plot_settings", placeholder=False),
                        title="Plot Controls",
                        open={"desktop": "open", "mobile": "closed"},
                    ),
                    output_widget("plotly"),
                    fillable=True,
                ),
            ),
            ui.nav_panel(
                "Table",
                ui.page_sidebar(
                    ui.sidebar(
                        ui.input_action_button(
                            "clear_table_row_selection",
                            "Clear Table Selections",
                            class_="popover-btn",
                        ),
                        ui.output_ui("table_column_selector_ui"),
                        title="Table Controls",
                        open={"desktop": "open", "mobile": "closed"},
                    ),
                    ui.output_data_frame("table"),
                    fillable=True,
                ),
            ),
            ui.nav_spacer(),
            ui.nav_menu(
                "Settings",
                ui.nav_control(
                    ui.tooltip(
                        ui.input_dark_mode(id="dark_mode", class_="dark-mode-switch"),
                        "Dark/Light Mode",
                    ),
                ),
            ),
        ),
        title="rxnDB",
        fillable=True,
    )
