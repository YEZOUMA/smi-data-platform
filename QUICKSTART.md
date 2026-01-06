# ⚡ QUICKSTART - Démarrage en 5 Minutes

## Installation Express

```bash
# 1. Exécuter le script d'installation
./install.sh

# 2. Configurer .env (IMPORTANT !)
nano .env
# Modifier au minimum:
# - POSTGRES_PASSWORD
# - AIRFLOW__WEBSERVER__SECRET_KEY
# - SUPERSET_SECRET_KEY

# 3. Démarrer tout
make up
make airflow-init
make import-data
make run-pipeline

# 4. Accéder aux interfaces
open http://localhost:8080  # Airflow
open http://localhost:8088  # Superset
open http://localhost:3000  # Grafana
```

## Commandes Essentielles

```bash
# Démarrer/Arrêter
make up              # Démarrer tous les services
make down            # Arrêter tous les services
make restart         # Redémarrer tous les services

# Pipeline
make run-pipeline    # Exécuter le pipeline ETL
make logs-airflow    # Voir les logs Airflow

# Monitoring
make health          # Vérifier la santé des services
make ps              # Lister les services actifs
make logs            # Voir tous les logs

# Base de données
make db-shell        # Ouvrir PostgreSQL
make db-backup       # Sauvegarder
make db-restore      # Restaurer

# Tests
make test            # Tous les tests
make test-unit       # Tests unitaires
make test-integration # Tests intégration

# Code Quality
make lint            # Linting
make format          # Formatage
make type-check      # Vérification types

# Nettoyage
make clean           # Nettoyer fichiers temporaires
make clean-all       # Nettoyage complet (ATTENTION: supprime les données)
```

## URLs des Services

| Service | URL | Credentials |
|---------|-----|-------------|
| Airflow | http://localhost:8080 | admin / admin |
| Superset | http://localhost:8088 | admin / admin |
| Grafana | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | - |
| MinIO | http://localhost:9001 | minioadmin / minioadmin |

## Vérification Rapide

```bash
# 1. Services actifs ?
make ps

# 2. Pipeline fonctionne ?
make run-pipeline

# 3. Données chargées ?
make db-shell
# Dans psql:
SELECT COUNT(*) FROM bronze.smi_raw;
SELECT COUNT(*) FROM silver.smi_cleaned;
SELECT COUNT(*) FROM gold.fait_deces_neonatals;
```

## Problèmes Courants

### Services ne démarrent pas
```bash
# Libérer les ports
sudo lsof -i :8080
sudo lsof -i :8088
sudo lsof -i :5433

# Redémarrer Docker
docker system prune -a
make up
```

### Pipeline échoue
```bash
# Voir les logs
make logs-airflow

# Vérifier les données sources
ls -lh data/source/

# Tester manuellement l'extraction
python -m src.extract.excel_extractor data/source/Donnees_POC2024_2025_10122025.xls
```

### Données manquantes
```bash
# Vérifier chaque couche
make db-shell
SELECT COUNT(*) FROM bronze.smi_raw;
SELECT COUNT(*) FROM silver.smi_cleaned;
SELECT COUNT(*) FROM gold.fait_deces_neonatals;
```

## Prochaines Étapes

1. ✅ Créer vos dashboards Superset
2. ✅ Configurer les alertes Grafana
3. ✅ Personnaliser les transformations dbt
4. ✅ Ajouter vos propres analyses
5. ✅ Mettre en production !

## Documentation Complète

- `README.md` - Vue d'ensemble
- `DEPLOYMENT_GUIDE.md` - Guide détaillé
- `PROJECT_SUMMARY.md` - Synthèse complète

## Support

- Email: support@sandtechnologies.bf
- Docs: https://docs.smi-platform.bf
- Issues: GitHub Issues

---

🚀 **C'est parti !**
