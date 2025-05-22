#######################################################
## .0. Load Libraries                            !!! ##
#######################################################
from faicons import icon_svg
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
            ui.output_ui("phase_selector"),
            title="Phases",
            width=250,
            padding=[20, 10, 0, 20],
            open={"desktop": "open", "mobile": "closed"},
        ),
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Custom CSS !!
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        ui.head_content(ui.include_css(app_dir / "styles.css")),
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Plotly and Table !!
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        ui.layout_columns(
            ui.card(
                ui.card_header(
                    "Visualization",
                    ui.tooltip(
                        ui.input_dark_mode(id="dark_mode", class_="dark-mode-switch"),
                        "Dark/Light Mode",
                    ),
                    ui.popover(
                        ui.span(
                            icon_svg("gear"),
                            class_="popover-gear-icon",
                        ),
                        ui.input_action_button(
                            "toggle_data_type",
                            "Toggle Data Type",
                            class_="popover-btn",
                        ),
                        title="Plot settings",
                    ),
                ),
                output_widget("plotly"),
                full_screen=True,
            ),
            ui.card(
                ui.card_header(
                    "Table",
                    ui.popover(
                        ui.span(
                            icon_svg("gear"),
                            class_="popover-gear-icon",
                        ),
                        ui.input_action_button(
                            "clear_selection",
                            "Clear Selection",
                            class_="popover-btn",
                        ),
                        ui.input_action_button(
                            "toggle_similar_reactions",
                            "Toggle Similar Reactions",
                            class_="popover-btn",
                        ),
                        title="Table settings",
                    ),
                ),
                ui.output_data_frame("table"),
                full_screen=True,
            ),
        ),
        title="rxnDB",
        fillable=True,
    )
