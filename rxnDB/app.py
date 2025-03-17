from shiny import App, ui, render

app_ui = ui.page_fluid(
    ui.h1("Welcome to rxnDB"),
    ui.p("A Shiny app built with Python.")
)

def server(input, output, session):
    @render.text
    def message():
        return "Hello from rxnDB!"

app = App(app_ui, server)
