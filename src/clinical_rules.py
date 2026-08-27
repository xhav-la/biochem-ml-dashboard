# -*- coding: utf-8 -*-
"""
clinical_rules.py
===================
Gjeneron ETIKETAT (labels) klinike bazuar në kritere të njohura mjekësore,
mbi bazën e të cilave trajnohen modelet ML. Kjo është "e vërteta bazë"
(ground truth) e nevojshme sepse dataset-i nuk vjen me diagnoza gati.
"""
import numpy as np
import pandas as pd
from . import config

T = config.THRESHOLDS


def metabolic_syndrome_score(row):
    """
    Bazuar në NCEP ATP III (thjeshtuar). Kriteret e vlerësuara:
      1. Trigliceridet >= 1.7 mmol/L
      2. HDL i ulët (gjinie-specifik)
      3. Glikemia agjërimi >= 5.6 mmol/L
      4. BMI >= 30 (proxy për obezitet abdominal -- REAL do ishte belin)
      5. Tensioni >= 130/85

    Kthen (n_kritere_pozitive, n_kritere_te_vleresueshme, kategori).
    Nëse <2 kritere janë të vlerësueshme (mungon shumica e të dhënave),
    kthehet kategori 'Të pamjaftueshme të dhëna'.
    """
    hits, evaluable = 0, 0

    if pd.notna(row.get("TRIGLICERIDI")):
        evaluable += 1
        if row["TRIGLICERIDI"] >= T["TRIGLICERIDI_HIGH"]:
            hits += 1

    if pd.notna(row.get("HDL")) and pd.notna(row.get("GJINIA")):
        evaluable += 1
        limit = T["HDL_LOW_MALE"] if row["GJINIA"] == "M" else T["HDL_LOW_FEMALE"]
        if row["HDL"] < limit:
            hits += 1

    if pd.notna(row.get("GLIKEMIA")):
        evaluable += 1
        if row["GLIKEMIA"] >= T["GLIKEMIA_IMPAIRED"]:
            hits += 1

    if pd.notna(row.get("BMI")):
        evaluable += 1
        if row["BMI"] >= T["BMI_OBESE_PROXY"]:
            hits += 1

    if pd.notna(row.get("TENSION_SISTOLIK")) and pd.notna(row.get("TENSION_DIASTOLIK")):
        evaluable += 1
        if (row["TENSION_SISTOLIK"] >= T["BP_SYSTOLIC_HIGH"] or
                row["TENSION_DIASTOLIK"] >= T["BP_DIASTOLIC_HIGH"]):
            hits += 1

    if evaluable < 2:
        category = "Të pamjaftueshme të dhëna"
    elif hits >= 3:
        category = "High"
    elif hits >= 1:
        category = "Medium"
    else:
        category = "Low"

    return hits, evaluable, category


def diabetes_status(row):
    """
    Sipas kritereve ADA (glukozë agjërimi ose HbA1c):
      - Diabetik: glikemia >= 7.0 mmol/L OSE HbA1c >= 6.5%
      - Prediabet: glikemia 5.6-6.9 OSE HbA1c 5.7-6.4%
      - Normal: nën këto vlera
      - E panjohur: nuk ka asnjë nga të dyja të matura
    """
    glu, hba1c = row.get("GLIKEMIA"), row.get("HBA1C")

    if pd.notna(glu):
        if glu >= T["GLIKEMIA_DIABETES"]:
            return "Diabetik"
        elif glu >= T["GLIKEMIA_PREDIABETES"]:
            return "Prediabet"
        else:
            if pd.isna(hba1c):
                return "Normal"

    if pd.notna(hba1c):
        if hba1c >= T["HBA1C_DIABETES"]:
            return "Diabetik"
        elif hba1c >= T["HBA1C_PREDIABETES"]:
            return "Prediabet"
        else:
            return "Normal"

    if pd.notna(glu):
        return "Normal"

    return "E panjohur"


def htn_lipid_risk(row):
    """
    Tension i lartë (nga sintetik ose real nëse ekziston) + profil lipidik.
    Kthen dict me flamuj të veçantë + kategori përmbledhëse.
    """
    flags = {}

    sys_bp, dia_bp = row.get("TENSION_SISTOLIK"), row.get("TENSION_DIASTOLIK")
    if pd.notna(sys_bp) and pd.notna(dia_bp):
        if sys_bp >= T["HTN_SYSTOLIC"] or dia_bp >= T["HTN_DIASTOLIC"]:
            flags["hipertension"] = "I lartë"
        elif sys_bp >= T["PREHTN_SYSTOLIC"] or dia_bp >= T["PREHTN_DIASTOLIC"]:
            flags["hipertension"] = "Kufitar (pre-hipertension)"
        else:
            flags["hipertension"] = "Normal"
    else:
        flags["hipertension"] = "Nuk ka të dhëna"

    chol, ldl = row.get("HOLESTEROL"), row.get("LDL")
    trig = row.get("TRIGLICERIDI")
    lipid_hits, lipid_eval = 0, 0
    if pd.notna(chol):
        lipid_eval += 1
        if chol >= T["CHOLESTEROL_HIGH"]:
            lipid_hits += 1
    if pd.notna(ldl):
        lipid_eval += 1
        if ldl >= T["LDL_HIGH"]:
            lipid_hits += 1
    if pd.notna(trig):
        lipid_eval += 1
        if trig >= T["TRIGLICERIDI_HIGH"]:
            lipid_hits += 1

    if lipid_eval == 0:
        flags["profili_lipidik"] = "Nuk ka të dhëna"
    elif lipid_hits >= 2:
        flags["profili_lipidik"] = "I lartë"
    elif lipid_hits == 1:
        flags["profili_lipidik"] = "Kufitar"
    else:
        flags["profili_lipidik"] = "Normal"

    return flags


def add_all_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Shton kolonat e etiketave në DataFrame (përdoret para trajnimit)."""
    df = df.copy()

    ms_results = df.apply(metabolic_syndrome_score, axis=1)
    df["MS_HITS"] = ms_results.apply(lambda x: x[0])
    df["MS_EVALUABLE"] = ms_results.apply(lambda x: x[1])
    df["METABOLIC_SYNDROME"] = ms_results.apply(lambda x: x[2])

    df["DIABETES_STATUS"] = df.apply(diabetes_status, axis=1)

    htn_results = df.apply(htn_lipid_risk, axis=1)
    df["HIPERTENSION"] = htn_results.apply(lambda x: x["hipertension"])
    df["PROFILI_LIPIDIK"] = htn_results.apply(lambda x: x["profili_lipidik"])

    return df
