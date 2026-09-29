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
import re
import streamlit as st
import pandas as pd

TABLE = "klientet"

# Nën-rrugë API që ndonjëherë ngjiten gabimisht bashkë me Project URL
# (p.sh. kopjuar nga faqja "Data API" në vend të "Project Settings -> API")
_API_SUBPATHS = re.compile(r"/(rest|auth|storage|realtime|functions|graphql)/v\d+/?$")


def _normalize_url(raw: str) -> str:
    """
    Pastron supabase_url pavarësisht si u ngjit: heq hapësira, thonjëza
    rrethuese, '/' në fund, dhe çdo nën-rrugë API (/rest/v1, etj.) të
    ngjitur gabimisht -- shkak i zakonshëm i gabimit PGRST125.
    """
    if not raw:
        return raw
    url = raw.strip().strip('"').strip("'").rstrip("/")
    url = _API_SUBPATHS.sub("", url).rstrip("/")
    return url


@st.cache_resource(show_spinner=False)
def _get_client():
    """Kthen klientin Supabase, ose None nëse s'është konfiguruar."""
    try:
        from supabase import create_client
        url = _normalize_url(st.secrets["supabase_url"])
        key = st.secrets["supabase_key"].strip().strip('"').strip("'")
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
