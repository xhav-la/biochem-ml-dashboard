# -*- coding: utf-8 -*-
"""
data_loader.py
===============
Ngarkon dataset-in real CSV (encoding CP1251, ndarës ';', decimal ',')
dhe e pastron: konverton vlerat në numra, trajton vlera "të egra"
(>75,000 / <0,3 / tekst si "da se povt"), grumbullon rreshtat për
pacient (disa pacientë kanë >1 vizitë laboratorike -> mesatare).
"""
import re
import pandas as pd
import numpy as np
from . import config


def _parse_numeric_cell(val):
    """
    Konverton një qelizë 'të egër' në float ose NaN.
    Trajton:
      - presje si decimal: '105,10' -> 105.10
      - operatorë krahasimi: '>75,000' -> 75.0 ; '<0,3' -> 0.3
      - tekst pa kuptim numerik: 'da se povt', 'ne don]vol' -> NaN
      - njësi ngjitur gabimisht: '23,00 KS d' -> 23.0
    """
    if pd.isna(val):
        return np.nan
    s = str(val).strip()
    if s == "" or s == ".":
        return np.nan
    s = s.replace(",", ".")
    # gjej numrin e parë valid (me shenjë opsionale, pika dhjetore opsionale)
    m = re.search(r"-?\d+(\.\d+)?", s)
    if not m:
        return np.nan
    try:
        return float(m.group(0))
    except ValueError:
        return np.nan


def load_raw(csv_path=None):
    """Lexon CSV-në origjinale me encoding-un e saktë (CP1251)."""
    csv_path = csv_path or config.PATHS["raw_csv"]
    df = pd.read_csv(
        csv_path,
        sep=";",
        encoding="cp1251",
        header=0,
        names=config.RAW_COLUMN_NAMES,
        na_values=["", " "],
        low_memory=False,
    )
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Pastron të gjitha kolonat biokimike (numerike) dhe kthen DataFrame të pastër."""
    df = df.copy()
    numeric_cols = [c for c in config.RAW_COLUMN_NAMES if c not in
                    ("PATIENT_ID", "GOD1", "IST", "ISTORGOD")]
    for c in numeric_cols:
        df[c] = df[c].apply(_parse_numeric_cell)

    # largo rreshta krejtësisht bosh (pa asnjë analizë)
    df = df.dropna(subset=numeric_cols, how="all")
    return df


def aggregate_per_patient(df: pd.DataFrame) -> pd.DataFrame:
    """
    Disa pacientë kanë disa rreshta (vizita të ndryshme laboratorike).
    I grumbullojmë me MESATARE (mean) për të pasur 1 rresht = 1 pacient,
    që të kemi profil biokimik sa më të plotë (kombinon analiza nga vizita
    të ndryshme të të njëjtit person).
    """
    numeric_cols = [c for c in config.RAW_COLUMN_NAMES if c not in
                    ("PATIENT_ID", "GOD1", "IST", "ISTORGOD")]
    agg = df.groupby("PATIENT_ID")[numeric_cols].mean().reset_index()
    # sa herë ka bërë analiza pacienti (info shtesë)
    visits = df.groupby("PATIENT_ID").size().rename("N_VIZITA")
    agg = agg.merge(visits, on="PATIENT_ID", how="left")
    return agg


def load_and_prepare(csv_path=None, min_core_fields=2):
    """
    Pipeline i plotë: ngarkon, pastron, grumbullon për pacient.
    `min_core_fields`: pacienti duhet të ketë të paktën kaq analiza nga
    lista CORE_BIOCHEM_COLS për t'u konsideruar 'i përdorshëm' për
    parashikimet klinike (përndryshe nuk ka mjaftueshëm informacion).
    """
    raw = load_raw(csv_path)
    cleaned = clean(raw)
    per_patient = aggregate_per_patient(cleaned)

    core_present = per_patient[config.CORE_BIOCHEM_COLS].notna().sum(axis=1)
    per_patient["N_CORE_TESTE_TE_PRANISHME"] = core_present
    usable = per_patient[core_present >= min_core_fields].reset_index(drop=True)

    return per_patient, usable


if __name__ == "__main__":
    all_patients, usable_patients = load_and_prepare()
    print(f"Gjithsej pacientë (të grumbulluar): {len(all_patients)}")
    print(f"Pacientë 'të përdorshëm' (>=2 analiza core): {len(usable_patients)}")
    print(usable_patients.head())
