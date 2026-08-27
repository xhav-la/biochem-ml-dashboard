# -*- coding: utf-8 -*-
"""
page_export.py
================
Faqja 'Eksport Batch': zgjidh disa pacientë (sipas ID, ose kampion i
rastësishëm, ose sipas filtrit të riskut) dhe shkarko një ZIP me
raportet PDF individuale për të gjithë, plus eksport CSV statistikor
për të gjithë popullsinë (për hulumtim).
"""
import io
import os
import zipfile
import tempfile
import streamlit as st
import pandas as pd

from src import train_models, diet_plan, generate_pdf, predict_patient as pp
from data_service import get_full_dataset, get_models


def _generate_pdf_bytes(row, models, encoders, medians):
    biochem = {c: row.get(c) for c in train_models.FEATURE_COLS if c not in ("MOSHA", "BMI")}
    demo = {
        "MOSHA": int(row["MOSHA"]), "GJINIA": row["GJINIA"],
        "NACIONALITETI": row["NACIONALITETI"], "PESHA_KG": row["PESHA_KG"],
        "GJATESIA_CM": row["GJATESIA_CM"], "BMI": row["BMI"],
    }
    patient_input = {**biochem, "MOSHA": demo["MOSHA"], "GJINIA": demo["GJINIA"], "BMI": demo["BMI"]}
    predictions = pp.predict_patient(patient_input, models, encoders, medians)
    diet = diet_plan.build_diet_plan(demo, predictions)

    tmp_path = os.path.join(tempfile.gettempdir(), f"raport_pacienti_{int(row['PATIENT_ID'])}.pdf")
    generate_pdf.build_patient_pdf(tmp_path, int(row["PATIENT_ID"]), biochem, demo, predictions, diet)
    with open(tmp_path, "rb") as f:
        data = f.read()
    os.remove(tmp_path)
    return data


def render():
    st.title("📁 Eksport Batch")
    df = get_full_dataset()
    models, encoders, medians = get_models()

    tab1, tab2 = st.tabs(["📄 Raporte PDF për Disa Pacientë", "📊 Eksport Statistikor (Gjithë Popullsia)"])

    # ---------------- TAB 1: batch PDF ----------------
    with tab1:
        st.write("Zgjidh se si të përzgjedhësh pacientët për të cilët do gjenerohen raporte PDF:")
        mode = st.radio("Mënyra e përzgjedhjes", ["ID specifike", "Kampion i rastësishëm", "Sipas filtrit të riskut"],
                         horizontal=True)

        selected_ids = []
        if mode == "ID specifike":
            ids_text = st.text_input("Fut ID-të, të ndara me presje (p.sh. 1,2,3,135)")
            if ids_text.strip():
                try:
                    selected_ids = [int(x.strip()) for x in ids_text.split(",") if x.strip()]
                except ValueError:
                    st.error("Format i pavlefshëm. Përdor vetëm numra të ndarë me presje.")

        elif mode == "Kampion i rastësishëm":
            n = st.slider("Sa pacientë (kampion i rastësishëm)?", 1, 50, 5)
            if st.button("Rifresko kampionin"):
                st.session_state["sample_ids"] = df.sample(n)["PATIENT_ID"].tolist()
            if "sample_ids" not in st.session_state:
                st.session_state["sample_ids"] = df.sample(n)["PATIENT_ID"].tolist()
            selected_ids = st.session_state["sample_ids"]
            st.write("ID-të e zgjedhura:", selected_ids)

        else:  # Sipas filtrit të riskut
            c1, c2 = st.columns(2)
            with c1:
                risk_field = st.selectbox("Fusha e riskut", [
                    "SIND_METABOLIKE_PARASHIKIM", "DIABET_PARASHIKIM",
                    "HIPERTENSION_PARASHIKIM", "LIPID_PARASHIKIM"])
            with c2:
                risk_value = st.selectbox("Kategoria", sorted(df[risk_field].dropna().unique()))
            max_n = st.slider("Numri maksimal i raporteve", 1, 100, 10)
            matched = df[df[risk_field] == risk_value]
            selected_ids = matched.sample(min(max_n, len(matched)), random_state=1)["PATIENT_ID"].tolist()
            st.write(f"{len(matched)} pacientë përputhen gjithsej; do gjenerohen raporte për {len(selected_ids)}.")

        if selected_ids:
            missing = [i for i in selected_ids if i not in df["PATIENT_ID"].values]
            valid_ids = [i for i in selected_ids if i in df["PATIENT_ID"].values]
            if missing:
                st.warning(f"ID që NUK u gjetën: {missing}")

            st.info(f"Gati për të gjeneruar **{len(valid_ids)}** raporte PDF.")
            if st.button("🚀 Gjenero ZIP me Raportet", type="primary", disabled=(len(valid_ids) == 0)):
                progress = st.progress(0, text="Duke gjeneruar raportet...")
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for i, pid in enumerate(valid_ids):
                        row = df[df["PATIENT_ID"] == pid].iloc[0]
                        pdf_bytes = _generate_pdf_bytes(row, models, encoders, medians)
                        zf.writestr(f"raport_pacienti_{pid}.pdf", pdf_bytes)
                        progress.progress((i + 1) / len(valid_ids),
                                           text=f"Gjeneruar {i+1}/{len(valid_ids)}")
                progress.empty()
                st.success(f"U gjeneruan {len(valid_ids)} raporte!")
                st.download_button("⬇️ Shkarko ZIP", data=zip_buffer.getvalue(),
                                    file_name="raportet_pacienteve.zip", mime="application/zip")

    # ---------------- TAB 2: full stats export ----------------
    with tab2:
        st.write(f"Eksporto tabelën e plotë statistikore për **{len(df):,} pacientë** "
                 "(demografi + antropometri + parashikime) — për analizë hulumtuese.")
        cols_out = [
            "PATIENT_ID", "MOSHA", "GJINIA", "NACIONALITETI", "PESHA_KG",
            "GJATESIA_CM", "BMI", "GLIKEMIA", "HBA1C", "HOLESTEROL", "LDL", "HDL",
            "TRIGLICERIDI", "SIND_METABOLIKE_PARASHIKIM", "DIABET_PARASHIKIM",
            "DIABET_AFERSIA_%", "HIPERTENSION_PARASHIKIM", "LIPID_PARASHIKIM",
        ]
        csv = df[cols_out].to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Shkarko CSV të Plotë", data=csv,
                            file_name="statistika_gjithe_popullsise.csv", mime="text/csv")
        st.dataframe(df[cols_out].head(50), use_container_width=True, hide_index=True)
