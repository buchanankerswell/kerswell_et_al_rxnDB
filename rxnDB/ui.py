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
            ui.output_ui("phase_selector_ui"),
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
                            "clear_selection",
                            "Clear Selection",
                            class_="popover-btn",
                        ),
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
