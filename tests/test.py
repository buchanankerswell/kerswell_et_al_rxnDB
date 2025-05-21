#######################################################
## .0.              Load Libraries               !!! ##
#######################################################
from unittest.mock import MagicMock

import pytest

from rxnDB.app import app
from rxnDB.ui import configure_ui


#######################################################
## .1.                Fixtures                   !!! ##
#######################################################
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def app_ui():
    """
    Fixture to provide a configured UI object for testing
    """
    phases = ["aluminosilicate", "olivine", "spinel", "wadsleyite", "ringwoodite"]
    return configure_ui(phases, phases)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def mock_input():
    """
    Fixture to create a mock input object for testing the server
    """
    mock = MagicMock()
    mock.reactants.return_value = [
        "aluminosilicate",
        "olivine",
        "spinel",
        "wadsleyite",
        "ringwoodite",
    ]
    mock.products.return_value = [
        "aluminosilicate",
        "olivine",
        "spinel",
        "wadsleyite",
        "ringwoodite",
    ]
    mock.mode.return_value = "light"
    mock.datatable_selected_rows.return_value = []

    return mock


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def mock_output():
    """
    Fixture to create a mock output object for testing the server
    """
    return MagicMock()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def mock_session():
    """
    Fixture to create a mock session object for testing the server
    """
    return MagicMock()


#######################################################
## .2.               Test Suite                  !!! ##
#######################################################
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
class TestApp:
    """
    Test suite for the main components of the Shiny app
    """

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_ui_configuration(self, app_ui):
        """
        Just check that UI configuration runs without errors
        """
        assert app_ui is not None

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_app_creation(self):
        """
        Test that the app object is properly created
        """
        assert app is not None
        assert hasattr(app, "ui")
        assert hasattr(app, "server")


#######################################################
## .3.          Server Smoke Test                !!! ##
#######################################################
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def test_server_smoke(mock_input, mock_output, mock_session):
    """
    Just test that server runs without errors
    """
    try:
        app.server(mock_input, mock_output, mock_session)
        assert True
    except Exception as e:
        pytest.fail(f"Server initialization failed with error: {e}")
