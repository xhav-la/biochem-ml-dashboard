# -*- coding: utf-8 -*-
"""
dashboard/data_service.py
============================
Funksione të përbashkëta për ngarkim & cache të të dhënave/modeleve,
përdoren nga të gjitha faqet e dashboard-it Streamlit.
"""
import os
import sys
import pandas as pd
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src import config, data_loader, synthetic_demo, clinical_rules, predict_patient, diet_plan, generate_pdf

CACHE_PARQUET = os.path.join(ROOT, "data", "patients_full_predicted.parquet")


@st.cache_resource(show_spinner="Duke ngarkuar modelet ML...")
def get_models():
    return predict_patient.load_models()


@st.cache_data(show_spinner="Duke ngarkuar dhe përpunuar dataset-in (30,000+ pacientë)...")
def get_full_dataset():
    """
    Ngarkon dataset-in e plotë me parashikime. Përdor parquet të para-
    llogaritur nëse ekziston (shpejt); përndryshe e rillogarit (ngadalë,
    ~1-2 min herën e parë).
    """
    if os.path.exists(CACHE_PARQUET):
        return pd.read_parquet(CACHE_PARQUET)

    _, usable = data_loader.load_and_prepare()
    demo = synthetic_demo.generate_for_patients(usable["PATIENT_ID"].tolist())
    merged = usable.merge(demo, on="PATIENT_ID", how="left")
    labeled = clinical_rules.add_all_labels(merged)
    models, encoders, medians = get_models()
    full = predict_patient.batch_predict_all(labeled, models, encoders, medians)
    full.to_parquet(CACHE_PARQUET)
    return full


def get_patient_row(patient_id: int):
    df = get_full_dataset()
    row = df[df["PATIENT_ID"] == patient_id]
    if row.empty:
        return None
    return row.iloc[0]


def row_to_predictions_dict(row):
    """Rindërton strukturën 'predictions' (siç e kthen predict_patient.predict_patient)
    nga një rresht i df-së së para-llogaritur, për ripërdorim në PDF/diet_plan."""
    return {
        "sindroma_metabolike": {"kategoria": row["SIND_METABOLIKE_PARASHIKIM"]},
        "rreziku_diabetit": {
            "kategoria": row["DIABET_PARASHIKIM"],
            "afersia_perqindje": row["DIABET_AFERSIA_%"],
        },
        "hipertension": {"kategoria": row["HIPERTENSION_PARASHIKIM"]},
        "profili_lipidik": {"kategoria": row["LIPID_PARASHIKIM"]},
    }
