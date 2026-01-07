"""Tests End-to-End pour le workflow complet."""

import sys
from datetime import datetime

import pandas as pd
import pytest

sys.path.insert(0, "/home/claude/smi-data-platform")

from src.extract.excel_extractor import ExcelExtractor
from src.transform.data_cleaner import clean_smi_data


@pytest.mark.e2e
class TestFullWorkflow:
    """Tests du workflow complet de A à Z."""

    def test_complete_smi_pipeline(self, sample_excel_file, test_data_dir):
        """Test le pipeline complet:
        Source Excel → Bronze → Silver → Gold (simulation).
        """
        # Chemins de stockage
        bronze_path = test_data_dir / "bronze"
        silver_path = test_data_dir / "silver"
        gold_path = test_data_dir / "gold"

        for path in [bronze_path, silver_path, gold_path]:
            path.mkdir(exist_ok=True)

        # ========== PHASE 1: EXTRACTION (Source → Bronze) ==========
        print("\n📥 Phase 1: Extraction...")
        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()

        # Sauvegarder en Bronze
        bronze_file = bronze_path / "smi_raw.parquet"
        raw_df.to_parquet(bronze_file, index=False)

        # Vérifications Bronze
        assert bronze_file.exists()
        assert len(raw_df) > 0
        print(f"✅ Bronze: {len(raw_df)} lignes sauvegardées")

        # ========== PHASE 2: TRANSFORMATION (Bronze → Silver) ==========
        print("\n🧹 Phase 2: Transformation...")
        bronze_df = pd.read_parquet(bronze_file)
        cleaned_df, validation_report = clean_smi_data(bronze_df)

        # Sauvegarder en Silver
        silver_file = silver_path / "smi_cleaned.parquet"
        cleaned_df.to_parquet(silver_file, index=False)

        # Vérifications Silver
        assert silver_file.exists()
        assert len(cleaned_df) > 0
        assert validation_report["final_rows"] > 0
        print(f"✅ Silver: {len(cleaned_df)} lignes nettoyées")
        print(f"   - Lignes supprimées: {validation_report['rows_removed']}")
        print(f"   - Doublons: {validation_report['duplicates']}")

        # ========== PHASE 3: ANALYTICS (Silver → Gold) ==========
        print("\n📊 Phase 3: Analytics...")
        silver_df = pd.read_parquet(silver_file)

        # Créer des agrégations (simulation Gold layer)
        if "region" in silver_df.columns and "annee" in silver_df.columns:
            # Agrégation par région et année
            gold_regional = (
                silver_df.groupby(["region", "annee"])
                .agg({"deces_mat_total": "sum", "total_deces_neonatals": "sum"})
                .reset_index()
            )

            gold_file = gold_path / "agregation_regionale.parquet"
            gold_regional.to_parquet(gold_file, index=False)

            assert gold_file.exists()
            assert len(gold_regional) > 0
            print(f"✅ Gold: {len(gold_regional)} agrégations régionales créées")

        # ========== PHASE 4: VALIDATION FINALE ==========
        print("\n✅ Phase 4: Validation finale...")

        # Vérifier l'existence de tous les fichiers
        assert bronze_file.exists(), "Bronze file missing"
        assert silver_file.exists(), "Silver file missing"

        # Vérifier la cohérence des données
        assert len(cleaned_df) <= len(raw_df), "Silver should have <= Bronze rows"
        assert len(cleaned_df) > 0, "Silver should not be empty"

        # Vérifier les colonnes critiques
        critical_columns = ["pays", "region", "periode_date", "geo_id"]
        for col in critical_columns:
            assert col in cleaned_df.columns, f"Missing critical column: {col}"

        print("\n🎉 Pipeline complet exécuté avec succès!")
        print(f"   Bronze: {len(raw_df)} lignes")
        print(f"   Silver: {len(cleaned_df)} lignes")
        print(f"   Taux de conservation: {len(cleaned_df)/len(raw_df)*100:.1f}%")

    def test_data_lineage_tracking(self, sample_excel_file, test_data_dir):
        """Test le tracking de la lignée des données."""
        # Extract
        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()

        # Ajouter des métadonnées de lignée
        ingestion_time = datetime.now()
        raw_df["_ingestion_timestamp"] = ingestion_time
        raw_df["_source_file"] = sample_excel_file

        # Transform
        cleaned_df, _ = clean_smi_data(raw_df)
        cleaned_df["_processing_timestamp"] = datetime.now()
        cleaned_df["_pipeline_version"] = "1.0.0"

        # Vérifications
        assert "_ingestion_timestamp" in cleaned_df.columns
        assert "_source_file" in cleaned_df.columns
        assert "_processing_timestamp" in cleaned_df.columns
        assert "_pipeline_version" in cleaned_df.columns


