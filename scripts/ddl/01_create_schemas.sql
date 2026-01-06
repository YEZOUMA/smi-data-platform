-- =============================================================================
-- SMI DATA PLATFORM - SCHEMA INITIALIZATION
-- =============================================================================
-- Description: Création des schémas, tables dimensionnelles et de faits
-- Version: 1.0.0
-- Date: Janvier 2026
-- Author: Yézouma - Sand Technologies
-- =============================================================================

-- =============================================================================
-- 1. CRÉATION DES SCHÉMAS
-- =============================================================================

-- Schéma Bronze: Données brutes non transformées
CREATE SCHEMA IF NOT EXISTS bronze;
COMMENT ON SCHEMA bronze IS 'Données brutes directement importées depuis la source';

-- Schéma Silver: Données nettoyées et normalisées
CREATE SCHEMA IF NOT EXISTS silver;
COMMENT ON SCHEMA silver IS 'Données nettoyées, validées et enrichies';

-- Schéma Gold: Données agrégées optimisées pour l'analyse
CREATE SCHEMA IF NOT EXISTS gold;
COMMENT ON SCHEMA gold IS 'Modèle dimensionnel (star schema) pour analytics';

-- Schéma de métadonnées et audit
CREATE SCHEMA IF NOT EXISTS metadata;
COMMENT ON SCHEMA metadata IS 'Métadonnées, logs et informations d audit';

-- =============================================================================
-- 2. EXTENSIONS POSTGRESQL
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- =============================================================================
-- 3. BRONZE LAYER - TABLES RAW
-- =============================================================================

-- Table pour stocker les données brutes importées
CREATE TABLE IF NOT EXISTS bronze.smi_raw (
    id SERIAL PRIMARY KEY,
    pays VARCHAR(100),
    region VARCHAR(100),
    province VARCHAR(100),
    district_sanitaire VARCHAR(150),
    commune_arrondissement VARCHAR(150),
    formation_sanitaire VARCHAR(200),
    periode VARCHAR(50),
    
    -- Décès maternels par cause
    deces_maternels_total NUMERIC,
    deces_autres_complications NUMERIC,
    deces_complications_avortements NUMERIC,
    deces_disproportion_foeto_pelvienne NUMERIC,
    deces_eclampsie NUMERIC,
    deces_geu NUMERIC,
    deces_hemorragie NUMERIC,
    deces_infections NUMERIC,
    deces_presentation_vicieuse NUMERIC,
    deces_rupture_uterine NUMERIC,
    deces_retention_placentaire NUMERIC,
    
    -- Décès communautaires et audits
    deces_maternels_communaute NUMERIC,
    deces_maternels_audites NUMERIC,
    deces_neonatals_communaute NUMERIC,
    
    -- Décès néonatals par tranche d'âge
    nouveau_nes_decedes_0_6_jours NUMERIC,
    nouveau_nes_decedes_7_28_jours NUMERIC,
    
    -- Indicateurs SMI
    proportion_deces_maternels_audites NUMERIC,
    proportion_deces_maternels_pour_100k NUMERIC,
    proportion_deces_neonatals_audites NUMERIC,
    proportion_deces_neonatal_naissances_vivantes NUMERIC,
    proportion_femmes_cpn1_trimestre1 NUMERIC,
    
    -- Métadonnées d'ingestion
    source_file VARCHAR(255),
    ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data_quality_score NUMERIC(3,2),
    
    CONSTRAINT chk_quality_score CHECK (data_quality_score >= 0 AND data_quality_score <= 1)
);

CREATE INDEX idx_bronze_periode ON bronze.smi_raw(periode);
CREATE INDEX idx_bronze_region ON bronze.smi_raw(region);
CREATE INDEX idx_bronze_formation ON bronze.smi_raw(formation_sanitaire);
CREATE INDEX idx_bronze_ingestion ON bronze.smi_raw(ingestion_timestamp);

COMMENT ON TABLE bronze.smi_raw IS 'Données SMI brutes importées depuis Excel';

-- =============================================================================
-- 4. SILVER LAYER - TABLES CLEANED
-- =============================================================================

