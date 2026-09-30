# -*- coding: utf-8 -*-
"""
page_meal_plan.py
===================
Faqja "📝 Plani Ushqimor (Dietologu)": dietologia harton planin javor
(7 ditë x 6 vakte) për një klient, sipas modelit të saj në Excel.

- Emri, pesha, gjatësia mbushen AUTOMATIKISHT kur zgjidhet klienti
  (nga baza e të dhënave Supabase ose nga klientët e sesionit).
- Titulli (Plani 1, Plani 2, ...) dhe periudha (datat) zgjidhen.
- Eksport në Excel (i njëjti format si modeli) dhe PDF.
- Planet ruhen në Supabase dhe mund të rihapen/kopjohen (p.sh. Plani 2
  nisur nga Plani 1).
"""
import datetime

import streamlit as st

import db
from meal_plan_export import DAYS, MEALS, build_meal_plan_pdf, build_meal_plan_xlsx, initials

PLAN_TITLES = [f"PLANI {i}" for i in range(1, 13)]
DEFAULT_NOTES = ""


# ----------------------------------------------------------------
# Gjendja (session_state): çdo fushë ka çelës të vetin, kështu që
# ngarkimi i klientit/planit mund t'i mbushë fushat automatikisht.
# ----------------------------------------------------------------
def _init_state():
    today = datetime.date.today()
    defaults = {
        "mp_emri": "", "mp_pesha": 0.0, "mp_gjatesia": 0.0, "mp_klient_id": None,
        "mp_titulli": PLAN_TITLES[0], "mp_dates": (today, today + datetime.timedelta(days=14)),
        "mp_shenime": DEFAULT_NOTES, "mp_lista": "", "mp_pergatitur": "",
        "mp_loaded_id": None,
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)
    for key, _, t in MEALS:
        st.session_state.setdefault(f"mp_time_{key}", t)
    for d in range(len(DAYS)):
        for key, _, _ in MEALS:
            st.session_state.setdefault(f"mp_{d}_{key}", "")


def _client_options():
    """Lista e klientëve për zgjedhje: nga Supabase dhe/ose nga sesioni."""
    options = []
    if db.is_configured():
        df = db.load_all_clients()
        for _, r in df.iterrows():
            options.append({
                "label": f"{r['emri']}  (#{r['id']}, {str(r.get('krijuar_me', ''))[:10]})",
                "emri": r["emri"], "pesha": r.get("pesha_kg"), "gjatesia": r.get("gjatesia_cm"),
                "klient_id": int(r["id"]),
            })
    for h in st.session_state.get("new_patients_history", []):
        options.append({
            "label": f"{h['emri']}  (sesioni, {h['koha']})",
            "emri": h["emri"], "pesha": h["demo"].get("PESHA_KG"),
            "gjatesia": h["demo"].get("GJATESIA_CM"), "klient_id": None,
        })
    return options


def _on_client_change():
    """Mbush automatikisht emrin, peshën, gjatësinë kur zgjidhet klienti."""
    label = st.session_state.get("mp_client_select")
    for opt in st.session_state.get("_mp_client_opts", []):
        if opt["label"] == label:
            st.session_state["mp_emri"] = opt["emri"] or ""
            st.session_state["mp_pesha"] = float(opt["pesha"] or 0.0)
            st.session_state["mp_gjatesia"] = float(opt["gjatesia"] or 0.0)
            st.session_state["mp_klient_id"] = opt["klient_id"]
            st.session_state["mp_loaded_id"] = None
            return


def _collect_plan():
    dates = st.session_state["mp_dates"]
    if isinstance(dates, (list, tuple)):
        d0 = dates[0] if len(dates) > 0 else None
        d1 = dates[1] if len(dates) > 1 else d0
    else:
        d0 = d1 = dates
    return {
        "emri": st.session_state["mp_emri"].strip(),
        "pesha": st.session_state["mp_pesha"] or None,
        "gjatesia": st.session_state["mp_gjatesia"] or None,
        "titulli": st.session_state["mp_titulli"],
        "data_fillimit": d0, "data_mbarimit": d1,
        "oraret": {key: st.session_state[f"mp_time_{key}"] for key, _, _ in MEALS},
        "ushqimet": {day: {key: st.session_state[f"mp_{d}_{key}"] for key, _, _ in MEALS}
                     for d, day in enumerate(DAYS)},
        "shenime": st.session_state["mp_shenime"],
        "lista": st.session_state["mp_lista"],
        "pergatitur_nga": st.session_state["mp_pergatitur"],
    }


def _plan_to_json(plan):
    """Datat -> tekst ISO, që të ruhen si JSON në Supabase."""
    out = dict(plan)
    for k in ("data_fillimit", "data_mbarimit"):
        out[k] = plan[k].isoformat() if plan[k] else None
    return out


