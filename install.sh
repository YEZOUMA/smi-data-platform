#!/bin/bash
set -e

echo "🚀 Installation de la Plateforme SMI Data Engineering"
echo "=================================================="

# Vérifier Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker n'est pas installé. Veuillez installer Docker Desktop."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose n'est pas installé."
    exit 1
fi

echo "✅ Docker et Docker Compose détectés"

# Vérifier Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 n'est pas installé."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
if (( $(echo "$PYTHON_VERSION < 3.11" | bc -l) )); then
    echo "❌ Python 3.11+ requis (version actuelle: $PYTHON_VERSION)"
    exit 1
fi

echo "✅ Python $PYTHON_VERSION détecté"

# Setup initial
echo ""
echo "📦 Configuration initiale..."
make setup

# Créer environnement virtuel
echo ""
echo "🐍 Création de l'environnement virtuel Python..."
python3 -m venv venv

# Activer et installer dépendances
echo ""
echo "📚 Installation des dépendances..."
source venv/bin/activate
pip install -e ".[dev]" --quiet

# Configuration .env
if [ ! -f .env ]; then
    echo ""
    echo "⚙️  Configuration des variables d'environnement..."
    cp .env.example .env
    echo "⚠️  Pensez à éditer le fichier .env avec vos paramètres !"
fi

echo ""
echo "✅ Installation terminée !"
echo ""
echo "🚀 Prochaines étapes:"
echo ""
echo "1. Éditer le fichier .env avec vos paramètres:"
echo "   nano .env"
echo ""
echo "2. Démarrer les services:"
echo "   make up"
echo ""
echo "3. Initialiser Airflow:"
echo "   make airflow-init"
echo ""
echo "4. Importer les données:"
echo "   make import-data"
echo ""
echo "5. Exécuter le pipeline:"
echo "   make run-pipeline"
echo ""
echo "6. Accéder aux services:"
echo "   - Airflow:    http://localhost:8080 (admin/admin)"
echo "   - Superset:   http://localhost:8088 (admin/admin)"
echo "   - Grafana:    http://localhost:3000 (admin/admin)"
echo ""
echo "📚 Pour plus d'informations:"
echo "   - README.md"
echo "   - DEPLOYMENT_GUIDE.md"
echo "   - PROJECT_SUMMARY.md"
echo ""
echo "🎉 Bonne chance avec votre projet SMI !"
