# 🚀 Guide de Déploiement - Plateforme SMI

## Table des Matières
1. [Prérequis](#prérequis)
2. [Installation Rapide](#installation-rapide)
3. [Configuration Détaillée](#configuration-détaillée)
4. [Démarrage des Services](#démarrage-des-services)
5. [Vérification](#vérification)
6. [Troubleshooting](#troubleshooting)

## Prérequis

### Système
- **OS**: Linux (Ubuntu 20.04+), macOS, ou Windows avec WSL2
- **RAM**: Minimum 8 GB (16 GB recommandé)
- **Disque**: 20 GB minimum d'espace libre
- **CPU**: 4 cœurs minimum

### Logiciels
```bash
# Docker
docker --version  # Doit être >= 24.0.0
docker-compose --version  # Doit être >= 2.0.0

# Python
python3 --version  # Doit être >= 3.11

# Git
git --version
```

## Installation Rapide

### 1. Cloner le Projet
```bash
git clone <repository-url>
cd smi-data-platform
```

### 2. Configuration Initiale
```bash
# Créer l'environnement virtuel Python
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou: venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -e ".[dev]"

# Configuration de base
make setup
```

### 3. Configurer les Variables d'Environnement
```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer .env avec vos paramètres
nano .env  # ou vim, code, etc.
```

**Variables Critiques à Modifier:**
```bash
# Sécurité - CHANGER EN PRODUCTION !
AIRFLOW__WEBSERVER__SECRET_KEY=<générer-une-clé-forte>
SUPERSET_SECRET_KEY=<générer-une-clé-forte>
POSTGRES_PASSWORD=<mot-de-passe-fort>

# Email pour notifications
NOTIFICATION_EMAIL_LIST=votre-email@example.com
```

### 4. Lancer l'Infrastructure
```bash
# Démarrer tous les services
make up

# Initialiser Airflow (première fois uniquement)
make airflow-init

# Importer les données sources
make import-data
```

### 5. Accéder aux Services

Les services seront disponibles aux URLs suivantes:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Airflow** | http://localhost:8080 | admin / admin |
| **Superset** | http://localhost:8088 | admin / admin |
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | - |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin |

## Configuration Détaillée

### Configuration PostgreSQL

Le Data Warehouse est automatiquement initialisé avec:
- Schémas: bronze, silver, gold, metadata
- Tables dimensionnelles et de faits
- Indexes et contraintes
- Fonctions utilitaires

**Connexion manuelle:**
```bash
make db-shell
# ou
psql -h localhost -p 5433 -U smi_user -d smi_dwh
```

### Configuration Airflow

**Connexions à configurer dans l'interface Airflow:**

1. **PostgreSQL DWH** (`postgres_dwh`)
   - Conn Type: `Postgres`
   - Host: `postgres-dwh`
   - Schema: `smi_dwh`
   - Login: `smi_user`
   - Password: `smi_password`
   - Port: `5432`

2. **MinIO S3** (`minio_s3`)
   - Conn Type: `Amazon Web Services`
   - Extra: 
   ```json
   {
     "aws_access_key_id": "minioadmin",
     "aws_secret_access_key": "minioadmin",
     "host": "http://minio:9000"
   }
   ```

### Configuration Superset

**Connexion au Data Warehouse:**

1. Accéder à Superset: http://localhost:8088
2. Aller dans Settings > Database Connections
3. Ajouter une connexion:
   - Database: `SMI Data Warehouse`
   - SQLAlchemy URI: 
     ```
     postgresql://smi_user:smi_password@postgres-dwh:5432/smi_dwh
     ```

### Configuration dbt

Le projet dbt est dans `/dbt` avec la structure:
```
dbt/
├── models/
│   ├── bronze/     # Sources brutes
│   ├── silver/     # Transformations
│   └── gold/       # Analytics
├── tests/          # Tests data quality
└── dbt_project.yml
```

**Exécuter dbt:**
```bash
make dbt-run      # Exécuter transformations
make dbt-test     # Exécuter tests
make dbt-docs     # Générer documentation
```

## Démarrage des Services

### Ordre de Démarrage Recommandé

1. **Infrastructure de Base**
   ```bash
   docker-compose up -d postgres-dwh postgres-airflow redis minio
   ```

2. **Airflow**
   ```bash
   docker-compose up -d airflow-init
   docker-compose up -d airflow-webserver airflow-scheduler
   ```

3. **Analytics & Monitoring**
   ```bash
   docker-compose up -d superset prometheus grafana
   ```

### Vérification du Démarrage

```bash
# Vérifier les services
make ps

# Vérifier la santé
make health

# Logs en temps réel
make logs
```

## Vérification

### 1. Vérifier PostgreSQL
```bash
make db-shell

# Dans psql:
\dt bronze.*      # Tables Bronze
\dt silver.*      # Tables Silver
\dt gold.*        # Tables Gold

# Compter les enregistrements
SELECT COUNT(*) FROM bronze.smi_raw;
```

### 2. Vérifier Airflow
1. Ouvrir http://localhost:8080
2. Vérifier que le DAG `smi_full_pipeline` est visible
3. L'activer (toggle ON)
4. Déclencher manuellement : "Trigger DAG"

### 3. Vérifier Superset
1. Ouvrir http://localhost:8088
2. Aller dans "Datasets"
3. Ajouter les tables gold.*
4. Créer un dashboard de test

### 4. Vérifier Grafana
1. Ouvrir http://localhost:3000
2. Vérifier la connexion à Prometheus
3. Importer les dashboards pré-configurés

## Exécution du Pipeline

### Exécution Manuelle
```bash
# Pipeline complet
make run-pipeline

# Suivre l'exécution
make logs-airflow
```

### Exécution Programmée
Le pipeline s'exécute automatiquement:
- **Fréquence**: Quotidien à 2h00 AM
- **Durée estimée**: 15-20 minutes
- **SLA**: 4 heures

### Monitoring de l'Exécution
- **Airflow UI**: http://localhost:8080/dags/smi_full_pipeline
- **Grafana**: http://localhost:3000 (dashboard "Pipeline Health")
- **Logs**: `make logs-airflow`

## Troubleshooting

### Problème: Services ne démarrent pas

**Solution 1: Vérifier Docker**
```bash
docker info
docker-compose version
```

**Solution 2: Libérer les ports**
```bash
# Vérifier les ports utilisés
sudo lsof -i :8080  # Airflow
sudo lsof -i :8088  # Superset
sudo lsof -i :5433  # PostgreSQL

# Arrêter les processus conflictuels
```

**Solution 3: Augmenter les ressources Docker**
- Dans Docker Desktop: Settings > Resources
- RAM: Minimum 8 GB
- Swap: 2 GB

### Problème: Airflow ne peut pas se connecter à PostgreSQL

**Solution:**
```bash
# Recréer les conteneurs
docker-compose down
docker-compose up -d postgres-dwh
sleep 10  # Attendre que PostgreSQL soit prêt
docker-compose up -d airflow-webserver airflow-scheduler
```

### Problème: Pipeline échoue

**Diagnostic:**
```bash
# Voir les logs détaillés
make logs-airflow

# Accéder au conteneur
docker exec -it smi-airflow-scheduler bash

# Vérifier les données sources
ls -lh /opt/airflow/data/source/

# Tester l'extraction manuellement
cd /opt/airflow
python -m src.extract.excel_extractor /opt/airflow/data/source/Donnees_POC2024_2025_10122025.xls
```

### Problème: Données manquantes

**Vérifications:**
```bash
# Vérifier chaque couche
make db-shell

# Bronze
SELECT COUNT(*) FROM bronze.smi_raw;
SELECT * FROM bronze.smi_raw LIMIT 5;

# Silver  
SELECT COUNT(*) FROM silver.smi_cleaned;
SELECT * FROM silver.smi_cleaned LIMIT 5;

# Gold
SELECT COUNT(*) FROM gold.fait_deces_neonatals;
```

### Problème: Performances lentes

**Optimisations:**
```bash
# 1. Augmenter les workers Airflow
# Éditer docker-compose.yml:
AIRFLOW_PARALLELISM=64
AIRFLOW_MAX_ACTIVE_TASKS=32

# 2. Optimiser PostgreSQL
# Éditer docker-compose.yml:
POSTGRES_SHARED_BUFFERS=512MB
POSTGRES_WORK_MEM=64MB

# 3. Redémarrer
docker-compose restart
```

## Maintenance

### Sauvegardes Automatiques
```bash
# Configurer dans .env:
BACKUP_ENABLED=True
BACKUP_SCHEDULE="0 2 * * *"  # 2h AM

# Sauvegarder manuellement
make db-backup

# Restaurer
make db-restore
```

### Nettoyage
```bash
# Nettoyer les fichiers temporaires
make clean

# Nettoyer complètement (ATTENTION: supprime les données)
make clean-all
```

### Mise à Jour
```bash
# Arrêter les services
make down

# Tirer les dernières modifications
git pull

# Mettre à jour les dépendances
pip install -e ".[dev]" --upgrade

# Redémarrer
make up
```

## Support

### Documentation
- **README**: Vue d'ensemble du projet
- **Architecture**: `/docs/architecture/`
- **Data Dictionary**: `/docs/data_dictionary/`
- **Runbooks**: `/docs/runbooks/`

### Ressources
- Email: support@sandtechnologies.bf
- Issues: GitHub Issues
- Documentation en ligne: https://docs.smi-platform.bf

### Logs
```bash
# Tous les services
make logs

# Service spécifique
docker-compose logs -f <service-name>

# Fichiers de logs
ls -lh airflow/logs/
```

---

**Version**: 1.0.0  
**Dernière mise à jour**: Janvier 2026  
**Maintenu par**: Sand Technologies - Healthcare Team
