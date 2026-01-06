# 📦 COMMENT UTILISER CE PROJET

## 🎯 Vous avez Téléchargé le Projet - Et Maintenant ?

### Étape 1 : Extraire l'Archive

```bash
# Si vous avez téléchargé le fichier .tar.gz
tar -xzf smi-data-platform.tar.gz
cd smi-data-platform

# Ou si vous avez téléchargé le dossier directement
cd smi-data-platform
```

### Étape 2 : Vérifier le Contenu

```bash
# Lister les fichiers
ls -la

# Vous devriez voir :
# - README.md
# - QUICKSTART.md
# - docker-compose.yml
# - Makefile
# - install.sh
# - src/
# - airflow/
# - etc.
```

### Étape 3 : Rendre le Script d'Installation Exécutable

```bash
chmod +x install.sh
```

### Étape 4 : Lancer l'Installation

```bash
./install.sh
```

## 🚀 Démarrage Rapide Complet

```bash
# 1. Extraire
tar -xzf smi-data-platform.tar.gz
cd smi-data-platform

# 2. Rendre exécutable
chmod +x install.sh

# 3. Installer
./install.sh

# 4. Configurer (IMPORTANT!)
cp .env.example .env
nano .env  # ou vim, code, etc.

# 5. Démarrer
make up
make airflow-init

# 6. Importer les données
make import-data

# 7. Lancer le pipeline
make run-pipeline
```

## 📍 Où Êtes-Vous ?

Après extraction, votre structure devrait être :

```
votre-dossier-de-travail/
└── smi-data-platform/          ← VOUS ÊTES ICI
    ├── README.md
    ├── docker-compose.yml
    ├── Makefile
    ├── install.sh
    ├── src/
    ├── airflow/
    ├── dbt/
    ├── scripts/
    └── ...
```

## 🔍 Vérification Rapide

```bash
# Êtes-vous au bon endroit ?
ls -1

# Vous devriez voir :
# README.md
# QUICKSTART.md
# docker-compose.yml
# Makefile
# pyproject.toml
# src
# airflow
# dbt
# scripts
# ...
```

## ⚠️ Prérequis Système

Avant de continuer, assurez-vous d'avoir :

- ✅ **Docker Desktop** installé et lancé
- ✅ **Python 3.11+** installé
- ✅ **Git** installé (optionnel mais recommandé)
- ✅ **8 GB RAM** minimum (16 GB recommandé)
- ✅ **20 GB d'espace disque** libre

### Vérifier Docker

```bash
docker --version
docker-compose --version

# Tester Docker
docker run hello-world
```

### Vérifier Python

```bash
python3 --version
# Doit être >= 3.11
```

## 🆘 Problèmes Courants

### "Permission denied" sur install.sh
```bash
chmod +x install.sh
```

### "Docker command not found"
- Installez Docker Desktop : https://www.docker.com/products/docker-desktop

### "Python version too old"
```bash
# Ubuntu/Debian
sudo apt install python3.11

# macOS (avec Homebrew)
brew install python@3.11

# Windows
# Télécharger depuis python.org
```

### Le dossier semble vide
```bash
# Vérifier les fichiers cachés
ls -la

# Vous avez peut-être extrait dans un sous-dossier
cd smi-data-platform  # Essayer encore
```

## 📚 Documentation Disponible

Une fois dans le dossier, consultez :

1. **QUICKSTART.md** - Démarrage en 5 minutes
2. **README.md** - Vue d'ensemble complète
3. **DEPLOYMENT_GUIDE.md** - Guide détaillé pas à pas
4. **PROJECT_SUMMARY.md** - Synthèse du projet

## 🎯 Premiers Pas Recommandés

```bash
# 1. Lire le Quickstart
cat QUICKSTART.md

# 2. Vérifier les prérequis
docker --version
python3 --version

# 3. Lancer l'installation
./install.sh

# 4. Suivre les instructions affichées
```

## 💡 Après l'Installation

Les services seront disponibles à :

- **Airflow** : http://localhost:8080 (admin/admin)
- **Superset** : http://localhost:8088 (admin/admin)
- **Grafana** : http://localhost:3000 (admin/admin)
- **Prometheus** : http://localhost:9090

## 🤝 Besoin d'Aide ?

- Consultez `DEPLOYMENT_GUIDE.md` pour le troubleshooting
- Regardez les logs : `make logs`
- Vérifiez la santé : `make health`

---

**Version**: 1.0.0  
**Date**: Janvier 2026  
**Équipe**: Sand Technologies - Healthcare Team

🎉 **Bon courage avec votre projet SMI !**
