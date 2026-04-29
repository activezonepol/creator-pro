# data_utils.py

import streamlit as st
from datetime import date, datetime
from renderer import EXCLUDE_EXPORT_KEYS

def _build_proj_dict():
    proj = {}
    
    # Klucze techniczne Streamlita i inne śmieci
    internal_keys = ['_upload_status', '_save_count', '_last_save']
    
    for k, v in st.session_state.items():
        # 1. KLUCZOWY FILTR: Ignoruj wszystko co zaczyna się od 'up_'
        # To tutaj odrzucamy te ciężkie pliki, które ważyły 8MB
        if k.startswith('up_') or k.startswith('_') or k in internal_keys:
            continue
            
        # 2. FILTR TYPÓW: Zapisuj tylko lekkie dane (tekst, linki, liczby)
        if not isinstance(v, (str, int, float, bool, list, dict, date, datetime)) or v is None:
            continue

        # 3. BEZPIECZNIK: Jeśli string jest nienaturalnie długi (>10 tyś znaków)
        # i nie jest linkiem, to znaczy że to ukryte zdjęcie - pomin je.
        if isinstance(v, str) and len(v) > 10000 and not v.startswith("http"):
            continue

        try:
            if isinstance(v, (date, datetime)):
                proj[k] = v.isoformat()
            else:
                proj[k] = v
        except Exception:
            pass
            
    return proj
