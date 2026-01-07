"""Tests unitaires pour le module data_cleaner."""

import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, "/home/claude/smi-data-platform")

from src.transform.data_cleaner import SMIDataCleaner, clean_smi_data


class TestSMIDataCleaner:
    """Tests pour la classe SMIDataCleaner."""

    def test_init_with_dataframe(self, sample_excel_data):
        """Test l'initialisation avec un DataFrame."""
        cleaner = SMIDataCleaner(sample_excel_data)

        assert cleaner.df is not None
        assert len(cleaner.df) == len(sample_excel_data)
        assert cleaner.original_row_count == len(sample_excel_data)

    def test_init_copies_dataframe(self, sample_excel_data):
        """Test que le DataFrame est copié (pas de référence)."""
        cleaner = SMIDataCleaner(sample_excel_data)

        # Modifier le cleaner.df ne doit pas affecter l'original
        cleaner.df.iloc[0, 0] = "Modified"
        assert sample_excel_data.iloc[0, 0] != "Modified"

    def test_clean_column_names(self, sample_excel_data):
        """Test le nettoyage des noms de colonnes."""
        cleaner = SMIDataCleaner(sample_excel_data)
        cleaner.clean_column_names()

        # Vérifier que les colonnes sont en minuscules
        for col in cleaner.df.columns:
            assert col == col.lower()
            assert " " not in col  # Pas d'espaces

        # Vérifier des transformations spécifiques
        assert "pays" in cleaner.df.columns
        assert "region" in cleaner.df.columns
        assert "periode" in cleaner.df.columns

    def test_clean_column_names_removes_accents(self):
        """Test la suppression des accents dans les noms de colonnes."""
        df = pd.DataFrame({"Région": [1, 2], "Période": [3, 4], "Décès": [5, 6]})

        cleaner = SMIDataCleaner(df)
        cleaner.clean_column_names()

        assert "region" in cleaner.df.columns
        assert "periode" in cleaner.df.columns
        assert "deces" in cleaner.df.columns

    def test_handle_missing_values_counters(self):
        """Test le traitement des valeurs manquantes pour les compteurs."""
        df = pd.DataFrame(
            {
                "pays": ["Burkina Faso"] * 5,
                "region": ["Nando"] * 5,
                "deces_mat_total": [1, np.nan, 2, np.nan, 3],
                "nombre_deces": [np.nan, 1, 2, np.nan, 4],
            }
        )

        cleaner = SMIDataCleaner(df)
        cleaner.clean_column_names()
        cleaner.handle_missing_values()

        # Les NaN dans les compteurs devraient être remplacés par 0
        assert cleaner.df["deces_mat_total"].isna().sum() == 0
        assert cleaner.df["nombre_deces"].isna().sum() == 0
        assert cleaner.df["deces_mat_total"].iloc[1] == 0

    def test_handle_missing_values_removes_null_geography(self):
        """Test la suppression des lignes avec géographie manquante."""
        df = pd.DataFrame(
            {
                "pays": ["Burkina Faso", "Burkina Faso", None, "Burkina Faso"],
                "region": ["Nando", None, "Sahel", "Centre"],
                "province": ["Sissili", "Mouhoun", "Seno", None],
                "deces_mat_total": [1, 2, 3, 4],
            }
        )

        cleaner = SMIDataCleaner(df)
        cleaner.clean_column_names()
        before_count = len(cleaner.df)
        cleaner.handle_missing_values()
        after_count = len(cleaner.df)

        # Devrait supprimer 3 lignes (celles avec None dans géographie)
        assert after_count < before_count
        assert cleaner.df["pays"].isna().sum() == 0
        assert cleaner.df["region"].isna().sum() == 0

    def test_parse_period_french_months(self):
        """Test le parsing des périodes en français."""
        df = pd.DataFrame(
            {
                "pays": ["Burkina Faso"] * 4,
                "region": ["Nando"] * 4,
                "periode": ["Janvier 2025", "Février 2025", "Mars 2025", "Avril 2025"],
            }
        )

        cleaner = SMIDataCleaner(df)
        cleaner.clean_column_names()
        cleaner.parse_period()

        assert "periode_date" in cleaner.df.columns
        assert "annee" in cleaner.df.columns
        assert "mois" in cleaner.df.columns
        assert "trimestre" in cleaner.df.columns

        # Vérifier les valeurs
        assert cleaner.df["annee"].iloc[0] == 2025
        assert cleaner.df["mois"].iloc[0] == 1
        assert cleaner.df["trimestre"].iloc[0] == 1

    def test_parse_period_extracts_all_components(self):
        """Test l'extraction de toutes les composantes temporelles."""
        df = pd.DataFrame({"pays": ["Burkina Faso"], "region": ["Nando"], "periode": ["Mars 2025"]})

        cleaner = SMIDataCleaner(df)
        cleaner.clean_column_names()
        cleaner.parse_period()

        assert cleaner.df["annee"].iloc[0] == 2025
        assert cleaner.df["mois"].iloc[0] == 3
        assert cleaner.df["trimestre"].iloc[0] == 1
        assert cleaner.df["semestre"].iloc[0] == 1

    def test_normalize_geography(self):
        """Test la normalisation de la géographie."""
        df = pd.DataFrame(
            {
                "pays": ["  burkina faso  ", "BURKINA FASO"],
                "region": ["nando  ", "  BOUCLE"],
                "province": ["Sissili", "mouhoun"],
                "district_sanitaire": ["DS Léo", "DS Dédougou"],
                "commune": ["Boura", "Dédougou"],
                "formation_sanitaire": ["BHM Boura", "CHU Dédougou"],
            }
        )

        cleaner = SMIDataCleaner(df)
        cleaner.clean_column_names()
        cleaner.normalize_geography()

        # Vérifier la normalisation
        assert cleaner.df["pays"].iloc[0] == "Burkina Faso"  # Title case
        assert cleaner.df["pays"].iloc[1] == "Burkina Faso"
        assert cleaner.df["region"].iloc[0] == "Nando"  # Espaces supprimés

        # Vérifier la création de geo_id
        assert "geo_id" in cleaner.df.columns

    def test_calculate_derived_metrics_total_neonatals(self):
        """Test le calcul du total des décès néonatals."""
        df = pd.DataFrame(
            {
                "pays": ["Burkina Faso"] * 3,
                "region": ["Nando"] * 3,
                "deces_neo_0_6_jours": [2, 3, 1],
                "deces_neo_7_28_jours": [1, 2, 0],
            }
        )

        cleaner = SMIDataCleaner(df)
        cleaner.clean_column_names()
        cleaner.calculate_derived_metrics()

        assert "total_deces_neonatals" in cleaner.df.columns
        assert cleaner.df["total_deces_neonatals"].iloc[0] == 3  # 2 + 1
        assert cleaner.df["total_deces_neonatals"].iloc[1] == 5  # 3 + 2
        assert cleaner.df["total_deces_neonatals"].iloc[2] == 1  # 1 + 0

    def test_validate_data_returns_report(self, sample_excel_data):
        """Test que validate_data retourne un rapport complet."""
        cleaner = SMIDataCleaner(sample_excel_data)
        report = cleaner.validate_data()

        assert "original_rows" in report
        assert "final_rows" in report
        assert "rows_removed" in report
        assert "columns" in report
        assert "missing_values_pct" in report
        assert "duplicates" in report
        assert "negative_values" in report

        assert report["original_rows"] == len(sample_excel_data)

    def test_get_cleaned_data_returns_copy(self, sample_excel_data):
        """Test que get_cleaned_data retourne une copie."""
        cleaner = SMIDataCleaner(sample_excel_data)
        df1 = cleaner.get_cleaned_data()
        df2 = cleaner.get_cleaned_data()

        # Modifier df1 ne doit pas affecter df2
        df1.iloc[0, 0] = "Modified"
        assert df2.iloc[0, 0] != "Modified"

    def test_clean_pipeline_executes_all_steps(self, sample_excel_data):
        """Test que clean_pipeline exécute toutes les étapes."""
        cleaner = SMIDataCleaner(sample_excel_data)
        cleaner.clean_pipeline()

        # Vérifier que chaque transformation a été appliquée
        # Colonnes nettoyées
        assert "pays" in cleaner.df.columns

        # Période parsée
        assert "periode_date" in cleaner.df.columns
        assert "annee" in cleaner.df.columns

        # Géographie normalisée
        assert "geo_id" in cleaner.df.columns

        # Métriques calculées
        # Note: Dépend de la présence des colonnes nécessaires

    def test_chaining_methods(self, sample_excel_data):
        """Test l'enchaînement des méthodes."""
        cleaner = SMIDataCleaner(sample_excel_data)
        result = cleaner.clean_column_names().handle_missing_values().normalize_geography()

        # Devrait retourner self
        assert result is cleaner


