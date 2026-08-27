# -*- coding: utf-8 -*-
"""
page_patient.py
==================
Faqja 'Profili i Pacientit': kërkim sipas ID, shfaqje interaktive e
parashikimeve (gauge charts), planit ushqimor, dhe shkarkim i PDF-së
së gjeneruar LIVE (jo e para-krijuar).
"""
import os
import tempfile
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from src import config, diet_plan, generate_pdf, train_models
from data_service import get_full_dataset, get_models

GAUGE_COLOR = {
    "Low": "#2e7d32", "Normal": "#2e7d32",
    "Medium": "#f9a825", "Kufitar": "#f9a825",
    "Kufitar (pre-hipertension)": "#f9a825", "Prediabet": "#f9a825",
    "High": "#c62828", "I lartë": "#c62828", "Diabetik": "#c62828",
}
ORDER_3 = {"Low": 33, "Medium": 66, "High": 100,
           "Normal": 20, "Kufitar": 60, "Kufitar (pre-hipertension)": 60,
           "I lartë": 95, "Prediabet": 60, "Diabetik": 95}


def _gauge(title, category, subtitle=""):
    val = ORDER_3.get(category, 50)
    color = GAUGE_COLOR.get(category, "#616161")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val,
        number={"suffix": "", "font": {"size": 1}},  # amaguar numri, shfaqim tekst poshtë
        title={"text": f"{title}<br><span style='font-size:0.7em'>{category}</span>"},
        gauge={
            "axis": {"range": [0, 100], "visible": False},
            "bar": {"color": color},
            "bgcolor": "#eeeeee",
            "steps": [
                {"range": [0, 40], "color": "#e8f5e9"},
                {"range": [40, 75], "color": "#fff8e1"},
                {"range": [75, 100], "color": "#ffebee"},
            ],
        },
    ))
    fig.update_layout(height=220, margin=dict(t=60, b=10, l=20, r=20))
    return fig


