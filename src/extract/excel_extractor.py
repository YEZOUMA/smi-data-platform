"""
Module d'extraction des données depuis Excel
"""
import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from prometheus_client import Counter, Histogram

# Métriques Prometheus
EXTRACTION_COUNTER = Counter(
    'smi_extraction_total',
    'Nombre total d extractions effectuées',
    ['status']
)
EXTRACTION_DURATION = Histogram(
    'smi_extraction_duration_seconds',
    'Durée d extraction en secondes'
)
RECORDS_EXTRACTED = Counter(
    'smi_records_extracted_total',
    'Nombre total d enregistrements extraits'
)

logger = logging.getLogger(__name__)


class ExcelExtractor:
    """
    Classe pour extraire les données depuis des fichiers Excel
    """
    
    def __init__(self, file_path: str):
        """
        Initialise l'extracteur
        
        Args:
            file_path: Chemin vers le fichier Excel
        """
        self.file_path = Path(file_path)
        self.df: Optional[pd.DataFrame] = None
        
        if not self.file_path.exists():
            raise FileNotFoundError(f"Fichier non trouvé: {file_path}")
    
    @EXTRACTION_DURATION.time()
    def extract(self) -> pd.DataFrame:
        """
        Extrait les données du fichier Excel
        
        Returns:
            DataFrame pandas avec les données extraites
        """
        try:
            logger.info(f"📥 Extraction depuis: {self.file_path}")
            
            # Lire le fichier Excel
            self.df = pd.read_excel(
                self.file_path,
                engine='xlrd'  # Pour les fichiers .xls
            )
            
            # Logs d'information
            logger.info(f"✅ Extraction réussie: {len(self.df)} lignes, {len(self.df.columns)} colonnes")
            
            # Métriques
            EXTRACTION_COUNTER.labels(status='success').inc()
            RECORDS_EXTRACTED.inc(len(self.df))
            
            return self.df
            
        except Exception as e:
            logger.error(f"❌ Erreur d'extraction: {str(e)}")
            EXTRACTION_COUNTER.labels(status='failure').inc()
            raise
    
    def get_schema_info(self) -> dict:
        """
        Retourne les informations sur le schéma des données
        
        Returns:
            Dictionnaire avec les métadonnées
        """
        if self.df is None:
            raise ValueError("Aucune donnée extraite. Appelez extract() d'abord.")
        
        return {
            'num_rows': len(self.df),
            'num_columns': len(self.df.columns),
            'columns': list(self.df.columns),
            'dtypes': self.df.dtypes.to_dict(),
            'memory_usage': self.df.memory_usage(deep=True).sum(),
            'missing_values': self.df.isnull().sum().to_dict()
        }
    
    def validate_schema(self, expected_columns: list) -> bool:
        """
        Valide que le schéma correspond aux colonnes attendues
        
        Args:
            expected_columns: Liste des colonnes attendues
            
        Returns:
            True si le schéma est valide
        """
        if self.df is None:
            raise ValueError("Aucune donnée extraite.")
        
        actual_columns = set(self.df.columns)
        expected_columns_set = set(expected_columns)
        
        missing = expected_columns_set - actual_columns
        extra = actual_columns - expected_columns_set
        
        if missing:
            logger.warning(f"⚠️  Colonnes manquantes: {missing}")
        
        if extra:
            logger.warning(f"⚠️  Colonnes supplémentaires: {extra}")
        
        return len(missing) == 0
    
    def get_data_quality_report(self) -> dict:
        """
        Génère un rapport de qualité des données
        
        Returns:
            Dictionnaire avec les métriques de qualité
        """
        if self.df is None:
            raise ValueError("Aucune donnée extraite.")
        
        report = {
            'total_rows': len(self.df),
            'total_columns': len(self.df.columns),
            'missing_values_pct': (self.df.isnull().sum() / len(self.df) * 100).to_dict(),
            'duplicates': int(self.df.duplicated().sum()),
            'numeric_columns': list(self.df.select_dtypes(include=['number']).columns),
            'object_columns': list(self.df.select_dtypes(include=['object']).columns),
        }
        
        # Statistiques descriptives pour colonnes numériques
        numeric_stats = self.df.select_dtypes(include=['number']).describe()
        report['numeric_statistics'] = numeric_stats.to_dict()
        
        return report


def extract_from_excel(file_path: str) -> pd.DataFrame:
    """
    Fonction utilitaire pour extraction rapide
    
    Args:
        file_path: Chemin vers le fichier Excel
        
    Returns:
        DataFrame avec les données
    """
    extractor = ExcelExtractor(file_path)
    return extractor.extract()


if __name__ == "__main__":
    # Test d'extraction
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        extractor = ExcelExtractor(file_path)
        df = extractor.extract()
        
        print("\n📊 Informations sur le schéma:")
        print(extractor.get_schema_info())
        
        print("\n📈 Rapport de qualité:")
        print(extractor.get_data_quality_report())
