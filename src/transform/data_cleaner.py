"""
Module de nettoyage et transformation des données SMI
"""
import logging
import re
from typing import Optional

import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class SMIDataCleaner:
    """
    Classe pour nettoyer et transformer les données SMI
    """
    
    # Mapping des noms de colonnes
    COLUMN_MAPPING = {
        'Pays': 'pays',
        'Région': 'region',
        'Province': 'province',
        'District sanitaire': 'district_sanitaire',
        'Commune/arrondissement': 'commune',
        'Formation sanitaire': 'formation_sanitaire',
        'Période': 'periode'
    }
    
    def __init__(self, df: pd.DataFrame):
        """
        Initialise le cleaner avec un DataFrame
        
        Args:
            df: DataFrame pandas à nettoyer
        """
        self.df = df.copy()
        self.original_row_count = len(df)
        logger.info(f"🧹 Initialisation du nettoyage: {self.original_row_count} lignes")
    
    def clean_column_names(self) -> 'SMIDataCleaner':
        """
        Nettoie les noms de colonnes:
        - Normalise en snake_case
        - Supprime les accents
        - Réduit les espaces
        
        Returns:
            self pour chaînage
        """
        logger.info("📝 Nettoyage des noms de colonnes...")
        
        def normalize_name(name: str) -> str:
            # Supprimer les espaces multiples
            name = re.sub(r'\s+', ' ', name.strip())
            
            # Remplacer certaines colonnes longues
            replacements = {
                'Décès maternels par cause de complication obstétricale': 'deces_mat_',
                'Nouveau-nes decedes de': 'deces_neo_',
                'SMI-': 'smi_'
            }
            
            for old, new in replacements.items():
                if old in name:
                    name = name.replace(old, new)
            
            # Convertir en minuscules et remplacer espaces par underscores
            name = name.lower().replace(' ', '_').replace('-', '_')
            
            # Supprimer les caractères spéciaux
            name = re.sub(r'[éèêë]', 'e', name)
            name = re.sub(r'[àâä]', 'a', name)
            name = re.sub(r'[îï]', 'i', name)
            name = re.sub(r'[ôö]', 'o', name)
            name = re.sub(r'[ùûü]', 'u', name)
            name = re.sub(r'[ç]', 'c', name)
            name = re.sub(r'[^\w_]', '_', name)
            
            # Supprimer les underscores multiples
            name = re.sub(r'_+', '_', name)
            name = name.strip('_')
            
            return name
        
        self.df.columns = [normalize_name(col) for col in self.df.columns]
        logger.info(f"✅ Noms de colonnes nettoyés: {len(self.df.columns)} colonnes")
        
        return self
    
    def handle_missing_values(self) -> 'SMIDataCleaner':
        """
        Traite les valeurs manquantes:
        - Compteurs de décès → 0
        - Ratios/Proportions → garder NaN
        - Géographie → supprimer la ligne
        
        Returns:
            self pour chaînage
        """
        logger.info("🔧 Traitement des valeurs manquantes...")
        
        # Colonnes de compteurs (remplacer NaN par 0)
        counter_cols = [col for col in self.df.columns if 'deces' in col or 'nombre' in col]
        for col in counter_cols:
            if col in self.df.columns:
                self.df[col] = self.df[col].fillna(0)
        
        # Supprimer les lignes avec géographie manquante
        geo_cols = ['pays', 'region', 'province', 'district_sanitaire', 
                   'commune', 'formation_sanitaire']
        geo_cols_present = [col for col in geo_cols if col in self.df.columns]
        
        before = len(self.df)
        self.df = self.df.dropna(subset=geo_cols_present, how='any')
        after = len(self.df)
        
        if before != after:
            logger.warning(f"⚠️  {before - after} lignes supprimées (géographie manquante)")
        
        return self
    
    def parse_period(self) -> 'SMIDataCleaner':
        """
        Parse et enrichit la colonne période:
        - Convertit en date
        - Extrait année, mois, trimestre, semestre
        
        Returns:
            self pour chaînage
        """
        logger.info("📅 Parsing des périodes...")
        
        if 'periode' not in self.df.columns:
            logger.warning("⚠️  Colonne 'periode' non trouvée")
            return self
        
        # Mapping français → anglais pour les mois
        mois_mapping = {
            'janvier': 'January', 'février': 'February', 'fevrier': 'February',
            'mars': 'March', 'avril': 'April', 'mai': 'May', 'juin': 'June',
            'juillet': 'July', 'août': 'August', 'aout': 'August',
            'septembre': 'September', 'octobre': 'October',
            'novembre': 'November', 'décembre': 'December', 'decembre': 'December'
        }
        
        def parse_date(period_str):
            if pd.isna(period_str):
                return None
            
            period_str = str(period_str).strip().lower()
            
            # Remplacer le mois français par anglais
            for fr, en in mois_mapping.items():
                period_str = period_str.replace(fr, en.lower())
            
            try:
                # Format: "mois YYYY"
                return pd.to_datetime(period_str, format='%B %Y', errors='coerce')
            except:
                try:
                    # Format: "mois-YYYY"
                    return pd.to_datetime(period_str, format='%B-%Y', errors='coerce')
                except:
                    logger.warning(f"⚠️  Impossible de parser la période: {period_str}")
                    return None
        
        self.df['periode_date'] = self.df['periode'].apply(parse_date)
        
        # Extraire les composantes temporelles
        self.df['annee'] = self.df['periode_date'].dt.year
        self.df['mois'] = self.df['periode_date'].dt.month
        self.df['trimestre'] = self.df['periode_date'].dt.quarter
        self.df['semestre'] = self.df['mois'].apply(lambda m: 1 if m <= 6 else 2 if not pd.isna(m) else None)
        
        # Compter les périodes valides
        valid_dates = self.df['periode_date'].notna().sum()
        logger.info(f"✅ {valid_dates}/{len(self.df)} périodes parsées avec succès")
        
        return self
    
    def normalize_geography(self) -> 'SMIDataCleaner':
        """
        Normalise les données géographiques:
        - Supprime les espaces en trop
        - Standardise la casse
        - Crée des identifiants géographiques
        
        Returns:
            self pour chaînage
        """
        logger.info("🗺️  Normalisation de la géographie...")
        
        geo_cols = ['pays', 'region', 'province', 'district_sanitaire', 
                   'commune', 'formation_sanitaire']
        
        for col in geo_cols:
            if col in self.df.columns:
                # Supprimer espaces multiples et trim
                self.df[col] = self.df[col].astype(str).str.strip()
                self.df[col] = self.df[col].str.replace(r'\s+', ' ', regex=True)
                
                # Standardiser la casse (Title Case)
                self.df[col] = self.df[col].str.title()
        
        # Créer un identifiant géographique unique
        if all(col in self.df.columns for col in geo_cols):
            self.df['geo_id'] = (
                self.df['pays'].astype(str) + '_' +
                self.df['region'].astype(str) + '_' +
                self.df['province'].astype(str) + '_' +
                self.df['district_sanitaire'].astype(str) + '_' +
                self.df['commune'].astype(str) + '_' +
                self.df['formation_sanitaire'].astype(str)
            )
            self.df['geo_id'] = self.df['geo_id'].str.replace(' ', '_').str.lower()
        
        logger.info("✅ Géographie normalisée")
        
        return self
    
    def calculate_derived_metrics(self) -> 'SMIDataCleaner':
        """
        Calcule des métriques dérivées:
        - Total des décès par catégorie
        - Ratios et proportions
        
        Returns:
            self pour chaînage
        """
        logger.info("📊 Calcul des métriques dérivées...")
        
        # Total décès maternels (somme de toutes les causes)
        cause_cols = [col for col in self.df.columns if 'deces_mat_' in col and col != 'deces_mat_total']
        if cause_cols:
            self.df['total_deces_maternels_calcule'] = self.df[cause_cols].sum(axis=1)
        
        # Total décès néonatals
        if 'deces_neo_0_6_jours' in self.df.columns and 'deces_neo_7_28_jours' in self.df.columns:
            self.df['total_deces_neonatals'] = (
                self.df['deces_neo_0_6_jours'].fillna(0) + 
                self.df['deces_neo_7_28_jours'].fillna(0)
            )
        
        logger.info("✅ Métriques dérivées calculées")
        
        return self
    
    def validate_data(self) -> dict:
        """
        Valide la qualité des données et retourne un rapport
        
        Returns:
            Dictionnaire avec les résultats de validation
        """
        logger.info("✅ Validation des données...")
        
        validation_report = {
            'original_rows': self.original_row_count,
            'final_rows': len(self.df),
            'rows_removed': self.original_row_count - len(self.df),
            'columns': len(self.df.columns),
            'missing_values_pct': (self.df.isnull().sum() / len(self.df) * 100).to_dict(),
            'duplicates': int(self.df.duplicated().sum()),
        }
        
        # Vérifier les valeurs négatives dans les compteurs
        counter_cols = [col for col in self.df.columns if 'deces' in col or 'nombre' in col]
        negative_values = {}
        for col in counter_cols:
            if col in self.df.columns:
                neg_count = (self.df[col] < 0).sum()
                if neg_count > 0:
                    negative_values[col] = int(neg_count)
        
        validation_report['negative_values'] = negative_values
        
        logger.info(f"✅ Validation terminée: {validation_report['final_rows']} lignes valides")
        
        return validation_report
    
    def get_cleaned_data(self) -> pd.DataFrame:
        """
        Retourne le DataFrame nettoyé
        
        Returns:
            DataFrame nettoyé
        """
        return self.df.copy()
    
    def clean_pipeline(self) -> 'SMIDataCleaner':
        """
        Exécute le pipeline complet de nettoyage
        
        Returns:
            self avec toutes les transformations appliquées
        """
        logger.info("🚀 Démarrage du pipeline de nettoyage...")
        
        (self
         .clean_column_names()
         .handle_missing_values()
         .parse_period()
         .normalize_geography()
         .calculate_derived_metrics())
        
        logger.info("✅ Pipeline de nettoyage terminé!")
        
        return self


def clean_smi_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Fonction utilitaire pour nettoyer les données SMI
    
    Args:
        df: DataFrame à nettoyer
        
    Returns:
        Tuple (DataFrame nettoyé, rapport de validation)
    """
    cleaner = SMIDataCleaner(df)
    cleaner.clean_pipeline()
    
    validation_report = cleaner.validate_data()
    cleaned_df = cleaner.get_cleaned_data()
    
    return cleaned_df, validation_report


if __name__ == "__main__":
    # Test du cleaner
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) > 1:
        from extract.excel_extractor import extract_from_excel
        
        file_path = sys.argv[1]
        df = extract_from_excel(file_path)
        
        cleaned_df, report = clean_smi_data(df)
        
        print("\n📊 Rapport de validation:")
        for key, value in report.items():
            print(f"  {key}: {value}")
        
        print("\n📋 Aperçu des données nettoyées:")
        print(cleaned_df.head())
