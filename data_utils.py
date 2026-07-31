# data_utils.py
import streamlit as st
from datetime import date, datetime
from renderer import is_offer_data_key

def _build_proj_dict():
    """
    Buduje słownik danych oferty do zapisu (Supabase / plik JSON).
    JEDYNY filtr: is_offer_data_key() - allowlist współdzielona z odczytem
    (renderer.load_project_data / force_load_project_data). Dzięki temu
    elementy interfejsu (przyciski, selectboxy, kontrolki nawigacji) nigdy
    nie trafiają do zapisanych danych - niezależnie od tego, jaki mają typ
    Pythona czy jak długi jest ich tekst.
    """
    proj = {}
    if 'f1_wylot' in st.session_state:
        st.write(f"DEBUG: f1_wylot w session_state = {st.session_state['f1_wylot']!r}, is_offer_data_key = {is_offer_data_key('f1_wylot')}")
    for k, v in st.session_state.items():
        if not is_offer_data_key(k):
            continue
        if v is None:
            continue
        if not isinstance(v, (str, int, float, bool, list, dict, date, datetime)):
            continue
        try:
            if isinstance(v, (date, datetime)):
                proj[k] = v.isoformat()
            else:
                proj[k] = v
        except Exception:
            pass
    return proj
