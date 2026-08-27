# -*- coding: utf-8 -*-
"""
predict_patient.py
=====================
Merr të dhënat e NJË pacienti (biokimi + demografi/antropometri) dhe
kthen parashikimet e të 4 modeleve, duke përdorur modelet e trajnuara
më parë mbi të gjithë datasetin (train_models.py).
"""
import joblib
import numpy as np
import pandas as pd

from . import config
from .train_models import FEATURE_COLS


def load_models():
    models = {
        "metsyn": joblib.load(config.PATHS["model_metsyn"]),
        "diabetes": joblib.load(config.PATHS["model_diabetes"]),
        "htn": joblib.load(config.PATHS["model_htn_lipid"].replace(".pkl", "_htn.pkl")),
        "lipid": joblib.load(config.PATHS["model_htn_lipid"].replace(".pkl", "_lipid.pkl")),
    }
    encoders = joblib.load(config.PATHS["encoders"])
    medians = joblib.load(config._p("models", "feature_medians.pkl"))
    return models, encoders, medians


def _build_feature_vector(patient: dict, encoders, medians, gender_key):
    row = {}
    for c in FEATURE_COLS:
        val = patient.get(c, np.nan)
        if val is None or (isinstance(val, float) and np.isnan(val)):
            val = medians[c]
        row[c] = val
    X = pd.DataFrame([row])[FEATURE_COLS]
    gender_enc = encoders[gender_key]
    X["GJINIA_ENC"] = gender_enc.transform([patient.get("GJINIA", "M")])
    return X


def predict_patient(patient: dict, models=None, encoders=None, medians=None):
    """
    `patient` duhet të ketë çelësat: kolonat biokimike të mundshme nga
    FEATURE_COLS (mund të mungojnë disa -> imputohen automatikisht),
    plus MOSHA, GJINIA ('M'/'F'), BMI.

    Kthen dict me rezultate për të 4 parashikimet.
    """
    if models is None:
        models, encoders, medians = load_models()

    results = {}

    # 1. Sindroma Metabolike
    X = _build_feature_vector(patient, encoders, medians, "gender_metsyn")
    clf = models["metsyn"]
    proba = clf.predict_proba(X)[0]
    labels = encoders["label_metsyn"].classes_
    pred_idx = np.argmax(proba)
    results["sindroma_metabolike"] = {
        "kategoria": labels[pred_idx],
        "probabilitetet": dict(zip(labels, proba.round(3))),
    }

    # 2. Rreziku i Diabetit
    X = _build_feature_vector(patient, encoders, medians, "gender_diabetes")
    clf = models["diabetes"]
    proba = clf.predict_proba(X)[0]
    labels = encoders["label_diabetes"].classes_
    proba_map = dict(zip(labels, proba))
    # "afërsia me diabetin" si % i vetëm: P(Diabetik) + 0.5*P(Prediabet)
    risk_pct = 100 * (proba_map.get("Diabetik", 0) + 0.5 * proba_map.get("Prediabet", 0))
    pred_idx = np.argmax(proba)
    results["rreziku_diabetit"] = {
        "kategoria": labels[pred_idx],
        "afersia_perqindje": round(risk_pct, 1),
        "probabilitetet": {k: round(v, 3) for k, v in proba_map.items()},
    }

    # 3. Hipertensioni
    X = _build_feature_vector(patient, encoders, medians, "gender_hipertension")
    clf = models["htn"]
    proba = clf.predict_proba(X)[0]
    labels = encoders["label_hipertension"].classes_
    pred_idx = np.argmax(proba)
    results["hipertension"] = {
        "kategoria": labels[pred_idx],
        "probabilitetet": dict(zip(labels, proba.round(3))),
    }

    # 4. Profili Lipidik
    X = _build_feature_vector(patient, encoders, medians, "gender_lipid")
    clf = models["lipid"]
    proba = clf.predict_proba(X)[0]
    labels = encoders["label_lipid"].classes_
    pred_idx = np.argmax(proba)
    results["profili_lipidik"] = {
        "kategoria": labels[pred_idx],
        "probabilitetet": dict(zip(labels, proba.round(3))),
    }

    return results


def batch_predict_all(labeled_df, models=None, encoders=None, medians=None):
    """
    Parashikim VEKTORIZUAR (i shpejtë) për TË GJITHË pacientët njëherësh --
    përdoret për eksportin statistikor/hulumtues (CSV/Excel), jo për PDF
    individuale. Kthen DataFrame me kolona shtesë *_PARASHIKIM.
    """
    if models is None:
        models, encoders, medians = load_models()

    df = labeled_df.copy()
    X = df[FEATURE_COLS].copy()
    for c in FEATURE_COLS:
        X[c] = X[c].fillna(medians[c])

    targets = [
        ("metsyn", "metsyn", "SIND_METABOLIKE_PARASHIKIM"),
        ("diabetes", "diabetes", "DIABET_PARASHIKIM"),
        ("htn", "hipertension", "HIPERTENSION_PARASHIKIM"),
        ("lipid", "lipid", "LIPID_PARASHIKIM"),
    ]
    for model_key, encoder_key, out_col in targets:
        Xg = X.copy()
        Xg["GJINIA_ENC"] = encoders[f"gender_{encoder_key}"].transform(df["GJINIA"])
        clf = models[model_key]
        pred = clf.predict(Xg)
        df[out_col] = encoders[f"label_{encoder_key}"].inverse_transform(pred)

        if model_key == "diabetes":
            proba = clf.predict_proba(Xg)
            classes = list(encoders["label_diabetes"].classes_)
            i_diab = classes.index("Diabetik") if "Diabetik" in classes else None
            i_pre = classes.index("Prediabet") if "Prediabet" in classes else None
            risk = np.zeros(len(df))
            if i_diab is not None:
                risk += proba[:, i_diab]
            if i_pre is not None:
                risk += 0.5 * proba[:, i_pre]
            df["DIABET_AFERSIA_%"] = (risk * 100).round(1)

    return df


if __name__ == "__main__":
    sample = {
        "GLIKEMIA": 6.8, "HBA1C": 6.1, "HOLESTEROL": 6.2, "LDL": 4.1,
        "HDL": 0.9, "TRIGLICERIDI": 2.3, "HEMOGLOBIN": 145, "MOSHA": 52,
        "GJINIA": "M", "BMI": 31.2,
    }
    out = predict_patient(sample)
    import json
    print(json.dumps(out, ensure_ascii=False, indent=2))
