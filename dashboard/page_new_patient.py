# -*- coding: utf-8 -*-
"""
page_new_patient.py
======================
Faqja '➕ Pacient i Ri' -- lejon nutricionistin/mjekun të fusë ME DORË
të dhënat e një pacienti/klienti TË RI (që s'ekziston në dataset-in
origjinal): demografi reale, antropometri reale, dhe rezultatet e
analizave biokimike qw ka bërë. Programi bën parashikimin LIVE me
modelet e trajnuara dhe gjeneron plan ushqimor + PDF, njësoj si për
pacientët nga dataseti.

SHËNIM: nëse `supabase_url`/`supabase_key` janë konfiguruar te Secrets,
klientët RUHEN PËRHERSHËM në Supabase (PostgreSQL). Përndryshe (fallback),
ruhen VETËM PËR KËTË SESION (session_state) -- shih README §5/§6.
"""
import os
import re
import io
import zipfile
import tempfile
import datetime
import streamlit as st
import pandas as pd

from src import config, diet_plan, generate_pdf
from src import predict_patient as pp
from data_service import get_models
from viz_utils import gauge
from synthetic_demo_nationalities import NATIONALITIES  # lista e nacionaliteteve (e ripërdorur)
import db  # lidhja me Supabase (ruajtje e përhershme)


def _build_db_record(client_name, biochem, demo, predictions, diet):
    """Duhet të përputhet SAKTËSISHT me kolonat e tabelës `klientet`
    (shih supabase/schema.sql) -- `predictions`/`diet` ruhen si JSON,
    kategoritë (sindroma metabolike, diabeti, etj.) nxirren prej tyre
    kur lexohen mbrapsht, jo si kolona më vete."""
    return {
        "emri": client_name,
        "mosha": demo["MOSHA"], "gjinia": demo["GJINIA"], "nacionaliteti": demo["NACIONALITETI"],
        "pesha_kg": demo["PESHA_KG"], "gjatesia_cm": demo["GJATESIA_CM"], "bmi": demo["BMI"],
        "tension_sistolik": demo.get("TENSION_SISTOLIK"), "tension_diastolik": demo.get("TENSION_DIASTOLIK"),
        "glikemia": biochem.get("GLIKEMIA"), "hba1c": biochem.get("HBA1C"),
        "holesterol": biochem.get("HOLESTEROL"), "ldl": biochem.get("LDL"), "hdl": biochem.get("HDL"),
        "trigliceridi": biochem.get("TRIGLICERIDI"), "hemoglobin": biochem.get("HEMOGLOBIN"),
        "hematokrit": biochem.get("HEMATOKRIT"), "trombociti": biochem.get("TROMBOCITI"),
        "albumini": biochem.get("ALBUMINI"), "totalni_proteini": biochem.get("TOTALNI_PROTEINI"),
        "crp": biochem.get("CRP"), "na": biochem.get("NA"), "mg": biochem.get("MG"), "fe": biochem.get("FE"),
        "tsh": biochem.get("TSH"), "ft4": biochem.get("FT4"),
        "predictions": predictions,
        "diet": diet,
    }


def _safe_filename(text):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", text).strip("_") or "klient"


def _number_or_none(val):
    """0.0 (vlera default e paprekur) trajtohet si 'nuk u fut' -> None (mungon)."""
    return None if (val is None or val == 0.0) else val