def _load_plan_into_state(row, as_copy=False):
    """Ngarkon një plan të ruajtur në fushat e formularit (callback)."""
    p = row["permbajtja"]
    st.session_state["mp_emri"] = p.get("emri", "")
    st.session_state["mp_pesha"] = float(p.get("pesha") or 0.0)
    st.session_state["mp_gjatesia"] = float(p.get("gjatesia") or 0.0)
    st.session_state["mp_klient_id"] = row.get("klient_id")
    st.session_state["mp_shenime"] = p.get("shenime", "")
    st.session_state["mp_lista"] = p.get("lista", "")
    st.session_state["mp_pergatitur"] = p.get("pergatitur_nga", "")
    for key, _, t in MEALS:
        st.session_state[f"mp_time_{key}"] = p.get("oraret", {}).get(key, t)
    for d, day in enumerate(DAYS):
        for key, _, _ in MEALS:
            st.session_state[f"mp_{d}_{key}"] = p.get("ushqimet", {}).get(day, {}).get(key, "")

    if as_copy:
        # Kopje si plan i ri: titulli kalon te plani pasardhës, datat nisin pas të mëparshmit
        idx = PLAN_TITLES.index(p["titulli"]) if p.get("titulli") in PLAN_TITLES else -1
        st.session_state["mp_titulli"] = PLAN_TITLES[min(idx + 1, len(PLAN_TITLES) - 1)]
        start = (datetime.date.fromisoformat(p["data_mbarimit"]) + datetime.timedelta(days=1)
                 if p.get("data_mbarimit") else datetime.date.today())
        st.session_state["mp_dates"] = (start, start + datetime.timedelta(days=14))
        st.session_state["mp_loaded_id"] = None
    else:
        st.session_state["mp_titulli"] = p.get("titulli", PLAN_TITLES[0])
        d0 = datetime.date.fromisoformat(p["data_fillimit"]) if p.get("data_fillimit") else datetime.date.today()
        d1 = datetime.date.fromisoformat(p["data_mbarimit"]) if p.get("data_mbarimit") else d0
        st.session_state["mp_dates"] = (d0, d1)
        st.session_state["mp_loaded_id"] = int(row["id"])


def _copy_day(src, targets):
    for t in targets:
        for key, _, _ in MEALS:
            st.session_state[f"mp_{t}_{key}"] = st.session_state[f"mp_{src}_{key}"]


def _clear_menu():
    for d in range(len(DAYS)):
        for key, _, _ in MEALS:
            st.session_state[f"mp_{d}_{key}"] = ""
    st.session_state["mp_loaded_id"] = None