-- Table des données nettoyées
CREATE TABLE IF NOT EXISTS silver.smi_cleaned (
    id SERIAL PRIMARY KEY,
    bronze_id INTEGER REFERENCES bronze.smi_raw(id),
    
    -- Géographie normalisée
    pays VARCHAR(100) NOT NULL,
    region VARCHAR(100) NOT NULL,
    province VARCHAR(100) NOT NULL,
    district_sanitaire VARCHAR(150) NOT NULL,
    commune VARCHAR(150) NOT NULL,
    formation_sanitaire VARCHAR(200) NOT NULL,
    
    -- Période normalisée
    periode_date DATE NOT NULL,
    annee INTEGER NOT NULL,
    trimestre INTEGER NOT NULL,
    mois INTEGER NOT NULL,
    semestre INTEGER NOT NULL,
    
    -- Décès maternels par cause (valeurs nettoyées)
    deces_maternels_total INTEGER DEFAULT 0,
    deces_autres_complications INTEGER DEFAULT 0,
    deces_complications_avortements INTEGER DEFAULT 0,
    deces_disproportion_foeto_pelvienne INTEGER DEFAULT 0,
    deces_eclampsie INTEGER DEFAULT 0,
    deces_geu INTEGER DEFAULT 0,
    deces_hemorragie INTEGER DEFAULT 0,
    deces_infections INTEGER DEFAULT 0,
    deces_presentation_vicieuse INTEGER DEFAULT 0,
    deces_rupture_uterine INTEGER DEFAULT 0,
    deces_retention_placentaire INTEGER DEFAULT 0,
    
    -- Décès communautaires et audits
    deces_maternels_communaute INTEGER DEFAULT 0,
    deces_maternels_audites INTEGER DEFAULT 0,
    deces_neonatals_communaute INTEGER DEFAULT 0,
    
    -- Décès néonatals
    nouveau_nes_decedes_0_6_jours INTEGER DEFAULT 0,
    nouveau_nes_decedes_7_28_jours INTEGER DEFAULT 0,
    total_deces_neonatals INTEGER GENERATED ALWAYS AS 
        (nouveau_nes_decedes_0_6_jours + nouveau_nes_decedes_7_28_jours) STORED,
    
    -- Indicateurs calculés
    taux_mortalite_maternelle NUMERIC(10,2),
    taux_audit_deces_maternels NUMERIC(5,2),
    taux_mortalite_neonatale NUMERIC(10,2),
    couverture_cpn1_trimestre1 NUMERIC(5,2),
    
    -- Flags de qualité
    is_complete BOOLEAN DEFAULT TRUE,
    is_valid BOOLEAN DEFAULT TRUE,
    has_anomalies BOOLEAN DEFAULT FALSE,
    
    -- Métadonnées
    processed_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processing_version VARCHAR(20),
    
    CONSTRAINT chk_trimestre CHECK (trimestre BETWEEN 1 AND 4),
    CONSTRAINT chk_mois CHECK (mois BETWEEN 1 AND 12),
    CONSTRAINT chk_semestre CHECK (semestre BETWEEN 1 AND 2),
    CONSTRAINT chk_deces_positifs CHECK (
        deces_maternels_total >= 0 AND
        total_deces_neonatals >= 0
    )
);

CREATE INDEX idx_silver_periode ON silver.smi_cleaned(periode_date);
CREATE INDEX idx_silver_geo ON silver.smi_cleaned(region, province, district_sanitaire);
CREATE INDEX idx_silver_annee_mois ON silver.smi_cleaned(annee, mois);
CREATE INDEX idx_silver_formation ON silver.smi_cleaned(formation_sanitaire);

COMMENT ON TABLE silver.smi_cleaned IS 'Données SMI nettoyées et normalisées';

-- =============================================================================
-- 5. GOLD LAYER - DIMENSIONS
-- =============================================================================

-- Dimension Géographie
CREATE TABLE IF NOT EXISTS gold.dim_geographie (
    geo_key SERIAL PRIMARY KEY,
    pays VARCHAR(100) NOT NULL,
    region VARCHAR(100) NOT NULL,
    province VARCHAR(100) NOT NULL,
    district_sanitaire VARCHAR(150) NOT NULL,
    commune VARCHAR(150) NOT NULL,
    formation_sanitaire VARCHAR(200) NOT NULL,
    
    -- Codes normalisés
    code_region VARCHAR(10),
    code_province VARCHAR(10),
    code_district VARCHAR(10),
    code_commune VARCHAR(10),
    code_formation VARCHAR(20),
    
    -- Coordonnées géographiques (pour cartographie)
    latitude NUMERIC(10, 8),
    longitude NUMERIC(11, 8),
    
    -- Métadonnées SCD Type 2
    effective_date DATE NOT NULL DEFAULT CURRENT_DATE,
    expiration_date DATE DEFAULT '9999-12-31',
    is_current BOOLEAN DEFAULT TRUE,
    version INTEGER DEFAULT 1,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT uq_geo_current UNIQUE (formation_sanitaire, is_current)
);

