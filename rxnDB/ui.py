#######################################################
## .0.              Load Libraries               !!! ##
#######################################################
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Shiny app !!
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
from shiny import ui
from faicons import icon_svg
from rxnDB.utils import app_dir
from shinywidgets import output_widget

#######################################################
## .1.              Shiny App UI                 !!! ##
#######################################################
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def configure_ui(phases: list[str], init_phases: list[str]) -> ui.page_sidebar:
    """
    Configures the Shiny app user interface
    """
    return ui.page_sidebar(
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Sidebar !!
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        ui.sidebar(
            ui.input_dark_mode(id="mode"),
            ui.input_checkbox_group("reactants", "Reactants", phases, selected=init_phases),
            ui.input_checkbox_group("products", "Products", phases, selected=init_phases)
        ),

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Top row with columns for action buttons !!
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        ui.layout_column_wrap(
            ui.input_action_button("download_plotly", "Download Figure"),
            ui.input_action_button("show_rxn_labels", "Show Rxn IDs"),
            ui.input_action_button("toggle_reactants", "Select All Reactants"),
            ui.input_action_button("toggle_products", "Select All Products"),
            fill=False
        ),

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        # Phase diagram and DataTable !!
        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        ui.layout_columns(
            ui.card(
                ui.card_header("Phase Diagram"),
                output_widget("plotly"),
                full_screen=True,
            ),
            ui.card(
                ui.card_header("Database"),
                ui.layout_column_wrap(
                    ui.input_action_button("toggle_find_similar_rxns", "Show Similar Rxns"),
                    ui.input_action_button("clear_selection", "Clear Selection"),
                    fill=False,
                ),
                ui.output_data_frame("datatable"),
                full_screen=True,
            )
        ),

        #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        ui.include_css(app_dir / "styles.css"),
        title="rxnsDB",
        fillable=True
    )