def render():
    st.title("🧑‍⚕️ Profili Individual i Pacientit")
    df = get_full_dataset()
    models, encoders, medians = get_models()

    from src import predict_patient as pp

    col_search, col_gap = st.columns([1, 3])
    with col_search:
        patient_id = st.number_input(
            "Fut ID e Pacientit", min_value=int(df["PATIENT_ID"].min()),
            max_value=int(df["PATIENT_ID"].max()), value=int(df["PATIENT_ID"].iloc[0]), step=1,
        )

    row = df[df["PATIENT_ID"] == patient_id]
    if row.empty:
        st.error("Ky ID pacienti nuk u gjet në dataset.")
        return
    row = row.iloc[0]

    # ---- Rindërto input + merr parashikime TË PLOTA (me probabilitete) ----
    biochem = {c: row.get(c) for c in train_models.FEATURE_COLS if c not in ("MOSHA", "BMI")}
    demo = {
        "MOSHA": int(row["MOSHA"]), "GJINIA": row["GJINIA"],
        "NACIONALITETI": row["NACIONALITETI"], "PESHA_KG": row["PESHA_KG"],
        "GJATESIA_CM": row["GJATESIA_CM"], "BMI": row["BMI"],
    }
    patient_input = {**biochem, "MOSHA": demo["MOSHA"], "GJINIA": demo["GJINIA"], "BMI": demo["BMI"]}
    predictions = pp.predict_patient(patient_input, models, encoders, medians)
    diet = diet_plan.build_diet_plan(demo, predictions)

    st.markdown("---")

    # ---- Demografi/Antropometri ----
    st.subheader("Demografia & Antropometria")
    d1, d2, d3, d4, d5, d6 = st.columns(6)
    d1.metric("Mosha", demo["MOSHA"])
    d2.metric("Gjinia", demo["GJINIA"])
    d3.metric("Nacionaliteti", demo["NACIONALITETI"])
    d4.metric("Pesha", f"{demo['PESHA_KG']} kg")
    d5.metric("Gjatësia", f"{demo['GJATESIA_CM']} cm")
    d6.metric("BMI", demo["BMI"])
    st.caption("⚠️ Demografia/antropometria janë sintetike (shih README).")

    st.markdown("---")

    # ---- Parametrat biokimikë ----
    st.subheader("Parametrat Biokimikë")
    bio_display = []
    for key, label in [
        ("HEMOGLOBIN", "Hemoglobina"), ("HEMATOKRIT", "Hematokriti"),
        ("TROMBOCITI", "Trombocitet"), ("GLIKEMIA", "Glikemia (mmol/L)"),
        ("HBA1C", "HbA1c (%)"), ("HOLESTEROL", "Kolesteroli Total (mmol/L)"),
        ("LDL", "LDL (mmol/L)"), ("HDL", "HDL (mmol/L)"),
        ("TRIGLICERIDI", "Trigliceridet (mmol/L)"), ("CRP", "CRP (mg/L)"),
    ]:
        val = biochem.get(key)
        val_str = f"{val:.2f}" if pd.notna(val) else "N/A (mungon)"
        bio_display.append({"Analiza": label, "Vlera": val_str,
                             "Referenca": config.REFERENCE_RANGES.get(key, "-")})
    st.dataframe(pd.DataFrame(bio_display), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ---- Parashikimet (gauge charts) ----
    st.subheader("Parashikimet e Modeleve ML")
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.plotly_chart(_gauge("Sindroma Metabolike", predictions["sindroma_metabolike"]["kategoria"]),
                         use_container_width=True)
    with g2:
        dia = predictions["rreziku_diabetit"]
        st.plotly_chart(_gauge("Rreziku i Diabetit", dia["kategoria"],
                                subtitle=f"{dia['afersia_perqindje']}%"), use_container_width=True)
        st.markdown(f"<p style='text-align:center'><b>Afërsia me diabetin: {dia['afersia_perqindje']}%</b></p>",
                    unsafe_allow_html=True)
    with g3:
        st.plotly_chart(_gauge("Hipertensioni", predictions["hipertension"]["kategoria"]),
                         use_container_width=True)
    with g4:
        st.plotly_chart(_gauge("Profili Lipidik", predictions["profili_lipidik"]["kategoria"]),
                         use_container_width=True)

    with st.expander("Shiko probabilitetet e plota për secilin model"):
        for key, title in [("sindroma_metabolike", "Sindroma Metabolike"),
                            ("rreziku_diabetit", "Rreziku i Diabetit"),
                            ("hipertension", "Hipertensioni"),
                            ("profili_lipidik", "Profili Lipidik")]:
            probs = predictions[key]["probabilitetet"]
            st.write(f"**{title}**:", {k: f"{v*100:.1f}%" for k, v in probs.items()})

    st.markdown("---")

    # ---- Plani Ushqimor ----
    st.subheader("🍽️ Plani Ushqimor i Personalizuar")
    c1, c2 = st.columns(2)
    c1.metric("Kalori Bazale (BMR)", f"{diet['kalori_bazale_bmr']} kcal/ditë")
    c2.metric("Kalori Ditore të Synuara", f"{diet['kalori_ditore_te_synuara']} kcal/ditë")

    ms = diet["ndarja_makronutrienteve"]
    macro_fig = go.Figure(go.Pie(
        labels=["Proteina", "Yndyra", "Karbohidrate"],
        values=[ms["proteina_%"], ms["yndyra_%"], ms["karbohidrate_%"]],
        hole=0.5, marker_colors=["#1f4e79", "#e07b39", "#2e7d32"],
    ))
    macro_fig.update_layout(height=280, margin=dict(t=10), title="Ndarja e Makronutrientëve")
    st.plotly_chart(macro_fig, use_container_width=True)

    colr, colk = st.columns(2)
    with colr:
        st.markdown("**Rekomandime:**")
        for r in diet["rekomandime"]:
            st.markdown(f"- {r}")
    with colk:
        st.markdown("**Kufizime:**")
        for r in diet["kufizime"]:
            st.markdown(f"- {r}")
    if diet["shenime"]:
        st.info("  \n".join(diet["shenime"]))

    st.markdown("---")

    # ---- Shkarko PDF LIVE ----
    if st.button("📄 Gjenero & Shkarko Raportin PDF", type="primary"):
        with st.spinner("Duke gjeneruar PDF-në..."):
            tmp_path = os.path.join(tempfile.gettempdir(), f"raport_pacienti_{patient_id}.pdf")
            generate_pdf.build_patient_pdf(tmp_path, patient_id, biochem, demo, predictions, diet)
            with open(tmp_path, "rb") as f:
                pdf_bytes = f.read()
        st.success("Raporti u gjenerua!")
        st.download_button("⬇️ Shkarko PDF", data=pdf_bytes,
                            file_name=f"raport_pacienti_{patient_id}.pdf", mime="application/pdf")
