# -*- coding: utf-8 -*-
"""
app.py — Dashboard Interaktiv (Streamlit)
============================================
Nis me:  streamlit run app.py
"""
import os
import sys
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from data_service import get_full_dataset, get_models, ROOT
from src import config
import page_patient
import page_compare
import page_export
from auth import require_login

st.set_page_config(
    page_title="Sistemi ML - Parametra Biokimikë",
    page_icon="🩺",
    layout="wide",
)

require_login()  # ndal ekzekutimin këtu nëse s'është loguar akoma

RISK_COLOR_MAP = {
    "Low": "#2e7d32", "Normal": "#2e7d32",
    "Medium": "#f9a825", "Kufitar": "#f9a825",
    "Kufitar (pre-hipertension)": "#f9a825", "Prediabet": "#f9a825",
    "High": "#c62828", "I lartë": "#c62828", "Diabetik": "#c62828",
}

st.sidebar.title("🩺 Navigimi")
page = st.sidebar.radio(
    "Zgjidh faqen",
    ["📊 Përmbledhje e Popullsisë", "🧑‍⚕️ Profili i Pacientit",
     "🔍 Krahasime & Filtra", "📁 Eksport Batch (PDF)"],
    label_visibility="collapsed",
)

if st.sidebar.button("🚪 Dil (Logout)"):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(
    "⚠️ Të dhënat demografike/antropometrike janë **sintetike** (prototip). "
    "Parametrat biokimikë janë reale nga dataseti origjinal."
)

df = get_full_dataset()

