# -*- coding: utf-8 -*-
"""
config.py
=========
Konfigurimi qendror: emrat e kolonave, njësitë, dhe PRAGJET KLINIKE
(clinical thresholds) të përdorura për të gjeneruar etiketat (labels)
për sindromën metabolike, diabetin, hipertensionin dhe profilin lipidik.

KUJDES MJEKËSOR: Pragjet janë të bazuara në udhëzime ndërkombëtare të
njohura (NCEP ATP III për sindromën metabolike, ADA për diabetin, ESC/ESH
për hipertension/lipide). Ky program ka qëllim edukativo-kërkimor dhe
NUK zëvendëson vlerësimin e mjekut.
"""

# ---------------------------------------------------------------
# Emrat origjinal (CP1251, kirilike/koduar keq) -> emra standard
# ---------------------------------------------------------------
RAW_COLUMN_NAMES = [
    "PATIENT_ID", "GOD1", "IST", "ISTORGOD",
    "HEMOGLOBIN", "HEMATOKRIT", "TROMBOCITI", "ALBUMINI",
    "TOTALNI_PROTEINI", "CRP", "AMILAZA", "NA", "MG", "FE",
    "HOLESTEROL", "LDL", "HDL", "TRIGLICERIDI", "GLIKEMIA", "HBA1C",
    "T3", "FT3", "TSH", "FT4", "VITAMIN_D", "T4", "VITAMIN_B12", "FERRITIN",
]

# Kolonat "kryesore" biokimike që përdoren për parashikimet klinike
# (të tjerat përdoren vetëm si tipare shtesë nëse janë të pranishme)
CORE_BIOCHEM_COLS = [
    "GLIKEMIA", "HBA1C", "HOLESTEROL", "LDL", "HDL", "TRIGLICERIDI",
    "HEMOGLOBIN", "HEMATOKRIT", "TROMBOCITI", "CRP",
]

# Njësitë supozohen: Glikemia/Holesterol/LDL/HDL/Trigliceridet në mmol/L
# (standard në Ballkan/Evropë). Nëse dataseti yt real i ka në mg/dL,
# ndrysho FLAG-un këtu dhe faktorët e konvertimit do aplikohen automatikisht.
UNITS_ARE_MMOL_L = True

MGDL_TO_MMOL = {
    "GLIKEMIA": 18.0,      # glukozë: mmol/L = mg/dL / 18
    "HOLESTEROL": 38.67,
    "LDL": 38.67,
    "HDL": 38.67,
    "TRIGLICERIDI": 88.57,
}

# ---------------------------------------------------------------
# PRAGJET KLINIKE (në mmol/L, siç janë të dhënat origjinale)
# ---------------------------------------------------------------
THRESHOLDS = {
    # Sindroma Metabolike (bazuar në NCEP ATP III, pa presion/bel real
    # -> përdorim BMI si proxy për obezitetin abdominal, shënuar qartë)
    "TRIGLICERIDI_HIGH": 1.7,        # mmol/L
    "HDL_LOW_MALE": 1.0,             # mmol/L
    "HDL_LOW_FEMALE": 1.3,           # mmol/L
    "GLIKEMIA_IMPAIRED": 5.6,        # mmol/L (glukozë agjërimi e ngritur)
    "BMI_OBESE_PROXY": 30.0,         # proxy për perimetrin e belit
    "BP_SYSTOLIC_HIGH": 130,
    "BP_DIASTOLIC_HIGH": 85,

    # Diabeti (kriteret diagnostike ADA)
    "GLIKEMIA_DIABETES": 7.0,        # mmol/L agjërimi -> diabet
    "GLIKEMIA_PREDIABETES": 5.6,     # 5.6-6.9 -> prediabet
    "HBA1C_DIABETES": 6.5,           # %
    "HBA1C_PREDIABETES": 5.7,        # %

    # Hipertension (ESC/ESH) - kërkon presion (real ose sintetik)
    "HTN_SYSTOLIC": 140,
    "HTN_DIASTOLIC": 90,
    "PREHTN_SYSTOLIC": 130,
    "PREHTN_DIASTOLIC": 85,

    # Profili lipidik i lartë
    "CHOLESTEROL_HIGH": 5.2,         # mmol/L
    "LDL_HIGH": 3.4,                 # mmol/L
    "LDL_VERY_HIGH": 4.9,

    # BMI kategori (OBSH)
    "BMI_UNDERWEIGHT": 18.5,
    "BMI_NORMAL": 25.0,
    "BMI_OVERWEIGHT": 30.0,
}

# Vlera minimale referencash normale (për raportim në PDF)
REFERENCE_RANGES = {
    "HEMOGLOBIN": ("120-160 g/L (F) / 130-170 g/L (M)"),
    "HEMATOKRIT": ("0.36-0.46 (F) / 0.40-0.50 (M)"),
    "TROMBOCITI": ("150-400 x10^9/L"),
    "GLIKEMIA": ("3.9-5.6 mmol/L (agjërim)"),
    "HBA1C": ("< 5.7 %"),
    "HOLESTEROL": ("< 5.2 mmol/L"),
    "LDL": ("< 3.0 mmol/L (optimale)"),
    "HDL": ("> 1.0 (M) / > 1.3 (F) mmol/L"),
    "TRIGLICERIDI": ("< 1.7 mmol/L"),
    "CRP": ("< 5 mg/L"),
}

RANDOM_SEED = 42

# Rrugë ABSOLUTE, bazuar te vendndodhja e këtij file -- kështu programi punon
# saktë pavarësisht nga cila dosje (main.py, dashboard/, etj.) thirret.
import os
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _p(*parts):
    return os.path.join(_PROJECT_ROOT, *parts)


PATHS = {
    "raw_csv": "/mnt/user-data/uploads/Об_Куманово_Лабораториски_резултати_2024_годиан.csv",
    "clean_parquet": _p("data", "patients_clean.parquet"),
    "synthetic_demo_csv": _p("data", "synthetic_demographics.csv"),
    "labeled_parquet": _p("data", "patients_labeled.parquet"),
    "model_metsyn": _p("models", "model_metabolic_syndrome.pkl"),
    "model_diabetes": _p("models", "model_diabetes_risk.pkl"),
    "model_htn_lipid": _p("models", "model_htn_lipid.pkl"),
    "encoders": _p("models", "encoders.pkl"),
    "reports_dir": _p("reports"),
}
