"""Configuration pytest et fixtures communes pour tous les tests."""

import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

import numpy as np
import pandas as pd
import pytest

# Configuration pytest
pytest_plugins = []


@pytest.fixture(scope="session")
def test_data_dir():
    """Répertoire temporaire pour les données de test."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_excel_data():
    """Données Excel de test simulant la structure réelle."""
    data = {
        "Pays": ["Burkina Faso"] * 10,
        "Région": ["Nando", "Boucle", "Nando", "Sahel", "Centre"] * 2,
        "Province": ["Sissili", "Mouhoun", "Sissili", "Seno", "Kadiogo"] * 2,
        "District sanitaire": ["DS Léo", "DS Dédougou", "DS Léo", "DS Dori", "DS Bogodogo"] * 2,
        "Commune/arrondissement": ["Boura", "Dédougou", "Léo", "Dori", "Bogodogo"] * 2,
        "Formation sanitaire": ["BHM Boura", "CHU Dédougou", "CSPS Léo", "CM Dori", "CMA Bogodogo"]
        * 2,
        "Période": ["Mars 2025", "Février 2025", "Janvier 2025", "Décembre 2024", "Novembre 2024"]
        * 2,
        # Décès maternels par cause
        "Décès maternels par cause de complication obstétricale": [0, 1, 0, 2, 1, 0, 0, 1, 0, 1],
        "Décès maternels par cause de complication obstétricale Hémorragie": [
            0,
            1,
            0,
            1,
            0,
            0,
            0,
            0,
            0,
            1,
        ],
        "Décès maternels par cause de complication obstétricale Eclampsie": [
            0,
            0,
            0,
            1,
            0,
            0,
            0,
            1,
            0,
            0,
        ],
        "Décès maternels par cause de complication obstétricale Infections": [
            0,
            0,
            0,
            0,
            1,
            0,
            0,
            0,
            0,
            0,
        ],
        "Décès maternels par cause de complication obstétricale Autres complications obstétricales": [
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
        ],
        # Décès néonatals
        "Nouveau-nes decedes de 0-6 jours": [0, 2, 1, 3, 2, 1, 0, 2, 1, 2],
        "Nouveau-nes decedes de 7-28 jours": [0, 1, 0, 1, 1, 0, 0, 1, 0, 1],
        # Autres indicateurs
        "Nombre de décès maternel en communauté": [0, 0, 0, 1, 0, 0, 0, 0, 0, 0],
        "Nombre de décès maternels audités": [0, 1, 0, 2, 1, 0, 0, 1, 0, 1],
        "Nombre de décès néonatal en communauté": [0, 1, 0, 1, 0, 0, 0, 1, 0, 0],
        # Proportions et indicateurs
        "SMI-Proportion de deces maternels audites": [
            np.nan,
            100.0,
            np.nan,
            100.0,
            100.0,
            np.nan,
            np.nan,
            100.0,
            np.nan,
            100.0,
        ],
        "SMI-Proportion de femmes vues au 1er trimestre pour la CPN1": [
            45.5,
            67.8,
            52.3,
            38.9,
            71.2,
            49.1,
            55.6,
            63.4,
            44.7,
            58.9,
        ],
    }

    return pd.DataFrame(data)


@pytest.fixture
def sample_excel_file(sample_excel_data, test_data_dir):
    """Crée un fichier Excel temporaire pour les tests."""
    file_path = test_data_dir / "test_data.xlsx"
    sample_excel_data.to_excel(file_path, index=False, engine="openpyxl")
    return str(file_path)


@pytest.fixture
def sample_cleaned_data():
    """Données nettoyées de test."""
    dates = pd.date_range(start="2024-01-01", periods=10, freq="ME")

    data = {
        "pays": ["Burkina Faso"] * 10,
        "region": ["Nando", "Boucle", "Nando", "Sahel", "Centre"] * 2,
        "province": ["Sissili", "Mouhoun", "Sissili", "Seno", "Kadiogo"] * 2,
        "district_sanitaire": ["Ds Leo", "Ds Dedougou", "Ds Leo", "Ds Dori", "Ds Bogodogo"] * 2,
        "commune": ["Boura", "Dedougou", "Leo", "Dori", "Bogodogo"] * 2,
        "formation_sanitaire": ["Bhm Boura", "Chu Dedougou", "Csps Leo", "Cm Dori", "Cma Bogodogo"]
        * 2,
        "periode_date": dates,
        "annee": [d.year for d in dates],
        "mois": [d.month for d in dates],
        "trimestre": [d.quarter for d in dates],
        "semestre": [1 if d.month <= 6 else 2 for d in dates],
        # Décès
        "deces_mat_total": [0, 1, 0, 2, 1, 0, 0, 1, 0, 1],
        "deces_mat_hemorragie": [0, 1, 0, 1, 0, 0, 0, 0, 0, 1],
        "deces_neo_0_6_jours": [0, 2, 1, 3, 2, 1, 0, 2, 1, 2],
        "deces_neo_7_28_jours": [0, 1, 0, 1, 1, 0, 0, 1, 0, 1],
        "total_deces_neonatals": [0, 3, 1, 4, 3, 1, 0, 3, 1, 3],
        # Flags
        "is_complete": [True] * 10,
        "is_valid": [True] * 10,
        "has_anomalies": [False] * 10,
    }

    return pd.DataFrame(data)


@pytest.fixture
def mock_postgres_hook():
    """Mock du PostgresHook pour les tests."""
    mock_hook = Mock()
    mock_engine = Mock()
    mock_hook.get_sqlalchemy_engine.return_value = mock_engine
    return mock_hook


@pytest.fixture
def mock_postgres_connection():
    """Mock de la connexion PostgreSQL."""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


@pytest.fixture
def sample_validation_report():
    """Rapport de validation de test."""
    return {
        "original_rows": 57829,
        "final_rows": 57500,
        "rows_removed": 329,
        "columns": 28,
        "duplicates": 0,
        "missing_values_pct": {
            "pays": 0.0,
            "region": 0.0,
            "deces_mat_total": 15.5,
        },
        "negative_values": {},
    }


@pytest.fixture
def sample_extraction_metadata():
    """Métadonnées d'extraction de test."""
    return {
        "num_rows": 57829,
        "num_columns": 28,
        "extraction_timestamp": datetime.now().isoformat(),
        "source_file": "test_data.xls",
        "file_size_mb": 19.5,
    }


