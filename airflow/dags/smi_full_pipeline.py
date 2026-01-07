"""DAG Airflow principal pour le pipeline SMI complet."""

import sys
from datetime import datetime, timedelta

from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

from airflow import DAG

sys.path.insert(0, "/opt/airflow")

import logging

import pandas as pd

from src.extract.excel_extractor import ExcelExtractor
from src.transform.data_cleaner import clean_smi_data

logger = logging.getLogger(__name__)

# Arguments par défaut
default_args = {
    "owner": "smi-team",
    "depends_on_past": False,
    "email": ["admin@smi-platform.bf"],
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=2),
}

# Configuration
SOURCE_FILE = "/opt/airflow/data/source/Donnees_POC2024_2025_10122025.xls"
BRONZE_PATH = "/opt/airflow/data/bronze/smi_raw.parquet"
SILVER_PATH = "/opt/airflow/data/silver/smi_cleaned.parquet"


def extract_data_task(**context):
    """Task 1: Extraction des données depuis Excel."""
    logger.info("🚀 Démarrage de l'extraction...")

    extractor = ExcelExtractor(SOURCE_FILE)
    df = extractor.extract()

    # Sauvegarder en parquet (Bronze layer)
    df.to_parquet(BRONZE_PATH, index=False, engine="pyarrow")

    # Push metadata vers XCom
    metadata = {
        "num_rows": len(df),
        "num_columns": len(df.columns),
        "extraction_timestamp": datetime.now().isoformat(),
    }
    context["ti"].xcom_push(key="extraction_metadata", value=metadata)

    logger.info(f"✅ Extraction terminée: {len(df)} lignes extraites")
    return metadata


def transform_data_task(**context):
    """Task 2: Nettoyage et transformation (Bronze → Silver)."""
    logger.info("🧹 Démarrage de la transformation...")

    # Charger depuis Bronze
    df = pd.read_parquet(BRONZE_PATH)

    # Nettoyer les données
    cleaned_df, validation_report = clean_smi_data(df)

    # Sauvegarder en Silver
    cleaned_df.to_parquet(SILVER_PATH, index=False, engine="pyarrow")

    # Push validation report vers XCom
    context["ti"].xcom_push(key="validation_report", value=validation_report)

    logger.info(f"✅ Transformation terminée: {len(cleaned_df)} lignes nettoyées")
    return validation_report


def load_to_postgres_bronze_task(**context):
    """Task 3: Charger les données brutes dans PostgreSQL (Bronze)."""
    logger.info("📥 Chargement dans PostgreSQL Bronze...")

    df = pd.read_parquet(BRONZE_PATH)

    # Connexion PostgreSQL
    pg_hook = PostgresHook(postgres_conn_id="postgres_dwh")
    engine = pg_hook.get_sqlalchemy_engine()

    # Charger dans bronze.smi_raw
    df.to_sql(
        "smi_raw",
        engine,
        schema="bronze",
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )

    logger.info(f"✅ {len(df)} lignes chargées dans bronze.smi_raw")


def load_to_postgres_silver_task(**context):
    """Task 4: Charger les données nettoyées dans PostgreSQL (Silver)."""
    logger.info("📥 Chargement dans PostgreSQL Silver...")

    df = pd.read_parquet(SILVER_PATH)

    # Connexion PostgreSQL
    pg_hook = PostgresHook(postgres_conn_id="postgres_dwh")
    engine = pg_hook.get_sqlalchemy_engine()

    # Charger dans silver.smi_cleaned
    df.to_sql(
        "smi_cleaned",
        engine,
        schema="silver",
        if_exists="append",
        index=False,
        method="multi",
        chunksize=1000,
    )

    logger.info(f"✅ {len(df)} lignes chargées dans silver.smi_cleaned")


def build_gold_dimensions_task(**context):
    """Task 5: Construire les dimensions Gold."""
    logger.info("🏗️  Construction des dimensions Gold...")

    pg_hook = PostgresHook(postgres_conn_id="postgres_dwh")

    # Construction de dim_geographie
    sql_geo = """
    INSERT INTO gold.dim_geographie (
        pays, region, province, district_sanitaire, commune, formation_sanitaire,
        code_formation, effective_date, is_current
    )
    SELECT DISTINCT
        pays, region, province, district_sanitaire, commune, formation_sanitaire,
        geo_id as code_formation,
        CURRENT_DATE as effective_date,
        TRUE as is_current
    FROM silver.smi_cleaned
    WHERE NOT EXISTS (
        SELECT 1 FROM gold.dim_geographie g
        WHERE g.formation_sanitaire = silver.smi_cleaned.formation_sanitaire
        AND g.is_current = TRUE
    );
    """

    # Construction de dim_temps
    sql_temps = """
    INSERT INTO gold.dim_temps (
        date_key, date, annee, trimestre, mois, semaine, jour, semestre,
        nom_mois, est_debut_mois, est_fin_mois
    )
    SELECT DISTINCT
        TO_CHAR(periode_date, 'YYYYMMDD')::INTEGER as date_key,
        periode_date as date,
        annee, trimestre, mois,
        EXTRACT(WEEK FROM periode_date)::INTEGER as semaine,
        EXTRACT(DAY FROM periode_date)::INTEGER as jour,
        semestre,
        TO_CHAR(periode_date, 'Month') as nom_mois,
        (EXTRACT(DAY FROM periode_date) = 1) as est_debut_mois,
        (periode_date = (DATE_TRUNC('month', periode_date) + INTERVAL '1 month - 1 day')::DATE) as est_fin_mois
    FROM silver.smi_cleaned
    WHERE periode_date IS NOT NULL
    ON CONFLICT (date_key) DO NOTHING;
    """

    pg_hook.run(sql_geo)
    pg_hook.run(sql_temps)

    logger.info("✅ Dimensions Gold construites")


