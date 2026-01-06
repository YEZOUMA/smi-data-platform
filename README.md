# 🏥 Plateforme de Data Engineering SMI Burkina Faso

## Vue d'ensemble

Plateforme complète de data engineering pour l'analyse des données de Santé Maternelle et Infantile (SMI) au Burkina Faso. Solution de niveau production avec architecture moderne, orchestration robuste et visualisations interactives.

### 📊 Statistiques du Dataset
- **57,829** enregistrements de formations sanitaires
- **28** variables (géographie, causes de décès, indicateurs)
- **Période**: 2024-2025
- **Couverture**: Nationale (toutes les régions du Burkina Faso)

### 🎯 Objectifs

- Pipeline ETL automatisé et orchestré
- Architecture en couches (Bronze → Silver → Gold)
- Modélisation dimensionnelle (schéma en étoile)
- Visualisations interactives avec Apache Superset
- Monitoring et observabilité complète
- Tests automatisés et CI/CD
- Documentation technique exhaustive

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SOURCE DE DONNÉES                           │
│              Fichier Excel (.xls) - 57K lignes                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    BRONZE LAYER (Raw)                           │
│              Données brutes (Parquet + PostgreSQL)              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                  ┌───────────────────────┐
                  │   Apache Airflow      │
                  │   Orchestration ETL   │
                  └───────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   SILVER LAYER (Cleaned)                        │
│         Données nettoyées, normalisées, enrichies              │
│              dbt Core - Transformations SQL                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    GOLD LAYER (Analytics)                       │
│              Modèle dimensionnel (Star Schema)                  │
│    Dim: Géographie, Temps, Causes | Fait: Décès, Indicateurs   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
            ┌─────────────────────────────────────┐
            │      Apache Superset                │
            │   Dashboards & Visualisations       │
            └─────────────────────────────────────┘
                              ↓
            ┌─────────────────────────────────────┐
            │   Prometheus + Grafana              │
            │   Monitoring & Alerting             │
            └─────────────────────────────────────┘
```

## 🚀 Stack Technologique

### Core Data Engineering
- **Python 3.11+** - Langage principal
- **PostgreSQL 15** - Data Warehouse
- **Apache Airflow 2.8+** - Orchestration
- **dbt Core 1.7+** - Transformations SQL
- **Great Expectations** - Data Quality

### Visualisation & Analytics
- **Apache Superset 3.1+** - Dashboards BI
- **Plotly** - Graphiques interactifs

### Monitoring & Observabilité
- **Prometheus** - Métriques
- **Grafana** - Visualisation métriques
- **Sentry** - Error tracking
- **ELK Stack** - Logs centralisés

### DevOps & Infrastructure
- **Docker & Docker Compose** - Containerisation
- **GitHub Actions** - CI/CD
- **MinIO** - Object Storage (S3-compatible)
- **Redis** - Cache & Message Broker

## 📁 Structure du Projet

```
smi-data-platform/
├── airflow/                    # Orchestration Airflow
│   ├── dags/                   # DAGs ETL
│   ├── plugins/                # Custom operators
│   └── config/                 # Configuration
├── dbt/                        # Transformations dbt
│   ├── models/                 # Modèles SQL
│   │   ├── bronze/             # Raw data
│   │   ├── silver/             # Cleaned data
│   │   └── gold/               # Analytics models
│   ├── tests/                  # Tests data quality
│   └── macros/                 # Macros réutilisables
├── src/                        # Code Python
│   ├── extract/                # Extraction des données
│   ├── transform/              # Transformations Python
│   ├── load/                   # Chargement dans DB
│   ├── quality/                # Data quality checks
│   └── utils/                  # Utilitaires
├── scripts/                    # Scripts SQL et shell
│   ├── ddl/                    # Schémas de base de données
│   ├── migrations/             # Migrations DB
│   └── seeds/                  # Données de référence
├── tests/                      # Tests unitaires et intégration
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── monitoring/                 # Configuration monitoring
│   ├── prometheus/
│   ├── grafana/
│   └── alertmanager/
├── superset/                   # Configuration Superset
│   ├── dashboards/             # Exports dashboards
│   └── datasets/               # Configuration datasets
├── docker/                     # Dockerfiles personnalisés
├── docs/                       # Documentation
│   ├── architecture/
│   ├── data_dictionary/
│   └── runbooks/
├── notebooks/                  # Notebooks d'analyse
├── .github/                    # GitHub Actions workflows
├── docker-compose.yml          # Infrastructure complète
├── Makefile                    # Commandes d'automatisation
├── pyproject.toml              # Dépendances Python
└── README.md                   # Ce fichier
```

## 🔧 Installation et Configuration

### Prérequis

- Docker Desktop 24.0+ avec Docker Compose V2
- Python 3.11+
- Git
- 8 GB RAM minimum (16 GB recommandé)
- 20 GB d'espace disque

### Installation Rapide

```bash
# 1. Cloner le repository
git clone <repo-url>
cd smi-data-platform