# Fixtures pour les tests d'intégration


@pytest.fixture
def integration_test_db():
    """Base de données de test pour les tests d'intégration."""
    # Configuration pour base de test
    config = {
        "host": "localhost",
        "port": 5433,
        "database": "smi_test",
        "user": "smi_user",
        "password": "smi_password",
    }
    return config


@pytest.fixture(scope="function")
def clean_test_tables(integration_test_db):
    """Nettoie les tables de test avant et après chaque test."""
    # Setup: nettoyer avant le test
    yield
    # Teardown: nettoyer après le test


# Fixtures pour Great Expectations


@pytest.fixture
def ge_context():
    """Contexte Great Expectations pour les tests."""
    from great_expectations.data_context import BaseDataContext

    context = BaseDataContext()
    return context


@pytest.fixture
def sample_expectation_suite():
    """Suite d'expectations de test."""
    return {
        "expectation_suite_name": "test_suite",
        "expectations": [
            {
                "expectation_type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "pays"},
            },
            {
                "expectation_type": "expect_column_values_to_be_in_set",
                "kwargs": {"column": "pays", "value_set": ["Burkina Faso"]},
            },
        ],
    }


# Helpers pour les tests


def assert_dataframe_equal(df1, df2, check_dtype=True):
    """Assert que deux DataFrames sont égaux."""
    pd.testing.assert_frame_equal(
        df1, df2, check_dtype=check_dtype, check_like=True  # Ignore l'ordre des colonnes
    )


def create_test_pipeline_run(status="success"):
    """Crée un mock d'exécution de pipeline."""
    return {
        "run_id": "test-run-123",
        "pipeline_name": "smi_full_pipeline",
        "start_time": datetime.now(),
        "end_time": datetime.now() + timedelta(minutes=15),
        "status": status,
        "records_processed": 57829,
        "records_inserted": 57500,
        "records_failed": 329,
    }


# Markers personnalisés
def pytest_configure(config):
    """Configuration des markers pytest personnalisés."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "e2e: marks tests as end-to-end tests")
    config.addinivalue_line("markers", "database: marks tests that require database connection")
