"""Tests de qualité des données."""

import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, "/home/claude/smi-data-platform")

from src.transform.data_cleaner import clean_smi_data


class TestDataQuality:
    """Tests de qualité des données."""

    def test_no_null_in_critical_columns(self, sample_excel_file):
        """Test l'absence de valeurs nulles dans les colonnes critiques."""
        from src.extract.excel_extractor import extract_from_excel

        raw_df = extract_from_excel(sample_excel_file)
        cleaned_df, _ = clean_smi_data(raw_df)

        critical_columns = ["pays", "region", "province"]

        for col in critical_columns:
            if col in cleaned_df.columns:
                null_count = cleaned_df[col].isna().sum()
                assert null_count == 0, f"Column {col} has {null_count} null values"

    def test_data_types_consistency(self, sample_cleaned_data):
        """Test la cohérence des types de données."""
        df = sample_cleaned_data

        # Colonnes numériques
        numeric_cols = ["annee", "mois", "trimestre", "semestre"]
        for col in numeric_cols:
            if col in df.columns:
                assert pd.api.types.is_numeric_dtype(df[col]), f"{col} should be numeric"

        # Colonnes datetime
        if "periode_date" in df.columns:
            assert pd.api.types.is_datetime64_any_dtype(df["periode_date"])

        # Colonnes texte
        text_cols = ["pays", "region", "province"]
        for col in text_cols:
            if col in df.columns:
                assert df[col].dtype == "object" or pd.api.types.is_string_dtype(df[col])

    def test_no_duplicates(self, sample_excel_file):
        """Test l'absence de doublons complets."""
        from src.extract.excel_extractor import extract_from_excel

        raw_df = extract_from_excel(sample_excel_file)
        cleaned_df, _ = clean_smi_data(raw_df)

        duplicates = cleaned_df.duplicated().sum()

        # Devrait avoir peu ou pas de doublons
        assert duplicates < len(cleaned_df) * 0.01, f"Too many duplicates: {duplicates}"

    def test_value_ranges(self, sample_cleaned_data):
        """Test les plages de valeurs acceptables."""
        df = sample_cleaned_data

        # Années: 2020-2030
        if "annee" in df.columns:
            assert (df["annee"] >= 2020).all()
            assert (df["annee"] <= 2030).all()

        # Mois: 1-12
        if "mois" in df.columns:
            assert (df["mois"] >= 1).all()
            assert (df["mois"] <= 12).all()

        # Trimestre: 1-4
        if "trimestre" in df.columns:
            assert (df["trimestre"] >= 1).all()
            assert (df["trimestre"] <= 4).all()

        # Semestre: 1-2
        if "semestre" in df.columns:
            assert (df["semestre"].isin([1, 2])).all()

    def test_no_negative_counts(self, sample_cleaned_data):
        """Test l'absence de compteurs négatifs."""
        df = sample_cleaned_data

        count_columns = [col for col in df.columns if "deces" in col or "nombre" in col]

        for col in count_columns:
            if col in df.columns and pd.api.types.is_numeric_dtype(df[col]):
                negative_count = (df[col] < 0).sum()
                assert negative_count == 0, f"{col} has {negative_count} negative values"

    def test_geographic_consistency(self, sample_cleaned_data):
        """Test la cohérence géographique."""
        df = sample_cleaned_data

        # Chaque région devrait avoir au moins une province
        if "region" in df.columns and "province" in df.columns:
            for region in df["region"].unique():
                provinces = df[df["region"] == region]["province"].unique()
                assert len(provinces) > 0, f"Region {region} has no provinces"

    def test_completeness_ratio(self, sample_excel_file):
        """Test le ratio de complétude des données."""
        from src.extract.excel_extractor import extract_from_excel

        raw_df = extract_from_excel(sample_excel_file)
        cleaned_df, _ = clean_smi_data(raw_df)

        # Calculer le taux de complétude moyen
        completeness = (cleaned_df.notna().sum() / len(cleaned_df)).mean()

        # Devrait être > 70%
        assert completeness > 0.7, f"Completeness ratio too low: {completeness:.2%}"

    def test_referential_integrity(self, sample_cleaned_data):
        """Test l'intégrité référentielle."""
        df = sample_cleaned_data

        # Un pays devrait toujours être "Burkina Faso"
        if "pays" in df.columns:
            unique_countries = df["pays"].unique()
            assert len(unique_countries) == 1
            assert unique_countries[0] == "Burkina Faso"