# 2. Créer l'environnement Python
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# 3. Installer les dépendances
pip install -e ".[dev]"

# 4. Copier les variables d'environnement
cp .env.example .env
# Éditer .env avec vos configurations

# 5. Démarrer l'infrastructure
make setup    # Initialise les bases de données
make up       # Lance tous les services

# 6. Initialiser Airflow
make airflow-init

# 7. Importer les données sources
make import-data

# 8. Exécuter le pipeline complet
make run-pipeline
```

### URLs des Services

- **Airflow**: http://localhost:8080 (admin/admin)
- **Superset**: http://localhost:8088 (admin/admin)
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

## 📊 Modèle de Données

### Tables de Dimensions

#### `dim_geographie`
Hiérarchie administrative complète du Burkina Faso
```sql
- geo_key (PK)
- pays, region, province, district, commune, formation_sanitaire
- code_region, code_province, code_district
- latitude, longitude (pour cartographie)
```

#### `dim_temps`
Dimension temporelle avec décompositions multiples
```sql
- date_key (PK)
- date, annee, trimestre, mois, semaine
- nom_mois, jour_semaine
- est_jour_ferie, saison
```

#### `dim_cause_deces`
Typologie des causes de décès maternels
```sql
- cause_key (PK)
- code_cause, nom_cause, categorie
- description, niveau_gravite
```

### Tables de Faits

#### `fait_deces_maternels`
Décès maternels par formation sanitaire et période
```sql
- fait_id (PK)
- geo_key (FK), date_key (FK), cause_key (FK)
- nombre_deces, deces_audites, deces_communaute
- taux_mortalite, proportion_audites
```

#### `fait_deces_neonatals`
Décès néonatals avec tranches d'âge
```sql
- fait_id (PK)
- geo_key (FK), date_key (FK)
- deces_0_6_jours, deces_7_28_jours, total_deces
- deces_communaute, taux_mortalite_neonatale
```

#### `fait_indicateurs_smi`
Indicateurs agrégés de qualité SMI
```sql
- fait_id (PK)
- geo_key (FK), date_key (FK)
- proportion_cpn1_trimestre1, couverture_cpn
- taux_audit, completude_donnees
```

## 🔄 Pipelines ETL

### Pipeline Principal (`smi_full_pipeline`)

**Fréquence**: Quotidien à 2h00 AM  
**Durée estimée**: 15-20 minutes  
**SLA**: 4 heures

#### Étapes du Pipeline

1. **Extract** (5 min)
   - Lecture fichier Excel source
   - Validation schéma et format
   - Sauvegarde en Bronze (Parquet)

2. **Transform - Bronze → Silver** (8 min)
   - Nettoyage des colonnes
   - Normalisation des données géographiques
   - Parsing et enrichissement dates
   - Traitement valeurs manquantes
   - Validation règles métier

3. **Transform - Silver → Gold** (5 min)
   - Construction dimensions (SCD Type 2)
   - Agrégations et calculs d'indicateurs
   - Population tables de faits
   - Calcul de métriques dérivées

4. **Quality Checks** (2 min)
   - Great Expectations validations
   - Contrôles de cohérence
   - Détection d'anomalies
   - Génération rapport qualité

5. **Finalization**
   - Refresh des vues matérialisées
   - Mise à jour métadonnées Superset
   - Envoi notifications
   - Archivage logs

### Autres DAGs

- `smi_incremental_load`: Chargement incrémental (horaire)
- `smi_data_quality`: Contrôles qualité quotidiens
- `smi_backup`: Sauvegarde automatique (hebdomadaire)
- `smi_aggregations`: Pré-calculs de cubes OLAP

## 📈 Dashboards Superset

### Dashboard 1: Vue Exécutive SMI
- KPIs principaux (décès, taux, audits)
- Tendances temporelles
- Top 10 régions à risque
- Alertes et anomalies

### Dashboard 2: Analyse Géographique
- Carte choroplèthe du Burkina Faso
- Heatmap par province
- Comparaisons régionales
- Drill-down jusqu'à la formation sanitaire

### Dashboard 3: Causes de Mortalité
- Distribution par type de complication
- Évolution des principales causes
- Analyse corrélations
- Prédictions ML

### Dashboard 4: Qualité des Données
- Taux de complétude
- Couverture audits
- Indicateurs de performance
- Monitoring de la plateforme

## 🧪 Tests et Qualité

### Tests Unitaires
```bash
make test-unit
```
- Tests des fonctions de transformation
- Tests des utilitaires
- Coverage > 80%

### Tests d'Intégration
```bash
make test-integration
```
- Tests des pipelines end-to-end
- Tests des connexions DB
- Validation des transformations dbt

### Tests de Qualité des Données
```bash
make test-data-quality
```
- Great Expectations suites
- Contrôles de cohérence
- Détection d'anomalies

### CI/CD

GitHub Actions workflows automatiques:
- Lint (ruff, black, mypy)
- Tests unitaires et intégration
- Validation dbt
- Build Docker images
- Déploiement automatique

## 📊 Monitoring et Alerting

### Métriques Prometheus

**Métriques Pipeline**:
- `smi_pipeline_duration_seconds`: Durée d'exécution
- `smi_pipeline_success_total`: Nombre de succès
- `smi_pipeline_failure_total`: Nombre d'échecs
- `smi_records_processed_total`: Records traités

**Métriques Data Quality**:
- `smi_data_completeness_ratio`: Taux de complétude
- `smi_data_validity_ratio`: Taux de validité
- `smi_anomalies_detected_total`: Anomalies détectées

### Dashboards Grafana

1. **Pipeline Health**: État des pipelines, SLA, tendances
2. **Data Quality**: Métriques qualité, évolutions
3. **Infrastructure**: CPU, mémoire, disque, réseau
4. **Business Metrics**: KPIs métier en temps réel

### Alerting

Configuration AlertManager pour:
- Échec de pipeline (critique)
- Dépassement SLA (warning)
- Anomalies de données (warning)
- Ressources système critiques (critical)

## 🔐 Sécurité

- Authentification RBAC sur tous les services
- Chiffrement des données sensibles
- Secrets gérés via variables d'environnement
- Audit logs complet
- Sauvegarde automatique quotidienne

## 📚 Documentation

- **Architecture Decision Records**: `/docs/architecture/adr/`
- **Data Dictionary**: `/docs/data_dictionary/`
- **Runbooks**: `/docs/runbooks/`
- **API Documentation**: Auto-générée avec Sphinx

## 🤝 Contribution

Voir `CONTRIBUTING.md` pour les guidelines de contribution.

## 📄 Licence

MIT License - Voir `LICENSE` pour plus de détails.

## 👥 Équipe

- **Solution Manager**: Yézouma
- **Organisation**: Sand Technologies - Healthcare Team
- **Projet**: CNIS - Burkina Faso

## 📞 Support

- Email: support@sandtechnologies.bf
- Issues: GitHub Issues
- Documentation: https://docs.smi-platform.bf

---

**Version**: 1.0.0  
**Dernière mise à jour**: Janvier 2026  
**Status**: Production Ready ✅
