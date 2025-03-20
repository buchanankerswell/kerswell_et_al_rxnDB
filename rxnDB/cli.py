#######################################################
## .0.              Load Libraries               !!! ##
#######################################################
import argparse

#######################################################
## .1.                   CLI                     !!! ##
#######################################################
#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def main() -> None:
    """
    Command line interface for launching the rxndb Shiny app
    """
    parser = argparse.ArgumentParser(description="Launch the rxnDB Shiny app")
    parser.add_argument("--port", type=int, default=8000,
                        help="Port to run the app on (default: 8000)")
    parser.add_argument("--host", type=str, default="127.0.0.1",
                        help="Host to run the app on (default: 127.0.0.1)")
    parser.add_argument("--launch-browser", action="store_true", default=True,
                        help="Open the browser automatically (default: True)")
    parser.add_argument("--reload", action="store_true", default=True,
                        help="Auto-reload the app when files change (default: True)")
    args = parser.parse_args()

    # Import here to avoid circular imports
    from shiny import run_app

    app_import_string: str = "rxnDB.app:app"

    options: dict[str, bool | int] = {
        "port": args.port,
        "host": args.host,
        "launch_browser": args.launch_browser,
        "reload": args.reload
    }

    run_app(app_import_string, **options)

#~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
if __name__ == "__main__":
    main()