CREATE INDEX idx_dim_geo_region ON gold.dim_geographie(region);
CREATE INDEX idx_dim_geo_province ON gold.dim_geographie(province);
CREATE INDEX idx_dim_geo_formation ON gold.dim_geographie(formation_sanitaire);
CREATE INDEX idx_dim_geo_current ON gold.dim_geographie(is_current) WHERE is_current = TRUE;

COMMENT ON TABLE gold.dim_geographie IS 'Dimension géographique hiérarchique (SCD Type 2)';

-- Dimension Temps
CREATE TABLE IF NOT EXISTS gold.dim_temps (
    date_key INTEGER PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    annee INTEGER NOT NULL,
    trimestre INTEGER NOT NULL,
    mois INTEGER NOT NULL,
    semaine INTEGER NOT NULL,
    jour INTEGER NOT NULL,
    semestre INTEGER NOT NULL,
    
    -- Libellés
    nom_mois VARCHAR(20),
    nom_jour_semaine VARCHAR(20),
    
    -- Indicateurs
    est_debut_mois BOOLEAN,
    est_fin_mois BOOLEAN,
    est_jour_ferie BOOLEAN DEFAULT FALSE,
    
    -- Saison (pour Burkina Faso)
    saison VARCHAR(20), -- 'Saison sèche' ou 'Saison des pluies'
    
    CONSTRAINT chk_temps_trimestre CHECK (trimestre BETWEEN 1 AND 4),
    CONSTRAINT chk_temps_mois CHECK (mois BETWEEN 1 AND 12),
    CONSTRAINT chk_temps_semestre CHECK (semestre BETWEEN 1 AND 2)
);

CREATE INDEX idx_dim_temps_annee ON gold.dim_temps(annee);
CREATE INDEX idx_dim_temps_mois ON gold.dim_temps(annee, mois);
CREATE INDEX idx_dim_temps_trimestre ON gold.dim_temps(annee, trimestre);

COMMENT ON TABLE gold.dim_temps IS 'Dimension temporelle avec décompositions multiples';

