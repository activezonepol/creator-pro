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

import streamlit as st

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
st.set_page_config(layout="wide", page_title="Activezone Oferta",
                   initial_sidebar_state="expanded")

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
# INICJALIZACJA SESSION STATE I FILTR UPLOADERÓW
# ---------------------------------------------------------------------------
if 'client_mode' not in st.session_state:
    st.session_state['client_mode'] = False

# Identyfikatory uploaderów — NIE MOŻNA ich przywracać z backupu, bo Streamlit wyrzuca błąd
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

# 1. TARCZA OCHRONNA (Przywraca stary stan z pominięciem plików, co naprawia błędy)
if 'RAW_STATE_BACKUP' in st.session_state:
    for k, v in st.session_state['RAW_STATE_BACKUP'].items():
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
        _int_val = max(8, int(float(_cur or _v)))
        if _int_val != _cur:  
            st.session_state[_k] = _int_val
    except Exception:
        st.session_state[_k] = _v

# ---------------------------------------------------------------------------
# AUTO-ZAPIS / AUTO-ODCZYT z localStorage przeglądarki
# ---------------------------------------------------------------------------
_LS_KEY = "activezone_project_v1"

if '_ls_loaded' not in st.session_state:
    st.session_state['_ls_loaded'] = False

_qp = st.query_params.to_dict()
if _qp.get('_ls_restore') and not st.session_state.get('_ls_loaded'):
    _ls_val = _qp['_ls_restore']
    if _ls_val != 'empty':
        try:
            _restored = json.loads(base64.b64decode(_ls_val).decode())
            load_project_data(_restored)
        except Exception:
            pass
    st.session_state['_ls_loaded'] = True
    st.query_params.clear()
    st.rerun()

if not st.session_state.get('_ls_loaded'):
    import streamlit.components.v1 as _comp_init
    _comp_init.html(f"""<script>
    (function() {{
        try {{
            var data = localStorage.getItem('{_LS_KEY}');
            var b64 = data ? btoa(unescape(encodeURIComponent(data))) : 'empty';
            var url = window.parent.location.href.split('?')[0].split('#')[0];
            window.parent.location.href = url + '?_ls_restore=' + b64;
        }} catch(e) {{
            var url = window.parent.location.href.split('?')[0].split('#')[0];
            window.parent.location.href = url + '?_ls_restore=empty';
        }}
    }})();
    </script>""", height=0)

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
def _attr_count():
    return st.session_state.get('num_attr', 0)

def _attr_order():
    n = _attr_count()
    raw = st.session_state.get('attr_order', [])
    seen = set()
    order = []
    for i in raw:
        if i not in seen and i < n:
            seen.add(i)
            order.append(i)
    for i in range(n):
        if i not in seen:
            order.append(i)
    st.session_state['attr_order'] = order
    return order

def _attr_add():
    n = st.session_state.get('num_attr', 0)
    st.session_state['num_attr'] = n + 1
    order = st.session_state.get('attr_order', list(range(n)))
    order = [i for i in order if i < n]
    order.append(n)
    st.session_state['attr_order'] = order
    st.session_state['last_page'] = f"ATTR:{n}"
    st.session_state['scroll_target'] = ""

def _attr_move(pos, direction):
    order = _attr_order()
    new_pos = pos + direction
    if 0 <= new_pos < len(order):
        order[pos], order[new_pos] = order[new_pos], order[pos]
        st.session_state['attr_order'] = order

def _attr_delete(pos):
    order = _attr_order()
    if pos < len(order):
        order.pop(pos)
        st.session_state['attr_order'] = order
        st.session_state['last_page'] = "  ↳ Przerywnik atrakcje"
        st.session_state['_attr_focused'] = None

def _attr_page_name(pos):
    order = _attr_order()
    idx = order[pos] if pos < len(order) else pos
    return f"ATTR:{idx}"

def _attr_display_name(pos):
    order = _attr_order()
    idx = order[pos] if pos < len(order) else pos
    name = str(st.session_state.get(f'amain_{idx}', '')).split('\n')[0][:25].strip()
    return name or f"Atrakcja {pos + 1}"

def _get_place_attr_order():
    order = _attr_order()
    return [['attr', i] for i in order]

def _move_place_attr(pos, direction):
    _attr_move(pos, direction)

def _rebuild_slide_order():
    _get_hotel_order()
    _attr_order()

def _build_proj_dict():
    proj = {}
    skip_prefixes = ('FormSubmitter', '$$', 'up_', 'fn_', 'dl_', 'btn_', 'sb_', 'pa_add_', 'sek_img_up')
    # Omijamy wszystkie tarcze, żeby się nie zapętlało w JSON
    internal_keys = {'_session_id', '_ls_loaded', '_ls_restore', '_scroll_pos',
                     'ready_export_html', 'show_link_info', '_attr_focused', 'STATE_BACKUP', 'RAW_STATE_BACKUP'}
    skip_keys = {
        'tyt_hero', 'tyt_logo_az', 'tyt_logo_cli', 'kie_hero', 'kie_th1', 'kie_th2', 'kie_th3', 'lot_hero',
        'app_bg', 'app_sc', 'bra_img_1', 'bra_img_2', 'bra_img_3', 'va_img_1', 'va_img_2', 'va_img_3',
        'pg_img_1', 'pg_img_2', 'pg_img_3', 'koszt_img_1', 'koszt_img_2', 'opi_main', 'nas_clients',
        'sek_img_up_0', 'sek_img_up_1', 'sek_img_up_2', 'sek_img_up_3', 'plc_img3_0', 'plc_img4_0',
    }
    dyn_skip = re.compile(
        r'^(uh1|uh1b|uh2|uh3|prg_img|'
        r'plc_img1|plc_img2|plc_img3|plc_img4|'
        r'atr_hero|atr_th1|atr_th2|atr_th3|'
        r'opi_img|nas_img|sek_img_up)_\d+$'
    )
    for k, v in st.session_state.items():
        if k in EXCLUDE_EXPORT_KEYS or k in internal_keys: continue
        if any(k.startswith(p) for p in skip_prefixes): continue
        if k in skip_keys or dyn_skip.match(k): continue
        try:
            if isinstance(v, bytes): proj[k] = base64.b64encode(v).decode()
            elif isinstance(v, (date, datetime)): proj[k] = v.isoformat()
            elif isinstance(v, (str, int, float, bool, list, dict)) or v is None: proj[k] = v
        except Exception: pass
    return proj

def section_template_manager(section_keys, file_prefix, default_filename, uploader_key, index=None):
    ATR_KEY_MAP = {"atype": "type", "amain": "main", "asub": "sub", "aopis": "opis"}
    _acc = st.session_state.get('color_accent', '#FF6600')

    st.markdown(
        f"<div style='font-size:10px;font-weight:700;color:{_acc};text-transform:uppercase;"
        f"margin-top:15px;margin-bottom:10px;letter-spacing:1.5px;'>"
        f"Zarządzanie szablonem sekcji</div>",
        unsafe_allow_html=True,
    )

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

    with st.container():
        st.markdown(
            f"<div style='border:1px solid #e2e8f0;border-radius:10px;padding:10px 14px 4px 14px;margin-bottom:8px;background:#fff;'>"
            f"<span style='font-size:9px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1.5px;'>Pobieranie</span></div>",
            unsafe_allow_html=True,
        )
        _cp1, _cp2 = st.columns(2)
        with _cp1:
            st.markdown(f"<div style='border:1px solid #e2e8f0;border-radius:7px;padding:9px 10px;background:#f8fafc;font-family:Montserrat,sans-serif;font-size:12px;font-weight:600;color:#334155;display:flex;align-items:center;gap:6px;min-height:38px;margin-bottom:8px;'><span style='color:{_acc};'>★</span> {_display}</div>", unsafe_allow_html=True)
        with _cp2:
            st.download_button("↓ POBIERZ", json_str, full_filename, key=f"dl_{uploader_key}", use_container_width=True)

    with st.container():
        st.markdown(
            f"<div style='border:1px solid #e2e8f0;border-radius:10px;padding:10px 14px 4px 14px;margin-bottom:4px;background:#fff;'>"
            f"<span style='font-size:9px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:1.5px;'>Wczytywanie</span></div>",
            unsafe_allow_html=True,
        )
        _cw1, _cw2 = st.columns(2)
        with _cw1:
            uploaded_file = st.file_uploader("JSON", type=['json'], key=f"up_{uploader_key}", label_visibility="collapsed")
        with _cw2:
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
    st.markdown("<div style='margin-bottom:8px;'></div>", unsafe_allow_html=True)

