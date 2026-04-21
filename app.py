"""
app.py
======
Punkt wejścia aplikacji Streamlit.
Importuje renderer.py i obsługuje cały sidebar (panel edycji),
tryb klienta oraz akcje globalne.
"""

import re
import json
import base64
from datetime import date, datetime
import uuid

import streamlit as st
import streamlit.components.v1 as components

from renderer import (
    COUNTRIES_DICT, FONTS_LIST, hotel_icons, icon_map, defaults, IMAGE_KEYS,
    EXCLUDE_EXPORT_KEYS, pl_days_map,
    clean_str, create_slug, parse_date_and_days, load_project_data,
    get_project_filename, auto_generate_kosztorys, build_day_options,
    optimize_img, optimize_logo, geocode_place, generate_map_data,
    get_road_distance, format_duration,
    get_local_css, build_presentation,
)

# ---------------------------------------------------------------------------
# KONFIGURACJA STRONY
# ---------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Activezone Oferta", initial_sidebar_state="expanded")

st.markdown("""
<style>
div.stButton > button {
    border-radius: 4px !important;
    font-family: 'Montserrat', sans-serif !important;
    text-transform: uppercase !important;
    font-size: 12px !important;
    letter-spacing: 1px !important;
    font-weight: 600 !important;
}
div.stDownloadButton > button {
    border-radius: 4px !important;
    font-family: 'Montserrat', sans-serif !important;
    text-transform: uppercase !important;
    font-size: 12px !important;
    letter-spacing: 1px !important;
    font-weight: 600 !important;
}
div.stDownloadButton > button svg { display: none !important; }
div[data-testid="stExpander"] {
    border-radius: 4px !important;
    border: 1px solid #e2e8f0 !important;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# INICJALIZACJA SESSION STATE & FILTR UPLOADERÓW
# ---------------------------------------------------------------------------
if 'client_mode' not in st.session_state:
    st.session_state['client_mode'] = False

# Identyfikatory uploaderów — NIE MOŻNA ich przywracać z backupu, bo Streamlit wyrzuca błąd.
_UPLOADER_KEYS_EXACT = {
    'tyt_hero', 'tyt_logo_az', 'tyt_logo_cli', 'kie_hero', 'lot_hero',
    'app_bg', 'app_sc', 'bra_img_1', 'bra_img_2', 'bra_img_3',
    'va_img_1', 'va_img_2', 'va_img_3', 'pg_img_1', 'pg_img_2', 'pg_img_3',
    'koszt_img_1', 'koszt_img_2', 'opi_main', 'nas_clients',
}
_UPLOADER_KEYS_REGEX = re.compile(
    r'^(uh1|uh1b|uh2|uh3|prg_img|plc_img1|plc_img2|plc_img3|plc_img4|'
    r'atr_hero|atr_th1|atr_th2|atr_th3|opi_img|nas_img|sek_img_up)_\d+$'
)

def _is_uploader_key(k):
    if k in _UPLOADER_KEYS_EXACT: return True
    if k.startswith('up_'): return True
    if _UPLOADER_KEYS_REGEX.match(k): return True
    return False

# 1. TARCZA OCHRONNA (Przywraca stary stan z pominięciem plików, co naprawia błędy z cache)
if 'STATE_BACKUP' in st.session_state:
    for k, v in st.session_state['STATE_BACKUP'].items():
        if k not in st.session_state and not _is_uploader_key(k):
            st.session_state[k] = v

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.session_state.setdefault('num_sekcje', 4)

_COLOR_DEFS = {
    'color_h1': '#003366', 'color_h2': '#003366', 'color_sub': '#FF6600',
    'color_accent': '#FF6600', 'color_text': '#333333', 'color_metric': '#003366',
}
_SIZE_DEFS = {
    'font_size_h1': 48, 'font_size_h2': 36, 'font_size_sub': 26,
    'font_size_text': 14, 'font_size_metric': 16,
}
for _k, _v in _COLOR_DEFS.items():
    _cur = st.session_state.setdefault(_k, _v)
    if not (isinstance(_cur, str) and _cur.startswith('#') and len(_cur) == 7):
        st.session_state[_k] = _v
for _k, _v in _SIZE_DEFS.items():
    _cur = st.session_state.setdefault(_k, _v)
    try:
        st.session_state[_k] = max(8, int(float(_cur or _v)))
    except Exception:
        st.session_state[_k] = _v

# ---------------------------------------------------------------------------
# AUTO-ZAPIS / AUTO-ODCZYT
# ---------------------------------------------------------------------------
if '_session_id' not in st.session_state:
    st.session_state['_session_id'] = uuid.uuid4().hex[:12]
_LS_KEY = f"activezone_{st.session_state['_session_id']}"

if '_ls_loaded' not in st.session_state:
    st.session_state['_ls_loaded'] = False

_qp = st.query_params.to_dict()
if _qp.get('_ls_restore') and not st.session_state.get('_ls_loaded'):
    try:
        _restored = json.loads(base64.b64decode(_qp['_ls_restore']).decode())
        load_project_data(_restored)
        st.session_state['_ls_loaded'] = True
        st.query_params.clear()
        st.rerun()
    except Exception:
        st.session_state['_ls_loaded'] = True
        st.query_params.clear()

# ---------------------------------------------------------------------------
# HELPERY UI
# ---------------------------------------------------------------------------
def set_focus(target_id):
    st.session_state['scroll_target'] = target_id

def _get_hotel_order():
    s = st.session_state
    n = s.get('num_hotels', 1)
    order = s.get('hotel_order', [])
    valid = list(range(n))
    order = [i for i in order if i in valid]
    for i in valid:
        if i not in order:
            order.append(i)
    s['hotel_order'] = order
    return order

def _move_hotel(idx, direction):
    order = _get_hotel_order()
    new_idx = idx + direction
    if 0 <= new_idx < len(order):
        order[idx], order[new_idx] = order[new_idx], order[idx]
        st.session_state['hotel_order'] = order

# -----------------------------------------------------------------------
# ZARZĄDZANIE LISTĄ OPISÓW ATRAKCJI I MIEJSC (pa_items)
# -----------------------------------------------------------------------
def _pa_items_get():
    s = st.session_state
    items = s.get('pa_items', [])
    np_ = s.get('num_places', 0)
    na_ = s.get('num_attr', 0)
    items = [it for it in items
             if (it['type'] == 'place' and it['idx'] < np_)
             or (it['type'] == 'attr'  and it['idx'] < na_)]
    s['pa_items'] = items
    return items

def _pa_items_add(typ):
    s = st.session_state
    if typ == 'place':
        idx = s.get('num_places', 0)
        s['num_places'] = idx + 1
    else:
        idx = s.get('num_attr', 0)
        s['num_attr'] = idx + 1
    items = _pa_items_get()
    items.append({'type': typ, 'idx': idx})
    s['pa_items'] = items
    s['last_page'] = f"  ↳ pa_{typ}_{idx}"
    s['scroll_target'] = ""
    return idx

def _pa_items_move(pos, direction):
    items = _pa_items_get()
    new_pos = pos + direction
    if 0 <= new_pos < len(items):
        items[pos], items[new_pos] = items[new_pos], items[pos]
        st.session_state['pa_items'] = items

def _pa_items_delete(pos):
    items = _pa_items_get()
    if 0 <= pos < len(items):
        items.pop(pos)
        st.session_state['pa_items'] = items
        st.session_state['last_page'] = "Program Wyjazdu"

def _pa_page_name(typ, idx):
    return f"  ↳ pa_{typ}_{idx}"

def _pa_display_name(typ, idx):
    s = st.session_state
    items = s.get('pa_items', [])
    type_pos = next(
        (pos + 1 for pos, it in enumerate([i for i in items if i['type'] == typ])
         if it['idx'] == idx),
        idx + 1
    )
    if typ == 'place':
        n = str(s.get(f'pmain_{idx}', '')).split('\n')[0][:25].strip()
        return n or f'Opis miejsca {type_pos}'
    else:
        n = str(s.get(f'amain_{idx}', '')).split('\n')[0][:25].strip()
        return n or f'Atrakcja {type_pos}'

def _rebuild_slide_order():
    _get_hotel_order()
    _pa_items_get()

def _build_proj_dict():
    proj = {}
    skip_prefixes = ('FormSubmitter', '$$', 'fn_', 'dl_', 'btn_', 'sb_', 'pa_add_')
    internal_keys = {'_session_id', '_ls_loaded', '_ls_restore', '_scroll_pos', 'ready_export_html', 'show_link_info', 'STATE_BACKUP'}
    
    for k, v in st.session_state.items():
        if k in EXCLUDE_EXPORT_KEYS or k in internal_keys: continue
        if any(k.startswith(p) for p in skip_prefixes): continue
        if _is_uploader_key(k): continue  # Funkcja z góry chroni przed zrzuceniem uploadera!
        
        try:
            if isinstance(v, bytes): proj[k] = base64.b64encode(v).decode()
            elif isinstance(v, (date, datetime)): proj[k] = v.isoformat()
            elif isinstance(v, (str, int, float, bool, list, dict)) or v is None: proj[k] = v
        except Exception: pass
    return proj

def section_template_manager(section_keys, file_prefix, default_filename, uploader_key, index=None):
    ATR_KEY_MAP = {"atype": "type", "amain": "main", "asub": "sub", "aopis": "opis"}
    _acc = st.session_state.get('color_accent', '#FF6600')
    st.markdown(f"<div style='font-size:10px;font-weight:700;color:{_acc};text-transform:uppercase;margin-top:15px;margin-bottom:10px;letter-spacing:1.5px;'>Zarządzanie szablonem sekcji</div>", unsafe_allow_html=True)
    _cl, _cr = st.columns(2)

    with _cl:
        st.markdown(f"<div style='border:1px solid #e2e8f0;border-radius:8px;padding:10px;background:#fff;margin-bottom:4px;'><div style='font-size:9px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;'>Wczytywanie</div>", unsafe_allow_html=True)
        uploaded_file = st.file_uploader("max. 200 MB", type=['json'], key=f"up_{uploader_key}")
        if st.button("↑ WCZYTAJ", key=f"btn_apply_{uploader_key}", use_container_width=True, disabled=not uploaded_file):
            try:
                data = json.load(uploaded_file)
                filtered_data = {}
                for k in section_keys:
                    save_key = k
                    load_key = k if index is None else re.sub(f'_{index}$', '', k)
                    if file_prefix == "ATR": load_key = ATR_KEY_MAP.get(load_key, load_key)
                    if load_key in data: filtered_data[save_key] = data[load_key]
                load_project_data(filtered_data)
                st.success("Wczytano.")
                st.rerun()
            except Exception: st.error("Błąd odczytu.")
        st.markdown("</div>", unsafe_allow_html=True)

    with _cr:
        export_data = {}
        for k in section_keys:
            save_key = k if index is None else re.sub(f'_{index}$', '', k)
            if file_prefix == "ATR": save_key = ATR_KEY_MAP.get(save_key, save_key)
            val = st.session_state.get(k)
            if val is not None:
                if isinstance(val, bytes): export_data[save_key] = base64.b64encode(val).decode('utf-8')
                elif isinstance(val, (date, datetime)): export_data[save_key] = val.isoformat()
                else: export_data[save_key] = val
        json_str = json.dumps(export_data)
        cc = st.session_state.get('country_code', 'OTH')
        base_slug = create_slug(default_filename)
        full_filename = f"{cc}-{file_prefix}-{base_slug}.json"
        _display = default_filename.replace("_", " ").title() if default_filename else "Slajd"
        st.markdown(f"<div style='border:1px solid #e2e8f0;border-radius:8px;padding:10px;background:#fff;margin-bottom:4px;'><div style='font-size:9px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1px;margin-bottom:6px;'>Pobieranie</div><div style='background:#f8fafc;border:1px solid #e2e