-- Dimension Cause de Décès
CREATE TABLE IF NOT EXISTS gold.dim_cause_deces (
    cause_key SERIAL PRIMARY KEY,
    code_cause VARCHAR(20) NOT NULL UNIQUE,
    nom_cause VARCHAR(150) NOT NULL,
    categorie VARCHAR(50),
    description TEXT,
    niveau_gravite INTEGER,
    ordre_affichage INTEGER,
    est_actif BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dim_cause_categorie ON gold.dim_cause_deces(categorie);
CREATE INDEX idx_dim_cause_actif ON gold.dim_cause_deces(est_actif);

COMMENT ON TABLE gold.dim_cause_deces IS 'Typologie des causes de décès maternels';

-- =============================================================================
-- 6. GOLD LAYER - TABLES DE FAITS
-- =============================================================================

-- Fait: Décès Maternels
CREATE TABLE IF NOT EXISTS gold.fait_deces_maternels (
    fait_id BIGSERIAL PRIMARY KEY,
    geo_key INTEGER NOT NULL REFERENCES gold.dim_geographie(geo_key),
    date_key INTEGER NOT NULL REFERENCES gold.dim_temps(date_key),
    cause_key INTEGER NOT NULL REFERENCES gold.dim_cause_deces(cause_key),
    
    -- Mesures additives
    nombre_deces INTEGER NOT NULL DEFAULT 0,
    deces_communaute INTEGER NOT NULL DEFAULT 0,
    deces_audites INTEGER NOT NULL DEFAULT 0,
    
    -- Mesures semi-additives / dérivées
    taux_mortalite NUMERIC(10,2),
    proportion_audites NUMERIC(5,2),
    
    -- Métadonnées
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    batch_id VARCHAR(50),
    
    CONSTRAINT uq_fait_deces_mat UNIQUE (geo_key, date_key, cause_key),
    CONSTRAINT chk_deces_positifs CHECK (nombre_deces >= 0)
);

CREATE INDEX idx_fait_deces_mat_geo ON gold.fait_deces_maternels(geo_key);
CREATE INDEX idx_fait_deces_mat_date ON gold.fait_deces_maternels(date_key);
CREATE INDEX idx_fait_deces_mat_cause ON gold.fait_deces_maternels(cause_key);
CREATE INDEX idx_fait_deces_mat_batch ON gold.fait_deces_maternels(batch_id);

COMMENT ON TABLE gold.fait_deces_maternels IS 'Faits des décès maternels par cause';

-- Fait: Décès Néonatals
CREATE TABLE IF NOT EXISTS gold.fait_deces_neonatals (
    fait_id BIGSERIAL PRIMARY KEY,
    geo_key INTEGER NOT NULL REFERENCES gold.dim_geographie(geo_key),
    date_key INTEGER NOT NULL REFERENCES gold.dim_temps(date_key),
    
    -- Mesures par tranche d'âge
    deces_0_6_jours INTEGER NOT NULL DEFAULT 0,
    deces_7_28_jours INTEGER NOT NULL DEFAULT 0,
    total_deces INTEGER GENERATED ALWAYS AS (deces_0_6_jours + deces_7_28_jours) STORED,
    deces_communaute INTEGER NOT NULL DEFAULT 0,
    
    -- Mesures dérivées
    taux_mortalite_neonatale NUMERIC(10,2),
    taux_mortalite_precoce NUMERIC(10,2), -- 0-6 jours
    taux_mortalite_tardive NUMERIC(10,2), -- 7-28 jours
    
    -- Métadonnées
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    batch_id VARCHAR(50),
    
    CONSTRAINT uq_fait_deces_neo UNIQUE (geo_key, date_key),
    CONSTRAINT chk_deces_neo_positifs CHECK (total_deces >= 0)
);

CREATE INDEX idx_fait_deces_neo_geo ON gold.fait_deces_neonatals(geo_key);
CREATE INDEX idx_fait_deces_neo_date ON gold.fait_deces_neonatals(date_key);
CREATE INDEX idx_fait_deces_neo_batch ON gold.fait_deces_neonatals(batch_id);

COMMENT ON TABLE gold.fait_deces_neonatals IS 'Faits des décès néonatals par tranche d âge';

-- Fait: Indicateurs SMI
CREATE TABLE IF NOT EXISTS gold.fait_indicateurs_smi (
    fait_id BIGSERIAL PRIMARY KEY,
    geo_key INTEGER NOT NULL REFERENCES gold.dim_geographie(geo_key),
    date_key INTEGER NOT NULL REFERENCES gold.dim_temps(date_key),
    
    -- Indicateurs de qualité
    taux_audit_deces_maternels NUMERIC(5,2),
    couverture_cpn1_trimestre1 NUMERIC(5,2),
    proportion_deces_pour_100k NUMERIC(10,2),
    
    -- Indicateurs de complétude
    completude_donnees NUMERIC(5,2),
    taux_remplissage NUMERIC(5,2),
    
    -- Nombre de formations rapportant
    nombre_formations_reportant INTEGER,
    
    -- Métadonnées
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    batch_id VARCHAR(50),
    
    CONSTRAINT uq_fait_indicateurs UNIQUE (geo_key, date_key)
);

CREATE INDEX idx_fait_indicateurs_geo ON gold.fait_indicateurs_smi(geo_key);
CREATE INDEX idx_fait_indicateurs_date ON gold.fait_indicateurs_smi(date_key);
CREATE INDEX idx_fait_indicateurs_batch ON gold.fait_indicateurs_smi(batch_id);

COMMENT ON TABLE gold.fait_indicateurs_smi IS 'Indicateurs agrégés de qualité SMI';

-- =============================================================================
-- 7. METADATA LAYER - TABLES D'AUDIT ET DE SUIVI
-- =============================================================================

-- Table d'audit des pipelines
CREATE TABLE IF NOT EXISTS metadata.pipeline_runs (
    run_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_name VARCHAR(100) NOT NULL,
    run_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20) NOT NULL, -- 'running', 'success', 'failed'
    records_processed INTEGER,
    records_inserted INTEGER,
    records_updated INTEGER,
    records_failed INTEGER,
    error_message TEXT,
    execution_time_seconds INTEGER,
    
    CONSTRAINT chk_pipeline_status CHECK (status IN ('running', 'success', 'failed', 'partial'))
);