class TestCleanSMIData:
    """Tests pour la fonction utilitaire clean_smi_data."""

    def test_clean_smi_data_returns_tuple(self, sample_excel_data):
        """Test que la fonction retourne un tuple (df, report)."""
        cleaned_df, report = clean_smi_data(sample_excel_data)

        assert isinstance(cleaned_df, pd.DataFrame)
        assert isinstance(report, dict)

    def test_clean_smi_data_report_structure(self, sample_excel_data):
        """Test la structure du rapport retourné."""
        _, report = clean_smi_data(sample_excel_data)

        assert "original_rows" in report
        assert "final_rows" in report
        assert "rows_removed" in report
        assert "columns" in report


@pytest.mark.parametrize(
    "input_period,expected_month",
    [
        ("Janvier 2025", 1),
        ("Février 2025", 2),
        ("Mars 2025", 3),
        ("Décembre 2024", 12),
    ],
)
def test_parse_period_parametrized(input_period, expected_month):
    """Test le parsing de différentes périodes."""
    df = pd.DataFrame({"pays": ["Burkina Faso"], "region": ["Nando"], "periode": [input_period]})

    cleaner = SMIDataCleaner(df)
    cleaner.clean_column_names()
    cleaner.parse_period()

    assert cleaner.df["mois"].iloc[0] == expected_month


class TestDataCleanerEdgeCases:
    """Tests des cas limites."""

    def test_empty_dataframe(self):
        """Test avec un DataFrame vide."""
        df = pd.DataFrame()
        cleaner = SMIDataCleaner(df)

        assert len(cleaner.df) == 0
        assert cleaner.original_row_count == 0

    def test_all_missing_values(self):
        """Test avec toutes les valeurs manquantes."""
        df = pd.DataFrame(
            {"pays": [None, None], "region": [None, None], "deces_mat_total": [None, None]}
        )

        cleaner = SMIDataCleaner(df)
        cleaner.clean_column_names()
        cleaner.handle_missing_values()

        # Toutes les lignes devraient être supprimées
        # (géographie manquante)
        assert len(cleaner.df) == 0

    def test_duplicate_column_names(self):
        """Test avec des noms de colonnes dupliqués."""
        # pandas gère automatiquement les doublons
        df = pd.DataFrame([[1, 2, 3]], columns=["col", "col", "col"])
        cleaner = SMIDataCleaner(df)
        cleaner.clean_column_names()

        # Devrait avoir des noms uniques
        assert len(set(cleaner.df.columns)) == len(cleaner.df.columns)
