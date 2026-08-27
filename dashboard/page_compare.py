# -*- coding: utf-8 -*-
"""
page_compare.py
==================
Faqja 'Krahasime & Filtra': lejon filtrim të thelluar mbi popullsinë
(nacionalitet, gjini, grupmoshë, kategori risku) dhe krahasim krah
për krah + eksport CSV të nën-grupit të filtruar (për hulumtim).
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from data_service import get_full_dataset

RISK_COLOR_MAP = {
    "Low": "#2e7d32", "Normal": "#2e7d32",
    "Medium": "#f9a825", "Kufitar": "#f9a825",
    "Kufitar (pre-hipertension)": "#f9a825", "Prediabet": "#f9a825",
    "High": "#c62828", "I lartë": "#c62828", "Diabetik": "#c62828",
}


def render():
    st.title("🔍 Krahasime & Filtra të Avancuara")
    df = get_full_dataset()

    st.subheader("Filtro Popullsinë")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        nationality = st.multiselect("Nacionaliteti", sorted(df["NACIONALITETI"].unique()),
                                       default=list(df["NACIONALITETI"].unique()))
    with f2:
        gender = st.multiselect("Gjinia", sorted(df["GJINIA"].unique()),
                                  default=list(df["GJINIA"].unique()))
    with f3:
        ms_cat = st.multiselect("Sindroma Metabolike",
                                  sorted(df["SIND_METABOLIKE_PARASHIKIM"].unique()),
                                  default=list(df["SIND_METABOLIKE_PARASHIKIM"].unique()))
    with f4:
        dia_cat = st.multiselect("Statusi i Diabetit",
                                   sorted(df["DIABET_PARASHIKIM"].unique()),
                                   default=list(df["DIABET_PARASHIKIM"].unique()))

    age_range = st.slider("Mosha", int(df["MOSHA"].min()), int(df["MOSHA"].max()),
                            (int(df["MOSHA"].min()), int(df["MOSHA"].max())))

    fdf = df[
        df["NACIONALITETI"].isin(nationality) &
        df["GJINIA"].isin(gender) &
        df["SIND_METABOLIKE_PARASHIKIM"].isin(ms_cat) &
        df["DIABET_PARASHIKIM"].isin(dia_cat) &
        df["MOSHA"].between(*age_range)
    ]

    st.markdown(f"**{len(fdf):,} pacientë** përputhen me filtrat ({len(fdf)/len(df)*100:.1f}% e popullsisë totale)")
    st.markdown("---")

    if fdf.empty:
        st.warning("Asnjë pacient nuk përputhet.")
        return

    # ---- Krahasim krahë për krahë sipas një dimensioni ----
    st.subheader("Krahaso sipas Dimensionit")
    dim = st.selectbox("Grupo sipas:", ["NACIONALITETI", "GJINIA"])
    metric = st.selectbox("Trego përqindjen për:",
                            ["SIND_METABOLIKE_PARASHIKIM", "DIABET_PARASHIKIM",
                             "HIPERTENSION_PARASHIKIM", "LIPID_PARASHIKIM"],
                            format_func=lambda x: {
                                "SIND_METABOLIKE_PARASHIKIM": "Sindroma Metabolike",
                                "DIABET_PARASHIKIM": "Statusi i Diabetit",
                                "HIPERTENSION_PARASHIKIM": "Hipertensioni",
                                "LIPID_PARASHIKIM": "Profili Lipidik",
                            }[x])

    cross = pd.crosstab(fdf[dim], fdf[metric], normalize="index") * 100
    fig = px.bar(cross, barmode="group", color_discrete_map=RISK_COLOR_MAP,
                 title=f"{metric} sipas {dim}")
    fig.update_layout(height=420, yaxis_title="%")
    st.plotly_chart(fig, use_container_width=True)

    # ---- Box plot biokimik sipas grupit ----
    st.subheader("Shpërndarja e Vlerave Biokimike sipas Grupit")
    biochem_var = st.selectbox("Zgjidh analizën:",
                                 ["GLIKEMIA", "HOLESTEROL", "LDL", "HDL", "TRIGLICERIDI", "BMI"])
    box_df = fdf.dropna(subset=[biochem_var])
    fig2 = px.box(box_df, x=dim, y=biochem_var, color=dim, points=False)
    fig2.update_layout(height=420, showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")

    # ---- Tabela + eksport ----
    st.subheader("Tabela e të Dhënave të Filtruara")
    show_cols = ["PATIENT_ID", "MOSHA", "GJINIA", "NACIONALITETI", "BMI",
                 "GLIKEMIA", "HOLESTEROL", "LDL", "HDL", "TRIGLICERIDI",
                 "SIND_METABOLIKE_PARASHIKIM", "DIABET_PARASHIKIM",
                 "HIPERTENSION_PARASHIKIM", "LIPID_PARASHIKIM"]
    st.dataframe(fdf[show_cols], use_container_width=True, hide_index=True, height=350)

    csv = fdf[show_cols].to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Shkarko Nën-grupin e Filtruar (CSV)", data=csv,
                        file_name="pacientet_filtruar.csv", mime="text/csv")