CREATE INDEX idx_pipeline_runs_date ON metadata.pipeline_runs(run_date);
CREATE INDEX idx_pipeline_runs_status ON metadata.pipeline_runs(status);
CREATE INDEX idx_pipeline_runs_name ON metadata.pipeline_runs(pipeline_name);

COMMENT ON TABLE metadata.pipeline_runs IS 'Historique d exécution des pipelines ETL';

-- Table de qualité des données
CREATE TABLE IF NOT EXISTS metadata.data_quality_checks (
    check_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID REFERENCES metadata.pipeline_runs(run_id),
    check_name VARCHAR(100) NOT NULL,
    check_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    table_name VARCHAR(100),
    check_passed BOOLEAN,
    expectation_suite VARCHAR(100),
    validation_result JSONB,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_quality_checks_run ON metadata.data_quality_checks(run_id);
CREATE INDEX idx_quality_checks_table ON metadata.data_quality_checks(table_name);
CREATE INDEX idx_quality_checks_passed ON metadata.data_quality_checks(check_passed);

COMMENT ON TABLE metadata.data_quality_checks IS 'Résultats des contrôles qualité des données';

-- =============================================================================
-- 8. VUES MATÉRIALISÉES POUR PERFORMANCE
-- =============================================================================

-- Vue: Agrégations mensuelles par région
CREATE MATERIALIZED VIEW IF NOT EXISTS gold.mv_deces_mensuels_region AS
SELECT 
    t.annee,
    t.mois,
    t.nom_mois,
    g.region,
    SUM(dm.nombre_deces) as total_deces_maternels,
    SUM(dn.total_deces) as total_deces_neonatals,
    AVG(dm.taux_mortalite) as taux_mortalite_moyen,
    COUNT(DISTINCT g.formation_sanitaire) as nombre_formations
FROM gold.fait_deces_maternels dm
JOIN gold.dim_geographie g ON dm.geo_key = g.geo_key
JOIN gold.dim_temps t ON dm.date_key = t.date_key
LEFT JOIN gold.fait_deces_neonatals dn ON dm.geo_key = dn.geo_key AND dm.date_key = dn.date_key
WHERE g.is_current = TRUE
GROUP BY t.annee, t.mois, t.nom_mois, g.region;

CREATE UNIQUE INDEX idx_mv_deces_region ON gold.mv_deces_mensuels_region(annee, mois, region);

COMMENT ON MATERIALIZED VIEW gold.mv_deces_mensuels_region IS 'Agrégations mensuelles des décès par région';

-- =============================================================================
-- 9. FONCTIONS UTILITAIRES
-- =============================================================================

-- Fonction pour rafraîchir toutes les vues matérialisées
CREATE OR REPLACE FUNCTION gold.refresh_materialized_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY gold.mv_deces_mensuels_region;
    -- Ajouter d'autres vues matérialisées ici
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION gold.refresh_materialized_views() IS 'Rafraîchit toutes les vues matérialisées';

-- =============================================================================
-- 10. GRANTS ET PERMISSIONS
-- =============================================================================

-- Schéma Bronze: Lecture/écriture pour le pipeline
GRANT USAGE ON SCHEMA bronze TO smi_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA bronze TO smi_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA bronze TO smi_user;

-- Schéma Silver: Lecture/écriture pour le pipeline
GRANT USAGE ON SCHEMA silver TO smi_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA silver TO smi_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA silver TO smi_user;

-- Schéma Gold: Lecture/écriture pour le pipeline, lecture pour analytics
GRANT USAGE ON SCHEMA gold TO smi_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA gold TO smi_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA gold TO smi_user;

-- Schéma Metadata
GRANT USAGE ON SCHEMA metadata TO smi_user;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA metadata TO smi_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA metadata TO smi_user;

-- =============================================================================
-- FIN DE L'INITIALISATION
-- =============================================================================

-- Log de confirmation
DO $$
BEGIN
    RAISE NOTICE '✅ Schémas et tables SMI créés avec succès!';
    RAISE NOTICE '📊 Schémas: bronze, silver, gold, metadata';
    RAISE NOTICE '📋 Tables de dimensions: 3 (géographie, temps, cause_deces)';
    RAISE NOTICE '📈 Tables de faits: 3 (deces_maternels, deces_neonatals, indicateurs_smi)';
END $$;