def render():
    st.title("➕ Pacient i Ri — Input i Analizave")
    st.caption(
        "Për klientë/pacientë të RINJ (jo në dataset-in origjinal). Fut të dhënat "
        "e analizave që i ka bërë klienti -- fushat që s'i ka bërë i lë 0 (do "
        "trajtohen si 'mungon')."
    )

    if db.is_configured():
        st.success("🟢 Baza e të dhënave (Supabase) është lidhur -- klientët ruhen PËRHERSHËM.")
    else:
        st.warning(
            "🟡 Baza e të dhënave s'është konfiguruar ende -- klientët ruhen VETËM për këtë "
            "sesion (fshihen kur rifreskon faqen). Shto `supabase_url`/`supabase_key` te "
            "Secrets për ruajtje të përhershme (shih README)."
        )

    models, encoders, medians = get_models()

    if "new_patients_history" not in st.session_state:
        st.session_state["new_patients_history"] = []  # listë dict-esh, për këtë sesion

    with st.form("new_patient_form", clear_on_submit=False):
        st.subheader("1. Identifikimi & Demografia")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            client_name = st.text_input("Emri/ID i Klientit *", placeholder="p.sh. A.K. ose #001")
        with c2:
            mosha = st.number_input("Mosha *", min_value=1, max_value=120, value=35, step=1)
        with c3:
            gjinia = st.selectbox("Gjinia *", ["M", "F"])
        with c4:
            nacionaliteti = st.selectbox("Nacionaliteti", NATIONALITIES)

        st.subheader("2. Antropometria")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            pesha = st.number_input("Pesha (kg) *", min_value=20.0, max_value=300.0, value=70.0, step=0.1)
        with c2:
            gjatesia = st.number_input("Gjatësia (cm) *", min_value=100.0, max_value=230.0, value=170.0, step=0.5)
        bmi = round(pesha / ((gjatesia / 100) ** 2), 1)
        with c3:
            st.metric("BMI (llogaritur)", bmi)
        with c4:
            st.write("")

        st.subheader("3. Tensioni (nëse është matur)")
        c1, c2 = st.columns(2)
        with c1:
            tension_sis = st.number_input("Tensioni Sistolik", min_value=0, max_value=260, value=0, step=1,
                                            help="Lëre 0 nëse s'është matur")
        with c2:
            tension_dia = st.number_input("Tensioni Diastolik", min_value=0, max_value=160, value=0, step=1,
                                            help="Lëre 0 nëse s'është matur")

        st.subheader("4. Analizat Biokimike Themelore")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            glikemia = st.number_input("Glikemia (mmol/L)", min_value=0.0, max_value=40.0, value=0.0, step=0.1)
            holesterol = st.number_input("Kolesteroli Total (mmol/L)", min_value=0.0, max_value=20.0, value=0.0, step=0.1)
        with c2:
            hba1c = st.number_input("HbA1c (%)", min_value=0.0, max_value=20.0, value=0.0, step=0.1)
            ldl = st.number_input("LDL (mmol/L)", min_value=0.0, max_value=15.0, value=0.0, step=0.1)
        with c3:
            trigliceridi = st.number_input("Trigliceridet (mmol/L)", min_value=0.0, max_value=20.0, value=0.0, step=0.1)
            hdl = st.number_input("HDL (mmol/L)", min_value=0.0, max_value=6.0, value=0.0, step=0.1)
        with c4:
            hemoglobina = st.number_input("Hemoglobina (g/L)", min_value=0.0, max_value=220.0, value=0.0, step=1.0)
            crp = st.number_input("CRP (mg/L)", min_value=0.0, max_value=300.0, value=0.0, step=0.1)

        with st.expander("5. Analiza Shtesë (opsionale)"):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                hematokrit = st.number_input("Hematokriti", min_value=0.0, max_value=1.0, value=0.0, step=0.01)
                na = st.number_input("Na (Natrium)", min_value=0.0, max_value=200.0, value=0.0, step=0.1)
            with c2:
                trombocit = st.number_input("Trombocitet", min_value=0.0, max_value=1000.0, value=0.0, step=1.0)
                mg = st.number_input("Mg (Magnez)", min_value=0.0, max_value=5.0, value=0.0, step=0.01)
            with c3:
                albumin = st.number_input("Albumina", min_value=0.0, max_value=100.0, value=0.0, step=0.1)
                fe = st.number_input("Fe (Hekur)", min_value=0.0, max_value=50.0, value=0.0, step=0.1)
            with c4:
                totalni_prot = st.number_input("Proteina Totale", min_value=0.0, max_value=120.0, value=0.0, step=0.1)
                tsh = st.number_input("TSH", min_value=0.0, max_value=50.0, value=0.0, step=0.01)
            ft4 = st.number_input("FT4", min_value=0.0, max_value=100.0, value=0.0, step=0.1)

        submitted = st.form_submit_button("🔮 Bëj Parashikimin & Gjenero Planin", type="primary")

    if not submitted:
        _render_history(models, encoders, medians)
        return

    if not client_name.strip():
        st.error("Ju lutem fut Emrin/ID e klientit.")
        _render_history(models, encoders, medians)
        return

    # ---- Ndërto input-in për modelet ----
    biochem = {
        "GLIKEMIA": _number_or_none(glikemia), "HBA1C": _number_or_none(hba1c),
        "HOLESTEROL": _number_or_none(holesterol), "LDL": _number_or_none(ldl),
        "HDL": _number_or_none(hdl), "TRIGLICERIDI": _number_or_none(trigliceridi),
        "HEMOGLOBIN": _number_or_none(hemoglobina), "CRP": _number_or_none(crp),
        "HEMATOKRIT": _number_or_none(hematokrit), "NA": _number_or_none(na),
        "TROMBOCITI": _number_or_none(trombocit), "MG": _number_or_none(mg),
        "ALBUMINI": _number_or_none(albumin), "FE": _number_or_none(fe),
        "TOTALNI_PROTEINI": _number_or_none(totalni_prot), "TSH": _number_or_none(tsh),
        "FT4": _number_or_none(ft4),
    }
    demo = {
        "MOSHA": int(mosha), "GJINIA": gjinia, "NACIONALITETI": nacionaliteti,
        "PESHA_KG": pesha, "GJATESIA_CM": gjatesia, "BMI": bmi,
        "TENSION_SISTOLIK": _number_or_none(float(tension_sis)),
        "TENSION_DIASTOLIK": _number_or_none(float(tension_dia)),
    }
    patient_input = {**biochem, "MOSHA": demo["MOSHA"], "GJINIA": demo["GJINIA"], "BMI": demo["BMI"]}

    predictions = pp.predict_patient(patient_input, models, encoders, medians)
    diet = diet_plan.build_diet_plan(demo, predictions)

    # ruaj në historikun e sesionit (fallback lokal, gjithmonë)
    st.session_state["new_patients_history"].append({
        "emri": client_name, "koha": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "biochem": biochem, "demo": demo, "predictions": predictions, "diet": diet,
    })

    # ruaj PËRHERSHËM te Supabase (nëse është konfiguruar)
    if db.is_configured():
        record = _build_db_record(client_name, biochem, demo, predictions, diet)
        if db.save_client(record):
            st.success(f"✅ Parashikimi u krye dhe **{client_name}** u ruajt përhershëm në bazën e të dhënave!")
        else:
            st.success(f"✅ Parashikimi u krye për **{client_name}**!")
    else:
        st.success(f"✅ Parashikimi u krye për **{client_name}**!")
    st.markdown("---")
    _render_results(client_name, biochem, demo, predictions, diet)
    _render_history(models, encoders, medians)