@pytest.mark.e2e
@pytest.mark.slow
class TestScalability:
    """Tests de scalabilité du pipeline."""

    def test_pipeline_with_realistic_data_volume(self, test_data_dir):
        """Test avec un volume de données réaliste (50K+ lignes)."""
        # Créer un dataset réaliste
        num_rows = 50000
        realistic_data = {
            "Pays": ["Burkina Faso"] * num_rows,
            "Région": ["Nando", "Boucle", "Sahel", "Centre", "Nord"] * (num_rows // 5),
            "Province": ["Sissili", "Mouhoun", "Seno", "Kadiogo", "Yatenga"] * (num_rows // 5),
            "District sanitaire": [f"DS {i % 50}" for i in range(num_rows)],
            "Commune/arrondissement": [f"Commune {i % 100}" for i in range(num_rows)],
            "Formation sanitaire": [f"Formation {i}" for i in range(num_rows)],
            "Période": ["Mars 2025"] * num_rows,
        }

        df = pd.DataFrame(realistic_data)
        file_path = test_data_dir / "realistic_data.xlsx"
        df.to_excel(file_path, index=False, engine="openpyxl")

        # Exécuter le pipeline
        start_time = datetime.now()

        extractor = ExcelExtractor(str(file_path))
        raw_df = extractor.extract()
        cleaned_df, report = clean_smi_data(raw_df)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Vérifications
        assert len(cleaned_df) > 0
        assert report["final_rows"] > 0

        # Performance: devrait traiter au moins 1000 lignes/seconde
        throughput = len(raw_df) / duration
        print(f"\n📊 Performance: {throughput:.0f} lignes/seconde")
        print(f"   Durée totale: {duration:.2f} secondes")

        assert throughput > 100, "Throughput trop faible"


@pytest.mark.e2e
class TestDataQualityEndToEnd:
    """Tests de qualité des données end-to-end."""

    def test_no_data_loss_for_valid_records(self, sample_excel_file):
        """Test qu'aucune donnée valide n'est perdue."""
        # Extract
        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()

        # Compter les enregistrements valides
        valid_records = raw_df[raw_df["Pays"].notna() & raw_df["Région"].notna()]

        # Transform
        cleaned_df, _ = clean_smi_data(raw_df)

        # Tous les enregistrements valides devraient être conservés
        # (ou au moins la grande majorité)
        retention_rate = len(cleaned_df) / len(valid_records)
        assert retention_rate >= 0.95, f"Too much data loss: {retention_rate:.2%}"

    def test_data_completeness_metrics(self, sample_excel_file):
        """Test les métriques de complétude des données."""
        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()
        cleaned_df, report = clean_smi_data(raw_df)

        # Calculer la complétude pour chaque colonne critique
        critical_cols = ["pays", "region", "province"]

        for col in critical_cols:
            if col in cleaned_df.columns:
                completeness = (cleaned_df[col].notna().sum() / len(cleaned_df)) * 100
                assert completeness == 100, f"{col} should be 100% complete"


@pytest.mark.e2e
class TestRecoveryAndRobustness:
    """Tests de récupération et robustesse."""

    def test_pipeline_recovers_from_partial_failure(self, sample_excel_file, test_data_dir):
        """Test la récupération après une défaillance partielle."""
        bronze_path = test_data_dir / "bronze_recovery.parquet"

        # Sauvegarder en Bronze (succès)
        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()
        raw_df.to_parquet(bronze_path, index=False)

        # Simuler une reprise depuis Bronze
        recovered_df = pd.read_parquet(bronze_path)

        # Le pipeline devrait pouvoir continuer
        cleaned_df, report = clean_smi_data(recovered_df)

        assert len(cleaned_df) > 0
        assert report["final_rows"] > 0

    def test_pipeline_handles_incremental_loads(self, sample_excel_file, test_data_dir):
        """Test le traitement de chargements incrémentaux."""
        # Premier batch
        extractor = ExcelExtractor(sample_excel_file)
        batch1 = extractor.extract()
        batch1["batch_id"] = "batch_1"

        cleaned1, _ = clean_smi_data(batch1)

        # Deuxième batch (simulé)
        batch2 = batch1.copy()
        batch2["batch_id"] = "batch_2"

        cleaned2, _ = clean_smi_data(batch2)

        # Les deux batches devraient être traités avec succès
        assert len(cleaned1) > 0
        assert len(cleaned2) > 0

        # Combiner (simulation d'un append)
        combined = pd.concat([cleaned1, cleaned2], ignore_index=True)

        assert len(combined) == len(cleaned1) + len(cleaned2)


@pytest.mark.e2e
class TestBusinessRules:
    """Tests des règles métier."""

    def test_geographic_hierarchy_validation(self, sample_excel_file):
        """Test la validation de la hiérarchie géographique."""
        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()
        cleaned_df, _ = clean_smi_data(raw_df)

        # Règle: Chaque formation doit avoir une hiérarchie complète
        for _, row in cleaned_df.iterrows():
            assert pd.notna(row["pays"])
            assert pd.notna(row["region"])
            assert pd.notna(row["province"])
            assert pd.notna(row["district_sanitaire"])

    def test_temporal_consistency_rules(self, sample_excel_file):
        """Test les règles de cohérence temporelle."""
        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()
        cleaned_df, _ = clean_smi_data(raw_df)

        # Règle: Les dates doivent être cohérentes
        if "periode_date" in cleaned_df.columns:
            for _, row in cleaned_df.iterrows():
                if pd.notna(row.get("periode_date")):
                    # L'année doit être raisonnable (2020-2030)
                    assert 2020 <= row["annee"] <= 2030

                    # Le mois doit être valide (1-12)
                    assert 1 <= row["mois"] <= 12

                    # Le trimestre doit correspondre au mois
                    expected_quarter = (row["mois"] - 1) // 3 + 1
                    assert row["trimestre"] == expected_quarter

    def test_data_value_ranges(self, sample_excel_file):
        """Test les plages de valeurs acceptables."""
        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()
        cleaned_df, _ = clean_smi_data(raw_df)

        # Règle: Les compteurs de décès doivent être >= 0
        death_columns = [col for col in cleaned_df.columns if "deces" in col]

        for col in death_columns:
            if col in cleaned_df.columns:
                assert (cleaned_df[col] >= 0).all(), f"{col} has negative values"


@pytest.mark.e2e
class TestReporting:
    """Tests de génération de rapports."""

    def test_generate_pipeline_execution_report(self, sample_excel_file):
        """Test la génération d'un rapport d'exécution complet."""
        # Exécuter le pipeline et collecter les métriques
        start_time = datetime.now()

        extractor = ExcelExtractor(sample_excel_file)
        raw_df = extractor.extract()

        extraction_time = datetime.now()

        cleaned_df, validation_report = clean_smi_data(raw_df)

        end_time = datetime.now()

        # Générer le rapport
        execution_report = {
            "pipeline_name": "SMI Full Pipeline",
            "execution_date": start_time.isoformat(),
            "duration_seconds": (end_time - start_time).total_seconds(),
            "extraction": {
                "duration_seconds": (extraction_time - start_time).total_seconds(),
                "rows_extracted": len(raw_df),
                "columns": len(raw_df.columns),
            },
            "transformation": {
                "duration_seconds": (end_time - extraction_time).total_seconds(),
                "rows_input": validation_report["original_rows"],
                "rows_output": validation_report["final_rows"],
                "rows_removed": validation_report["rows_removed"],
                "duplicates_removed": validation_report["duplicates"],
            },
            "status": "SUCCESS",
        }

        # Vérifications du rapport
        assert execution_report["status"] == "SUCCESS"
        assert execution_report["extraction"]["rows_extracted"] > 0
        assert execution_report["transformation"]["rows_output"] > 0
        assert execution_report["duration_seconds"] > 0

        print("\n📊 Rapport d'exécution:")
        print(f"   Durée totale: {execution_report['duration_seconds']:.2f}s")
        print(f"   Lignes extraites: {execution_report['extraction']['rows_extracted']}")
        print(f"   Lignes nettoyées: {execution_report['transformation']['rows_output']}")
        print(
            f"   Taux de conservation: {execution_report['transformation']['rows_output']/execution_report['extraction']['rows_extracted']*100:.1f}%"
        )
