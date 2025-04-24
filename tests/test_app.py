#######################################################
## .0.              Load Libraries               !!! ##
#######################################################
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

import rxnDB.data.loader as db
import rxnDB.visualize as vis
from rxnDB.app import app
from rxnDB.ui import configure_ui


#######################################################
## .1.                Fixtures                   !!! ##
#######################################################
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def sample_data():
    """
    Fixture to provide sample data for testing
    """
    data = {
        "id": [1, 2, 3, 4],
        "reactant1": ["Ky", "And", "Ky", "And"],
        "reactant2": ["Sil", "Ol", "Ky", "Ol"],
        "reactant3": [None, None, "And", "Ky"],
        "product1": ["Sil", "Ol", "Sil", "Ol"],
        "product2": [None, None, "Ol", "And"],
        "product3": [None, None, None, None],
        "pmin": [1, 1, 1, 1],
        "pmax": [2, 2, 2, 2],
        "tmin": [100, 100, 100, 100],
        "tmax": [200, 200, 200, 200],
        "b": [0.5, 0.3, 0.6, 0.2],
        "t1": [0.1, 0.2, 0.1, 0.3],
        "t2": [0.1, 0.2, 0.1, 0.3],
        "t3": [0.1, 0.2, 0.1, 0.3],
        "t4": [0.1, 0.2, 0.1, 0.3],
        "rxn": ["Ky+Sil=>Sil", "And+Ol=>Ol", "Ky+Ky+And=>Sil+Ol", "And+Ol+Ky=>Ol+And"],
    }
    return pd.DataFrame(data)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def reactants():
    """
    Fixture to provide reactants
    """
    return ["Ky", "And", "Sil"]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def products():
    """
    Fixture to provide products
    """
    return ["And", "Sil", "Ol"]


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def filtered_data_by_rxn(sample_data, reactants, products):
    """
    Fixture to provide filtered data based on rxns
    """
    return db.filter_data_by_rxn(sample_data, reactants, products)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def filtered_data_by_ids(sample_data):
    """
    Fixture to provide filtered data based on rxn ids
    """
    ids = [1, 3]
    return db.filter_data_by_ids(sample_data, ids)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
def sample_plotly_data() -> pd.DataFrame:
    """
    Fixture to provide sample data for reaction-based tests
    """
    return pd.DataFrame(
        {
            "id": [1, 2],
            "P (GPa)": [1, 2],
            "T (˚C)": [100, 200],
            "Rxn": ["A+B=>C", "D+E=>F+G+H"],
        }
    )


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def app_ui():
    """
    Fixture to provide a configured UI object for testing
    """
    phases = ["Ky", "And", "Sil", "Ol", "Wd"]
    return configure_ui(phases, phases)


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def mock_input():
    """
    Fixture to create a mock input object for testing the server
    """
    mock = MagicMock()
    mock.reactants.return_value = ["Ky", "And", "Sil", "Ol", "Wd"]
    mock.products.return_value = ["Ky", "And", "Sil", "Ol", "Wd"]
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


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
@pytest.fixture
def mock_fig():
    """
    Fixture to create a mocked figure object for testing visualization
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
    def test_data_loader(self):
        """
        Test core data loading functionality
        """
        # Check basic data properties
        assert isinstance(db.phases, list)
        assert isinstance(db.data, pd.DataFrame)
        assert not db.data.empty

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_filter_data_by_rxn(self, filtered_data_by_rxn):
        """
        Test the filter_data_by_rxn function
        """
        assert isinstance(filtered_data_by_rxn, pd.DataFrame)
        assert not filtered_data_by_rxn.empty

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def test_filter_data_by_ids(self, filtered_data_by_ids):
        """
        Test the filter_data_by_ids function
        """
        assert isinstance(filtered_data_by_ids, pd.DataFrame)
        assert not filtered_data_by_ids.empty

    # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    @patch("plotly.graph_objects.Figure")
    def test_visualization(self, mock_fig):
        """
        Test core visualization functionality
        """
        mock_fig.return_value = mock_fig

        # Test plotting function
        _ = vis.plot_reaction_lines(
            df=sample_plotly_data(),
            rxn_ids=[1, 2],
            dark_mode=False,
            color_palette="Alphabet",
        )

        # Just verify the function runs and calls Figure constructor
        assert mock_fig.called

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
