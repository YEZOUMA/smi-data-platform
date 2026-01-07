.PHONY: help setup up down restart logs ps clean test lint format install-dev import-data run-pipeline

# Variables
DOCKER_COMPOSE := docker compose
PYTHON := python3
PIP := pip3

# Couleurs pour les messages
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Afficher ce message d'aide
	@echo "$(GREEN)Plateforme SMI Data Engineering - Commandes disponibles:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'

# Installation et Configuration
setup: ## Configuration initiale complète du projet
	@echo "$(GREEN)🚀 Configuration initiale de la plateforme SMI...$(NC)"
	@mkdir -p data/{bronze,silver,gold,source}
	@mkdir -p airflow/logs
	@chmod -R 777 airflow/logs
	@cp -n .env.example .env 2>/dev/null || true
	@echo "$(GREEN)✅ Configuration terminée!$(NC)"
	@echo "$(YELLOW)⚠️  Pensez à éditer le fichier .env avec vos paramètres$(NC)"

install-dev: ## Installer les dépendances Python de développement
	@echo "$(GREEN)📦 Installation des dépendances...$(NC)"
	@$(PIP) install -e ".[dev]"
	@echo "$(GREEN)✅ Dépendances installées!$(NC)"

# Docker & Services
up: ## Démarrer tous les services
	@echo "$(GREEN)🚀 Démarrage des services...$(NC)"
	@$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✅ Services démarrés!$(NC)"
	@echo "\n$(YELLOW)Services disponibles:$(NC)"
	@echo "  - Airflow:    http://localhost:8080 (admin/admin)"
	@echo "  - Superset:   http://localhost:8088 (admin/admin)"
	@echo "  - Grafana:    http://localhost:3000 (admin/admin)"
	@echo "  - Prometheus: http://localhost:9090"
	@echo "  - MinIO:      http://localhost:9001 (minioadmin/minioadmin)"

down: ## Arrêter tous les services
	@echo "$(YELLOW)🛑 Arrêt des services...$(NC)"
	@$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✅ Services arrêtés!$(NC)"

restart: down up ## Redémarrer tous les services

logs: ## Afficher les logs de tous les services
	@$(DOCKER_COMPOSE) logs -f

logs-airflow: ## Afficher les logs Airflow
	@$(DOCKER_COMPOSE) logs -f airflow-webserver airflow-scheduler

logs-superset: ## Afficher les logs Superset
	@$(DOCKER_COMPOSE) logs -f superset

ps: ## Lister les services en cours d'exécution
	@$(DOCKER_COMPOSE) ps

# Gestion des données
import-data: ## Importer les données source
	@echo "$(GREEN)📥 Importation des données source...$(NC)"
	@if [ -f data/source/Donnees_POC2024_2025_10122025.xls ]; then \
		echo "$(GREEN)✅ Fichier source déjà présent dans data/source/$(NC)"; \
	elif [ -f /mnt/user-data/uploads/Donnees_POC2024_2025_10122025.xls ]; then \
		cp /mnt/user-data/uploads/Donnees_POC2024_2025_10122025.xls data/source/; \
		echo "$(GREEN)✅ Fichier copié depuis /mnt/user-data/uploads/$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  Fichier source non trouvé. Placez Donnees_POC2024_2025_10122025.xls dans data/source/$(NC)"; \
	fi

run-pipeline: ## Exécuter le pipeline ETL complet
	@echo "$(GREEN)🔄 Exécution du pipeline ETL...$(NC)"
	@$(DOCKER_COMPOSE) exec airflow-scheduler airflow dags trigger smi_full_pipeline
	@echo "$(GREEN)✅ Pipeline déclenché! Vérifiez l'interface Airflow pour le statut.$(NC)"

run-incremental: ## Exécuter le chargement incrémental
	@$(DOCKER_COMPOSE) exec airflow-scheduler airflow dags trigger smi_incremental_load

# Airflow Management
airflow-init: ## Initialiser Airflow (première fois)
	@echo "$(GREEN)🔧 Initialisation Airflow...$(NC)"
	@$(DOCKER_COMPOSE) up airflow-init
	@echo "$(GREEN)✅ Airflow initialisé!$(NC)"

airflow-shell: ## Ouvrir un shell dans le conteneur Airflow
	@$(DOCKER_COMPOSE) exec airflow-scheduler bash

# Database Management
db-shell: ## Ouvrir un shell PostgreSQL dans le DWH
	@$(DOCKER_COMPOSE) exec postgres-dwh psql -U smi_user -d smi_dwh

db-migrate: ## Exécuter les migrations de base de données
	@echo "$(GREEN)🔄 Exécution des migrations...$(NC)"
	@$(DOCKER_COMPOSE) exec postgres-dwh psql -U smi_user -d smi_dwh -f /docker-entrypoint-initdb.d/01_create_schemas.sql
	@echo "$(GREEN)✅ Migrations terminées!$(NC)"

