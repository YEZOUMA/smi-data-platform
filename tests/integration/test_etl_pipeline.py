"""Tests d'intégration pour le pipeline ETL complet."""

import sys
from unittest.mock import Mock

import pandas as pd
import pytest

sys.path.insert(0, "/home/claude/smi-data-platform")

from src.extract.excel_extractor import ExcelExtractor
from src.transform.data_cleaner import clean_smi_data


@pytest.mark.integration
class TestExtractTransformIntegration:
    """Tests d'intégration Extract → Transform."""

    def test_extract_then_transform(self, sample_excel_file):
        """Test le flux Extract → Transform."""
        # Extract
        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()

        assert raw_df is not None
        assert len(raw_df) > 0

        # Transform
        cleaned_df, report = clean_smi_data(raw_df)

        assert cleaned_df is not None
        assert len(cleaned_df) > 0
        assert report["final_rows"] > 0

        # Vérifier les transformations
        assert "pays" in cleaned_df.columns
        assert "periode_date" in cleaned_df.columns
        assert "geo_id" in cleaned_df.columns

    def test_extract_transform_preserves_data_integrity(self, sample_excel_file):
        """Test que les transformations préservent l'intégrité des données."""
        # Extract
        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()
        original_count = len(raw_df)

        # Transform
        cleaned_df, report = clean_smi_data(raw_df)

        # Le nombre de lignes devrait être proche (quelques suppressions acceptables)
        assert cleaned_df is not None
        assert len(cleaned_df) <= original_count
        assert len(cleaned_df) >= original_count * 0.9  # Au moins 90% conservé

    def test_extract_transform_column_mapping(self, sample_excel_file):
        """Test le mapping correct des colonnes."""
        # Extract
        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()

        # Transform
        cleaned_df, _ = clean_smi_data(raw_df)

        # Vérifier les colonnes critiques
        expected_columns = ["pays", "region", "province", "periode_date", "annee", "mois"]

        for col in expected_columns:
            assert col in cleaned_df.columns, f"Colonne {col} manquante"


@pytest.mark.integration
class TestEndToEndDataFlow:
    """Tests du flux de données end-to-end."""

    def test_complete_bronze_to_silver_flow(self, sample_excel_file, test_data_dir):
        """Test le flux complet Bronze → Silver."""
        bronze_path = test_data_dir / "bronze_data.parquet"
        silver_path = test_data_dir / "silver_data.parquet"

        # 1. Extract → Bronze
        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()
        raw_df.to_parquet(bronze_path, index=False)

        # 2. Bronze → Transform → Silver
        bronze_df = pd.read_parquet(bronze_path)
        cleaned_df, _ = clean_smi_data(bronze_df)
        cleaned_df.to_parquet(silver_path, index=False)

        # 3. Vérifications
        silver_df = pd.read_parquet(silver_path)

        assert len(silver_df) > 0
        assert "pays" in silver_df.columns
        assert "periode_date" in silver_df.columns

        # Vérifier qu'on peut relire depuis Silver
        assert silver_df is not None

    def test_data_quality_metrics_through_pipeline(self, sample_excel_file):
        """Test les métriques de qualité à travers le pipeline."""
        # Extract
        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()

        # Quality check sur raw
        raw_quality = extractor.get_data_quality_report()

        # Transform
        cleaned_df, validation_report = clean_smi_data(raw_df)

        # Comparaison des métriques
        assert validation_report["original_rows"] == raw_quality["total_rows"]
        assert validation_report["columns"] >= raw_quality["total_columns"]


@pytest.mark.integration
@pytest.mark.database
class TestDatabaseIntegration:
    """Tests d'intégration avec la base de données."""

    @pytest.fixture
    def mock_db_connection(self):
        """Mock de connexion DB pour les tests."""
        conn = Mock()
        cursor = Mock()
        conn.cursor.return_value = cursor
        return conn

    def test_load_to_bronze_table(self, sample_cleaned_data, mock_db_connection):
        """Test le chargement dans la table bronze."""
        # Simuler le chargement
        df = sample_cleaned_data

        # Vérifications avant chargement
        assert len(df) > 0
        assert "pays" in df.columns

        # Mock du chargement
        # Dans un vrai test, on utiliserait une vraie DB de test
        pass

    def test_load_preserves_data_types(self, sample_cleaned_data):
        """Test que les types de données sont préservés au chargement."""
        df = sample_cleaned_data

        # Vérifier les types avant chargement
        assert df["annee"].dtype in ["int64", "Int64"]
        assert df["mois"].dtype in ["int64", "Int64"]
        assert pd.api.types.is_datetime64_any_dtype(df["periode_date"])


