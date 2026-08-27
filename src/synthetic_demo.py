# -*- coding: utf-8 -*-
"""
synthetic_demo.py
===================
!!! KUJDES !!!
Dataseti origjinal NUK përmban të dhëna demografike (moshë, gjini,
nacionalitet) as antropometrike (peshë, gjatësi). Ky modul GJENERON
të dhëna SINTETIKE (fiktive, statistikisht të arsyeshme) VETËM për
qëllime PROTOTIPI/DEMONSTRIMI të programit.

KUR TË KESH TË DHËNAT REALE: zëvendëso këtë modul me një funksion
që lexon një dataset të dytë real (p.sh. Excel me PATIENT_ID, MOSHA,
GJINIA, NACIONALITETI, PESHA_KG, GJATESIA_CM) dhe bashkon (merge) me
PATIENT_ID -- struktura e pjesës tjetër të programit NUK ndryshon.

Gjenerimi është DETERMINISTIK (i lidhur me seed = PATIENT_ID), pra
rifreskimi jep gjithmonë të njëjtat vlera për të njëjtin pacient.
"""
import numpy as np
import pandas as pd
from . import config

NATIONALITIES = ["Maqedonas", "Shqiptar", "Turk", "Rom", "Serb", "Tjetër"]
# shpërndarje afërsisht reflektuese e rajonit të Kumanovës (VETËM SUPOZIM
# për prototip -- zëvendëso me shpërndarjen reale kur ta kesh)
NATIONALITY_WEIGHTS = [0.45, 0.35, 0.05, 0.07, 0.05, 0.03]


def generate_for_patients(patient_ids, seed=config.RANDOM_SEED):
    """Gjeneron demografi + antropometri sintetike, deterministike për ID."""
    n = len(patient_ids)
    records = []
    for pid in patient_ids:
        rng = np.random.default_rng(seed + int(pid))  # deterministik per pid

        gender = rng.choice(["M", "F"])
        age = int(np.clip(rng.normal(45, 16), 18, 90))
        nationality = rng.choice(NATIONALITIES, p=NATIONALITY_WEIGHTS)

        # gjatësia sipas gjinisë (cm)
        if gender == "M":
            height = rng.normal(176, 7)
            weight = rng.normal(82, 14)
        else:
            height = rng.normal(163, 6)
            weight = rng.normal(70, 13)
        height = float(np.clip(height, 145, 205))
        weight = float(np.clip(weight, 40, 160))

        # presioni sintetik (nevojitet për hipertension, s'ekziston real)
        sys_bp = float(np.clip(rng.normal(125, 15) + (age - 45) * 0.3, 90, 200))
        dia_bp = float(np.clip(rng.normal(80, 10) + (age - 45) * 0.15, 55, 120))

        records.append({
            "PATIENT_ID": pid,
            "MOSHA": age,
            "GJINIA": gender,
            "NACIONALITETI": nationality,
            "PESHA_KG": round(weight, 1),
            "GJATESIA_CM": round(height, 1),
            "TENSION_SISTOLIK": round(sys_bp, 0),
            "TENSION_DIASTOLIK": round(dia_bp, 0),
        })
    demo = pd.DataFrame(records)
    demo["BMI"] = (demo["PESHA_KG"] / ((demo["GJATESIA_CM"] / 100) ** 2)).round(1)
    return demo


def bmi_category(bmi):
    t = config.THRESHOLDS
    if bmi < t["BMI_UNDERWEIGHT"]:
        return "Nën peshë"
    elif bmi < t["BMI_NORMAL"]:
        return "Normale"
    elif bmi < t["BMI_OVERWEIGHT"]:
        return "Mbipeshë"
    else:
        return "Obezitet"


if __name__ == "__main__":
    demo = generate_for_patients([1, 2, 3, 4, 5])
    print(demo)
