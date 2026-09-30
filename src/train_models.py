# -*- coding: utf-8 -*-
"""
train_models.py
==================
Trajnon modelet ML MBI TË GJITHË DATASETIN (batch training), pastaj i
ruan modelet në disk (.pkl). Këto modele më pas përdoren në
predict_patient.py për të bërë parashikime PËR NJË PACIENT TË VETËM.

Modele:
  1. Sindroma Metabolike   -> klasifikim (Low / Medium / High)
  2. Rreziku i Diabetit    -> klasifikim 3-klasësh (Normal/Prediabet/Diabetik)
                              + probabilitet (%) i përdorur si "afërsia" e riskut
  3. Hipertensioni         -> klasifikim (Normal / Kufitar / I lartë)
  4. Profili Lipidik       -> klasifikim (Normal / Kufitar / I lartë)

SHËNIM I RËNDËSISHËM mbi vlerat mungesë: modelet përdorin
`HistGradientBoostingClassifier`, i cili trajton NaN (analiza që
mungojnë) NATYRSHËM -- MOS zëvendësohen me median apo ndonjë vlerë
tjetër statistikore. Modeli mëson vetë, gjatë trajnimit, si të vendosë
kur një analizë e caktuar mungon, bazuar në modelet reale të mungesës
në dataset. Kjo është ndryshe nga qasja e mëparshme (RandomForest +
imputim median), e ndryshuar me kërkesë të qartë: analizat që mungojnë
duhet të MBETEN mungesë, jo të "hamendësohen".
"""
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import LabelEncoder

from . import config
from . import data_loader
from . import synthetic_demo
from . import clinical_rules

FEATURE_COLS = [
    "HEMOGLOBIN", "HEMATOKRIT", "TROMBOCITI", "ALBUMINI", "TOTALNI_PROTEINI",
    "CRP", "NA", "MG", "FE", "HOLESTEROL", "LDL", "HDL", "TRIGLICERIDI",
    "GLIKEMIA", "HBA1C", "TSH", "FT4", "MOSHA", "BMI",
]
CATEGORICAL_COLS = ["GJINIA"]


def build_dataset():
    """Ngarkon, gjeneron demo sintetike, aplikon etiketat klinike."""
    _, usable = data_loader.load_and_prepare()
    demo = synthetic_demo.generate_for_patients(usable["PATIENT_ID"].tolist())
    merged = usable.merge(demo, on="PATIENT_ID", how="left")
    labeled = clinical_rules.add_all_labels(merged)
    return labeled


def _prepare_features(df, gender_encoder=None, fit=False):
    """
    KEQ imputim -- vlerat mungesë (NaN) MBETEN NaN, i kalohen modelit siç
    janë. HistGradientBoostingClassifier i trajton NaN vetë (pa median,
    pa asnjë vlerë "e hamendësuar").
    """
    X = df[FEATURE_COLS].copy()  # NaN mbeten NaN -- QËLLIMISHT, mos i prek

    if fit:
        gender_encoder = LabelEncoder()
        gender_enc = gender_encoder.fit_transform(df["GJINIA"])
    else:
        gender_enc = gender_encoder.transform(df["GJINIA"])
    X["GJINIA_ENC"] = gender_enc
    return X, gender_encoder


def _train_one(df, label_col, exclude_labels, model_path, encoders, name):
    sub = df[~df[label_col].isin(exclude_labels)].copy()
    print(f"\n--- Trajnim: {name} ({len(sub)} pacientë të përdorshëm) ---")

    X, gender_enc = _prepare_features(sub, fit=True)
    encoders[f"gender_{name}"] = gender_enc

    y_enc = LabelEncoder()
    y = y_enc.fit_transform(sub[label_col])
    encoders[f"label_{name}"] = y_enc

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=config.RANDOM_SEED, stratify=y
    )

    clf = HistGradientBoostingClassifier(
        max_iter=300, max_depth=8, learning_rate=0.08,
        class_weight="balanced", random_state=config.RANDOM_SEED,
        early_stopping=True, validation_fraction=0.15, n_iter_no_change=15,
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Saktësia (accuracy) mbi test set: {acc:.3f}")
    print(classification_report(y_test, y_pred, target_names=y_enc.classes_))

    joblib.dump(clf, model_path)
    print(f"Modeli u ruajt: {model_path}")

    return clf


def train_all():
    df = build_dataset()
    df.to_parquet(config.PATHS["labeled_parquet"])

    encoders = {}

    _train_one(
        df, "METABOLIC_SYNDROME",
        exclude_labels=["Të pamjaftueshme të dhëna"],
        model_path=config.PATHS["model_metsyn"],
        encoders=encoders, name="metsyn",
    )

    _train_one(
        df, "DIABETES_STATUS",
        exclude_labels=["E panjohur"],
        model_path=config.PATHS["model_diabetes"],
        encoders=encoders, name="diabetes",
    )

    _train_one(
        df, "HIPERTENSION",
        exclude_labels=["Nuk ka të dhëna"],
        model_path=config.PATHS["model_htn_lipid"].replace(".pkl", "_htn.pkl"),
        encoders=encoders, name="hipertension",
    )

    _train_one(
        df, "PROFILI_LIPIDIK",
        exclude_labels=["Nuk ka të dhëna"],
        model_path=config.PATHS["model_htn_lipid"].replace(".pkl", "_lipid.pkl"),
        encoders=encoders, name="lipid",
    )

    joblib.dump(encoders, config.PATHS["encoders"])
    joblib.dump(FEATURE_COLS, config._p("models", "feature_cols.pkl"))

    print("\n=== Trajnimi përfundoi për të 4 modelet (pa imputim median -- NaN trajtohen nga vetë modeli). ===")


if __name__ == "__main__":
    train_all()