def build_gold_facts_task(**context):
    """Task 6: Construire les tables de faits Gold."""
    logger.info("📊 Construction des tables de faits Gold...")

    pg_hook = PostgresHook(postgres_conn_id="postgres_dwh")

    # Construction fait_deces_neonatals
    sql_deces_neo = """
    INSERT INTO gold.fait_deces_neonatals (
        geo_key, date_key, deces_0_6_jours, deces_7_28_jours,
        deces_communaute, taux_mortalite_neonatale, batch_id
    )
    SELECT
        g.geo_key,
        t.date_key,
        s.nouveau_nes_decedes_0_6_jours,
        s.nouveau_nes_decedes_7_28_jours,
        s.deces_neonatals_communaute,
        s.taux_mortalite_neonatale,
        '{{ run_id }}' as batch_id
    FROM silver.smi_cleaned s
    JOIN gold.dim_geographie g ON s.formation_sanitaire = g.formation_sanitaire AND g.is_current = TRUE
    JOIN gold.dim_temps t ON s.periode_date = t.date
    WHERE s.periode_date IS NOT NULL
    ON CONFLICT (geo_key, date_key) DO UPDATE SET
        deces_0_6_jours = EXCLUDED.deces_0_6_jours,
        deces_7_28_jours = EXCLUDED.deces_7_28_jours,
        deces_communaute = EXCLUDED.deces_communaute,
        taux_mortalite_neonatale = EXCLUDED.taux_mortalite_neonatale;
    """

    pg_hook.run(sql_deces_neo)

    logger.info("✅ Tables de faits Gold construites")


def refresh_materialized_views_task(**context):
    """Task 7: Rafraîchir les vues matérialisées."""
    logger.info("🔄 Rafraîchissement des vues matérialisées...")

    pg_hook = PostgresHook(postgres_conn_id="postgres_dwh")

    sql = "SELECT gold.refresh_materialized_views();"
    pg_hook.run(sql)

    logger.info("✅ Vues matérialisées rafraîchies")


def send_notification_task(**context):
    """Task 8: Envoyer notification de succès."""
    extraction_metadata = context["ti"].xcom_pull(
        key="extraction_metadata", task_ids="extract_data"
    )
    validation_report = context["ti"].xcom_pull(key="validation_report", task_ids="transform_data")

    logger.info(
        f"""
    ✅ PIPELINE SMI TERMINÉ AVEC SUCCÈS

    📊 Extraction:
    - Lignes extraites: {extraction_metadata['num_rows']}
    - Colonnes: {extraction_metadata['num_columns']}

    🧹 Transformation:
    - Lignes initiales: {validation_report['original_rows']}
    - Lignes finales: {validation_report['final_rows']}
    - Lignes supprimées: {validation_report['rows_removed']}
    - Doublons: {validation_report['duplicates']}

    ⏱️  Exécution: {datetime.now().isoformat()}
    """
    )


# Définition du DAG
with DAG(
    "smi_full_pipeline",
    default_args=default_args,
    description="Pipeline ETL complet pour les données SMI",
    schedule_interval="0 2 * * *",  # 2h AM tous les jours
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["smi", "etl", "production"],
    max_active_runs=1,
) as dag:

    # Task 1: Extraction
    extract = PythonOperator(
        task_id="extract_data",
        python_callable=extract_data_task,
        provide_context=True,
    )

    # Task 2: Transformation
    transform = PythonOperator(
        task_id="transform_data",
        python_callable=transform_data_task,
        provide_context=True,
    )

    # Task 3: Chargement Bronze
    load_bronze = PythonOperator(
        task_id="load_to_postgres_bronze",
        python_callable=load_to_postgres_bronze_task,
        provide_context=True,
    )

    # Task 4: Chargement Silver
    load_silver = PythonOperator(
        task_id="load_to_postgres_silver",
        python_callable=load_to_postgres_silver_task,
        provide_context=True,
    )

    # Task 5: Construction dimensions Gold
    build_dimensions = PythonOperator(
        task_id="build_gold_dimensions",
        python_callable=build_gold_dimensions_task,
        provide_context=True,
    )

    # Task 6: Construction faits Gold
    build_facts = PythonOperator(
        task_id="build_gold_facts",
        python_callable=build_gold_facts_task,
        provide_context=True,
    )

    # Task 7: Rafraîchir vues matérialisées
    refresh_views = PythonOperator(
        task_id="refresh_materialized_views",
        python_callable=refresh_materialized_views_task,
        provide_context=True,
    )

    # Task 8: Notification
    notify = PythonOperator(
        task_id="send_notification",
        python_callable=send_notification_task,
        provide_context=True,
        trigger_rule="all_success",
    )

    # Définition du flux
    extract >> transform >> [load_bronze, load_silver]
    load_silver >> build_dimensions >> build_facts >> refresh_views >> notify