# ----------------------------------------------------------------
def render():
    _init_state()
    st.title("📝 Plani Ushqimor (Dietologu)")
    st.caption("Harto planin javor për klientin. Emri, pesha dhe gjatësia mbushen automatikisht nga "
               "klienti i zgjedhur; titulli i planit dhe periudha zgjidhen më poshtë.")

    # ---------- 1. Klienti ----------
    st.subheader("1. Klienti")
    opts = _client_options()
    st.session_state["_mp_client_opts"] = opts
    if opts:
        labels = ["— zgjidh klientin —"] + [o["label"] for o in opts]
        st.selectbox("Zgjidh klientin (mbush automatikisht emrin, peshën, gjatësinë)", labels,
                     key="mp_client_select", on_change=_on_client_change)
    else:
        st.info("Ende s'ka klientë të ruajtur. Shto klientë te faqja \"➕ Pacient i Ri\", "
                "ose plotëso të dhënat më poshtë me dorë.")

    c1, c2, c3 = st.columns([2, 1, 1])
    c1.text_input("Emri dhe mbiemri *", key="mp_emri")
    c2.number_input("Pesha (kg)", min_value=0.0, max_value=300.0, step=0.1, key="mp_pesha")
    c3.number_input("Gjatësia (cm)", min_value=0.0, max_value=230.0, step=0.5, key="mp_gjatesia",
                    help="0 = e panjohur (shfaqet '...' në plan)")

    # ---------- 2. Plani dhe periudha ----------
    st.subheader("2. Plani dhe periudha")
    c1, c2 = st.columns([1, 2])
    c1.selectbox("Titulli i planit", PLAN_TITLES, key="mp_titulli")
    c2.date_input("Periudha (data e fillimit – data e mbarimit)", key="mp_dates", format="DD.MM.YYYY")

    with st.expander("⏰ Oraret e vakteve"):
        cols = st.columns(len(MEALS))
        for col, (key, name, _) in zip(cols, MEALS):
            col.text_input(name, key=f"mp_time_{key}")

    # ---------- 3. Menuja javore ----------
    st.subheader("3. Menuja javore")
    tabs = st.tabs([d.title() for d in DAYS])
    for d, (tab, day) in enumerate(zip(tabs, DAYS)):
        with tab:
            cols = st.columns(3)
            for i, (key, name, _) in enumerate(MEALS):
                with cols[i % 3]:
                    st.text_area(f"{name} ({st.session_state[f'mp_time_{key}']})",
                                 key=f"mp_{d}_{key}", height=140)

    with st.expander("📋 Kopjo menunë e një dite te ditët e tjera"):
        c1, c2, c3 = st.columns([1, 2, 1])
        src = c1.selectbox("Nga dita", range(len(DAYS)), format_func=lambda i: DAYS[i].title(), key="mp_copy_src")
        tgt = c2.multiselect("Te ditët", [i for i in range(len(DAYS)) if i != src],
                             format_func=lambda i: DAYS[i].title(), key="mp_copy_tgt")
        c3.write("")
        c3.button("Kopjo", on_click=_copy_day, args=(src, tgt), disabled=not tgt)
        st.button("🧹 Pastro të gjithë menunë", on_click=_clear_menu)

    # ---------- 4. Shënime, lista, nënshkrimi ----------
    st.subheader("4. Shënime dhe nënshkrimi")
    c1, c2 = st.columns(2)
    c1.text_area("Shënime", key="mp_shenime", height=150,
                 placeholder="> Çdo mëngjes fillo me 1 gotë ujë me fara chia dhe limon\n"
                             "> Sallatat me max 1 lugë të madhe vaj, pa majonezë...")
    c2.text_area("Lista ushqimore (opsionale)", key="mp_lista", height=150)
    st.text_input("Përgatitur nga", key="mp_pergatitur", placeholder="p.sh. Doc.Dr. ...")

    plan = _collect_plan()
    st.markdown("---")

    # ---------- 5. Ruaj / Eksporto ----------
    st.subheader("5. Ruaj dhe eksporto")
    if not plan["emri"]:
        st.warning("Plotëso emrin e klientit për të ruajtur/eksportuar planin.")
        return

    file_base = f"Plan_ushqimor_{plan['titulli'].split()[-1]}_{initials(plan['emri'])}"
    c1, c2, c3 = st.columns(3)
    c1.download_button("⬇️ Shkarko Excel", data=build_meal_plan_xlsx(plan),
                       file_name=f"{file_base}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       type="primary")
    c2.download_button("⬇️ Shkarko PDF", data=build_meal_plan_pdf(plan),
                       file_name=f"{file_base}.pdf", mime="application/pdf")

    if db.is_configured():
        loaded = st.session_state.get("mp_loaded_id")
        label = f"💾 Përditëso planin #{loaded}" if loaded else "💾 Ruaj planin në bazën e të dhënave"
        if c3.button(label):
            record = {
                "klient_id": st.session_state.get("mp_klient_id"),
                "emri": plan["emri"], "titulli": plan["titulli"],
                "data_fillimit": plan["data_fillimit"].isoformat() if plan["data_fillimit"] else None,
                "data_mbarimit": plan["data_mbarimit"].isoformat() if plan["data_mbarimit"] else None,
                "permbajtja": _plan_to_json(plan),
            }
            new_id = db.save_meal_plan(record, plan_id=loaded)
            if new_id:
                st.session_state["mp_loaded_id"] = new_id
                st.success(f"Plani u ruajt (#{new_id}).")
    else:
        c3.caption("Ruajtja e planeve kërkon Supabase të konfiguruar.")

    # ---------- 6. Planet e ruajtura ----------
    if db.is_configured():
        _render_saved_plans(plan["emri"])


def _render_saved_plans(current_name):
    st.markdown("---")
    st.subheader("🗂️ Planet e ruajtura")
    df = db.load_meal_plans()
    if df.empty:
        st.info("Ende s'ka plane të ruajtura.")
        return
    only_this = st.checkbox(f"Vetëm planet e klientit: {current_name}", value=True)
    if only_this:
        df = df[df["emri"].str.strip().str.lower() == current_name.strip().lower()]
    if df.empty:
        st.info("Ky klient s'ka ende plane të ruajtura.")
        return

    for _, row in df.iterrows():
        d0 = row.get("data_fillimit") or "..."
        d1 = row.get("data_mbarimit") or "..."
        c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
        c1.markdown(f"**{row['titulli']}** — {row['emri']}  \n{d0} → {d1}  ·  #{row['id']}")
        c2.button("✏️ Hap", key=f"mp_open_{row['id']}", on_click=_load_plan_into_state,
                  args=(row.to_dict(), False), help="Hap këtë plan për ta ndryshuar")
        c3.button("📄 Kopjo si plan i ri", key=f"mp_copy_{row['id']}", on_click=_load_plan_into_state,
                  args=(row.to_dict(), True),
                  help="Nis planin pasardhës (p.sh. Plani 2) me këtë menu si bazë")
        if c4.button("🗑️ Fshij", key=f"mp_del_{row['id']}"):
            if db.delete_meal_plan(row["id"]):
                if st.session_state.get("mp_loaded_id") == row["id"]:
                    st.session_state["mp_loaded_id"] = None
                st.rerun()
