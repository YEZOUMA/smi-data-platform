"""Tests unitaires pour le module excel_extractor."""

import sys

import pandas as pd
import pytest

sys.path.insert(0, "/home/claude/smi-data-platform")

from src.extract.excel_extractor import ExcelExtractor, extract_from_excel


class TestExcelExtractor:
    """Tests pour la classe ExcelExtractor."""

    def test_init_with_valid_file(self, sample_excel_file):
        """Test l'initialisation avec un fichier valide."""
        extractor = ExcelExtractor(sample_excel_file)
        assert extractor.file_path.exists()
        assert extractor.df is None

    def test_init_with_invalid_file(self):
        """Test l'initialisation avec un fichier inexistant."""
        with pytest.raises(FileNotFoundError):
            ExcelExtractor("/path/to/nonexistent/file.xls")

    def test_extract_success(self, sample_excel_file):
        """Test l'extraction réussie de données."""
        extractor = ExcelExtractor(sample_excel_file)
        df = extractor.extract()

        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10  # Nombre de lignes dans sample_data
        assert len(df.columns) > 0

    def test_extract_sets_df_attribute(self, sample_excel_file):
        """Test que extract() définit l'attribut df."""
        extractor = ExcelExtractor(sample_excel_file)
        extractor.extract()

        assert extractor.df is not None
        assert isinstance(extractor.df, pd.DataFrame)

    def test_get_schema_info_without_extract(self, sample_excel_file):
        """Test get_schema_info() avant extract() lève une erreur."""
        extractor = ExcelExtractor(sample_excel_file)

        with pytest.raises(ValueError, match="Aucune donnée extraite"):
            extractor.get_schema_info()

    def test_get_schema_info_after_extract(self, sample_excel_file):
        """Test get_schema_info() après extraction."""
        extractor = ExcelExtractor(sample_excel_file)
        extractor.extract()
        schema_info = extractor.get_schema_info()

        assert "num_rows" in schema_info
        assert "num_columns" in schema_info
        assert "columns" in schema_info
        assert "dtypes" in schema_info
        assert "memory_usage" in schema_info
        assert "missing_values" in schema_info

        assert schema_info["num_rows"] == 10
        assert schema_info["num_columns"] > 0
        assert isinstance(schema_info["columns"], list)

    def test_validate_schema_all_columns_present(self, sample_excel_file):
        """Test validate_schema() avec toutes les colonnes présentes."""
        extractor = ExcelExtractor(sample_excel_file)
        df = extractor.extract()

        expected_columns = list(df.columns)[:3]  # Prendre 3 colonnes
        is_valid = extractor.validate_schema(expected_columns)

        assert is_valid is True

    def test_validate_schema_missing_columns(self, sample_excel_file):
        """Test validate_schema() avec des colonnes manquantes."""
        extractor = ExcelExtractor(sample_excel_file)
        extractor.extract()

        expected_columns = ["Pays", "Région", "ColonneInexistante"]
        is_valid = extractor.validate_schema(expected_columns)

        assert is_valid is False

    def test_get_data_quality_report(self, sample_excel_file):
        """Test le rapport de qualité des données."""
        extractor = ExcelExtractor(sample_excel_file)
        extractor.extract()
        report = extractor.get_data_quality_report()

        assert "total_rows" in report
        assert "total_columns" in report
        assert "missing_values_pct" in report
        assert "duplicates" in report
        assert "numeric_columns" in report
        assert "object_columns" in report

        assert report["total_rows"] == 10
        assert report["duplicates"] >= 0

    def test_extract_with_metrics(self, sample_excel_file):
        """Test que les métriques Prometheus sont incrémentées."""
        from src.extract.excel_extractor import EXTRACTION_COUNTER, RECORDS_EXTRACTED

        # Capturer les valeurs avant
        before_success = EXTRACTION_COUNTER.labels(status="success")._value._value
        before_records = RECORDS_EXTRACTED._value._value

        extractor = ExcelExtractor(sample_excel_file)
        extractor.extract()

        # Les métriques devraient avoir augmenté
        after_success = EXTRACTION_COUNTER.labels(status="success")._value._value
        after_records = RECORDS_EXTRACTED._value._value

        assert after_success > before_success
        assert after_records > before_records


class TestExtractFromExcel:
    """Tests pour la fonction utilitaire extract_from_excel."""

    def test_extract_from_excel_success(self, sample_excel_file):
        """Test extraction rapide avec la fonction utilitaire."""
        df = extract_from_excel(sample_excel_file)

        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10

    def test_extract_from_excel_invalid_file(self):
        """Test avec fichier invalide."""
        with pytest.raises(FileNotFoundError):
            extract_from_excel("/invalid/path/file.xls")


@pytest.mark.slow
class TestExcelExtractorPerformance:
    """Tests de performance pour l'extraction."""

    def test_large_file_extraction(self, test_data_dir):
        """Test l'extraction d'un grand fichier."""
        # Créer un grand DataFrame
        large_df = pd.DataFrame({"col1": range(50000), "col2": ["value"] * 50000})

        large_file = test_data_dir / "large_file.xlsx"
        large_df.to_excel(large_file, index=False, engine="openpyxl")

        extractor = ExcelExtractor(str(large_file))
        df = extractor.extract()

        assert len(df) == 50000


@pytest.mark.parametrize("file_extension", [".xls", ".xlsx"])
def test_different_excel_formats(file_extension, sample_excel_data, test_data_dir):
    """Test l'extraction de différents formats Excel."""
    file_path = test_data_dir / f"test_data{file_extension}"

    if file_extension == ".xls":
        sample_excel_data.to_excel(file_path, index=False, engine="openpyxl")
    else:
        sample_excel_data.to_excel(file_path, index=False, engine="openpyxl")

    extractor = ExcelExtractor(str(file_path))
    df = extractor.extract()

    assert df is not None
    assert len(df) == len(sample_excel_data)