def _render_history(models, encoders, medians):
    """Shfaq historikun PËRHERSHËM (Supabase) nëse është konfiguruar,
    përndryshe historikun e sesionit (fallback, sjellja fillestare)."""
    if db.is_configured():
        _render_db_history()
    else:
        _render_session_history(models, encoders, medians)


def _render_results(client_name, biochem, demo, predictions, diet):
    st.subheader(f"📋 Rezultatet — {client_name}")

    missing_core = [k for k in ("GLIKEMIA", "HBA1C", "HOLESTEROL", "LDL", "HDL", "TRIGLICERIDI")
                    if biochem.get(k) is None]
    if missing_core:
        st.info(f"ℹ️ Analiza që mungojnë (u zëvendësuan me median statistikore për parashikim): "
                f"{', '.join(missing_core)}")
    if demo.get("TENSION_SISTOLIK") is None:
        st.info("ℹ️ Tensioni nuk u fut -- parashikimi i hipertensionit bazohet vetëm në median statistikore.")

    g1, g2, g3, g4 = st.columns(4)
    with g1:
        st.plotly_chart(gauge("Sindroma Metabolike", predictions["sindroma_metabolike"]["kategoria"]),
                         use_container_width=True, key=f"g1_{client_name}_{id(predictions)}")
    with g2:
        dia = predictions["rreziku_diabetit"]
        st.plotly_chart(gauge("Rreziku i Diabetit", dia["kategoria"]),
                         use_container_width=True, key=f"g2_{client_name}_{id(predictions)}")
        st.markdown(f"<p style='text-align:center'><b>Afërsia me diabetin: {dia['afersia_perqindje']}%</b></p>",
                    unsafe_allow_html=True)
    with g3:
        st.plotly_chart(gauge("Hipertensioni", predictions["hipertension"]["kategoria"]),
                         use_container_width=True, key=f"g3_{client_name}_{id(predictions)}")
    with g4:
        st.plotly_chart(gauge("Profili Lipidik", predictions["profili_lipidik"]["kategoria"]),
                         use_container_width=True, key=f"g4_{client_name}_{id(predictions)}")

    st.markdown("#### 🍽️ Plani Ushqimor")
    c1, c2 = st.columns(2)
    c1.metric("Kalori Bazale (BMR)", f"{diet['kalori_bazale_bmr']} kcal/ditë")
    c2.metric("Kalori Ditore të Synuara", f"{diet['kalori_ditore_te_synuara']} kcal/ditë")
    colr, colk = st.columns(2)
    with colr:
        st.markdown("**Rekomandime:**")
        for r in diet["rekomandime"]:
            st.markdown(f"- {r}")
    with colk:
        st.markdown("**Kufizime:**")
        for r in diet["kufizime"]:
            st.markdown(f"- {r}")

    if st.button(f"📄 Gjenero PDF për {client_name}", key=f"pdf_btn_{client_name}_{id(predictions)}"):
        with st.spinner("Duke gjeneruar PDF-në..."):
            tmp_path = os.path.join(tempfile.gettempdir(), f"raport_{_safe_filename(client_name)}.pdf")
            generate_pdf.build_patient_pdf(tmp_path, client_name, biochem, demo, predictions, diet)
            with open(tmp_path, "rb") as f:
                pdf_bytes = f.read()
        st.download_button("⬇️ Shkarko PDF", data=pdf_bytes,
                            file_name=f"raport_{_safe_filename(client_name)}.pdf",
                            mime="application/pdf", key=f"dl_{client_name}_{id(predictions)}")


