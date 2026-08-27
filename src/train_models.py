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
"""
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
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
    X = df[FEATURE_COLS].copy()
    # imputim i thjeshtë me median (ruajmë mediánat për inferencë konsistente)
    for c in FEATURE_COLS:
        X[c] = X[c].fillna(X[c].median())

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

    clf = RandomForestClassifier(
        n_estimators=200, max_depth=12, min_samples_leaf=5,
        class_weight="balanced", random_state=config.RANDOM_SEED, n_jobs=-1,
    )
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Saktësia (accuracy) mbi test set: {acc:.3f}")
    print(classification_report(y_test, y_pred, target_names=y_enc.classes_))

    joblib.dump(clf, model_path)
    print(f"Modeli u ruajt: {model_path}")

    # feature importance (top 8) - e dobishme për transparencë klinike
    importances = pd.Series(clf.feature_importances_, index=X.columns)
    print("Tiparet më me ndikim:")
    print(importances.sort_values(ascending=False).head(8).round(3))

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
    # ruaj mediánat për imputim konsistent gjatë inferencës
    medians = df[FEATURE_COLS].median()
    joblib.dump(medians, config._p("models", "feature_medians.pkl"))

    print("\n=== Trajnimi përfundoi për të 4 modelet. ===")


if __name__ == "__main__":
    train_all()