def _section_header(label):
    st.markdown(f"<div style='font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-top: 15px; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; letter-spacing: 1px;'>{label}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# TRYB KLIENTA
# ---------------------------------------------------------------------------
if st.session_state['client_mode']:
    accent_color = st.session_state.get('color_accent', '#FF6600')
    st.markdown(
        f"<style>div.stButton {{ position: fixed !important; top: 20px !important; left: 20px !important; z-index: 999999 !important; width: auto !important; }} div.stButton > button {{ background-color: {accent_color} !important; color: white !important; border: none !important; border-radius: 30px !important; padding: 15px 25px !important; font-family: 'Montserrat', sans-serif !important; font-size: 14px !important; font-weight: 700 !important; box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important; display: flex !important; align-items: center !important; justify-content: center !important; width: auto !important; white-space: nowrap !important; }} div.stButton > button:hover {{ transform: scale(1.02); opacity: 0.9; }}</style>",
        unsafe_allow_html=True,
    )
    if st.button("ZAKOŃCZ PODGLĄD"):
        st.session_state['client_mode'] = False
        st.rerun()
    build_presentation()
    st.stop()

# ---------------------------------------------------------------------------
# SIDEBAR — NAWIGACJA
# ---------------------------------------------------------------------------
with st.sidebar:
    _acc = st.session_state.get('color_accent', '#FF6600')
    _h1c = st.session_state.get('color_h1', '#003366')
    st.markdown(
        f"<style>section[data-testid='stSidebar'] button[kind='primary']{{background-color:{_acc}!important;border-color:{_acc}!important;color:white!important;}} section[data-testid='stSidebar'] [data-testid='stButton']:has(button[key*='aord_up_']) button, section[data-testid='stSidebar'] [data-testid='stButton']:has(button[key*='aord_dn_']) button{{padding:0!important;min-height:22px!important;font-size:11px!important;background:transparent!important;border:none!important;color:#94a3b8!important;box-shadow:none!important;}} section[data-testid='stSidebar'] [data-testid='stButton']:has(button[key*='aord_del_']) button{{padding:0!important;min-height:22px!important;font-size:11px!important;background-color:#ef4444!important;border-color:#ef4444!important;color:white!important;}}</style>",
        unsafe_allow_html=True,
    )
    _n_attr = _attr_count()
    _attr_pages = [_attr_page_name(pos) for pos in range(_n_attr)]

    _nav_top = ["Strona Tytułowa", "Opis Kierunku", "Mapa Podróży", "Jak lecimy?", "  ↳ Przerywnik hotel", "Zakwaterowanie", "  ↳ Przerywnik program", "Program Wyjazdu", "  ↳ Przerywnik atrakcje"]
    _nav_bot = ["Aplikacja (Komunikacja)", "Materiały Brandingowe", "Wirtualny Asystent", "Pillow Gifts", "Kosztorys", "  ↳ Przerywnik o nas", "Co o nas mówią", "O Nas (Zespół)", "Wygląd i Kolory", "Zapisz / Wczytaj Projekt"]
    _nav_all = _nav_top + _attr_pages + _nav_bot
    _last = st.session_state.get('last_page', _nav_all[0])

    def _fmt_nav(p):
        if p.startswith("ATTR:"):
            idx = int(p.split(":")[1])
            pos = next((pos for pos, ix in enumerate(_attr_order()) if ix == idx), 0)
            return "  ★ " + _attr_display_name(pos)
        return p

    _top_idx = _nav_top.index(_last) if _last in _nav_top else None
    page_top = st.radio("WYBIERZ SEKCJE DO EDYCJI:", _nav_top, index=_top_idx)

    st.markdown(f"<div style='display:flex;align-items:center;gap:6px;padding:3px 0 3px 4px;'><span style='color:{_acc};font-size:13px;font-weight:700;'>★</span><span style='font-size:12px;font-weight:600;color:#334155;font-family:Montserrat,sans-serif;'>DODAJ ATRAKCJE/MIEJSCE</span></div>", unsafe_allow_html=True)
    if st.button("＋ Dodaj", key="attr_add_main_btn", use_container_width=True):
        _attr_add()
        st.rerun()

    page_attr = None
    for _ap in range(_n_attr):
        _ap_key = _attr_pages[_ap]
        _ap_active = (_last == _ap_key)
        _ca, _cb, _cc, _cd = st.columns([6, 1, 1, 1])
        if _ca.button(f"★ {_attr_display_name(_ap)}", key=f"attr_nav_{_ap}", use_container_width=True, type="primary" if _ap_active else "secondary"):
            page_attr = _ap_key
        if _ap > 0:
            _cb.button("▲", key=f"aord_up_{_ap}", on_click=_attr_move, args=(_ap, -1), use_container_width=True)
        if _ap < _n_attr - 1:
            _cc.button("▼", key=f"aord_dn_{_ap}", on_click=_attr_move, args=(_ap, 1), use_container_width=True)
        _cd.button("✕", key=f"aord_del_{_ap}", on_click=_attr_delete, args=(_ap,), use_container_width=True)

    st.markdown("""<script>(function() { function styleAttrBtns() { var sidebar = document.querySelector('[data-testid="stSidebar"]'); if (!sidebar) return; sidebar.querySelectorAll('button').forEach(function(btn) { var txt = btn.innerText.trim(); if (txt === '▲' || txt === '▼') { btn.style.cssText += ';min-height:22px!important;height:22px!important;padding:0 2px!important;font-size:11px!important;background:transparent!important;border-color:#e2e8f0!important;color:#94a3b8!important;'; } if (txt === '✕') { btn.style.cssText += ';min-height:22px!important;height:22px!important;padding:0 2px!important;font-size:11px!important;background-color:#dc2626!important;border-color:#dc2626!important;color:white!important;'; } }); } var obs = new MutationObserver(styleAttrBtns); obs.observe(document.body, {childList:true, subtree:true}); styleAttrBtns(); })();</script>""", unsafe_allow_html=True)

    _bot_idx = _nav_bot.index(_last) if _last in _nav_bot else None
    page_bot = st.radio("", _nav_bot, index=_bot_idx, label_visibility="collapsed")

    if page_attr is not None:
        page = page_attr
        st.session_state['last_page'] = page
        st.session_state['scroll_target'] = ""
        st.rerun()
    elif page_top is not None and page_top != _last:
        page = page_top
        st.session_state['last_page'] = page
        st.session_state['scroll_target'] = ""
    elif page_bot is not None and page_bot != _last:
        page = page_bot
        st.session_state['last_page'] = page
        st.session_state['scroll_target'] = ""
    else:
        page = _last if _last in (_nav_top + _attr_pages + _nav_bot) else _nav_top[0]

    _inter_pages = {"  ↳ Przerywnik hotel", "  ↳ Przerywnik program", "  ↳ Przerywnik atrakcje", "  ↳ Przerywnik o nas"}
    _is_attr_page = page.startswith("ATTR:")

    if page == "Wygląd i Kolory":
        st.markdown("<h2 style='color:#003366;margin-bottom:0;font-size:22px;font-weight:700;font-family:Montserrat,sans-serif;'>KONFIGURACJA WYGLĄDU</h2><div style='font-size:13px;color:#64748b;margin-bottom:15px;font-family:Open Sans,sans-serif;'>Dostosuj kolory i typografię oferty</div>", unsafe_allow_html=True)
    elif page == "Zapisz / Wczytaj Projekt":
        st.markdown("<h2 style='color:#003366;margin-bottom:0;font-size:22px;font-weight:700;font-family:Montserrat,sans-serif;'>ZARZĄDZANIE PROJEKTEM</h2><div style='font-size:13px;color:#64748b;margin-bottom:15px;font-family:Open Sans,sans-serif;'>Eksportuj lub importuj cały plik JSON</div>", unsafe_allow_html=True)
    elif page in _inter_pages:
        _h1_col = st.session_state.get("color_h1", "#003366")
        _page_label = page.strip().lstrip("↳").strip()
        st.markdown(f"<h2 style='color:{_h1_col};margin-bottom:0;font-size:20px;font-weight:700;font-family:Montserrat,sans-serif;text-transform:uppercase;margin-left:12px;border-left:3px solid {_h1_col};padding-left:10px;'>{_page_label}</h2><div style='font-size:13px;color:#64748b;margin-bottom:15px;font-family:Open Sans,sans-serif;margin-left:12px;'>Slajd przerywnikowy — edytuj treść i wygląd poniżej.</div>", unsafe_allow_html=True)
    elif _is_attr_page:
        _acc_col = st.session_state.get("color_accent", "#FF6600")
        _attr_idx = int(page.split(":")[1]) if page.startswith("ATTR:") else 0
        _attr_pos = next((p for p, ix in enumerate(_attr_order()) if ix == _attr_idx), 0)
        _label = _attr_display_name(_attr_pos)
        st.markdown(f"<h2 style='color:{_acc_col};margin-bottom:0;font-size:20px;font-weight:700;font-family:Montserrat,sans-serif;margin-left:12px;border-left:3px solid {_acc_col};padding-left:10px;'>★ {_label}</h2><div style='font-size:13px;color:#64748b;margin-bottom:15px;font-family:Open Sans,sans-serif;margin-left:12px;'>Edytuj treść slajdu atrakcji poniżej.</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h2 style='color:#003366;margin-bottom:0;font-size:22px;font-weight:700;font-family:Montserrat,sans-serif;text-transform:uppercase;'>{page}</h2><div style='font-size:13px;color:#64748b;margin-bottom:15px;font-family:Open Sans,sans-serif;'>Wprowadź dane dla tej sekcji poniżej:</div>", unsafe_allow_html=True)

    if page == "  ↳ Przerywnik hotel":
        _bg_default = st.session_state.get('color_h1', '#003366')
        for _ck, _cv in [(f"sek_0_bg", _bg_default), (f"sek_0_txt", '#ffffff')]:
            _v = st.session_state.get(_ck, _cv)
            if not (isinstance(_v, str) and _v.startswith('#') and len(_v) == 7): st.session_state[_ck] = _cv
        st.button("POKAŻ PODGLĄD", key=f"btn_sek_0", on_click=set_focus, args=(f"slide-sek_0",), use_container_width=True)
        st.checkbox("Ukryj ten slajd w prezentacji", key=f"sek_hide_0")
        st.text_input("Duży tytuł (uppercase):", key=f"sek_0_title", value=st.session_state.get(f"sek_0_title", "ZAKWATEROWANIE"))
        st.text_input("Nadtytuł (overline, kolor akcentu):", key=f"sek_0_sub", value=st.session_state.get(f"sek_0_sub", "NASZE HOTELE"))
        _ic1, _ic2 = st.columns(2)
        _ic1.color_picker("Kolor gradientu/tła:", key=f"sek_0_bg")
        _ic2.color_picker("Kolor tytułu:", key=f"sek_0_txt")
        _up_s = st.file_uploader("Zdjęcie tła (16:9):", key=f"sek_img_up_0")
        if _up_s: st.session_state[f"sek_0_img"] = optimize_img(_up_s.getvalue())

    elif page == "  ↳ Przerywnik program":
        _bg_default = st.session_state.get('color_h1', '#003366')
        for _ck, _cv in [(f"sek_3_bg", _bg_default), (f"sek_3_txt", '#ffffff')]:
            _v = st.session_state.get(_ck, _cv)
            if not (isinstance(_v, str) and _v.startswith('#') and len(_v) == 7): st.session_state[_ck] = _cv
        st.button("POKAŻ PODGLĄD", key=f"btn_sek_3", on_click=set_focus, args=(f"slide-sek_3",), use_container_width=True)
        st.checkbox("Ukryj ten slajd w prezentacji", key=f"sek_hide_3")
        st.text_input("Duży tytuł (uppercase):", key=f"sek_3_title", value=st.session_state.get(f"sek_3_title", "PROGRAM"))
        st.text_input("Nadtytuł (overline, kolor akcentu):", key=f"sek_3_sub", value=st.session_state.get(f"sek_3_sub", "NASZ PLAN WYJAZDU"))
        _ic1, _ic2 = st.columns(2)
        _ic1.color_picker("Kolor gradientu/tła:", key=f"sek_3_bg")
        _ic2.color_picker("Kolor tytułu:", key=f"sek_3_txt")
        _up_s = st.file_uploader("Zdjęcie tła (16:9):", key=f"sek_img_up_3")
        if _up_s: st.session_state[f"sek_3_img"] = optimize_img(_up_s.getvalue())

    elif page == "  ↳ Przerywnik atrakcje":
        _bg_default = st.session_state.get('color_h1', '#003366')
        for _ck, _cv in [(f"sek_1_bg", _bg_default), (f"sek_1_txt", '#ffffff')]:
            _v = st.session_state.get(_ck, _cv)
            if not (isinstance(_v, str) and _v.startswith('#') and len(_v) == 7): st.session_state[_ck] = _cv
        st.button("POKAŻ PODGLĄD", key=f"btn_sek_1", on_click=set_focus, args=(f"slide-sek_1",), use_container_width=True)
        st.checkbox("Ukryj ten slajd w prezentacji", key=f"sek_hide_1")
        st.text_input("Duży tytuł (uppercase):", key=f"sek_1_title", value=st.session_state.get(f"sek_1_title", "ATRAKCJE"))
        st.text_input("Nadtytuł (overline, kolor akcentu):", key=f"sek_1_sub", value=st.session_state.get(f"sek_1_sub", "PROGRAM WYJAZDU"))
        _ic1, _ic2 = st.columns(2)
        _ic1.color_picker("Kolor gradientu/tła:", key=f"sek_1_bg")
        _ic2.color_picker("Kolor tytułu:", key=f"sek_1_txt")
        _up_s = st.file_uploader("Zdjęcie tła (16:9):", key=f"sek_img_up_1")
        if _up_s: st.session_state[f"sek_1_img"] = optimize_img(_up_s.getvalue())

    elif page == "  ↳ Przerywnik o nas":
        _bg_default = st.session_state.get('color_h1', '#003366')
        for _ck, _cv in [(f"sek_2_bg", _bg_default), (f"sek_2_txt", '#ffffff')]:
            _v = st.session_state.get(_ck, _cv)
            if not (isinstance(_v, str) and _v.startswith('#') and len(_v) == 7): st.session_state[_ck] = _cv
        st.button("POKAŻ PODGLĄD", key=f"btn_sek_2", on_click=set_focus, args=(f"slide-sek_2",), use_container_width=True)
        st.checkbox("Ukryj ten slajd w prezentacji", key=f"sek_hide_2")
        st.text_input("Duży tytuł (uppercase):", key=f"sek_2_title", value=st.session_state.get(f"sek_2_title", "CO O NAS MÓWIĄ"))
        st.text_input("Nadtytuł (overline, kolor akcentu):", key=f"sek_2_sub", value=st.session_state.get(f"sek_2_sub", "REKOMENDACJE"))
        _ic1, _ic2 = st.columns(2)
        _ic1.color_picker("Kolor gradientu/tła:", key=f"sek_2_bg")
        _ic2.color_picker("Kolor tytułu:", key=f"sek_2_txt")
        _up_s = st.file_uploader("Zdjęcie tła (16:9):", key=f"sek_img_up_2")
        if _up_s: st.session_state[f"sek_2_img"] = optimize_img(_up_s.getvalue())

    elif page == "Strona Tytułowa":
        tit_keys = ['t_date', 'country_name', 'country_code', 't_main', 't_sub', 't_klient', 't_kierunek', 't_pax', 't_hotel', 't_trans', 'img_hero_t', 'logo_az', 'logo_cli', 'hide_logo_cli']
        section_template_manager(tit_keys, "TYT", "strona-tytulowa", "tit")
        st.text_input("Termin:", key="t_date", on_change=parse_date_and_days)
        st.selectbox("Kraj docelowy:", list(COUNTRIES_DICT.keys()), key="country_name")
        st.session_state['country_code'] = COUNTRIES_DICT[st.session_state['country_name']]
        for k, l in [('t_main', 'Tytuł H1'), ('t_sub', 'Podtytuł'), ('t_klient', 'Klient'), ('t_kierunek', 'Kierunek'), ('t_pax', 'Liczba osób'), ('t_hotel', 'Hotel'), ('t_trans', 'Dojazd')]:
            st.text_input(l, key=k)
        u1 = st.file_uploader("Zdjęcie główne (4:5)", key="tyt_hero")
        if u1: st.session_state['img_hero_t'] = optimize_img(u1.getvalue())
        c1, c2 = st.columns(2)
        u2 = c1.file_uploader("Logo Firmy", key="tyt_logo_az")
        if u2: st.session_state['logo_az'] = optimize_logo(u2.getvalue())
        u3 = c2.file_uploader("Logo Klienta", key="tyt_logo_cli")
        if u3: st.session_state['logo_cli'] = optimize_logo(u3.getvalue())
        c2.checkbox("Ukryj logo klienta na stronie tytułowej", key="hide_logo_cli")

    elif page == "Opis Kierunku":
        k_keys = ['k_hide', 'k_overline', 'k_main', 'k_sub', 'k_opis', 'k_facts', 'k_facts_title', 'k_box_bg', 'k_box_txt', 'img_hero_k']
        section_template_manager(k_keys, "KIE", st.session_state.get('k_main', 'czarnogora'), "kie")
        st.checkbox("Ukryj ten slajd w PDF", key="k_hide")
        st.text_input("Mały nadtytuł (overline):", key="k_overline", value=st.session_state.get('k_overline', 'NASZ KIERUNEK'))
        st.text_input("Nazwa kierunku (duży tytuł H1):", key="k_main")
        st.text_input("Podtytuł:", key="k_sub")
        st.text_area("Opis (prawa kolumna):", height=160, key="k_opis", help="Główny opis kierunku po prawej stronie slajdu.")
        _section_header("BOX Z FAKTAMI (lewa kolumna)")
        for _ck, _cv in [('k_box_bg', st.session_state.get('color_h1', '#003366')), ('k_box_txt', '#ffffff')]:
            _v = st.session_state.get(_ck, _cv)
            if not (isinstance(_v, str) and _v.startswith('#') and len(_v) == 7): st.session_state[_ck] = _cv
        cb1, cb2 = st.columns(2)
        cb1.color_picker("Kolor tła boksu", key="k_box_bg")
        cb2.color_picker("Kolor tekstu w boksie", key="k_box_txt")
        st.text_input("Tytuł boksu (np. FAKTY):", key="k_facts_title", value=st.session_state.get('k_facts_title', 'FAKTY'))
        st.text_area("Fakty (Format: 'Etykieta: Wartość'):", height=160, key="k_facts", value=st.session_state.get('k_facts', 'Stolica: \nWaluta: \nRóżnica czasu: \nTemperatury: '), help="Każda linia = jeden wpis. 'Etykieta: Wartość' pogrubia etykietę.")
        _section_header("ZDJĘCIE (jedno zdjęcie w dwóch ramkach)")
        u4 = st.file_uploader("Zdjęcie kierunku:", key="kie_hero")
        if u4: st.session_state['img_hero_k'] = optimize_img(u4.getvalue())

    elif page == "Mapa Podróży":
        map_keys = ['map_hide', 'map_overline', 'map_title', 'map_subtitle', 'map_desc', 'img_map_bg', 'map_zoom', 'num_map_points', 'img_map_bg_auto', 'auto_map_points']
        for i in range(st.session_state.get('num_map_points', 3)): map_keys.extend([f'map_pt_name_{i}', f'map_conn_{i}', f'map_pt_sym_{i}', f'map_pt_x_{i}', f'map_pt_y_{i}'])
        section_template_manager(map_keys, "MAP", "mapa-podrozy", "map")
        st.checkbox("Ukryj slajd", key="map_hide")
        st.text_input("Mały nadtytuł:", key="map_overline")
        st.text_area("Główny tytuł H1:", key="map_title")
        st.text_input("Podtytuł:", key="map_subtitle")
        st.text_area("Opis pod mapą:", height=100, key="map_desc")
        _section_header("AUTOMATYCZNY KREATOR MAPY")
        map_zoom = st.slider("Zoom startowy:", 4, 12, key="map_zoom")
        st.number_input("Liczba punktów na trasie:", 1, 10, step=1, key="num_map_points")
        points_data = []
        for i in range(st.session_state['num_map_points']):
            for dk, dv in [(f'map_pt_name_{i}', f'Punkt {i+1}'), (f'map_conn_{i}', 'Brak'), (f'map_pt_sym_{i}', False), (f'map_pt_x_{i}', 15), (f'map_pt_y_{i}', 10)]:
                if dk not in st.session_state: st.session_state[dk] = dv
            with st.expander(f"Punkt {i+1}", expanded=True):
                st.text_input("Nazwa:", key=f"map_pt_name_{i}")
                st.selectbox("Połączenie:", ["Brak", "Przejazd (Linia ciągła)", "Przelot (Linia przerywana + Samolot)"], key=f"map_conn_{i}")
                pt_sym = st.checkbox("Punkt oddalony (symboliczny)", key=f"map_pt_sym_{i}")
                if pt_sym:
                    c1, c2 = st.columns(2)
                    c1.slider("Pozycja X %:", 0, 100, key=f"map_pt_x_{i}")
                    c2.slider("Pozycja Y %:", 0, 100, key=f"map_pt_y_{i}")
                points_data.append({'name': st.session_state[f"map_pt_name_{i}"], 'conn': st.session_state[f"map_conn_{i}"], 'symbolic': st.session_state[f"map_pt_sym_{i}"], 'x': st.session_state[f"map_pt_x_{i}"], 'y': st.session_state[f"map_pt_y_{i}"]})
        if st.button("GENERUJ MAPĘ", type="primary", use_container_width=True):
            with st.spinner("Pobieranie danych..."):
                country = st.session_state.get('country_name', '')
                valid_pts = []
                for p in points_data:
                    nm = p['name'].strip()
                    if not nm: continue
                    if p['symbolic']: valid_pts.append({'name': nm, 'conn': p['conn'], 'symbolic': True, 'x': p['x'], 'y': p['y']})
                    else:
                        lat, lon = geocode_place(nm, country)
                        if lat is None: lat, lon = geocode_place(nm)
                        if lat is not None: valid_pts.append({'name': nm, 'conn': p['conn'], 'symbolic': False, 'lat': lat, 'lon': lon})
                if valid_pts:
                    try:
                        bg_b64, final_pts = generate_map_data(valid_pts, zoom=map_zoom)
                        if bg_b64 is not None or final_pts:
                            if bg_b64: st.session_state['img_map_bg_auto'] = bg_b64
                            st.session_state['auto_map_points'] = final_pts
                            st.success("Wygenerowano.")
                            st.rerun()
                    except Exception: st.error("Błąd podczas generowania mapy.")
                else: st.warning("Nie udało się zgeokodować żadnego punktu.")
        _section_header("ODLEGŁOŚCI I CZAS DOJAZDU")
        st.text_input("Tytuł sekcji:", key="map_dist_title")
        _ors_from_secrets = st.secrets.get("ORS_API_KEY", "") if hasattr(st, 'secrets') else ""
        if _ors_from_secrets and not st.session_state.get('ors_api_key'): st.session_state['ors_api_key'] = _ors_from_secrets
        if not _ors_from_secrets: st.text_input("Klucz ORS API:", key="ors_api_key", type="password")
        st.number_input("Liczba par miejscowości:", 0, 10, step=1, key="num_dist_pairs")
        for di in range(st.session_state.get('num_dist_pairs', 0)):
            for dk, dv in [(f'dist_a_{di}', ''), (f'dist_b_{di}', ''), (f'dist_km_{di}', '—'), (f'dist_time_{di}', '—')]:
                if dk not in st.session_state: st.session_state[dk] = dv
            with st.expander(f"Para {di+1}", expanded=True):
                ca, cb = st.columns(2)
                ca.text_input("Miejsce A:", key=f"dist_a_{di}")
                cb.text_input("Miejsce B:", key=f"dist_b_{di}")
                if st.button("POBIERZ ODLEGŁOŚĆ", key=f"btn_dist_{di}", use_container_width=True):
                    ors_key = (st.secrets.get("ORS_API_KEY", "") if hasattr(st, 'secrets') else "") or st.session_state.get('ors_api_key', '').strip()
                    a = st.session_state.get(f'dist_a_{di}', '').strip()
                    b = st.session_state.get(f'dist_b_{di}', '').strip()
                    if a and b:
                        with st.spinner("Szukam..."):
                            km, mins, err = get_road_distance(a, b, ors_key, st.session_state.get('country_name', ''))
                        if km is not None:
                            st.session_state[f'dist_km_{di}'] = f'{km}'
                            st.session_state[f'dist_time_{di}'] = format_duration(mins)
                            st.success("Zapisano!")
                            st.rerun()
                cd1, cd2 = st.columns(2)
                cd1.text_input("Odległość (km):", key=f"dist_km_{di}")
                cd2.text_input("Czas dojazdu:", key=f"dist_time_{di}")

    elif page == "Jak lecimy?":
        l_keys = ['l_hide', 'l_przesiadka', 'l_port', 'l_czas', 'l_overline', 'l_main', 'l_sub', 'm_route', 'm_luggage', 'f1', 'f2', 'f3', 'f4', 'l_desc', 'l_extra', 'img_hero_l']
        section_template_manager(l_keys, "LOT", "jak-lecimy", "lot")
        st.checkbox("Ukryj ten slajd w PDF", key="l_hide")
        st.text_input("Mały nadtytuł:", key="l_overline")
        st.text_input("Tytuł (H1):", key="l_main")
        for k, l in [('l_sub', 'Podtytuł'), ('m_route', 'Trasa'), ('m_luggage', 'Bagaż'), ('f1', 'Lot 1'), ('f2', 'Lot 2')]:
            st.text_input(l, key=k)
        if st.checkbox("Lot z przesiadką", key="l_przesiadka"):
            _section_header("DANE PRZESIADKI")
            c1, c2 = st.columns(2)
            c1.text_input("Port przesiadkowy:", key="l_port")
            c2.text_input("Długość przesiadki:", key="l_czas")
            for k, l in [('f3', 'Lot 3'), ('f4', 'Lot 4')]: st.text_input(l, key=k)
        for k, l in [('l_desc', 'Opis'), ('l_extra', 'Dodatkowe info')]:
            st.text_area(l, key=k)
        u5 = st.file_uploader("Foto Samolotu", key="lot_hero")
        if u5: st.session_state['img_hero_l'] = optimize_img(u5.getvalue())

    elif page == "Zakwaterowanie":
        st.number_input("Liczba hoteli:", 1, 3, step=1, key="num_hotels")
        _rebuild_slide_order()
        hotel_order = _get_hotel_order()
        if len(hotel_order) > 1:
            _section_header("KOLEJNOŚĆ HOTELI")
            for pos, hi in enumerate(hotel_order):
                name = str(st.session_state.get(f'h_title_{hi}', f'Hotel {hi+1}')).split('\n')[0][:35] or f'Hotel {hi+1}'
                col_lbl, col_up, col_dn = st.columns([8, 1, 1])
                col_lbl.markdown(f"<div style='padding:6px 10px; background:#f1f5f9; border-radius:4px; border-left:3px solid #003366; font-size:12px;'><strong style='color:#003366;'>Hotel {pos+1}</strong><br>{name}</div>", unsafe_allow_html=True)
                if pos > 0: col_up.button("▲", key=f"ho_up_{pos}", on_click=_move_hotel, args=(pos, -1))
                if pos < len(hotel_order) - 1: col_dn.button("▼", key=f"ho_dn_{pos}", on_click=_move_hotel, args=(pos, 1))
        st.divider()
        for i in range(st.session_state['num_hotels']):
            with st.expander(f"Hotel {i+1}"):
                st.button("POKAŻ PODGLĄD", key=f"btn_show_hot_{i}", on_click=set_focus, args=(f"slide-hotel-{i}",), use_container_width=True)
                for dk, dv in [(f'h_hide_{i}', False), (f'h_overline_{i}', 'ZAKWATEROWANIE'), (f'h_title_{i}', f'NAZWA HOTELU {i+1} 5*'), (f'h_subtitle_{i}', 'Komfort i elegancja'), (f'h_url_{i}', 'www.hotel.com'), (f'h_booking_{i}', '8.9'), (f'h_amenities_{i}', ["Basen", "SPA"]), (f'h_text_{i}', 'Zapewniamy zakwaterowanie.'), (f'h_advantages_{i}', 'Położenie')]:
                    if dk not in st.session_state: st.session_state[dk] = dv
                h_keys = [f'h_hide_{i}', f'h_overline_{i}', f'h_title_{i}', f'h_subtitle_{i}', f'h_url_{i}', f'h_booking_{i}', f'h_amenities_{i}', f'h_text_{i}', f'h_advantages_{i}', f'img_hotel_1_{i}', f'img_hotel_1b_{i}', f'img_hotel_2_{i}', f'img_hotel_3_{i}']
                section_template_manager(h_keys, "HOT", st.session_state.get(f'h_title_{i}', f'hotel-{i+1}'), f"hot_{i}", index=i)
                st.checkbox("Ukryj ten slajd w PDF", key=f"h_hide_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.text_input("Mały nadtytuł:", key=f"h_overline_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.text_area("Nazwa hotelu (H1):", key=f"h_title_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.text_input("Podtytuł:", key=f"h_subtitle_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                c1, c2 = st.columns(2)
                c1.text_input("Strona www:", key=f"h_url_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                c2.text_input("Ocena Booking:", key=f"h_booking_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.multiselect("Udogodnienia (ikonki):", list(hotel_icons.keys()), key=f"h_amenities_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.text_area("Opis hotelu:", height=100, key=f"h_text_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.text_area("Atuty hotelu:", height=100, key=f"h_advantages_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                cl1, cl2 = st.columns(2)
                u_h1 = cl1.file_uploader("Zdj. Lewe Górne", key=f"uh1_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                if u_h1: st.session_state[f'img_hotel_1_{i}'] = optimize_img(u_h1.getvalue())
                u_h1b = cl2.file_uploader("Zdj. Lewe Dolne", key=f"uh1b_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                if u_h1b: st.session_state[f'img_hotel_1b_{i}'] = optimize_img(u_h1b.getvalue())
                c3, c4 = st.columns(2)
                u_h2 = c3.file_uploader("Zdj. Dolne 1", key=f"uh2_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                if u_h2: st.session_state[f'img_hotel_2_{i}'] = optimize_img(u_h2.getvalue())
                u_h3 = c4.file_uploader("Zdj. Dolne 2", key=f"uh3_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                if u_h3: st.session_state[f'img_hotel_3_{i}'] = optimize_img(u_h3.getvalue())

    elif page == "Program Wyjazdu":
        st.checkbox("Ukryj CAŁĄ sekcję Programu w PDF", key="prg_hide")
        st.number_input("Ilość dni:", 1, 15, step=1, key="num_days")
        st.date_input("Data startu:", key="p_start_dt")
        for d in range(st.session_state.get("num_days", 4)):
            with st.expander(f"Dzień {d+1}"):
                for dk in [f"attr_{d}", f"desc_{d}"]:
                    if dk not in st.session_state: st.session_state[dk] = ""
                d_keys = [f'img_d_{d}', f'attr_{d}', f'desc_{d}']
                section_template_manager(d_keys, "PRG", f"Dzien_{d+1}", f"prg_{d}", index=d)
                ud = st.file_uploader(f"Foto D{d+1} (16:9)", key=f"prg_img_{d}")
                if ud: st.session_state[f"img_d_{d}"] = optimize_img(ud.getvalue())
                st.text_input(f"Highlights D{d+1}", key=f"attr_{d}")
                st.text_area(f"Opis D{d+1}", key=f"desc_{d}")

    elif _is_attr_page:
        _i = int(page.split(":")[1]) if page.startswith("ATTR:") else None
        if _i is None or _i >= _attr_count():
            st.warning("Nie znaleziono atrakcji.")
        else:
            _pos = next((p for p, ix in enumerate(_attr_order()) if ix == _i), 0)
            day_options_global = build_day_options(
                st.session_state.get('p_start_dt', date.today()),
                int(st.session_state.get('num_days', 5)),
            )
            for _dk, _dv in [(f"amain_{_i}", ""), (f"asub_{_i}", ""), (f"aday_{_i}", "Brak przypisania"), (f"atype_{_i}", "Atrakcja"), (f"aopis_{_i}", ""), (f"ahide_{_i}", False)]:
                if _dk not in st.session_state: st.session_state[_dk] = _dv

            if st.session_state.get('_attr_focused') != _i:
                st.session_state['_attr_focused'] = _i
                set_focus(f"attr_{_i}")
                
            a_keys = [f'ahide_{_i}', f'amain_{_i}', f'asub_{_i}', f'aday_{_i}', f'atype_{_i}', f'aopis_{_i}', f'ah_{_i}', f'at1_{_i}', f'at2_{_i}', f'at3_{_i}']
            section_template_manager(a_keys, "ATR", st.session_state.get(f"amain_{_i}") or f"Atrakcja_{_pos+1}", f"atr_{_i}", index=_i)
            
            st.checkbox("Ukryj ten slajd w PDF", key=f"ahide_{_i}", on_change=set_focus, args=(f"attr_{_i}",))
            st.text_input("Nazwa:", key=f"amain_{_i}", on_change=set_focus, args=(f"attr_{_i}",))
            st.text_input("Podtytuł:", key=f"asub_{_i}", on_change=set_focus, args=(f"attr_{_i}",))
            _curr = st.session_state.get(f"aday_{_i}", day_options_global[0])
            if _curr not in day_options_global: st.session_state[f"aday_{_i}"] = day_options_global[0]
            st.selectbox("Przypisz do dnia:", day_options_global, key=f"aday_{_i}", on_change=set_focus, args=(f"attr_{_i}",))
            st.selectbox("Ikona:", list(icon_map.keys()), key=f"atype_{_i}", on_change=set_focus, args=(f"attr_{_i}",))
            st.text_area("Opis:", key=f"aopis_{_i}", on_change=set_focus, args=(f"attr_{_i}",))
            _upa = st.file_uploader("Foto Główne", key=f"atr_hero_{_i}", on_change=set_focus, args=(f"attr_{_i}",))
            if _upa: st.session_state[f"ah_{_i}"] = optimize_img(_upa.getvalue())
            _ac1, _ac2, _ac3 = st.columns(3)
            _uat1 = _ac1.file_uploader("Fot. 1", key=f"atr_th1_{_i}", on_change=set_focus, args=(f"attr_{_i}",))
            if _uat1: st.session_state[f"at1_{_i}"] = optimize_img(_uat1.getvalue())
            _uat2 = _ac2.file_uploader("Fot. 2", key=f"atr_th2_{_i}", on_change=set_focus, args=(f"attr_{_i}",))
            if _uat2: st.session_state[f"at2_{_i}"] = optimize_img(_uat2.getvalue())
            _uat3 = _ac3.file_uploader("Fot. 3", key=f"atr_th3_{_i}", on_change=set_focus, args=(f"attr_{_i}",))
            if _uat3: st.session_state[f"at3_{_i}"] = optimize_img(_uat3.getvalue())

    elif page == "Aplikacja (Komunikacja)":
        app_keys = ['app_hide', 'app_overline', 'app_title', 'app_subtitle', 'app_features', 'img_app_bg', 'img_app_screen']
        section_template_manager(app_keys, "APP", "Aplikacja", "app")
        st.checkbox("Ukryj slajd", key="app_hide")
        st.text_input("Mały nadtytuł:", key="app_overline")
        st.text_area("Główny tytuł H1:", key="app_title")
        st.text_input("Podtytuł:", key="app_subtitle")
        st.text_area("Punkty na liście:", height=200, key="app_features")
        c1, c2 = st.columns(2)
        u_bg = c1.file_uploader("Zdj. tła (Prawa str.)", key="app_bg")
        if u_bg: st.session_state['img_app_bg'] = optimize_img(u_bg.getvalue())
        u_sc = c2.file_uploader("Ekran Aplikacji", key="app_sc")
        if u_sc: st.session_state['img_app_screen'] = optimize_img(u_sc.getvalue())

    elif page == "Materiały Brandingowe":
        bra_keys = ['brand_hide', 'brand_overline', 'brand_title', 'brand_subtitle', 'brand_features', 'img_brand_1', 'img_brand_2', 'img_brand_3']
        section_template_manager(bra_keys, "BRA", "Branding", "bra")
        st.checkbox("Ukryj slajd", key="brand_hide")
        st.text_input("Mały nadtytuł:", key="brand_overline")
        st.text_area("Główny tytuł H1:", key="brand_title")
        st.text_input("Podtytuł:", key="brand_subtitle")
        st.text_area("Punkty na liście:", height=200, key="brand_features")
        c1, c2, c3 = st.columns(3)
        u1 = c1.file_uploader("Zdj 1", key="bra_img_1")
        if u1: st.session_state['img_brand_1'] = optimize_img(u1.getvalue())
        u2 = c2.file_uploader("Zdj 2", key="bra_img_2")
        if u2: st.session_state['img_brand_2'] = optimize_img(u2.getvalue())
        u3 = c3.file_uploader("Zdj 3", key="bra_img_3")
        if u3: st.session_state['img_brand_3'] = optimize_img(u3.getvalue())

    elif page == "Wirtualny Asystent":
        va_keys = ['va_hide', 'va_overline', 'va_title', 'va_subtitle', 'va_text', 'img_va_1', 'img_va_2', 'img_va_3']
        section_template_manager(va_keys, "VA", "Asystent", "va")
        st.checkbox("Ukryj slajd", key="va_hide")
        st.text_input("Mały nadtytuł:", key="va_overline")
        st.text_area("Główny tytuł H1:", key="va_title")
        st.text_input("Podtytuł:", key="va_subtitle")
        st.text_area("Treść oferty:", height=200, key="va_text")
        c1, c2, c3 = st.columns(3)
        u1 = c1.file_uploader("Zdj 1", key="va_img_1")
        if u1: st.session_state['img_va_1'] = optimize_img(u1.getvalue())
        u2 = c2.file_uploader("Zdj 2", key="va_img_2")
        if u2: st.session_state['img_va_2'] = optimize_img(u2.getvalue())
        u3 = c3.file_uploader("Zdj 3", key="va_img_3")
        if u3: st.session_state['img_va_3'] = optimize_img(u3.getvalue())

    elif page == "Pillow Gifts":
        gif_keys = ['pg_hide', 'pg_overline', 'pg_title', 'pg_subtitle', 'pg_text', 'img_pg_1', 'img_pg_2', 'img_pg_3']
        section_template_manager(gif_keys, "GIF", "Gifts", "gif")
        st.checkbox("Ukryj slajd", key="pg_hide")
        st.text_input("Mały nadtytuł:", key="pg_overline")
        st.text_area("Główny tytuł H1:", key="pg_title")
        st.text_input("Podtytuł:", key="pg_subtitle")
        st.text_area("Treść oferty:", height=200, key="pg_text")
        c1, c2, c3 = st.columns(3)
        u1 = c1.file_uploader("Zdjęcie 1", key="pg_img_1")
        if u1: st.session_state['img_pg_1'] = optimize_img(u1.getvalue())
        u2 = c2.file_uploader("Zdjęcie 2", key="pg_img_2")
        if u2: st.session_state['img_pg_2'] = optimize_img(u2.getvalue())
        u3 = c3.file_uploader("Zdjęcie 3", key="pg_img_3")
        if u3: st.session_state['img_pg_3'] = optimize_img(u3.getvalue())

    elif page == "Kosztorys":
        koszt_keys = ['koszt_hide_1', 'koszt_hide_2', 'koszt_h1_title', 'koszt_title', 'koszt_pax', 'koszt_price', 'koszt_hotel', 'koszt_dbl', 'koszt_sgl', 'koszt_zawiera_1', 'koszt_zawiera_2', 'koszt_nie_zawiera', 'koszt_opcje', 'img_koszt_1', 'img_koszt_2']
        section_template_manager(koszt_keys, "KOS", "Kosztorys", "koszt")
        c1, c2 = st.columns(2)
        c1.checkbox("Ukryj CAŁY Kosztorys", key="koszt_hide_1")
        c2.checkbox("Ukryj Slajd 2", key="koszt_hide_2")
        st.text_input("Tytuł H1:", key="koszt_h1_title", value=st.session_state.get('koszt_h1_title', 'KOSZTORYS'))
        st.text_input("Overline:", key="koszt_title")
        _section_header("GŁÓWNE DANE TABELI")
        c1, c2 = st.columns(2)
        c1.text_input("Wielkość grupy:", key="koszt_pax")
        c2.text_input("Cena:", key="koszt_price")
        st.text_input("Wybrany Hotel / Standard:", key="koszt_hotel")
        c1, c2 = st.columns(2)
        c1.text_input("Ilość pokoi DBL:", key="koszt_dbl")
        c2.text_input("Ilość pokoi SGL:", key="koszt_sgl")
        if st.button("GENERUJ LISTĘ KOSZTÓW Z OFERTY", type="primary", use_container_width=True):
            auto_generate_kosztorys()
            st.success("Wygenerowano.")
            st.rerun()
        st.text_area("Cena zawiera (Slajd 1):", height=150, key="koszt_zawiera_1")
        st.text_area("Cena zawiera (Slajd 2):", height=150, key="koszt_zawiera_2")
        st.text_area("Nie policzone w cenie:", height=100, key="koszt_nie_zawiera")
        st.text_area("Koszty opcjonalne:", height=100, key="koszt_opcje")
        c1, c2 = st.columns(2)
        u1 = c1.file_uploader("Zdj. Slajd 1", key="koszt_img_1")
        if u1: st.session_state['img_koszt_1'] = optimize_img(u1.getvalue())
        u2 = c2.file_uploader("Zdj. Slajd 2", key="koszt_img_2")
        if u2: st.session_state['img_koszt_2'] = optimize_img(u2.getvalue())

    elif page == "Co o nas mówią":
        opi_keys = ['testim_hide', 'testim_overline', 'testim_title', 'testim_subtitle', 'img_testim_main', 'testim_count']
        for i in range(st.session_state.get('testim_count', 3)):
            opi_keys.extend([f'testim_img_{i}', f'testim_head_{i}', f'testim_quote_{i}', f'testim_author_{i}', f'testim_role_{i}'])
        section_template_manager(opi_keys, "OPI", "Opinie", "opi")
        st.checkbox("Ukryj ten slajd w PDF", key="testim_hide")
        st.text_input("Mały nadtytuł:", key="testim_overline")
        st.text_area("Główny tytuł H1:", key="testim_title")
        st.text_area("Podtytuł:", key="testim_subtitle")
        u_main = st.file_uploader("Zdjęcie główne slajdu", key="opi_main")
        if u_main: st.session_state['img_testim_main'] = optimize_img(u_main.getvalue())
        st.number_input("Liczba opinii:", 1, 4, step=1, key="testim_count")
        for i in range(st.session_state['testim_count']):
            with st.expander(f"Opinia {i+1}"):
                u_testim = st.file_uploader("Zdjęcie / Logo", key=f"opi_img_{i}")
                if u_testim: st.session_state[f"testim_img_{i}"] = optimize_img(u_testim.getvalue())
                st.text_input("Nagłówek", key=f"testim_head_{i}")
                st.text_area("Treść", key=f"testim_quote_{i}")
                c1, c2 = st.columns(2)
                c1.text_input("Autor", key=f"testim_author_{i}")
                c2.text_input("Stanowisko", key=f"testim_role_{i}")

    elif page == "O Nas (Zespół)":
        nas_keys = ['about_hide', 'about_overline', 'about_title', 'about_sub', 'about_desc', 'about_panel_title', 'about_panel_text', 'team_count', 'img_about_clients']
        for i in range(st.session_state.get('team_count', 2)):
            nas_keys.extend([f't_name_{i}', f't_role_{i}', f't_desc_{i}', f't_img_{i}'])
        section_template_manager(nas_keys, "NAS", "Zespol", "nas")
        st.checkbox("Ukryj ten slajd", key="about_hide")
        st.text_input("Nadtytuł:", key="about_overline")
        st.text_input("Tytuł H1:", key="about_title")
        st.text_input("Podtytuł:", key="about_sub")
        st.text_area("Opis główny:", height=100, key="about_desc")
        u_clients = st.file_uploader("Zdjęcie prawe", key="nas_clients")
        if u_clients: st.session_state['img_about_clients'] = optimize_img(u_clients.getvalue())
        st.number_input("Liczba osób w zespole:", 1, 4, step=1, key="team_count")
        for i in range(st.session_state['team_count']):
            with st.expander(f"Osoba {i+1}"):
                st.text_input("Imię i nazwisko", key=f"t_name_{i}")
                st.text_input("Stanowisko", key=f"t_role_{i}")
                st.text_area("Krótki opis", key=f"t_desc_{i}")
                u_team = st.file_uploader("Zdjęcie okrągłe", key=f"nas_img_{i}")
                if u_team: st.session_state[f"t_img_{i}"] = optimize_img(u_team.getvalue())

    elif page == "Wygląd i Kolory":
        for (f_key, c_key, s_key, label) in [
            ('font_h1', 'color_h1', 'font_size_h1', 'H1'),
            ('font_h2', 'color_h2', 'font_size_h2', 'H2'),
            ('font_sub', 'color_sub', 'font_size_sub', 'Podt.'),
            ('font_text', 'color_text', 'font_size_text', 'Tekstu'),
            ('font_metric', 'color_metric', 'font_size_metric', 'Wyr.'),
        ]:
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.selectbox(f"Czcionka {label}", FONTS_LIST, key=f_key)
            c2.color_picker(f"Kolor {label}", key=c_key)
            c3.number_input("Rozmiar (px)", min_value=8, max_value=120, step=1, format="%d", key=s_key)
        st.color_picker("Akcent", key="color_accent")

    elif page == "Zapisz / Wczytaj Projekt":
        proj = _build_proj_dict()
        proj_json = json.dumps(proj, ensure_ascii=False)
        st.markdown("##### Zapis w przeglądarce")
        import streamlit.components.v1 as _comp
        ls_html = f"<script>(function() {{ localStorage.setItem('{_LS_KEY}', {proj_json!r}); var el = document.getElementById('ls-status'); if (el) el.textContent = 'Zapisano o ' + new Date().toLocaleTimeString('pl-PL'); }})();</script><div style='font-size:11px;color:#64748b;'><span id='ls-status'>Zapisuję...</span></div>"
        _comp.html(ls_html, height=30)

        if st.button("WCZYTAJ Z PRZEGLĄDARKI", use_container_width=True, type="primary"):
            restore_html = f"<script>(function() {{ var data = localStorage.getItem('{_LS_KEY}'); if (!data) return; try {{ var b64 = btoa(unescape(encodeURIComponent(data))); window.parent.location.href = window.parent.location.href.split('?')[0].split('#')[0] + '?_ls_restore=' + b64; }} catch(e) {{}} }})();</script>"
            _comp.html(restore_html, height=0)

        st.markdown("---")
        st.download_button("POBIERZ PLIK PROJEKTU (JSON)", proj_json, get_project_filename(), use_container_width=True)
        st.markdown("---")
        upf = st.file_uploader("Wgraj projekt z dysku (.json)", type=['json'], key="up_export")
        if upf and st.button("WCZYTAJ PROJEKT Z PLIKU", use_container_width=True, type="primary"):
            data = json.load(upf)
            load_project_data(data)
            st.rerun()

    # -----------------------------------------------------------------------
    # SZYBKIE AKCJE
    # -----------------------------------------------------------------------
    st.divider()
    st.markdown("<div style='font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 10px; letter-spacing: 1px;'>SZYBKIE AKCJE (CAŁA OFERTA)</div>", unsafe_allow_html=True)

    _proj_quick = _build_proj_dict()
    _proj_quick_json = json.dumps(_proj_quick, ensure_ascii=False)
    _acc = st.session_state.get('color_accent', '#FF6600')
    _save_html = f"""<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"><style>.save-btn {{ display: flex; align-items: center; justify-content: center; gap: 8px; width: 100%; padding: 8px 0; background: transparent; border: 2px solid {_acc}; color: {_acc}; border-radius: 4px; font-family: 'Montserrat', sans-serif; font-size: 12px; font-weight: 600; text-transform: uppercase; cursor: pointer; transition: background 0.2s, color 0.2s; }} .save-btn:hover {{ background: {_acc}; color: white; }} #save-msg {{ font-size: 10px; color: #64748b; font-family: 'Open Sans', sans-serif; text-align: center; margin-top: 4px; }}</style><button class="save-btn" onclick="doSave()"><i class="fa-regular fa-circle-dot"></i>ZAPISZ</button><div id="save-msg"></div><script>function doSave() {{ try {{ localStorage.setItem('{_LS_KEY}', {_proj_quick_json!r}); document.getElementById('save-msg').style.color = '#16a34a'; document.getElementById('save-msg').textContent = 'Zapisano o ' + new Date().toLocaleTimeString('pl-PL'); }} catch(e) {{}} }}</script>"""
    import streamlit.components.v1 as _comp_quick
    _comp_quick.html(_save_html, height=62)

    if st.button("PRZYGOTUJ OFERTĘ DO POBRANIA", type="secondary", use_container_width=True):
        with st.spinner("Generowanie ostatecznego pliku oferty..."):
            export_content = build_presentation(export_mode=True)
            acc = st.session_state.get('color_accent', '#FF6600')
            t_main = st.session_state.get('t_main', 'Oferta')
            client_html = f'<!DOCTYPE html><html lang="pl"><head><meta charset="UTF-8"><title>{t_main}</title>{get_local_css(return_str=True)}<style>body{{background:#f4f5f7;margin:0;}} .presentation-wrapper{{height:100vh;overflow-y:auto;scroll-snap-type:y proximity;}} .client-export-btn{{position:fixed;top:20px;left:20px;z-index:9999;background:{acc};color:white;border:none;padding:15px 25px;border-radius:4px;font-family:sans-serif;font-size:12px;font-weight:700;text-transform:uppercase;cursor:pointer;box-shadow:0 4px 15px rgba(0,0,0,0.3);}} @media print{{.client-export-btn{{display:none !important;}} .presentation-wrapper{{height:auto !important;overflow:visible !important;}}}}</style></head><body><button class="client-export-btn" onclick="window.print()">POBIERZ JAKO PDF</button><div class="presentation-wrapper">{export_content}</div></body></html>'
            st.session_state['ready_export_html'] = client_html
            st.rerun()

    if st.session_state.get('ready_export_html'):
        st.download_button("POBIERZ GOTOWY PLIK HTML", st.session_state['ready_export_html'], get_project_filename().replace('.json', '.html'), "text/html", type="primary", use_container_width=True)

    if st.button("GENERUJ LINK DO OFERTY ONLINE", use_container_width=True):
        st.session_state['show_link_info'] = not st.session_state.get('show_link_info', False)
    if st.session_state.get('show_link_info', False):
        st.info("Wyeksportuj plik HTML za pomocą przycisku wyżej i umieść go na serwerze swojej agencji. Plik jest w pełni autonomiczną stroną WWW.")

    if st.button("PODGLĄD PEŁNOEKRANOWY", use_container_width=True):
        st.session_state['client_mode'] = True
        st.rerun()

# ---------------------------------------------------------------------------
# ZAPIS STANÓW WIDŻETÓW (BEZ UPLOADERÓW)
# ---------------------------------------------------------------------------
raw_backup = {}
for bk, bv in st.session_state.items():
    if bk == 'RAW_STATE_BACKUP': 
        continue
    if bk.startswith(('up_', 'btn_', '$$', 'FormSubmitter')): 
        continue
    if type(bv).__name__ == 'UploadedFile' or (isinstance(bv, list) and len(bv) > 0 and type(bv[0]).__name__ == 'UploadedFile'):
        continue
    raw_backup[bk] = bv
    
st.session_state['RAW_STATE_BACKUP'] = raw_backup

build_presentation(page)