def _render_session_history(models, encoders, medians):
    history = st.session_state.get("new_patients_history", [])
    if not history:
        return

    st.markdown("---")
    st.subheader(f"🕑 Klientët e Futur Këtë Sesion ({len(history)})")
    st.caption("⚠️ Kjo listë fshihet nëse mbyll/rifreskon aplikacionin -- nuk ruhet përgjithmonë.")

    summary_rows = []
    for h in history:
        summary_rows.append({
            "Klienti": h["emri"], "Koha": h["koha"], "Mosha": h["demo"]["MOSHA"],
            "Gjinia": h["demo"]["GJINIA"], "BMI": h["demo"]["BMI"],
            "Sindroma Metabolike": h["predictions"]["sindroma_metabolike"]["kategoria"],
            "Diabeti": h["predictions"]["rreziku_diabetit"]["kategoria"],
            "Hipertensioni": h["predictions"]["hipertension"]["kategoria"],
            "Lipidet": h["predictions"]["profili_lipidik"]["kategoria"],
        })
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        csv = pd.DataFrame(summary_rows).to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Shkarko Përmbledhjen (CSV)", data=csv,
                            file_name="klientet_e_rinj_sesioni.csv", mime="text/csv")
    with c2:
        if st.button("🗑️ Pastro Historikun e Sesionit"):
            st.session_state["new_patients_history"] = []
            st.rerun()

    with st.expander("📁 Shkarko PDF për të gjithë klientët (ZIP)"):
        if st.button("Gjenero ZIP me të gjitha raportet e sesionit"):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                for h in history:
                    tmp_path = os.path.join(tempfile.gettempdir(),
                                             f"raport_{_safe_filename(h['emri'])}.pdf")
                    generate_pdf.build_patient_pdf(tmp_path, h["emri"], h["biochem"], h["demo"],
                                                    h["predictions"], h["diet"])
                    with open(tmp_path, "rb") as f:
                        zf.writestr(f"raport_{_safe_filename(h['emri'])}.pdf", f.read())
            st.download_button("⬇️ Shkarko ZIP", data=zip_buffer.getvalue(),
                                file_name="raportet_klienteve_sesioni.zip", mime="application/zip")