# ============================================================
# FAQJA 1: PËRMBLEDHJE E POPULLSISË
# ============================================================
if page == "📊 Përmbledhje e Popullsisë":
    st.title("📊 Përmbledhje e Popullsisë së Pacientëve")
    st.caption(f"Bazuar në {len(df):,} pacientë (nga dataseti real i analizave laboratorike)")

    # ---- Filtra global në sidebar ----
    st.sidebar.markdown("### Filtra")
    genders = st.sidebar.multiselect("Gjinia", sorted(df["GJINIA"].unique()),
                                       default=list(df["GJINIA"].unique()))
    nationalities = st.sidebar.multiselect("Nacionaliteti", sorted(df["NACIONALITETI"].unique()),
                                             default=list(df["NACIONALITETI"].unique()))
    age_range = st.sidebar.slider("Mosha", int(df["MOSHA"].min()), int(df["MOSHA"].max()),
                                    (int(df["MOSHA"].min()), int(df["MOSHA"].max())))

    fdf = df[
        df["GJINIA"].isin(genders) &
        df["NACIONALITETI"].isin(nationalities) &
        df["MOSHA"].between(*age_range)
    ]

    if fdf.empty:
        st.warning("Asnjë pacient nuk përputhet me filtrat e zgjedhur.")
        st.stop()

    # ---- KPI kartat ----
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Pacientë (të filtruar)", f"{len(fdf):,}")
    c2.metric("Sindromë Metabolike e Lartë",
              f"{(fdf['SIND_METABOLIKE_PARASHIKIM']=='High').mean()*100:.1f}%")
    c3.metric("Diabetikë / Prediabetikë",
              f"{fdf['DIABET_PARASHIKIM'].isin(['Diabetik','Prediabet']).mean()*100:.1f}%")
    c4.metric("Hipertension i Lartë",
              f"{(fdf['HIPERTENSION_PARASHIKIM']=='I lartë').mean()*100:.1f}%")
    c5.metric("Profil Lipidik i Lartë",
              f"{(fdf['LIPID_PARASHIKIM']=='I lartë').mean()*100:.1f}%")

    st.markdown("---")

    # ---- Rreshti 1: demografi ----
    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Shpërndarja e Moshës")
        fig = px.histogram(fdf, x="MOSHA", nbins=30, color_discrete_sequence=["#1f4e79"])
        fig.update_layout(height=320, margin=dict(t=10))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Gjinia")
        vc = fdf["GJINIA"].value_counts().reset_index()
        vc.columns = ["Gjinia", "Numri"]
        fig = px.pie(vc, names="Gjinia", values="Numri", hole=0.45,
                     color_discrete_sequence=["#1f4e79", "#e07b39"])
        fig.update_layout(height=320, margin=dict(t=10))
        st.plotly_chart(fig, use_container_width=True)
    with col3:
        st.subheader("Nacionaliteti")
        vc = fdf["NACIONALITETI"].value_counts().reset_index()
        vc.columns = ["Nacionaliteti", "Numri"]
        fig = px.bar(vc, x="Nacionaliteti", y="Numri", color="Nacionaliteti")
        fig.update_layout(height=320, margin=dict(t=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    # ---- Rreshti 2: BMI + risk categories ----
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Shpërndarja e BMI-së sipas Kategorisë")
        bmi_bins = pd.cut(fdf["BMI"], bins=[0, 18.5, 25, 30, 100],
                           labels=["Nën peshë", "Normale", "Mbipeshë", "Obezitet"])
        vc = bmi_bins.value_counts().reindex(["Nën peshë", "Normale", "Mbipeshë", "Obezitet"]).reset_index()
        vc.columns = ["Kategoria BMI", "Numri"]
        fig = px.bar(vc, x="Kategoria BMI", y="Numri",
                     color="Kategoria BMI",
                     color_discrete_sequence=["#42a5f5", "#2e7d32", "#f9a825", "#c62828"])
        fig.update_layout(height=340, margin=dict(t=10), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("Sindroma Metabolike sipas Grupmoshës")
        fdf2 = fdf.copy()
        fdf2["Grupmosha"] = pd.cut(fdf2["MOSHA"], bins=[17, 30, 45, 60, 75, 100],
                                     labels=["18-30", "31-45", "46-60", "61-75", "76+"])
        cross = pd.crosstab(fdf2["Grupmosha"], fdf2["SIND_METABOLIKE_PARASHIKIM"], normalize="index") * 100
        cross = cross[[c for c in ["Low", "Medium", "High"] if c in cross.columns]]
        fig = px.bar(cross, barmode="stack",
                     color_discrete_map=RISK_COLOR_MAP)
        fig.update_layout(height=340, margin=dict(t=10), yaxis_title="%")
        st.plotly_chart(fig, use_container_width=True)

    # ---- Rreshti 3: 4 kategoritë e riskut krah për krah ----
    st.subheader("Shpërndarja e 4 Parashikimeve Kryesore")
    r1, r2, r3, r4 = st.columns(4)
    risk_cols = [
        (r1, "SIND_METABOLIKE_PARASHIKIM", "Sindroma Metabolike"),
        (r2, "DIABET_PARASHIKIM", "Statusi i Diabetit"),
        (r3, "HIPERTENSION_PARASHIKIM", "Hipertensioni"),
        (r4, "LIPID_PARASHIKIM", "Profili Lipidik"),
    ]
    for col, colname, title in risk_cols:
        with col:
            vc = fdf[colname].value_counts().reset_index()
            vc.columns = ["Kategoria", "Numri"]
            fig = px.pie(vc, names="Kategoria", values="Numri", title=title,
                         color="Kategoria", color_discrete_map=RISK_COLOR_MAP, hole=0.4)
            fig.update_layout(height=300, margin=dict(t=40, b=0), showlegend=True,
                               legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig, use_container_width=True)

    # ---- Scatter: BMI vs Glikemia ----
    st.subheader("Marrëdhënia BMI ↔ Glikemia (sipas Statusit të Diabetit)")
    scatter_df = fdf.dropna(subset=["BMI", "GLIKEMIA"])
    if len(scatter_df) > 3000:
        scatter_df = scatter_df.sample(3000, random_state=42)
    fig = px.scatter(scatter_df, x="BMI", y="GLIKEMIA", color="DIABET_PARASHIKIM",
                      color_discrete_map=RISK_COLOR_MAP, opacity=0.6,
                      hover_data=["PATIENT_ID", "MOSHA", "GJINIA"])
    fig.update_layout(height=420)
    st.plotly_chart(fig, use_container_width=True)

# ============================================================
# FAQJA 2: PROFILI I PACIENTIT
# ============================================================
elif page == "🧑‍⚕️ Profili i Pacientit":
    page_patient.render()

# ============================================================
# FAQJA 3: KRAHASIME & FILTRA
# ============================================================
elif page == "🔍 Krahasime & Filtra":
    page_compare.render()

# ============================================================
# FAQJA 4: EKSPORT BATCH
# ============================================================
elif page == "📁 Eksport Batch (PDF)":
    page_export.render()
