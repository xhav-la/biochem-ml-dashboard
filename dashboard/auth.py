# -*- coding: utf-8 -*-
"""
auth.py
=========
Portë e thjeshtë me fjalëkalim për dashboard-in. Fjalëkalimi RUHET në
Streamlit Secrets (`.streamlit/secrets.toml` lokalisht -- kurrë mos e
commito në git! -- ose në "Secrets" të Streamlit Community Cloud kur
publikohet online).

Përdorim: thirr `require_login()` në krye të `app.py`, para çdo
përmbajtjeje tjetër. Nëse fjalëkalimi është i saktë, vazhdon normalisht;
përndryshe ndalon ekzekutimin (st.stop()).
"""
import hashlib
import streamlit as st


def _hash(txt: str) -> str:
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()


def require_login():
    if st.session_state.get("authenticated", False):
        return  # tashmë i loguar këtë sesion

    st.title("🔒 Sistemi ML - Parametra Biokimikë")
    st.caption("Ky dashboard përmban të dhëna reale shëndetësore -- kërkohet fjalëkalim.")

    pwd = st.text_input("Fjalëkalimi", type="password")
    submitted = st.button("Hyr")

    try:
        real_password = st.secrets["app_password"]
    except (KeyError, FileNotFoundError):
        st.error(
            "⚠️ Fjalëkalimi nuk është konfiguruar ende. Shto `app_password` te "
            "`.streamlit/secrets.toml` (lokalisht) ose te 'Secrets' në Streamlit "
            "Community Cloud (online)."
        )
        st.stop()

    if submitted:
        if _hash(pwd) == _hash(real_password):
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Fjalëkalim i pasaktë.")
            st.stop()
    else:
        st.stop()
