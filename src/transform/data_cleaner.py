"""Module de nettoyage et transformation des données SMI."""

import logging
import re
from typing import Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class SMIDataCleaner:
    """Classe pour nettoyer et transformer les données SMI."""

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.original_row_count = len(df)
        logger.info(f"Initialisation du nettoyage : {self.original_row_count} lignes")

    # ------------------------------------------------------------------
    # 1. Nettoyage des noms de colonnes (avec unicité garantie)
    # ------------------------------------------------------------------
    def clean_column_names(self) -> "SMIDataCleaner":
        logger.info("Nettoyage des noms de colonnes")

        def normalize(name: str) -> str:
            name = re.sub(r"\s+", " ", name.strip().lower())
            name = name.replace("-", "_")

            replacements = {
                "décès maternels par cause de complication obstétricale": "deces_mat_",
                "nouveau-nes decedes de": "deces_neo_",
                "smi-": "smi_",
            }
            for old, new in replacements.items():
                name = name.replace(old, new)

            accents = {
                "é": "e", "è": "e", "ê": "e", "ë": "e",
                "à": "a", "â": "a", "ä": "a",
                "î": "i", "ï": "i",
                "ô": "o", "ö": "o",
                "ù": "u", "û": "u", "ü": "u",
                "ç": "c",
            }
            for a, b in accents.items():
                name = name.replace(a, b)

            name = re.sub(r"[^\w_]", "_", name)
            name = re.sub(r"_+", "_", name).strip("_")
            return name

        normalized = [normalize(c) for c in self.df.columns]

        # Garantir unicité des noms de colonnes
        seen = {}
        unique_cols = []
        for col in normalized:
            if col not in seen:
                seen[col] = 0
                unique_cols.append(col)
            else:
                seen[col] += 1
                unique_cols.append(f"{col}_{seen[col]}")

        self.df.columns = unique_cols
        return self

    # ------------------------------------------------------------------
    # 2. Valeurs manquantes (sans FutureWarning Pandas 2.x)
    # ------------------------------------------------------------------
    def handle_missing_values(self) -> "SMIDataCleaner":
        logger.info("Traitement des valeurs manquantes")

        counter_cols = [c for c in self.df.columns if "deces" in c or "nombre" in c]
        for c in counter_cols:
            if c in self.df.columns:
                self.df[c] = pd.to_numeric(self.df[c], errors="coerce").fillna(0)

        self.df = self.df.infer_objects(copy=False)

        geo_cols = [
            "pays", "region", "province", "district_sanitaire",
            "commune", "formation_sanitaire",
        ]
        geo_present = [c for c in geo_cols if c in self.df.columns]

        before = len(self.df)
        if geo_present:
            self.df = self.df.dropna(subset=geo_present, how="any")
        after = len(self.df)

        if before != after:
            logger.warning(f"{before - after} lignes supprimées (géographie manquante)")

        return self

    # ------------------------------------------------------------------
    # 3. Parsing des périodes
    # ------------------------------------------------------------------
    def parse_period(self) -> "SMIDataCleaner":
        logger.info("Parsing de la période")

        if "periode" not in self.df.columns:
            logger.warning("Colonne 'periode' absente")
            return self

        mois = {
            "janvier": "January", "février": "February", "fevrier": "February",
            "mars": "March", "avril": "April", "mai": "May",
            "juin": "June", "juillet": "July", "août": "August", "aout": "August",
            "septembre": "September", "octobre": "October",
            "novembre": "November", "décembre": "December", "decembre": "December",
        }

        def parse(val: Any) -> Optional[pd.Timestamp]:
            if pd.isna(val):
                return pd.NaT
            v = str(val).strip().lower()
            for fr, en in mois.items():
                v = v.replace(fr, en.lower())
            return pd.to_datetime(v, errors="coerce", format="%B %Y")

        self.df["periode_date"] = self.df["periode"].apply(parse)
        self.df["annee"] = self.df["periode_date"].dt.year
        self.df["mois"] = self.df["periode_date"].dt.month
        self.df["trimestre"] = self.df["periode_date"].dt.quarter
        self.df["semestre"] = self.df["mois"].apply(
            lambda m: 1 if m <= 6 else 2 if pd.notna(m) else pd.NA
        )

        return self

    # ------------------------------------------------------------------
    # 4. Normalisation géographique + geo_id
    # ------------------------------------------------------------------
    def normalize_geography(self) -> "SMIDataCleaner":
        logger.info("Normalisation géographique")

        geo_cols = [
            "pays", "region", "province", "district_sanitaire",
            "commune", "formation_sanitaire",
        ]
        present = [c for c in geo_cols if c in self.df.columns]

        for c in present:
            self.df[c] = self.df[c].astype(str).str.strip().str.replace(r"\s+", " ", regex=True).str.title()

        if present:
            self.df["geo_id"] = self.df[present].astype(str).agg("_".join, axis=1).str.replace(" ", "_").str.lower()

        return self

    # ------------------------------------------------------------------
    # 5. Métriques dérivées
    # ------------------------------------------------------------------
    def calculate_derived_metrics(self) -> "SMIDataCleaner":
        logger.info("Calcul des métriques dérivées")

        mat_cols = [c for c in self.df.columns if c.startswith("deces_mat_") and c != "deces_mat_total"]
        if mat_cols:
            self.df["total_deces_maternels_calcule"] = self.df[mat_cols].sum(axis=1)

        if {"deces_neo_0_6_jours", "deces_neo_7_28_jours"}.issubset(self.df.columns):
            self.df["total_deces_neonatals"] = (
                self.df["deces_neo_0_6_jours"] + self.df["deces_neo_7_28_jours"]
            )

        return self

    # ------------------------------------------------------------------
    # 6. Validation
    # ------------------------------------------------------------------
    def validate_data(self) -> dict:
        numeric_cols = self.df.select_dtypes(include="number")
        negative_values = {col: int((numeric_cols[col] < 0).sum()) for col in numeric_cols.columns}

        return {
            "original_rows": self.original_row_count,
            "final_rows": len(self.df),
            "rows_removed": self.original_row_count - len(self.df),
            "columns": len(self.df.columns),
            "duplicates": int(self.df.duplicated().sum()),
            "missing_values_pct": (self.df.isna().mean() * 100).to_dict(),
            "negative_values": negative_values,
        }

    # ------------------------------------------------------------------
    def get_cleaned_data(self) -> pd.DataFrame:
        return self.df.copy()

    def clean_pipeline(self) -> "SMIDataCleaner":
        return (
            self.clean_column_names()
            .handle_missing_values()
            .parse_period()
            .normalize_geography()
            .calculate_derived_metrics()
        )


def clean_smi_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    cleaner = SMIDataCleaner(df).clean_pipeline()
    return cleaner.get_cleaned_data(), cleaner.validate_data()
