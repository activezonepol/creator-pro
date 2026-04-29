# data_utils.py

import streamlit as st
from datetime import date, datetime
from renderer import EXCLUDE_EXPORT_KEYS

def _build_proj_dict():
    """Serializuje session_state do słownika gotowego do zapisu JSON."""
    proj = {}
    
    # Pomiń klucze techniczne, widgety oraz bufory z my_components
    skip_prefixes = ('FormSubmitter', '$$', 'up_', 'fn_', 'dl_', 'btn_', 'sb_', 'pa_add_', 'sek_img_up',
                     'attr_add_btn', 'attrnav_', 'attrup_', 'attrdn_', 'attrdel_', 'attr_select',
                     'nav_top_radio', 'nav_bot_radio', '_hash_', '_bytes_', 'buffer_', 'temp_')
                     
    internal_keys = {'_session_id', '_ls_loaded', '_ls_restore', '_scroll_pos',
                     'ready_export_html', 'show_link_info', '_attr_focused', 'STATE_BACKUP',
                     '_supabase_data', '_loaded_from_supabase', 'last_supabase_save', 
                     'last_save_status', '_user_edited', '_debug_loaded', 'last_save_count'}
                     
    for k, v in st.session_state.items():
        if k in EXCLUDE_EXPORT_KEYS or k in internal_keys:
            continue
        if any(k.startswith(p) for p in skip_prefixes):
            continue
            
        # 1. ABSOLUTNA BLOKADA: Ignorujemy surowe bajty (zdjęcia w RAM)
        if isinstance(v, bytes):
            continue
            
        # 2. ABSOLUTNA BLOKADA: Ignorujemy gigantyczne kody starych zdjęć Base64.
        # Przepuszczamy tylko krótkie teksty i publiczne linki HTTP ze Storage.
        if isinstance(v, str) and len(v) > 50000 and not v.startswith("http"):
            continue
            
        try:
            if isinstance(v, (date, datetime)):
                proj[k] = v.isoformat()
            elif isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                proj[k] = v
        except Exception:
            pass
            
    return proj