def _row_to_biochem_demo(row):
    biochem = {
        "HEMOGLOBIN": row.get("hemoglobin"), "HEMATOKRIT": row.get("hematokrit"),
        "TROMBOCITI": row.get("trombociti"), "ALBUMINI": row.get("albumini"),
        "TOTALNI_PROTEINI": row.get("totalni_proteini"), "CRP": row.get("crp"),
        "NA": row.get("na"), "MG": row.get("mg"), "FE": row.get("fe"),
        "HOLESTEROL": row.get("holesterol"), "LDL": row.get("ldl"), "HDL": row.get("hdl"),
        "TRIGLICERIDI": row.get("trigliceridi"), "GLIKEMIA": row.get("glikemia"),
        "HBA1C": row.get("hba1c"), "TSH": row.get("tsh"), "FT4": row.get("ft4"),
    }
    demo = {
        "MOSHA": row.get("mosha"), "GJINIA": row.get("gjinia"), "NACIONALITETI": row.get("nacionaliteti"),
        "PESHA_KG": row.get("pesha_kg"), "GJATESIA_CM": row.get("gjatesia_cm"), "BMI": row.get("bmi"),
    }
    return biochem, demo


def _render_db_history():
    st.markdown("---")
    st.subheader("🗂️ Klientët e Ruajtur (Baza e të Dhënave)")

    df = db.load_all_clients()
    if df.empty:
        st.info("Ende s'ka klientë të ruajtur në bazën e të dhënave.")
        return

    search = st.text_input("🔎 Kërko klient sipas emrit/ID")
    fdf = df[df["emri"].str.contains(search, case=False, na=False)] if search else df

    st.caption(f"{len(fdf)} nga {len(df)} klientë gjithsej")

    # nxjerr kategoritë nga kolona `predictions` (jsonb) për shfaqje në tabelë
    def _safe_get(preds, key):
        try:
            return preds[key]["kategoria"]
        except Exception:
            return None

    fdf = fdf.copy()
    fdf["Sindroma Metabolike"] = fdf["predictions"].apply(lambda p: _safe_get(p, "sindroma_metabolike"))
    fdf["Diabeti"] = fdf["predictions"].apply(lambda p: _safe_get(p, "rreziku_diabetit"))
    fdf["Hipertensioni"] = fdf["predictions"].apply(lambda p: _safe_get(p, "hipertension"))
    fdf["Lipidet"] = fdf["predictions"].apply(lambda p: _safe_get(p, "profili_lipidik"))

    show_cols = ["id", "emri", "krijuar_me", "mosha", "gjinia", "bmi",
                 "Sindroma Metabolike", "Diabeti", "Hipertensioni", "Lipidet"]
    show_cols = [c for c in show_cols if c in fdf.columns]
    st.dataframe(fdf[show_cols], use_container_width=True, hide_index=True, height=300)

    csv = fdf[show_cols].to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Shkarko Listën e Plotë (CSV)", data=csv,
                        file_name="klientet_te_gjithe.csv", mime="text/csv")

    st.markdown("#### Hap një Klient Specifik")
    if fdf.empty:
        return
    options = {f"#{r.id} — {r.emri} ({str(r.krijuar_me)[:16]})": r.id for r in fdf.itertuples()}
    choice = st.selectbox("Zgjidh klientin", list(options.keys()))
    if not choice:
        return
    sel_id = options[choice]
    row = fdf[fdf["id"] == sel_id].iloc[0]

    biochem, demo = _row_to_biochem_demo(row)
    predictions = row.get("predictions")
    diet = row.get("diet")

    if predictions and diet:
        _render_results(row["emri"] + f" (ruajtur {str(row['krijuar_me'])[:16]})", biochem, demo, predictions, diet)

    if st.button("🗑️ Fshi këtë klient", key=f"del_{sel_id}"):
        if db.delete_client(sel_id):
            st.success("U fshi.")
            st.rerun()
        else:
            st.error("Fshirja dështoi.")