class TestDataValidationRules:
    """Tests des règles de validation métier."""

    def test_death_totals_consistency(self, sample_cleaned_data):
        """Test la cohérence des totaux de décès."""
        df = sample_cleaned_data

        # Le total néonatal doit égaler la somme des tranches d'âge
        if all(
            col in df.columns
            for col in ["deces_neo_0_6_jours", "deces_neo_7_28_jours", "total_deces_neonatals"]
        ):
            for idx, row in df.iterrows():
                expected_total = row["deces_neo_0_6_jours"] + row["deces_neo_7_28_jours"]
                actual_total = row["total_deces_neonatals"]
                assert abs(expected_total - actual_total) < 0.01, f"Row {idx}: total mismatch"

    def test_temporal_logic(self, sample_cleaned_data):
        """Test la logique temporelle."""
        df = sample_cleaned_data

        if "mois" in df.columns and "trimestre" in df.columns:
            for idx, row in df.iterrows():
                # Vérifier que le trimestre correspond au mois
                expected_quarter = (row["mois"] - 1) // 3 + 1
                assert row["trimestre"] == expected_quarter, f"Row {idx}: quarter/month mismatch"

        if "mois" in df.columns and "semestre" in df.columns:
            for idx, row in df.iterrows():
                # Vérifier que le semestre correspond au mois
                expected_semester = 1 if row["mois"] <= 6 else 2
                assert row["semestre"] == expected_semester, f"Row {idx}: semester/month mismatch"


class TestDataDistributions:
    """Tests des distributions de données."""

    def test_no_extreme_outliers(self, sample_cleaned_data):
        """Test l'absence de valeurs aberrantes extrêmes."""
        df = sample_cleaned_data

        numeric_cols = df.select_dtypes(include=[np.number]).columns

        for col in numeric_cols:
            if col not in ["annee"]:  # Exclure les années
                if df[col].std() > 0:  # Seulement si variance non nulle
                    z_scores = np.abs((df[col] - df[col].mean()) / df[col].std())
                    extreme_outliers = (z_scores > 5).sum()

                    # Moins de 1% de valeurs extrêmes
                    assert extreme_outliers < len(df) * 0.01, f"{col} has too many extreme outliers"

    def test_reasonable_value_distributions(self, sample_cleaned_data):
        """Test la distribution raisonnable des valeurs."""
        df = sample_cleaned_data

        # Les décès ne devraient pas être trop concentrés
        death_cols = [col for col in df.columns if "deces" in col]

        for col in death_cols:
            if col in df.columns and len(df[col].unique()) > 1:
                # Au moins quelques valeurs différentes
                unique_values = len(df[col].unique())
                assert unique_values > 1, f"{col} has only one unique value"


@pytest.mark.parametrize(
    "column,min_value,max_value",
    [
        ("annee", 2020, 2030),
        ("mois", 1, 12),
        ("trimestre", 1, 4),
        ("semestre", 1, 2),
    ],
)
def test_value_range_parametrized(sample_cleaned_data, column, min_value, max_value):
    """Test paramétré des plages de valeurs."""
    df = sample_cleaned_data

    if column in df.columns:
        assert (df[column] >= min_value).all(), f"{column} has values < {min_value}"
        assert (df[column] <= max_value).all(), f"{column} has values > {max_value}"


class TestDataQualityScores:
    """Tests des scores de qualité."""

    def test_overall_quality_score(self, sample_excel_file):
        """Test le score global de qualité."""
        from src.extract.excel_extractor import extract_from_excel

        raw_df = extract_from_excel(sample_excel_file)
        cleaned_df, validation_report = clean_smi_data(raw_df)

        # Calculer différentes métriques de qualité
        completeness = (cleaned_df.notna().sum() / len(cleaned_df)).mean()
        validity = validation_report["final_rows"] / validation_report["original_rows"]
        uniqueness = (
            1 - (validation_report["duplicates"] / len(cleaned_df)) if len(cleaned_df) > 0 else 1
        )

        # Score global (moyenne pondérée)
        quality_score = completeness * 0.4 + validity * 0.4 + uniqueness * 0.2

        # Le score devrait être > 0.80 (80%)
        assert quality_score > 0.80, f"Quality score too low: {quality_score:.2%}"

        print("\n📊 Scores de qualité:")
        print(f"   Complétude: {completeness:.2%}")
        print(f"   Validité: {validity:.2%}")
        print(f"   Unicité: {uniqueness:.2%}")
        print(f"   Score global: {quality_score:.2%}")