db-backup: ## Sauvegarder la base de données
	@echo "$(GREEN)💾 Sauvegarde de la base de données...$(NC)"
	@mkdir -p backups
	@$(DOCKER_COMPOSE) exec -T postgres-dwh pg_dump -U smi_user smi_dwh > backups/smi_dwh_$$(date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Sauvegarde créée dans backups/$(NC)"

db-restore: ## Restaurer la dernière sauvegarde
	@echo "$(YELLOW)⚠️  Restauration de la dernière sauvegarde...$(NC)"
	@$(DOCKER_COMPOSE) exec -T postgres-dwh psql -U smi_user -d smi_dwh < $$(ls -t backups/*.sql | head -1)
	@echo "$(GREEN)✅ Base de données restaurée!$(NC)"

# dbt Management
dbt-run: ## Exécuter les transformations dbt
	@echo "$(GREEN)🔄 Exécution dbt...$(NC)"
	@cd dbt && dbt run --profiles-dir .
	@echo "$(GREEN)✅ Transformations dbt terminées!$(NC)"

dbt-test: ## Exécuter les tests dbt
	@echo "$(GREEN)🧪 Tests dbt...$(NC)"
	@cd dbt && dbt test --profiles-dir .

dbt-docs: ## Générer et servir la documentation dbt
	@cd dbt && dbt docs generate --profiles-dir . && dbt docs serve --profiles-dir .

# Tests
test: test-unit test-integration ## Exécuter tous les tests

test-unit: ## Exécuter les tests unitaires
	@echo "$(GREEN)🧪 Tests unitaires...$(NC)"
	@pytest tests/unit -v --cov=src --cov-report=html --cov-report=term
	@echo "$(GREEN)✅ Tests unitaires terminés!$(NC)"

test-integration: ## Exécuter les tests d'intégration
	@echo "$(GREEN)🧪 Tests d'intégration...$(NC)"
	@pytest tests/integration -v
	@echo "$(GREEN)✅ Tests d'intégration terminés!$(NC)"

test-e2e: ## Exécuter les tests end-to-end
	@echo "$(GREEN)🧪 Tests E2E...$(NC)"
	@pytest tests/e2e -v
	@echo "$(GREEN)✅ Tests E2E terminés!$(NC)"

test-data-quality: ## Exécuter les tests de qualité des données
	@echo "$(GREEN)🧪 Tests qualité des données...$(NC)"
	@great_expectations checkpoint run data_quality_checkpoint
	@echo "$(GREEN)✅ Tests qualité terminés!$(NC)"

# Code Quality
lint: ## Exécuter le linting (ruff)
	@echo "$(GREEN)🔍 Linting du code...$(NC)"
	@ruff check src tests airflow

format: ## Formater le code (black, isort)
	@echo "$(GREEN)🎨 Formatage du code...$(NC)"
	@black src tests airflow
	@isort src tests airflow
	@echo "$(GREEN)✅ Code formaté!$(NC)"

type-check: ## Vérifier les types (mypy)
	@echo "$(GREEN)🔍 Vérification des types...$(NC)"
	@mypy src

# Monitoring
metrics: ## Afficher les métriques Prometheus
	@echo "$(GREEN)📊 Métriques disponibles sur http://localhost:9090$(NC)"
	@open http://localhost:9090 || xdg-open http://localhost:9090 || echo "Ouvrez manuellement: http://localhost:9090"

grafana: ## Ouvrir Grafana
	@echo "$(GREEN)📊 Grafana disponible sur http://localhost:3000$(NC)"
	@open http://localhost:3000 || xdg-open http://localhost:3000 || echo "Ouvrez manuellement: http://localhost:3000"

# Documentation
docs: ## Générer la documentation Sphinx
	@echo "$(GREEN)📚 Génération de la documentation...$(NC)"
	@cd docs && make html
	@echo "$(GREEN)✅ Documentation générée dans docs/_build/html/$(NC)"

docs-serve: docs ## Générer et servir la documentation
	@cd docs/_build/html && python -m http.server 8000

# Nettoyage
clean: ## Nettoyer les fichiers temporaires
	@echo "$(YELLOW)🧹 Nettoyage des fichiers temporaires...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf htmlcov/ .coverage
	@echo "$(GREEN)✅ Nettoyage terminé!$(NC)"

clean-all: clean down ## Nettoyer complètement (données + conteneurs)
	@echo "$(RED)⚠️  ATTENTION: Suppression complète des données et volumes!$(NC)"
	@read -p "Êtes-vous sûr? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	@$(DOCKER_COMPOSE) down -v
	@rm -rf data/bronze/* data/silver/* data/gold/*
	@echo "$(GREEN)✅ Nettoyage complet terminé!$(NC)"

# Utilitaires
shell: ## Ouvrir un shell Python avec le contexte du projet
	@$(PYTHON) -i -c "import sys; sys.path.insert(0, 'src'); print('🐍 Shell Python avec contexte SMI chargé')"

jupyter: ## Lancer Jupyter Notebook
	@echo "$(GREEN)📓 Lancement Jupyter Notebook...$(NC)"
	@jupyter notebook notebooks/

version: ## Afficher les versions des composants
	@echo "$(GREEN)📦 Versions des composants:$(NC)"
	@echo "  Python:     $$($(PYTHON) --version)"
	@echo "  Docker:     $$(docker --version)"
	@echo "  Docker Compose: $$(docker compose version)"
	@$(PIP) show pandas dbt-core apache-airflow 2>/dev/null | grep -E "Name|Version" || echo "  Packages non installés"

health: ## Vérifier la santé des services
	@echo "$(GREEN)🏥 État des services:$(NC)"
	@$(DOCKER_COMPOSE) ps
	@echo "\n$(GREEN)Endpoints disponibles:$(NC)"
	@curl -s http://localhost:8080/health >/dev/null && echo "  ✅ Airflow" || echo "  ❌ Airflow"
	@curl -s http://localhost:8088/health >/dev/null && echo "  ✅ Superset" || echo "  ❌ Superset"
	@curl -s http://localhost:3000/api/health >/dev/null && echo "  ✅ Grafana" || echo "  ❌ Grafana"
	@curl -s http://localhost:9090/-/healthy >/dev/null && echo "  ✅ Prometheus" || echo "  ❌ Prometheus"

# Par défaut, afficher l'aide
.DEFAULT_GOAL := help
