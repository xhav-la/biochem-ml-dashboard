# -*- coding: utf-8 -*-
"""
db.py
=======
Lidhja me Supabase (PostgreSQL falas) për ruajtje TË PËRHERSHME të
klientëve të futur në faqen "➕ Pacient i Ri".

DIZAJN: nëse kredencialet (`supabase_url` / `supabase_key`) nuk janë
konfiguruar ende te Secrets, funksionet këtu kthejnë `None`/listë bosh
në vend që të thyejnë aplikacionin -- dashboard-i vazhdon të punojë
normalisht (vetëm pa ruajtje të përhershme, çka ishte sjellja fillestare
me session_state).
"""
import streamlit as st
import pandas as pd

TABLE = "klientet"


@st.cache_resource(show_spinner=False)
def _get_client():
    """Kthen klientin Supabase, ose None nëse s'është konfiguruar."""
    try:
        from supabase import create_client
        url = st.secrets["supabase_url"]
        key = st.secrets["supabase_key"]
    except (KeyError, FileNotFoundError, ImportError):
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


def is_configured() -> bool:
    return _get_client() is not None


def save_client(record: dict):
    """
    Ruan një klient të ri. `record` duhet të përputhet me kolonat e
    tabelës `klientet` (shih supabase_setup.sql). Kthen True/False.
    """
    client = _get_client()
    if client is None:
        return False
    try:
        client.table(TABLE).insert(record).execute()
        return True
    except Exception as e:
        st.warning(f"Ruajtja në bazën e të dhënave dështoi: {e}")
        return False


def load_all_clients() -> pd.DataFrame:
    """Kthen TË GJITHË klientët e ruajtur, më të rejtë së pari. DataFrame bosh nëse s'ka lidhje."""
    client = _get_client()
    if client is None:
        return pd.DataFrame()
    try:
        res = client.table(TABLE).select("*").order("krijuar_me", desc=True).execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.warning(f"Leximi nga baza e të dhënave dështoi: {e}")
        return pd.DataFrame()


def delete_client(client_id):
    client = _get_client()
    if client is None:
        return False
    try:
        client.table(TABLE).delete().eq("id", client_id).execute()
        return True
    except Exception:
        return False