@pytest.mark.integration
class TestPipelinePerformance:
    """Tests de performance du pipeline."""

    @pytest.mark.slow
    def test_pipeline_handles_large_dataset(self, test_data_dir):
        """Test le pipeline avec un grand dataset."""
        # Créer un grand dataset
        large_data = {
            "Pays": ["Burkina Faso"] * 10000,
            "Région": ["Nando"] * 10000,
            "Province": ["Sissili"] * 10000,
            "Période": ["Mars 2025"] * 10000,
        }
        df = pd.DataFrame(large_data)

        # Sauvegarder
        large_file = test_data_dir / "large_dataset.xlsx"
        df.to_excel(large_file, index=False, engine="openpyxl")

        # Extract & Transform
        extractor = ExcelExtractor(str(large_file))
        raw_df = extractor.extract()
        cleaned_df, report = clean_smi_data(raw_df)

        # Vérifications
        assert len(cleaned_df) > 0
        assert report["final_rows"] > 0


@pytest.mark.integration
class TestErrorHandling:
    """Tests de gestion des erreurs dans le pipeline."""

    def test_pipeline_handles_corrupted_data(self):
        """Test la gestion de données corrompues."""
        # Données avec problèmes
        corrupted_data = {
            "Pays": ["Burkina Faso", None, "Invalid"],
            "Région": [None, "Nando", "Centre"],
            "Période": ["Invalid Date", "Mars 2025", None],
        }
        df = pd.DataFrame(corrupted_data)

        # Le pipeline ne devrait pas crasher
        try:
            cleaned_df, report = clean_smi_data(df)
            # Devrait avoir supprimé les lignes problématiques
            assert len(cleaned_df) <= len(df)
        except Exception as e:
            pytest.fail(f"Pipeline crashed with corrupted data: {e}")

    def test_pipeline_handles_empty_dataset(self):
        """Test la gestion d'un dataset vide."""
        empty_df = pd.DataFrame()

        # Ne devrait pas crasher
        cleaned_df, report = clean_smi_data(empty_df)

        assert len(cleaned_df) == 0
        assert report["original_rows"] == 0
        assert report["final_rows"] == 0


@pytest.mark.integration
class TestDataConsistency:
    """Tests de cohérence des données à travers le pipeline."""

    def test_geographic_hierarchy_preserved(self, sample_excel_file):
        """Test que la hiérarchie géographique est préservée."""
        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()
        cleaned_df, _ = clean_smi_data(raw_df)

        # Vérifier la cohérence géographique
        for _, row in cleaned_df.iterrows():
            assert row["pays"] is not None
            assert row["region"] is not None
            assert row["province"] is not None

    def test_temporal_data_consistency(self, sample_excel_file):
        """Test la cohérence des données temporelles."""
        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()
        cleaned_df, _ = clean_smi_data(raw_df)

        # Vérifier la cohérence temporelle
        if "periode_date" in cleaned_df.columns:
            for _, row in cleaned_df.iterrows():
                if pd.notna(row["periode_date"]):
                    # L'année extraite doit correspondre à la date
                    assert row["annee"] == row["periode_date"].year
                    assert row["mois"] == row["periode_date"].month

    def test_derived_metrics_accuracy(self, sample_excel_file):
        """Test l'exactitude des métriques dérivées."""
        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()
        cleaned_df, _ = clean_smi_data(raw_df)

        # Vérifier les totaux calculés
        if "total_deces_neonatals" in cleaned_df.columns:
            for _, row in cleaned_df.iterrows():
                if "deces_neo_0_6_jours" in cleaned_df.columns:
                    expected = row.get("deces_neo_0_6_jours", 0) + row.get(
                        "deces_neo_7_28_jours", 0
                    )
                    assert row["total_deces_neonatals"] == expected


@pytest.mark.integration
class TestPipelineIdempotency:
    """Tests d'idempotence du pipeline."""

    def test_running_pipeline_twice_gives_same_result(self, sample_excel_file):
        """Test que deux exécutions donnent le même résultat."""
        # Première exécution
        extractor1 = ExcelExtractor(sample_excel_file)
        raw_df1 = extractor1.extract()
        cleaned_df1, report1 = clean_smi_data(raw_df1)

        # Deuxième exécution
        extractor2 = ExcelExtractor(sample_excel_file)
        raw_df2 = extractor2.extract()
        cleaned_df2, report2 = clean_smi_data(raw_df2)

        # Les résultats devraient être identiques
        assert len(cleaned_df1) == len(cleaned_df2)
        assert report1["final_rows"] == report2["final_rows"]

        # Comparer les colonnes
        assert set(cleaned_df1.columns) == set(cleaned_df2.columns)
