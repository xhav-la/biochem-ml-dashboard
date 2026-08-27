# -*- coding: utf-8 -*-
"""
diet_plan.py
==============
Krijon një plan ushqimor bazë, të personalizuar, duke përdorur:
  - Antropometrinë (peshë, gjatësi, BMI) -> nevojat kalorike (Mifflin-St Jeor)
  - Demografinë (moshë, gjini)
  - Rezultatet e parashikimeve klinike (sindroma metabolike, diabeti,
    hipertensioni, profili lipidik) -> rregullime specifike

KUJDES: Ky është plan i përgjithshëm, edukativ. Për plan real duhet
konsultim me nutricionist/mjek, veçanërisht për pacientë me gjendje
kronike.
"""


def bmr_mifflin(weight_kg, height_cm, age, gender):
    """Basal Metabolic Rate (Mifflin-St Jeor)."""
    if gender == "M":
        return 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        return 10 * weight_kg + 6.25 * height_cm - 5 * age - 161


def daily_calories(weight_kg, height_cm, age, gender, activity_factor=1.375):
    """TDEE = BMR * faktori i aktivitetit (default: aktivitet i lehtë)."""
    bmr = bmr_mifflin(weight_kg, height_cm, age, gender)
    return round(bmr * activity_factor)


def build_diet_plan(patient_demo: dict, predictions: dict):
    """
    `patient_demo`: {MOSHA, GJINIA, PESHA_KG, GJATESIA_CM, BMI}
    `predictions`: output nga predict_patient.predict_patient()
    """
    weight = patient_demo["PESHA_KG"]
    height = patient_demo["GJATESIA_CM"]
    age = patient_demo["MOSHA"]
    gender = patient_demo["GJINIA"]
    bmi = patient_demo["BMI"]

    tdee = daily_calories(weight, height, age, gender)
    target_calories = tdee
    notes = []
    restrictions = []
    recommendations = []

    # --- Rregullim sipas BMI ---
    if bmi >= 30:
        target_calories = round(tdee * 0.80)  # deficit ~20% për humbje peshe
        notes.append("BMI tregon obezitet -> synohet deficit kalorik i moderuar (~20%).")
    elif bmi >= 25:
        target_calories = round(tdee * 0.90)
        notes.append("BMI tregon mbipeshë -> deficit i lehtë kalorik (~10%).")
    elif bmi < 18.5:
        target_calories = round(tdee * 1.10)
        notes.append("BMI tregon nën peshë -> mbingarkesë e lehtë kalorike (~10%).")

    # --- Rregullime sipas rezultateve klinike ---
    diab_cat = predictions.get("rreziku_diabetit", {}).get("kategoria")
    if diab_cat in ("Prediabet", "Diabetik"):
        restrictions.append("Kufizo sheqerin e thjeshtë, ëmbëlsirat, lëngjet me sheqer.")
        recommendations.append("Prefero karbohidrate me indeks të ulët glicemik (perime, drithëra "
                                "të plota, bishtajore) të ndara në 4-5 vakte të vogla.")
        if diab_cat == "Diabetik":
            notes.append("Kategoria 'Diabetik' -> KËSHILLOHET domosdoshmërisht konsultim me endokrinolog "
                          "përpara ndryshimit të dietës.")

    lipid_cat = predictions.get("profili_lipidik", {}).get("kategoria")
    if lipid_cat in ("Kufitar", "I lartë"):
        restrictions.append("Kufizo yndyrat e ngopura (mish i kuq i yndyrshëm, produkte të plota "
                             "qumështi, ushqime të skuqura).")
        recommendations.append("Rrit peshkun e yndyrshëm (omega-3), vajin e ullirit, arrat, fibrat "
                                "e tretshme (tërshërë, fasule).")

    htn_cat = predictions.get("hipertension", {}).get("kategoria")
    if htn_cat in ("Kufitar (pre-hipertension)", "I lartë"):
        restrictions.append("Kufizo kripën (natriumin) < 5g/ditë; shmang ushqimet e konservuara/"
                             "përpunuara.")
        recommendations.append("Dietë tip DASH: shumë perime, fruta, drithëra të plota, produkte "
                                "të qumështit me pak yndyrë, pak mish i kuq.")

    ms_cat = predictions.get("sindroma_metabolike", {}).get("kategoria")
    if ms_cat == "High":
        recommendations.append("Rrit aktivitetin fizik në të paktën 150 min/javë (ecje e shpejtë, "
                                "not, çiklizëm) përveç ndryshimeve ushqimore.")

    if not restrictions:
        restrictions.append("Nuk ka kufizime specifike urgjente -- ruaj dietë të balancuar.")
    if not recommendations:
        recommendations.append("Vazhdo me dietë të larmishme, e pasur me perime, fruta dhe proteina "
                                "me cilësi të lartë.")

    macro_split = {"proteina_%": 25, "yndyra_%": 30, "karbohidrate_%": 45}
    if diab_cat in ("Prediabet", "Diabetik"):
        macro_split = {"proteina_%": 25, "yndyra_%": 35, "karbohidrate_%": 40}

    return {
        "kalori_bazale_bmr": round(bmr_mifflin(weight, height, age, gender)),
        "kalori_ditore_te_synuara": target_calories,
        "ndarja_makronutrienteve": macro_split,
        "kufizime": restrictions,
        "rekomandime": recommendations,
        "shenime": notes,
    }
