"""
app.py
======
Punkt wejścia aplikacji Streamlit.
Importuje renderer.py i obsługuje cały sidebar (panel edycji),
tryb klienta oraz akcje globalne.

OSTATNIA AKTUALIZACJA: 2024-04-23 15:35 UTC
NAPRAWIONO: StreamlitValueAssignmentNotAllowedError - buttony atrakcji → selectbox
"""

import re
import json
import base64
from datetime import date, datetime
import time

import streamlit as st
from supabase import create_client, Client

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
# SUPABASE CONNECTION
# ---------------------------------------------------------------------------
@st.cache_resource
def init_supabase() -> Client:
    """Inicjalizacja połączenia z Supabase - wykonuje się raz na session."""
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

# ---------------------------------------------------------------------------
# KONFIGURACJA STRONY
# ---------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="Activezone Oferta",
                   initial_sidebar_state="expanded")

st.markdown("""
<style>
/* Zmniejszenie sidebara i powiększenie głównej części */
section[data-testid="stSidebar"] {
    width: 320px !important;
    min-width: 320px !important;
}
section[data-testid="stSidebar"] > div {
    width: 320px !important;
}
/* Główna część zajmuje resztę */
.main .block-container {
    max-width: 100% !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}

/* Buttony nawigacyjne w sidebarze - kompaktowe */
[data-testid="stSidebar"] div.stButton > button {
    border-radius: 4px !important;
    font-family: 'Montserrat', sans-serif !important;
    text-transform: uppercase !important;
    font-size: 10px !important;
    letter-spacing: 0.5px !important;
    font-weight: 600 !important;
    padding: 6px 8px !important;
    min-height: 28px !important;
    height: 28px !important;
}
/* Pozostałe buttony (poza sidearem) - normalne */
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
# INICJALIZACJA SESSION STATE
# ---------------------------------------------------------------------------
if 'client_mode' not in st.session_state:
    st.session_state['client_mode'] = False

# ---------------------------------------------------------------------------
# AUTO-LOAD Z SUPABASE (WERSJA STABILNA - JEDNORAZOWE WCZYTANIE)
# ---------------------------------------------------------------------------
if '_data_loaded_once' not in st.session_state:
    try:
        # Pobieramy dane tylko raz na całą sesję użytkownika
        result = supabase.table('projects').select('data').eq('user_email', 'default_user').order('updated_at', desc=True).limit(1).execute()
        
        if result.data and result.data[0].get('data'):
            project_data = result.data[0]['data']
            # Wczytujemy dane do sesji (renderer.py dba o to, by nic nie nadpisać)
            load_project_data(project_data)
            st.session_state['_debug_loaded'] = "📥 Dane wczytane z Supabase (start sesji)"
        else:
            st.session_state['_debug_loaded'] = "📥 Brak danych w bazie - użyto defaults"
            # Wczytujemy wartości domyślne tylko, jeśli baza jest pusta
            for k, v in defaults.items():
                if k not in st.session_state:
                    st.session_state[k] = v
        
        # Oznaczamy, że dane zostały już zainicjowane
        st.session_state['_data_loaded_once'] = True
        
    except Exception as e:
        st.error(f"❌ Błąd wczytywania bazy: {str(e)[:50]}")
        # W razie awarii bazy ładujemy defaults, aby nie zepsuć aplikacji
        for k, v in defaults.items():
            if k not in st.session_state:
                st.session_state[k] = v
        st.session_state['_data_loaded_once'] = True

# ---------------------------------------------------------------------------
# HELPERY UI
# ---------------------------------------------------------------------------
# (Reszta Twoich helperów zostaje bez zmian)
# HELPERY UI
# ---------------------------------------------------------------------------

def set_focus(target_id):
    st.session_state['scroll_target'] = target_id
    st.session_state['_user_edited'] = True  # Użytkownik coś zmienił


def _get_hotel_order():
    """Zwraca kolejność hoteli — lista indeksów [0,1,2,...]."""
    s = st.session_state
    n = s.get('num_hotels', 1)
    order = s.get('hotel_order', [])
    # Upewnij się że lista jest kompletna i aktualna
    valid = list(range(n))
    order = [i for i in order if i in valid]
    for i in valid:
        if i not in order:
            order.append(i)
    s['hotel_order'] = order
    return order


def _move_hotel(idx, direction):
    """Przesuwa hotel w górę (-1) lub w dół (+1)."""
    order = _get_hotel_order()
    new_idx = idx + direction
    if 0 <= new_idx < len(order):
        order[idx], order[new_idx] = order[new_idx], order[idx]
        st.session_state['hotel_order'] = order


# -----------------------------------------------------------------------
# ZARZĄDZANIE LISTĄ OPISÓW ATRAKCJI I MIEJSC (pa_items)
# pa_items = lista słowników: {type: 'place'/'attr', idx: int}
# -----------------------------------------------------------------------

# -----------------------------------------------------------------------
# PROSTY SYSTEM ATRAKCJI — jedna lista attr_order = [0, 1, 2, ...]
# -----------------------------------------------------------------------

def _attr_count():
    """Liczba dodanych atrakcji."""
    return st.session_state.get('num_attr', 0)

def _attr_order():
    """Kolejność atrakcji — lista indeksów. Zawsze unikalna i kompletna."""
    n = _attr_count()
    raw = st.session_state.get('attr_order', [])
    # Deduplikuj zachowując kolejność (naprawia stare zepsute dane)
    seen = set()
    order = []
    for i in raw:
        if i not in seen and i < n:
            seen.add(i)
            order.append(i)
    # Dodaj brakujące indeksy na końcu
    for i in range(n):
        if i not in seen:
            order.append(i)
    st.session_state['attr_order'] = order
    return order

def _attr_add():
    """Dodaje nową atrakcję i przechodzi do jej strony."""
    n = st.session_state.get('num_attr', 0)
    st.session_state['num_attr'] = n + 1
    # Pobierz order PRZED zwiększeniem num_attr, żeby nie dodawał n automatycznie
    order = st.session_state.get('attr_order', list(range(n)))
    order = [i for i in order if i < n]  # oczyść stare
    order.append(n)  # dodaj nowy idx na końcu
    st.session_state['attr_order'] = order
    # last_page koduje idx (nie pos) żeby być odporny na przestawienia
    st.session_state['last_page'] = f"ATTR:{n}"
    st.session_state['scroll_target'] = ""

def _attr_move(pos, direction):
    """Przesuwa atrakcję w górę/dół."""
    order = _attr_order()
    new_pos = pos + direction
    if 0 <= new_pos < len(order):
        order[pos], order[new_pos] = order[new_pos], order[pos]
        st.session_state['attr_order'] = order


def _attr_delete(pos):
    """Usuwa atrakcję z listy na pozycji pos."""
    order = _attr_order()
    if pos < len(order):
        order.pop(pos)
        st.session_state['attr_order'] = order
        st.session_state['last_page'] = "  ↳ Przerywnik atrakcje"
        st.session_state['_attr_focused'] = None

def _attr_page_name(pos):
    """Nazwa strony nawigacji dla atrakcji na pozycji pos.
    Format: ATTR:idx — tylko idx, odporny na zmiany nazwy."""
    order = _attr_order()
    idx = order[pos] if pos < len(order) else pos
    return f"ATTR:{idx}"


def _attr_display_name(pos):
    """Wyświetlana nazwa atrakcji na pozycji pos."""
    order = _attr_order()
    idx = order[pos] if pos < len(order) else pos
    name = str(st.session_state.get(f'amain_{idx}', '')).split('\n')[0][:25].strip()
    return name or f"Atrakcja {pos + 1}"

# Wsteczna kompatybilność z renderer.py
def _get_place_attr_order():
    order = _attr_order()
    return [['attr', i] for i in order]

def _move_place_attr(pos, direction):
    _attr_move(pos, direction)

def _rebuild_slide_order():
    _get_hotel_order()
    _attr_order()


def _build_proj_dict():
    """Serializuje session_state do słownika gotowego do zapisu JSON."""
    proj = {}
    # Prefiksy i klucze widgetów które NIE MOGĄ być zapisane (kolizja z Streamlit)
    skip_prefixes = ('FormSubmitter', '$$', 'up_', 'fn_', 'dl_', 'btn_', 'sb_', 'pa_add_', 'sek_img_up',
                     'attr_add_btn', 'attrnav_', 'attrup_', 'attrdn_', 'attrdel_', 'attr_select',
                     'nav_top_radio', 'nav_bot_radio')
    # Klucze wewnętrzne które nie powinny trafić do pliku projektu
    internal_keys = {'_session_id', '_ls_loaded', '_ls_restore', '_scroll_pos',
                     'ready_export_html', 'show_link_info', '_attr_focused', 'STATE_BACKUP',
                     '_supabase_data', '_loaded_from_supabase', 'last_supabase_save', 
                     'last_save_status', '_user_edited', '_debug_loaded'}
    skip_keys = {
        'tyt_hero', 'tyt_logo_az', 'tyt_logo_cli',
        'kie_hero', 'kie_th1', 'kie_th2', 'kie_th3', 'lot_hero',
        'app_bg', 'app_sc', 'bra_img_1', 'bra_img_2', 'bra_img_3',
        'va_img_1', 'va_img_2', 'va_img_3',
        'pg_img_1', 'pg_img_2', 'pg_img_3',
        'koszt_img_1', 'koszt_img_2', 'opi_main', 'nas_clients',
        # file_uploader przerywników (UploadedFile, nie bytes — dane trafiają do sek_*_img)
        'sek_img_up_0', 'sek_img_up_1', 'sek_img_up_2', 'sek_img_up_3',
        # file_uploader miniatur miejsc
        'plc_img3_0', 'plc_img4_0',
    }
    dyn_skip = re.compile(
        r'^(uh1|uh1b|uh2|uh3|prg_img|'
        r'plc_img1|plc_img2|plc_img3|plc_img4|'
        r'atr_hero|atr_th1|atr_th2|atr_th3|'
        r'opi_img|nas_img|'
        r'sek_img_up)_\d+$'
    )
    for k, v in st.session_state.items():
        if k in EXCLUDE_EXPORT_KEYS or k in internal_keys:
            continue
        if any(k.startswith(p) for p in skip_prefixes):
            continue
        if k in skip_keys or dyn_skip.match(k):
            continue
        try:
            if isinstance(v, bytes):
                proj[k] = base64.b64encode(v).decode()
            elif isinstance(v, (date, datetime)):
                proj[k] = v.isoformat()
            elif isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                proj[k] = v
        except Exception:
            pass
    return proj


def _validate_and_load_json(uploaded_file, expected_keys=None):
    """
    Bezpiecznie ładuje i waliduje JSON z uploaded file.
    
    Args:
        uploaded_file: Plik z st.file_uploader
        expected_keys: Lista opcjonalnych kluczy do sprawdzenia (None = pomiń walidację)
    
    Returns:
        dict: Załadowane dane lub None w przypadku błędu
        str: Komunikat błędu lub None jeśli OK
    """
    if not uploaded_file:
        return None, "Brak pliku"
    
    try:
        # 1. Sprawdź czy to JSON
        uploaded_file.seek(0)  # Reset pozycji pliku
        content = uploaded_file.read()
        
        # 2. Sprawdź czy nie jest pusty
        if not content or len(content.strip()) == 0:
            return None, "Plik jest pusty"
        
        # 3. Parsuj JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            return None, f"Nieprawidłowy format JSON: {str(e)[:100]}"
        
        # 4. Sprawdź czy to słownik (nie lista, string, etc)
        if not isinstance(data, dict):
            return None, f"Plik musi zawierać obiekt JSON ({{}}), znaleziono: {type(data).__name__}"
        
        # 5. Walidacja kluczy (opcjonalna)
        if expected_keys:
            found_keys = set(data.keys())
            expected_set = set(expected_keys)
            if not found_keys.intersection(expected_set):
                return None, f"Brak oczekiwanych kluczy. Znaleziono: {', '.join(list(found_keys)[:5])}"
        
        return data, None
        
    except Exception as e:
        return None, f"Błąd odczytu: {str(e)[:100]}"


def section_template_manager(section_keys, file_prefix, default_filename, uploader_key, index=None):
    ATR_KEY_MAP = {"atype": "type", "amain": "main", "asub": "sub", "aopis": "opis"}
    _acc = st.session_state.get('color_accent', '#FF6600')

    # Zwijany expander - domyślnie ukryty
    with st.expander("⚙️ Zarządzanie szablonem sekcji", expanded=False):
        # Przygotuj dane eksportu
        export_data = {}
        for k in section_keys:
            save_key = k if index is None else re.sub(f'_{index}$', '', k)
            if file_prefix == "ATR":
                save_key = ATR_KEY_MAP.get(save_key, save_key)
            val = st.session_state.get(k)
            if val is not None:
                if isinstance(val, bytes):
                    export_data[save_key] = base64.b64encode(val).decode('utf-8')
                elif isinstance(val, (date, datetime)):
                    export_data[save_key] = val.isoformat()
                else:
                    export_data[save_key] = val
        json_str = json.dumps(export_data)
        cc = st.session_state.get('country_code', 'OTH')
        base_slug = create_slug(default_filename)
        full_filename = f"{cc}-{file_prefix}-{base_slug}.json"
        _display = default_filename.replace("_", " ").title() if default_filename else "Slajd"

        # ── KOMPAKTOWY LAYOUT 3 KOLUMNY ──────────────────────────────────
        col1, col2, col3 = st.columns([1.2, 1, 1])
        
        with col1:
            st.markdown(
                f"<div style='font-size:11px;font-weight:600;color:#334155;padding:8px 0;'>"
                f"<span style='color:{_acc};'>★</span> {_display}</div>",
                unsafe_allow_html=True,
            )
        
        with col2:
            st.download_button(
                "↓ ZAPISZ", json_str, full_filename,
                key=f"dl_{uploader_key}", use_container_width=True,
            )
        
        with col3:
            uploaded_file = st.file_uploader(
                "↑ WCZYTAJ", type=['json'], key=f"up_{uploader_key}",
                label_visibility="collapsed",
            )
        
        # Button Wczytaj w osobnym wierszu (pełna szerokość)
        if uploaded_file:
            if st.button("↑ WCZYTAJ SZABLON", key=f"btn_apply_{uploader_key}",
                         use_container_width=True, type="primary"):
                # Bezpieczne ładowanie z walidacją
                data, error = _validate_and_load_json(uploaded_file, expected_keys=section_keys)
                
                if error:
                    st.error(f"❌ {error}")
                else:
                    try:
                        filtered_data = {}
                        for k in section_keys:
                            save_key = k
                            load_key = k if index is None else re.sub(f'_{index}$', '', k)
                            if file_prefix == "ATR":
                                load_key = ATR_KEY_MAP.get(load_key, load_key)
                            if load_key in data:
                                filtered_data[save_key] = data[load_key]
                        
                        if not filtered_data:
                            st.warning("⚠️ Nie znaleziono pasujących danych w pliku")
                        else:
                            load_project_data(filtered_data)
                            st.success(f"✅ Wczytano {len(filtered_data)} pól")
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ Błąd przetwarzania danych: {str(e)[:100]}")


def _section_header(label):
    st.markdown(
        f"<div style='font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; "
        f"margin-top: 15px; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; "
        f"letter-spacing: 1px;'>{label}</div>",
        unsafe_allow_html=True,
    )


def save_to_supabase():
    """Zapisz projekt do Supabase - wywołuj w on_change inputów"""
    try:
        data = _build_proj_dict()
        # Sprawdź czy rekord istnieje
        existing = supabase.table('projects').select('id').eq('user_email', 'default_user').execute()
        
        if existing.data:
            # UPDATE istniejącego rekordu
            supabase.table('projects').update({
                'project_name': st.session_state.get('t_main', 'Projekt'),
                'data': data,
                'updated_at': datetime.now().isoformat()
            }).eq('user_email', 'default_user').execute()
        else:
            # INSERT nowego rekordu
            supabase.table('projects').insert({
                'user_email': 'default_user',
                'project_name': st.session_state.get('t_main', 'Projekt'),
                'data': data,
                'updated_at': datetime.now().isoformat()
            }).execute()
    except Exception:
        pass  # Cichy błąd


# ---------------------------------------------------------------------------
# TRYB KLIENTA
# ---------------------------------------------------------------------------
if st.session_state['client_mode']:
    accent_color = st.session_state.get('color_accent', '#FF6600')
    st.markdown(
        f"<style>div.stButton {{ position: fixed !important; top: 20px !important; left: 20px !important; "
        f"z-index: 999999 !important; width: auto !important; }} "
        f"div.stButton > button {{ background-color: {accent_color} !important; color: white !important; "
        f"border: none !important; border-radius: 30px !important; padding: 15px 25px !important; "
        f"font-family: 'Montserrat', sans-serif !important; font-size: 14px !important; font-weight: 700 !important; "
        f"box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important; display: flex !important; align-items: center !important; "
        f"justify-content: center !important; width: auto !important; white-space: nowrap !important; }} "
        f"div.stButton > button:hover {{ transform: scale(1.02); opacity: 0.9; }}</style>",
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
    # ---------------------------------------------------------------------------
    # STATUS AUTO-SAVE (na samej górze - zawsze widoczny)
    # ---------------------------------------------------------------------------
    save_status = st.session_state.get('last_save_status', '⏳ Czekam na zmiany...')
    save_count = st.session_state.get('last_save_count', 0)
    
    st.markdown(
        f"<div style='background:#f0f9ff;border-left:3px solid #0ea5e9;padding:8px 12px;margin-bottom:15px;border-radius:4px;'>"
        f"<div style='font-size:11px;font-weight:600;color:#0369a1;margin-bottom:4px;'>AUTO-ZAPIS (co 10s)</div>"
        f"<div style='font-size:10px;color:#64748b;'>{save_status}</div>"
        f"<div style='font-size:9px;color:#94a3b8;margin-top:2px;'>{save_count} pól w bazie</div>"
        f"</div>",
        unsafe_allow_html=True
    )
    
    st.markdown("---")
    
    # ---------------------------------------------------------------------------
    # RESZTA SIDEBARA
    # ---------------------------------------------------------------------------
    _acc = st.session_state.get('color_accent', '#FF6600')
    _h1c = st.session_state.get('color_h1', '#003366')
    # CSS: primary button w sidebarze = kolor akcentu (pomarańczowy)
    st.markdown(
        f"<style>"
        f"section[data-testid='stSidebar'] button[kind='primary']{{background-color:{_acc}!important;border-color:{_acc}!important;color:white!important;}}"
        f"section[data-testid='stSidebar'] [data-testid='stButton']:has(button[key*='aord_up_']) button,"
        f"section[data-testid='stSidebar'] [data-testid='stButton']:has(button[key*='aord_dn_']) button"
        f"{{padding:0!important;min-height:22px!important;font-size:11px!important;"
        f"background:transparent!important;border:none!important;color:#94a3b8!important;box-shadow:none!important;}}"
        f"section[data-testid='stSidebar'] [data-testid='stButton']:has(button[key*='aord_del_']) button"
        f"{{padding:0!important;min-height:22px!important;font-size:11px!important;"
        f"background-color:#ef4444!important;border-color:#ef4444!important;color:white!important;}}"
        f"</style>",
        unsafe_allow_html=True,
    )
    _n_attr = _attr_count()
    _attr_pages = [_attr_page_name(pos) for pos in range(_n_attr)]

    # Nawigacja górna — bez atrakcji
    _nav_top = ["Strona Tytułowa", "Opis Kierunku", "Mapa Podróży", "Jak lecimy?",
                "  ↳ Przerywnik hotel", "Zakwaterowanie",
                "  ↳ Przerywnik program", "Program Wyjazdu",
                "  ↳ Przerywnik atrakcje"]
    # Nawigacja dolna — bez atrakcji
    _nav_bot = ["Aplikacja (Komunikacja)", "Materiały Brandingowe", "Wirtualny Asystent",
                "Pillow Gifts", "Kosztorys",
                "  ↳ Przerywnik o nas", "Co o nas mówią", "O Nas (Zespół)",
                "Wygląd i Kolory", "Zapisz / Wczytaj Projekt"]

    _nav_all = _nav_top + _attr_pages + _nav_bot
    _last = st.session_state.get('last_page', _nav_all[0])
    _default_idx = _nav_all.index(_last) if _last in _nav_all else 0

    def _fmt_nav(p):
        if p.startswith("ATTR:"):
            idx = int(p.split(":")[1])
            pos = next((pos for pos, ix in enumerate(_attr_order()) if ix == idx), 0)
            return "  ★ " + _attr_display_name(pos)
        return p

    # Nawigacja górna — RADIO (najstabilniejsze)
    st.markdown("**WYBIERZ SEKCJE DO EDYCJI:**")
    
    _top_index = _nav_top.index(_last) if _last in _nav_top else 0
    st.radio(
        "Nawigacja górna",
        _nav_top,
        index=_top_index,
        key="nav_top_radio",
        label_visibility="collapsed",
        on_change=lambda: st.session_state.update({'last_page': st.session_state['nav_top_radio']})
    )

    # --- SEKCJA ATRAKCJI wbudowana w nawigację ---
    # Przycisk ＋ DODAJ ATRAKCJE/MIEJSCE
    st.markdown(
        f"<div style='display:flex;align-items:center;gap:6px;"
        f"padding:3px 0 3px 4px;'>"
        f"<span style='color:{_acc};font-size:13px;font-weight:700;'>★</span>"
        f"<span style='font-size:12px;font-weight:600;color:#334155;"
        f"font-family:Montserrat,sans-serif;'>"
        f"ATRAKCJE ({_n_attr})</span></div>",
        unsafe_allow_html=True,
    )
    
    # Lista atrakcji z buttonami zarządzania (bez if st.button - zapisujemy wartości)
    if _n_attr > 0:
        for _ap in range(_n_attr):
            _ap_key = _attr_pages[_ap]
            _ap_name = _attr_display_name(_ap)
            _ap_active = (_last == _ap_key)
            
            _ca, _cb, _cc, _cd = st.columns([6, 1, 1, 1])
            
            # Button nawigacji
            _ca.button(
                f"★ {_ap_name}", 
                key=f"attrnav_{_ap}",
                use_container_width=True,
                type="primary" if _ap_active else "secondary"
            )
            
            # Buttony zarządzania
            if _ap > 0:
                _cb.button("▲", key=f"attrup_{_ap}", use_container_width=True)
            if _ap < _n_attr - 1:
                _cc.button("▼", key=f"attrdn_{_ap}", use_container_width=True)
            _cd.button("✕", key=f"attrdel_{_ap}", use_container_width=True)
    
    st.caption("💡 Zarządzaj kolejnością i usuwaj atrakcje przyciskami ▲▼✕")

    # Nawigacja dolna — RADIO
    _bot_index = _nav_bot.index(_last) if _last in _nav_bot else 0
    st.radio(
        "Nawigacja dolna",
        _nav_bot,
        index=_bot_index,
        key="nav_bot_radio",
        label_visibility="collapsed",
        on_change=lambda: st.session_state.update({'last_page': st.session_state['nav_bot_radio']})
    )

    # Nagłówek zakładki (używa _last który jest już zdefiniowany)
    _inter_pages = {"  ↳ Przerywnik hotel", "  ↳ Przerywnik program", "  ↳ Przerywnik atrakcje", "  ↳ Przerywnik o nas"}
    _is_attr_page = _last.startswith("ATTR:")

# ---------------------------------------------------------------------------
# USTALANIE AKTYWNEJ STRONY (po sidebarze)
# ---------------------------------------------------------------------------
# Obsługa buttonów atrakcji (sprawdzanie wartości POZA sidebarem)
for _ap in range(_n_attr):
    # Nawigacja
    if st.session_state.get(f'attrnav_{_ap}', False):
        st.session_state['last_page'] = _attr_pages[_ap]
        st.rerun()
    # Move up
    if st.session_state.get(f'attrup_{_ap}', False):
        _attr_move(_ap, -1)
        st.rerun()
    # Move down
    if st.session_state.get(f'attrdn_{_ap}', False):
        _attr_move(_ap, 1)
        st.rerun()
    # Delete
    if st.session_state.get(f'attrdel_{_ap}', False):
        _attr_delete(_ap)
        st.rerun()

page = _last

# ---------------------------------------------------------------------------
# PRZYCISKI: ZAPISZ TERAZ + DODAJ ATRAKCJĘ (POZA sidebarem)
# ---------------------------------------------------------------------------
col_save, col_add = st.columns([1, 1])

with col_save:
    if st.button("💾 ZAPISZ TERAZ", use_container_width=True, type="primary"):
        # Wywołujemy gotową funkcję zapisu
        save_to_supabase()
        st.success("✅ Projekt zapisany w chmurze!")
        st.rerun()

with col_add:
    # Używamy tylko potrzebnych parametrów, bez zbędnego klucza (key), który powoduje błędy
    if st.button("➕ Dodaj atrakcję", type="primary", use_container_width=True):
        _attr_add()
        st.rerun()

# Custom CSS dla białego emoji w przycisku (nie usuwaj tego, to zostaje)
st.markdown("""
<style>
button[data-testid="baseButton-primary"] {
    color: white !important;
}
</style>
""", unsafe_allow_html=True)
# ---------------------------------------------------------------------------
# NAGŁÓWKI STRON
# ---------------------------------------------------------------------------
with st.container():
    if page == "Wygląd i Kolory":
        st.markdown("<h2 style='color:#003366;margin-bottom:0;font-size:22px;font-weight:700;font-family:Montserrat,sans-serif;'>KONFIGURACJA WYGLĄDU</h2>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:13px;color:#64748b;margin-bottom:15px;font-family:Open Sans,sans-serif;'>Dostosuj kolory i typografię oferty</div>", unsafe_allow_html=True)
    elif page == "Zapisz / Wczytaj Projekt":
        st.markdown("<h2 style='color:#003366;margin-bottom:0;font-size:22px;font-weight:700;font-family:Montserrat,sans-serif;'>ZARZĄDZANIE PROJEKTEM</h2>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:13px;color:#64748b;margin-bottom:15px;font-family:Open Sans,sans-serif;'>Eksportuj lub importuj cały plik JSON</div>", unsafe_allow_html=True)
    elif page in _inter_pages:
        _h1_col = st.session_state.get("color_h1", "#003366")
        _page_label = page.strip().lstrip("↳").strip()
        st.markdown(f"<h2 style='color:{_h1_col};margin-bottom:0;font-size:20px;font-weight:700;font-family:Montserrat,sans-serif;text-transform:uppercase;margin-left:12px;border-left:3px solid {_h1_col};padding-left:10px;'>{_page_label}</h2>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:13px;color:#64748b;margin-bottom:15px;font-family:Open Sans,sans-serif;margin-left:12px;'>Slajd przerywnikowy — edytuj treść i wygląd poniżej.</div>", unsafe_allow_html=True)
    elif _is_attr_page:
        _acc_col = st.session_state.get("color_accent", "#FF6600")
        _attr_idx = int(page.split(":")[1]) if page.startswith("ATTR:") else 0
        _attr_pos = next((p for p, ix in enumerate(_attr_order()) if ix == _attr_idx), 0)
        _label = _attr_display_name(_attr_pos)
        st.markdown(f"<h2 style='color:{_acc_col};margin-bottom:0;font-size:20px;font-weight:700;font-family:Montserrat,sans-serif;margin-left:12px;border-left:3px solid {_acc_col};padding-left:10px;'>★ {_label}</h2>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:13px;color:#64748b;margin-bottom:15px;font-family:Open Sans,sans-serif;margin-left:12px;'>Edytuj treść slajdu atrakcji poniżej.</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h2 style='color:#003366;margin-bottom:0;font-size:22px;font-weight:700;font-family:Montserrat,sans-serif;text-transform:uppercase;'>{page}</h2>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:13px;color:#64748b;margin-bottom:15px;font-family:Open Sans,sans-serif;'>Wprowadź dane dla tej sekcji poniżej:</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# LAYOUT 2 KOLUMNY: Formularz edycji | Podgląd slajdu
# ---------------------------------------------------------------------------
col_form, col_preview = st.columns([0.3, 0.7], gap="medium")

with col_form:
    _acc = st.session_state.get('color_accent', '#FF6600')
    st.markdown(f"<h3 style='color:{_acc};font-size:16px;margin-bottom:20px;'>EDYCJA SLAJDU</h3>", unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # STRONA TYTUŁOWA
    # -----------------------------------------------------------------------
    if page == "  ↳ Przerywnik hotel":
        _bg_default = st.session_state.get('color_h1', '#003366')
        for _ck, _cv in [(f"sek_0_bg", _bg_default), (f"sek_0_txt", '#ffffff')]:
            _v = st.session_state.get(_ck, _cv)
            if not (isinstance(_v, str) and _v.startswith('#') and len(_v) == 7):
                st.session_state[_ck] = _cv
        st.button("POKAŻ PODGLĄD", key=f"btn_sek_0",
                  on_click=set_focus, args=(f"slide-sek_0",),
                  use_container_width=True)
        st.checkbox("Ukryj ten slajd w prezentacji", key=f"sek_hide_0")
        st.text_input("Duży tytuł (uppercase):", key=f"sek_0_title",
)
        st.text_input("Nadtytuł (overline, kolor akcentu):", key=f"sek_0_sub",
)
        _ic1, _ic2 = st.columns(2)
        _ic1.color_picker("Kolor gradientu/tła:", key=f"sek_0_bg")
        _ic2.color_picker("Kolor tytułu:", key=f"sek_0_txt")
        _up_s = st.file_uploader("Zdjęcie tła (16:9):", key=f"sek_img_up_0")
        if _up_s:
            st.session_state[f"sek_0_img"] = optimize_img(_up_s.getvalue())

    elif page == "  ↳ Przerywnik program":
        _bg_default = st.session_state.get('color_h1', '#003366')
        for _ck, _cv in [(f"sek_3_bg", _bg_default), (f"sek_3_txt", '#ffffff')]:
            _v = st.session_state.get(_ck, _cv)
            if not (isinstance(_v, str) and _v.startswith('#') and len(_v) == 7):
                st.session_state[_ck] = _cv
        st.button("POKAŻ PODGLĄD", key=f"btn_sek_3",
                  on_click=set_focus, args=(f"slide-sek_3",),
                  use_container_width=True)
        st.checkbox("Ukryj ten slajd w prezentacji", key=f"sek_hide_3")
        st.text_input("Duży tytuł (uppercase):", key=f"sek_3_title",
)
        st.text_input("Nadtytuł (overline, kolor akcentu):", key=f"sek_3_sub",
)
        _ic1, _ic2 = st.columns(2)
        _ic1.color_picker("Kolor gradientu/tła:", key=f"sek_3_bg")
        _ic2.color_picker("Kolor tytułu:", key=f"sek_3_txt")
        _up_s = st.file_uploader("Zdjęcie tła (16:9):", key=f"sek_img_up_3")
        if _up_s:
            st.session_state[f"sek_3_img"] = optimize_img(_up_s.getvalue())

    elif page == "  ↳ Przerywnik atrakcje":
        _bg_default = st.session_state.get('color_h1', '#003366')
        for _ck, _cv in [(f"sek_1_bg", _bg_default), (f"sek_1_txt", '#ffffff')]:
            _v = st.session_state.get(_ck, _cv)
            if not (isinstance(_v, str) and _v.startswith('#') and len(_v) == 7):
                st.session_state[_ck] = _cv
        st.button("POKAŻ PODGLĄD", key=f"btn_sek_1",
                  on_click=set_focus, args=(f"slide-sek_1",),
                  use_container_width=True)
        st.checkbox("Ukryj ten slajd w prezentacji", key=f"sek_hide_1")
        st.text_input("Duży tytuł (uppercase):", key=f"sek_1_title",
)
        st.text_input("Nadtytuł (overline, kolor akcentu):", key=f"sek_1_sub",
)
        _ic1, _ic2 = st.columns(2)
        _ic1.color_picker("Kolor gradientu/tła:", key=f"sek_1_bg")
        _ic2.color_picker("Kolor tytułu:", key=f"sek_1_txt")
        _up_s = st.file_uploader("Zdjęcie tła (16:9):", key=f"sek_img_up_1")
        if _up_s:
            st.session_state[f"sek_1_img"] = optimize_img(_up_s.getvalue())

    elif page == "  ↳ Przerywnik o nas":
        _bg_default = st.session_state.get('color_h1', '#003366')
        for _ck, _cv in [(f"sek_2_bg", _bg_default), (f"sek_2_txt", '#ffffff')]:
            _v = st.session_state.get(_ck, _cv)
            if not (isinstance(_v, str) and _v.startswith('#') and len(_v) == 7):
                st.session_state[_ck] = _cv
        st.button("POKAŻ PODGLĄD", key=f"btn_sek_2",
                  on_click=set_focus, args=(f"slide-sek_2",),
                  use_container_width=True)
        st.checkbox("Ukryj ten slajd w prezentacji", key=f"sek_hide_2")
        st.text_input("Duży tytuł (uppercase):", key=f"sek_2_title",
)
        st.text_input("Nadtytuł (overline, kolor akcentu):", key=f"sek_2_sub",
)
        _ic1, _ic2 = st.columns(2)
        _ic1.color_picker("Kolor gradientu/tła:", key=f"sek_2_bg")
        _ic2.color_picker("Kolor tytułu:", key=f"sek_2_txt")
        _up_s = st.file_uploader("Zdjęcie tła (16:9):", key=f"sek_img_up_2")
        if _up_s:
            st.session_state[f"sek_2_img"] = optimize_img(_up_s.getvalue())

    elif page == "Strona Tytułowa":
        tit_keys = [
            't_date', 'country_name', 'country_code', 't_main', 't_sub',
            't_klient', 't_kierunek', 't_pax', 't_hotel', 't_trans',
            'img_hero_t', 'logo_az', 'logo_cli', 'hide_logo_cli',
        ]
        section_template_manager(tit_keys, "TYT", "strona-tytulowa", "tit")
        
        # 1. Termin - jawne value=...
        st.text_input("Termin:", 
                      value=st.session_state.get("t_date", ""), 
                      key="t_date", 
                      on_change=lambda: (parse_date_and_days(), save_to_supabase()))
        
        # 2. Kraj - selectbox
        st.selectbox("Kraj docelowy:", 
                     list(COUNTRIES_DICT.keys()), 
                     key="country_name", 
                     on_change=save_to_supabase)
        st.session_state['country_code'] = COUNTRIES_DICT.get(st.session_state['country_name'], 'OTH')
        
        # 3. Pętla pól tekstowych z jawnym value=...
        for k, l in [
            ('t_main', 'Tytuł H1'), ('t_sub', 'Podtytuł'), ('t_klient', 'Klient'),
            ('t_kierunek', 'Kierunek'), ('t_pax', 'Liczba osób'),
            ('t_hotel', 'Hotel'), ('t_trans', 'Dojazd'),
        ]:
            st.text_input(l, 
                          value=st.session_state.get(k, ""), 
                          key=k, 
                          on_change=save_to_supabase)
        
        # 4. Uploadery zdjęć
        u1 = st.file_uploader("Zdjęcie główne (4:5)", key="tyt_hero")
        if u1:
            st.session_state['img_hero_t'] = optimize_img(u1.getvalue())
            save_to_supabase()
            
        c1, c2 = st.columns(2)
        u2 = c1.file_uploader("Logo Firmy", key="tyt_logo_az")
        if u2:
            st.session_state['logo_az'] = optimize_logo(u2.getvalue())
            save_to_supabase()
            
        u3 = c2.file_uploader("Logo Klienta", key="tyt_logo_cli")
        if u3:
            st.session_state['logo_cli'] = optimize_logo(u3.getvalue())
            save_to_supabase()
            
        # 5. Checkbox z jawnym value
        c2.checkbox("Ukryj logo klienta na stronie tytułowej", 
                    value=st.session_state.get("hide_logo_cli", False),
                    key="hide_logo_cli", 
                    on_change=save_to_supabase)
    # -----------------------------------------------------------------------
    # OPIS KIERUNKU
    # -----------------------------------------------------------------------
    elif page == "Opis Kierunku":
        k_keys = [
            'k_hide', 'k_overline', 'k_main', 'k_sub', 'k_opis',
            'k_facts', 'k_facts_title', 'k_box_bg', 'k_box_txt', 'img_hero_k',
        ]
        section_template_manager(k_keys, "KIE", st.session_state.get('k_main', 'czarnogora'), "kie")
        st.checkbox("Ukryj ten slajd w PDF", key="k_hide")
        st.text_input("Mały nadtytuł (overline):", key="k_overline",
)
        st.text_input("Nazwa kierunku (duży tytuł H1):", key="k_main")
        st.text_input("Podtytuł:", key="k_sub")
        st.text_area("Opis (prawa kolumna):", height=160, key="k_opis",
                     help="Główny opis kierunku po prawej stronie slajdu.")

        _section_header("BOX Z FAKTAMI (lewa kolumna)")
        # Walidacja kolorów boksu
        for _ck, _cv in [('k_box_bg', st.session_state.get('color_h1', '#003366')),
                         ('k_box_txt', '#ffffff')]:
            _v = st.session_state.get(_ck, _cv)
            if not (isinstance(_v, str) and _v.startswith('#') and len(_v) == 7):
                st.session_state[_ck] = _cv
        cb1, cb2 = st.columns(2)
        cb1.color_picker("Kolor tła boksu", key="k_box_bg")
        cb2.color_picker("Kolor tekstu w boksie", key="k_box_txt")
        st.text_input("Tytuł boksu (np. FAKTY):", key="k_facts_title",
)
        st.text_area(
            "Fakty (Format: 'Etykieta: Wartość'):", height=160, key="k_facts",
            help="Każda linia = jeden wpis. 'Etykieta: Wartość' pogrubia etykietę.",
        )

        _section_header("ZDJĘCIE (jedno zdjęcie w dwóch ramkach)")
        u4 = st.file_uploader("Zdjęcie kierunku:", key="kie_hero")
        if u4:
            st.session_state['img_hero_k'] = optimize_img(u4.getvalue())

    # -----------------------------------------------------------------------
    # MAPA PODRÓŻY
    # -----------------------------------------------------------------------
    elif page == "Mapa Podróży":
        map_keys = [
            'map_hide', 'map_overline', 'map_title', 'map_subtitle', 'map_desc',
            'img_map_bg', 'map_zoom', 'num_map_points', 'img_map_bg_auto', 'auto_map_points',
        ]
        for i in range(st.session_state.get('num_map_points', 3)):
            map_keys.extend([f'map_pt_name_{i}', f'map_conn_{i}', f'map_pt_sym_{i}',
                              f'map_pt_x_{i}', f'map_pt_y_{i}'])
        section_template_manager(map_keys, "MAP", "mapa-podrozy", "map")
        st.checkbox("Ukryj slajd", key="map_hide")
        st.text_input("Mały nadtytuł:", key="map_overline")
        st.text_area("Główny tytuł H1:", key="map_title")
        st.text_input("Podtytuł:", key="map_subtitle")
        st.text_area("Opis pod mapą:", height=100, key="map_desc")
        _section_header("AUTOMATYCZNY KREATOR MAPY")
        map_zoom = st.slider("Zoom startowy (auto-zoom dostosuje dla wielu punktów):", 4, 12, key="map_zoom")
        st.number_input("Liczba punktów na trasie:", 1, 10, step=1, key="num_map_points")
        points_data = []
        for i in range(st.session_state['num_map_points']):
            for dk, dv in [(f'map_pt_name_{i}', f'Punkt {i+1}'), (f'map_conn_{i}', 'Brak'),
                           (f'map_pt_sym_{i}', False), (f'map_pt_x_{i}', 15), (f'map_pt_y_{i}', 10)]:
                if dk not in st.session_state:
                    st.session_state[dk] = dv
            with st.expander(f"Punkt {i+1}", expanded=True):
                st.text_input("Nazwa (np. Rzym, Hiszpania):", key=f"map_pt_name_{i}")
                conn_opts = ["Brak", "Przejazd (Linia ciągła)", "Przelot (Linia przerywana + Samolot)"]
                st.selectbox("Połączenie z NASTĘPNYM punktem:", conn_opts, key=f"map_conn_{i}")
                pt_sym = st.checkbox("Punkt oddalony (symboliczny)", key=f"map_pt_sym_{i}")
                if pt_sym:
                    c1, c2 = st.columns(2)
                    c1.slider("Pozycja X %:", 0, 100, key=f"map_pt_x_{i}")
                    c2.slider("Pozycja Y %:", 0, 100, key=f"map_pt_y_{i}")
                points_data.append({
                    'name': st.session_state[f"map_pt_name_{i}"],
                    'conn': st.session_state[f"map_conn_{i}"],
                    'symbolic': st.session_state[f"map_pt_sym_{i}"],
                    'x': st.session_state[f"map_pt_x_{i}"],
                    'y': st.session_state[f"map_pt_y_{i}"],
                })
        if st.button("GENERUJ MAPĘ AUTOMATYCZNIE", type="primary", use_container_width=True):
            with st.spinner("Pobieranie i renderowanie danych..."):
                country = st.session_state.get('country_name', '')
                valid_pts = []
                for p in points_data:
                    nm = p['name'].strip()
                    if not nm:
                        continue
                    if p['symbolic']:
                        valid_pts.append({'name': nm, 'conn': p['conn'], 'symbolic': True,
                                          'x': p['x'], 'y': p['y']})
                    else:
                        lat, lon = geocode_place(nm, country)
                        if lat is None:
                            lat, lon = geocode_place(nm)
                        if lat is not None:
                            valid_pts.append({'name': nm, 'conn': p['conn'], 'symbolic': False,
                                              'lat': lat, 'lon': lon})
                if valid_pts:
                    try:
                        bg_b64, final_pts = generate_map_data(valid_pts, zoom=map_zoom)
                        if bg_b64 is not None or final_pts:
                            if bg_b64:
                                st.session_state['img_map_bg_auto'] = bg_b64
                            st.session_state['auto_map_points'] = final_pts
                            st.success("Mapa wygenerowana pomyślnie.")
                            st.rerun()
                    except Exception:
                        st.error("Błąd podczas generowania mapy.")
                else:
                    st.warning("Nie udało się zgeokodować żadnego punktu.")

        # --- Sekcja odległości ---
        _section_header("ODLEGŁOŚCI I CZAS DOJAZDU")
        st.text_input("Tytuł sekcji na slajdzie:", key="map_dist_title")

        # Klucz ORS — wczytywany z Streamlit Secrets (priorytet) lub wpisany ręcznie
        _ors_from_secrets = st.secrets.get("ORS_API_KEY", "") if hasattr(st, 'secrets') else ""
        if _ors_from_secrets and not st.session_state.get('ors_api_key'):
            st.session_state['ors_api_key'] = _ors_from_secrets

        if _ors_from_secrets:
            st.markdown(
                "<div style='font-size:11px; color:#16a34a; margin-bottom:8px; "
                "padding:6px 10px; background:#f0fdf4; border-radius:4px; "
                "border-left:3px solid #16a34a;'>"
                "✓ Klucz API wczytany z konfiguracji aplikacji.</div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<div style='font-size:11px; color:#64748b; margin-bottom:8px;'>"
                "Klucz API OpenRouteService — wpisz ręcznie lub skonfiguruj "
                "w Streamlit Secrets jako <code>ORS_API_KEY</code>.</div>",
                unsafe_allow_html=True,
            )
            st.text_input("Klucz ORS API:", key="ors_api_key", type="password",
                          help="Zarejestruj się na openrouteservice.org → Dashboard → API Key")

        st.number_input("Liczba par miejscowości:", 0, 10, step=1, key="num_dist_pairs")

        for di in range(st.session_state.get('num_dist_pairs', 0)):
            for dk, dv in [
                (f'dist_a_{di}', ''), (f'dist_b_{di}', ''),
                (f'dist_km_{di}', '—'), (f'dist_time_{di}', '—'),
            ]:
                if dk not in st.session_state:
                    st.session_state[dk] = dv

            with st.expander(f"Para {di+1}: {st.session_state.get(f'dist_a_{di}','')} → {st.session_state.get(f'dist_b_{di}','')}",
                             expanded=True):
                ca, cb = st.columns(2)
                ca.text_input("Miejsce A:", key=f"dist_a_{di}")
                cb.text_input("Miejsce B:", key=f"dist_b_{di}")

                if st.button("POBIERZ ODLEGŁOŚĆ", key=f"btn_dist_{di}",
                             use_container_width=True):
                    # Klucz z Secrets ma priorytet, potem z pola tekstowego
                    ors_key = (st.secrets.get("ORS_API_KEY", "") if hasattr(st, 'secrets') else "") \
                              or st.session_state.get('ors_api_key', '').strip()
                    a = st.session_state.get(f'dist_a_{di}', '').strip()
                    b = st.session_state.get(f'dist_b_{di}', '').strip()
                    if not a or not b:
                        st.warning("Wpisz obie nazwy miejscowości.")
                    else:
                        with st.spinner(f"Szukam trasy {a} → {b}..."):
                            km, mins, err = get_road_distance(
                                a, b, ors_key,
                                st.session_state.get('country_name', ''),
                            )
                        if km is not None:
                            st.session_state[f'dist_km_{di}'] = f'{km}'
                            st.session_state[f'dist_time_{di}'] = format_duration(mins)
                            if err:
                                # Fallback haversine - pokaż ostrzeżenie z wyjaśnieniem
                                st.warning(f"✓ Zapisano: {km} km, {format_duration(mins)}\n\n⚠️ {err}")
                            else:
                                st.success(f"✓ Trasa drogowa: {km} km, {format_duration(mins)}")
                            st.rerun()
                        else:
                            st.error(f"Nie udało się pobrać trasy.\n\n{err}")

                cd1, cd2 = st.columns(2)
                cd1.text_input("Odległość (km) — edytowalna:", key=f"dist_km_{di}")
                cd2.text_input("Czas dojazdu — edytowalny:", key=f"dist_time_{di}")

    # -----------------------------------------------------------------------
    # JAK LECIMY
    # -----------------------------------------------------------------------
    elif page == "Jak lecimy?":
        l_keys = [
            'l_hide', 'l_przesiadka', 'l_port', 'l_czas', 'l_overline', 'l_main',
            'l_sub', 'm_route', 'm_luggage', 'f1', 'f2', 'f3', 'f4',
            'l_desc', 'l_extra', 'img_hero_l',
        ]
        section_template_manager(l_keys, "LOT", "jak-lecimy", "lot")
        st.checkbox("Ukryj ten slajd w PDF", key="l_hide")
        st.text_input("Mały nadtytuł:", key="l_overline")
        st.text_input("Tytuł (H1):", key="l_main")
        for k, l in [('l_sub', 'Podtytuł'), ('m_route', 'Trasa'), ('m_luggage', 'Bagaż'),
                     ('f1', 'Lot 1'), ('f2', 'Lot 2')]:
            st.text_input(l, key=k)
        if st.checkbox("Lot z przesiadką", key="l_przesiadka"):
            _section_header("DANE PRZESIADKI I KOLEJNE ODCINKI LOTU")
            c1, c2 = st.columns(2)
            c1.text_input("Port przesiadkowy:", key="l_port")
            c2.text_input("Długość przesiadki:", key="l_czas")
            for k, l in [('f3', 'Lot 3'), ('f4', 'Lot 4')]:
                st.text_input(l, key=k)
        for k, l in [('l_desc', 'Opis'), ('l_extra', 'Dodatkowe info')]:
            st.text_area(l, key=k)
        u5 = st.file_uploader("Foto Samolotu", key="lot_hero")
        if u5:
            st.session_state['img_hero_l'] = optimize_img(u5.getvalue())

    # -----------------------------------------------------------------------
    # ZAKWATEROWANIE
    # -----------------------------------------------------------------------
    elif page == "Zakwaterowanie":

        st.number_input("Liczba hoteli:", 1, 3, step=1, key="num_hotels")
        _rebuild_slide_order()
        hotel_order = _get_hotel_order()

        # Panel kolejności hoteli
        if len(hotel_order) > 1:
            _section_header("KOLEJNOŚĆ HOTELI W PREZENTACJI")
            for pos, hi in enumerate(hotel_order):
                name = str(st.session_state.get(f'h_title_{hi}', f'Hotel {hi+1}')).split('\n')[0][:35] or f'Hotel {hi+1}'
                col_lbl, col_up, col_dn = st.columns([8, 1, 1])
                col_lbl.markdown(
                    f"<div style='padding:6px 10px; background:#f1f5f9; border-radius:4px; "
                    f"border-left:3px solid #003366; font-size:12px; color:#1e293b;'>"
                    f"<strong style='color:#003366; font-size:10px; text-transform:uppercase; "
                    f"letter-spacing:1px;'>Hotel {pos+1}</strong><br>{name}</div>",
                    unsafe_allow_html=True,
                )
                if pos > 0:
                    col_up.button("▲", key=f"ho_up_{pos}",
                                  on_click=_move_hotel, args=(pos, -1),
                                  use_container_width=True)
                if pos < len(hotel_order) - 1:
                    col_dn.button("▼", key=f"ho_dn_{pos}",
                                  on_click=_move_hotel, args=(pos, 1),
                                  use_container_width=True)

        st.divider()
        for i in range(st.session_state['num_hotels']):
            with st.expander(f"Hotel {i+1}" + (f" — {str(st.session_state.get(f'h_title_{i}','')).split(chr(10))[0][:30]}" if st.session_state.get(f'h_title_{i}') else "")):
                st.button("POKAŻ PODGLĄD", key=f"btn_show_hot_{i}",
                          on_click=set_focus, args=(f"slide-hotel-{i}",), use_container_width=True)
                for dk, dv in [
                    (f'h_hide_{i}', False), (f'h_overline_{i}', 'ZAKWATEROWANIE'),
                    (f'h_title_{i}', f'NAZWA HOTELU {i+1} 5*'),
                    (f'h_subtitle_{i}', 'Komfort i elegancja na najwyższym poziomie'),
                    (f'h_url_{i}', 'www.przykładowy-hotel.com'), (f'h_booking_{i}', '8.9'),
                    (f'h_amenities_{i}', ["Basen", "SPA", "Wi-Fi", "Restauracja", "Plaża"]),
                    (f'h_text_{i}', 'Zapewniamy zakwaterowanie w starannie wyselekcjonowanym hotelu.'),
                    (f'h_advantages_{i}', 'Położenie tuż przy prywatnej plaży'),
                ]:
                    if dk not in st.session_state:
                        st.session_state[dk] = dv
                h_keys = [
                    f'h_hide_{i}', f'h_overline_{i}', f'h_title_{i}', f'h_subtitle_{i}',
                    f'h_url_{i}', f'h_booking_{i}', f'h_amenities_{i}', f'h_text_{i}',
                    f'h_advantages_{i}', f'img_hotel_1_{i}', f'img_hotel_1b_{i}',
                    f'img_hotel_2_{i}', f'img_hotel_3_{i}',
                ]
                section_template_manager(
                    h_keys, "HOT", st.session_state.get(f'h_title_{i}', f'hotel-{i+1}'),
                    f"hot_{i}", index=i,
                )
                st.checkbox("Ukryj ten slajd w PDF", key=f"h_hide_{i}",
                            on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.text_input("Mały nadtytuł:", key=f"h_overline_{i}",
                              on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.text_area("Nazwa hotelu (H1):", key=f"h_title_{i}",
                             on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.text_input("Podtytuł:", key=f"h_subtitle_{i}",
                              on_change=set_focus, args=(f"slide-hotel-{i}",))
                c1, c2 = st.columns(2)
                c1.text_input("Strona www:", key=f"h_url_{i}",
                              on_change=set_focus, args=(f"slide-hotel-{i}",))
                c2.text_input("Ocena Booking.com:", key=f"h_booking_{i}",
                              on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.multiselect("Udogodnienia (ikonki):", list(hotel_icons.keys()),
                               key=f"h_amenities_{i}", on_change=set_focus,
                               args=(f"slide-hotel-{i}",))
                st.text_area("Opis hotelu:", height=200, key=f"h_text_{i}",
                             on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.text_area("Atuty hotelu:", height=100, key=f"h_advantages_{i}",
                             on_change=set_focus, args=(f"slide-hotel-{i}",))
                cl1, cl2 = st.columns(2)
                u_h1 = cl1.file_uploader("Zdj. Lewe Górne", key=f"uh1_{i}",
                                         on_change=set_focus, args=(f"slide-hotel-{i}",))
                if u_h1:
                    st.session_state[f'img_hotel_1_{i}'] = optimize_img(u_h1.getvalue())
                u_h1b = cl2.file_uploader("Zdj. Lewe Dolne", key=f"uh1b_{i}",
                                          on_change=set_focus, args=(f"slide-hotel-{i}",))
                if u_h1b:
                    st.session_state[f'img_hotel_1b_{i}'] = optimize_img(u_h1b.getvalue())
                c3, c4 = st.columns(2)
                u_h2 = c3.file_uploader("Zdj. Dolne 1", key=f"uh2_{i}",
                                        on_change=set_focus, args=(f"slide-hotel-{i}",))
                if u_h2:
                    st.session_state[f'img_hotel_2_{i}'] = optimize_img(u_h2.getvalue())
                u_h3 = c4.file_uploader("Zdj. Dolne 2", key=f"uh3_{i}",
                                        on_change=set_focus, args=(f"slide-hotel-{i}",))
                if u_h3:
                    st.session_state[f'img_hotel_3_{i}'] = optimize_img(u_h3.getvalue())


    # -----------------------------------------------------------------------
    # PROGRAM WYJAZDU
    # -----------------------------------------------------------------------
    elif page == "Program Wyjazdu":

        st.checkbox("Ukryj CAŁĄ sekcję Programu w PDF", key="prg_hide")
        st.number_input("Ilość dni:", 1, 15, step=1, key="num_days")
        st.date_input("Data startu:", key="p_start_dt")
        for d in range(st.session_state.get("num_days", 4)):
            with st.expander(f"Dzień {d+1}"):
                for dk in [f"attr_{d}", f"desc_{d}"]:
                    if dk not in st.session_state:
                        st.session_state[dk] = ""
                d_keys = [f'img_d_{d}', f'attr_{d}', f'desc_{d}']
                section_template_manager(d_keys, "PRG", f"Dzien_{d+1}", f"prg_{d}", index=d)
                ud = st.file_uploader(f"Foto D{d+1} (16:9)", key=f"prg_img_{d}")
                if ud:
                    st.session_state[f"img_d_{d}"] = optimize_img(ud.getvalue())
                st.text_input(f"Highlights D{d+1}", key=f"attr_{d}")
                st.text_area(f"Opis D{d+1}", key=f"desc_{d}")

    # -----------------------------------------------------------------------
    # OPISY MIEJSC (nowy układ wg wzoru)
    # -----------------------------------------------------------------------
    elif _is_attr_page:
        # Wyciągnij indeks z nazwy strony np. "  ↳ Atrakcja 1" -> pos=0 -> idx
        # Wyciągnij idx bezpośrednio z ATTR:idx:nazwa (idx = rzeczywisty indeks danych)
        _i = int(page.split(":")[1]) if page.startswith("ATTR:") else None
        if _i is None or _i >= _attr_count():
            st.warning("Nie znaleziono atrakcji.")
        else:
            _pos = next((p for p, ix in enumerate(_attr_order()) if ix == _i), 0)
            day_options_global = build_day_options(
                st.session_state.get('p_start_dt', date.today()),
                int(st.session_state.get('num_days', 5)),
            )
            for _dk, _dv in [
                (f"amain_{_i}", ""), (f"asub_{_i}", ""),
                (f"aday_{_i}", "Brak przypisania"), (f"atype_{_i}", "Atrakcja"),
                (f"aopis_{_i}", ""), (f"ahide_{_i}", False),
            ]:
                if _dk not in st.session_state:
                    st.session_state[_dk] = _dv

            # Auto-scroll: tylko gdy zmieniono aktywną atrakcję
            if st.session_state.get('_attr_focused') != _i:
                st.session_state['_attr_focused'] = _i
                set_focus(f"attr_{_i}")
            a_keys = [f'ahide_{_i}', f'amain_{_i}', f'asub_{_i}',
                      f'aday_{_i}', f'atype_{_i}', f'aopis_{_i}',
                      f'ah_{_i}', f'at1_{_i}', f'at2_{_i}', f'at3_{_i}']
            section_template_manager(a_keys, "ATR",
                st.session_state.get(f"amain_{_i}") or f"Atrakcja_{_pos+1}",
                f"atr_{_i}", index=_i)

            st.checkbox("Ukryj ten slajd w PDF", key=f"ahide_{_i}",
                        on_change=set_focus, args=(f"attr_{_i}",))
            st.text_input("Nazwa:", key=f"amain_{_i}",
                          on_change=set_focus, args=(f"attr_{_i}",))
            st.text_input("Podtytuł:", key=f"asub_{_i}",
                          on_change=set_focus, args=(f"attr_{_i}",))
            _curr = st.session_state.get(f"aday_{_i}", day_options_global[0])
            if _curr not in day_options_global:
                st.session_state[f"aday_{_i}"] = day_options_global[0]
            st.selectbox("Przypisz do dnia:", day_options_global, key=f"aday_{_i}",
                         on_change=set_focus, args=(f"attr_{_i}",))
            
            # Przycisk powrotu do programu (jeśli atrakcja przypisana do dnia)
            assigned_day = st.session_state.get(f"aday_{_i}", "Brak przypisania")
            if assigned_day != "Brak przypisania":
                if st.button(f"⬅️ Wróć do Programu ({assigned_day})", 
                            key=f"back_to_program_{_i}", 
                            use_container_width=True, 
                            type="secondary"):
                    st.session_state['last_page'] = "Program Wyjazdu"
                    st.rerun()
            
            st.selectbox("Ikona:", ["Brak"] + list(icon_map.keys()), key=f"atype_{_i}",
                         on_change=set_focus, args=(f"attr_{_i}",))
            st.text_area("Opis:", key=f"aopis_{_i}",
                         on_change=set_focus, args=(f"attr_{_i}",))
            _upa = st.file_uploader("Foto Główne", key=f"atr_hero_{_i}",
                                    on_change=set_focus, args=(f"attr_{_i}",))
            if _upa: st.session_state[f"ah_{_i}"] = optimize_img(_upa.getvalue())
            _ac1, _ac2, _ac3 = st.columns(3)
            _uat1 = _ac1.file_uploader("Fot. 1", key=f"atr_th1_{_i}",
                                       on_change=set_focus, args=(f"attr_{_i}",))
            if _uat1: st.session_state[f"at1_{_i}"] = optimize_img(_uat1.getvalue())
            _uat2 = _ac2.file_uploader("Fot. 2", key=f"atr_th2_{_i}",
                                       on_change=set_focus, args=(f"attr_{_i}",))
            if _uat2: st.session_state[f"at2_{_i}"] = optimize_img(_uat2.getvalue())
            _uat3 = _ac3.file_uploader("Fot. 3", key=f"atr_th3_{_i}",
                                       on_change=set_focus, args=(f"attr_{_i}",))
            if _uat3: st.session_state[f"at3_{_i}"] = optimize_img(_uat3.getvalue())

    elif page == "Aplikacja (Komunikacja)":
        app_keys = [
            'app_hide', 'app_overline', 'app_title', 'app_subtitle',
            'app_features', 'img_app_bg', 'img_app_screen',
        ]
        section_template_manager(app_keys, "APP", "Aplikacja", "app")
        st.checkbox("Ukryj slajd", key="app_hide")
        st.text_input("Mały nadtytuł:", key="app_overline")
        st.text_area("Główny tytuł H1:", key="app_title")
        st.text_input("Podtytuł:", key="app_subtitle")
        st.text_area("Punkty na liście:", height=200, key="app_features")
        c1, c2 = st.columns(2)
        u_bg = c1.file_uploader("Zdj. tła (Prawa str.)", key="app_bg")
        if u_bg:
            st.session_state['img_app_bg'] = optimize_img(u_bg.getvalue())
        u_sc = c2.file_uploader("Ekran Aplikacji", key="app_sc")
        if u_sc:
            st.session_state['img_app_screen'] = optimize_img(u_sc.getvalue())

    # -----------------------------------------------------------------------
    # MATERIAŁY BRANDINGOWE
    # -----------------------------------------------------------------------
    elif page == "Materiały Brandingowe":
        bra_keys = [
            'brand_hide', 'brand_overline', 'brand_title', 'brand_subtitle',
            'brand_features', 'img_brand_1', 'img_brand_2', 'img_brand_3',
        ]
        section_template_manager(bra_keys, "BRA", "Branding", "bra")
        st.checkbox("Ukryj slajd", key="brand_hide")
        st.text_input("Mały nadtytuł:", key="brand_overline")
        st.text_area("Główny tytuł H1:", key="brand_title")
        st.text_input("Podtytuł:", key="brand_subtitle")
        st.text_area("Punkty na liście (Enter = nowy punkt):", height=300, key="brand_features")
        c1, c2, c3 = st.columns(3)
        u1 = c1.file_uploader("Zdj 1 (Lewa góra)", key="bra_img_1")
        if u1:
            st.session_state['img_brand_1'] = optimize_img(u1.getvalue())
        u2 = c2.file_uploader("Zdj 2 (Prawa góra)", key="bra_img_2")
        if u2:
            st.session_state['img_brand_2'] = optimize_img(u2.getvalue())
        u3 = c3.file_uploader("Zdj 3 (Dół)", key="bra_img_3")
        if u3:
            st.session_state['img_brand_3'] = optimize_img(u3.getvalue())

    # -----------------------------------------------------------------------
    # WIRTUALNY ASYSTENT
    # -----------------------------------------------------------------------
    elif page == "Wirtualny Asystent":
        va_keys = [
            'va_hide', 'va_overline', 'va_title', 'va_subtitle',
            'va_text', 'img_va_1', 'img_va_2', 'img_va_3',
        ]
        section_template_manager(va_keys, "VA", "Asystent", "va")
        st.checkbox("Ukryj slajd", key="va_hide")
        st.text_input("Mały nadtytuł:", key="va_overline")
        st.text_area("Główny tytuł H1:", key="va_title")
        st.text_input("Podtytuł:", key="va_subtitle")
        st.text_area("Treść oferty:", height=300, key="va_text")
        c1, c2, c3 = st.columns(3)
        u1 = c1.file_uploader("Zdj 1 (Szerokie)", key="va_img_1")
        if u1:
            st.session_state['img_va_1'] = optimize_img(u1.getvalue())
        u2 = c2.file_uploader("Zdj 2 (Lewy dół)", key="va_img_2")
        if u2:
            st.session_state['img_va_2'] = optimize_img(u2.getvalue())
        u3 = c3.file_uploader("Zdj 3 (Prawy dół)", key="va_img_3")
        if u3:
            st.session_state['img_va_3'] = optimize_img(u3.getvalue())

    # -----------------------------------------------------------------------
    # PILLOW GIFTS
    # -----------------------------------------------------------------------
    elif page == "Pillow Gifts":
        gif_keys = [
            'pg_hide', 'pg_overline', 'pg_title', 'pg_subtitle',
            'pg_text', 'pg_features', 'img_pg_1', 'img_pg_2', 'img_pg_3',
        ]
        section_template_manager(gif_keys, "GIF", "Gifts", "gif")
        st.checkbox("Ukryj slajd", key="pg_hide")
        st.text_input("Mały nadtytuł:", key="pg_overline")
        st.text_area("Główny tytuł H1:", key="pg_title")
        st.text_input("Podtytuł:", key="pg_subtitle")
        st.text_area("Opis (tekst główny):", height=200, key="pg_text")
        st.text_area("Punktory (każda linia = jeden punkt):", height=150, key="pg_features",
                     help="Każda linia to jeden punkt z kwadratowym punktorkiem ■")
        c1, c2, c3 = st.columns(3)
        u1 = c1.file_uploader("Zdjęcie 1", key="pg_img_1")
        if u1:
            st.session_state['img_pg_1'] = optimize_img(u1.getvalue())
        u2 = c2.file_uploader("Zdjęcie 2 (Pionowe)", key="pg_img_2")
        if u2:
            st.session_state['img_pg_2'] = optimize_img(u2.getvalue())
        u3 = c3.file_uploader("Zdjęcie 3", key="pg_img_3")
        if u3:
            st.session_state['img_pg_3'] = optimize_img(u3.getvalue())

    # -----------------------------------------------------------------------
    # KOSZTORYS
    # -----------------------------------------------------------------------
    elif page == "Kosztorys":
        koszt_keys = [
            'koszt_hide_1', 'koszt_hide_2', 'koszt_h1_title', 'koszt_title',
            'koszt_pax', 'koszt_price', 'koszt_hotel', 'koszt_dbl', 'koszt_sgl',
            'koszt_zawiera_1', 'koszt_zawiera_2', 'koszt_nie_zawiera',
            'koszt_opcje', 'img_koszt_1', 'img_koszt_2',
        ]
        section_template_manager(koszt_keys, "KOS", "Kosztorys", "koszt")
        c1, c2 = st.columns(2)
        c1.checkbox("Ukryj CAŁY Kosztorys (Slajd 1 i 2)", key="koszt_hide_1")
        c2.checkbox("Ukryj TYLKO Slajd 2 (Ciąg dalszy)", key="koszt_hide_2")
        st.text_input("Tytuł H1 (duży, górna część):", key="koszt_h1_title")
        st.text_input("Overline (mały nadtytuł):", key="koszt_title")
        _section_header("GŁÓWNE DANE TABELI")
        c1, c2 = st.columns(2)
        c1.text_input("Wielkość grupy:", key="koszt_pax")
        c2.text_input("Cena:", key="koszt_price")
        st.text_input("Wybrany Hotel / Standard:", key="koszt_hotel")
        c1, c2 = st.columns(2)
        c1.text_input("Ilość pokoi DBL:", key="koszt_dbl")
        c2.text_input("Ilość pokoi SGL:", key="koszt_sgl")
        _section_header("AUTO-UZUPEŁNIANIE")
        if st.button("GENERUJ LISTĘ KOSZTÓW Z OFERTY", type="primary", use_container_width=True):
            auto_generate_kosztorys()
            st.success("Lista kosztów wygenerowana pomyślnie.")
            st.rerun()
        _section_header("TREŚĆ KOSZTORYSU")
        st.text_area("Cena zawiera (Część 1 - Slajd 1):", height=200, key="koszt_zawiera_1")
        st.text_area("Cena zawiera (Część 2 - Slajd 2):", height=150, key="koszt_zawiera_2")
        st.text_area("Nie policzone w cenie:", height=100, key="koszt_nie_zawiera")
        st.text_area("Koszty opcjonalne:", height=100, key="koszt_opcje")
        _section_header("ZDJĘCIA")
        c1, c2 = st.columns(2)
        u1 = c1.file_uploader("Zdjęcie (Slajd 1)", key="koszt_img_1")
        if u1:
            st.session_state['img_koszt_1'] = optimize_img(u1.getvalue())
        u2 = c2.file_uploader("Zdjęcie (Slajd 2)", key="koszt_img_2")
        if u2:
            st.session_state['img_koszt_2'] = optimize_img(u2.getvalue())

    # -----------------------------------------------------------------------
    # CO O NAS MÓWIĄ
    # -----------------------------------------------------------------------
    elif page == "Co o nas mówią":


        opi_keys = [
            'testim_hide', 'testim_overline', 'testim_title', 'testim_subtitle',
            'img_testim_main', 'testim_count',
        ]
        for i in range(st.session_state.get('testim_count', 3)):
            opi_keys.extend([f'testim_img_{i}', f'testim_head_{i}',
                             f'testim_quote_{i}', f'testim_author_{i}', f'testim_role_{i}'])
        section_template_manager(opi_keys, "OPI", "Opinie", "opi")
        st.checkbox("Ukryj ten slajd w PDF", key="testim_hide")
        st.text_input("Mały nadtytuł:", key="testim_overline")
        st.text_area("Główny tytuł H1:", key="testim_title")
        st.text_area("Podtytuł:", key="testim_subtitle")
        u_main = st.file_uploader("Zdjęcie główne slajdu", key="opi_main")
        if u_main:
            st.session_state['img_testim_main'] = optimize_img(u_main.getvalue())
        st.number_input("Liczba opinii:", 1, 4, step=1, key="testim_count")
        for i in range(st.session_state['testim_count']):
            for dk in [f"testim_head_{i}", f"testim_quote_{i}",
                       f"testim_author_{i}", f"testim_role_{i}"]:
                if dk not in st.session_state:
                    st.session_state[dk] = ""
            with st.expander(f"Opinia {i+1}"):
                u_testim = st.file_uploader("Zdjęcie / Logo", key=f"opi_img_{i}")
                if u_testim:
                    st.session_state[f"testim_img_{i}"] = optimize_img(u_testim.getvalue())
                st.text_input("Nagłówek", key=f"testim_head_{i}")
                st.text_area("Treść rekomendacji", key=f"testim_quote_{i}")
                c1, c2 = st.columns(2)
                c1.text_input("Autor (Pogrubiony)", key=f"testim_author_{i}")
                c2.text_input("Stanowisko", key=f"testim_role_{i}")

    # -----------------------------------------------------------------------
    # O NAS / ZESPÓŁ
    # -----------------------------------------------------------------------
    elif page == "O Nas (Zespół)":
        nas_keys = [
            'about_hide', 'about_overline', 'about_title', 'about_sub',
            'about_desc', 'about_panel_title', 'about_panel_text',
            'team_count', 'img_about_clients',
        ]
        for i in range(st.session_state.get('team_count', 2)):
            nas_keys.extend([f't_name_{i}', f't_role_{i}', f't_desc_{i}', f't_img_{i}'])
        section_template_manager(nas_keys, "NAS", "Zespol", "nas")
        st.checkbox("Ukryj ten slajd w PDF", key="about_hide")
        st.text_input("Mały nadtytuł:", key="about_overline")
        st.text_area("Główny tytuł H1:", key="about_title")
        st.text_input("Podtytuł:", key="about_sub")
        st.text_area("Opis główny:", height=150, key="about_desc")
        u_clients = st.file_uploader("Zdjęcie prawe (Klienci / Logotypy)", key="nas_clients")
        if u_clients:
            st.session_state['img_about_clients'] = optimize_img(u_clients.getvalue())
        st.number_input("Liczba osób w zespole:", 1, 4, step=1, key="team_count")
        for i in range(st.session_state['team_count']):
            for dk in [f"t_name_{i}", f"t_role_{i}", f"t_desc_{i}"]:
                if dk not in st.session_state:
                    st.session_state[dk] = ""
            with st.expander(f"Osoba {i+1}"):
                st.text_input("Imię i nazwisko", key=f"t_name_{i}")
                st.text_input("Stanowisko", key=f"t_role_{i}")
                st.text_area("Krótki opis", key=f"t_desc_{i}")
                u_team = st.file_uploader("Zdjęcie (okrągłe)", key=f"nas_img_{i}")
                if u_team:
                    st.session_state[f"t_img_{i}"] = optimize_img(u_team.getvalue())

    # -----------------------------------------------------------------------
    # WYGLĄD I KOLORY
    # -----------------------------------------------------------------------
    # -----------------------------------------------------------------------
    # WYGLĄD I KOLORY
    # -----------------------------------------------------------------------
    elif page == "Wygląd i Kolory":
        # Upewnij się że wszystkie wartości kolorów i rozmiarów są poprawne
        # zanim Streamlit wyrenderuje widgety
        color_defaults = {
            'color_h1': '#003366', 'color_h2': '#003366', 'color_sub': '#FF6600',
            'color_accent': '#FF6600', 'color_text': '#333333', 'color_metric': '#003366',
        }
        size_defaults = {
            'font_size_h1': 48, 'font_size_h2': 36, 'font_size_sub': 26,
            'font_size_text': 14, 'font_size_metric': 16,
        }
        for k, v in color_defaults.items():
            val = st.session_state.get(k, v)
            if not (isinstance(val, str) and val.startswith('#') and len(val) == 7):
                st.session_state[k] = v
        for k, v in size_defaults.items():
            val = st.session_state.get(k, v)
            try:
                _int_val = int(float(val)) if val else v
                if _int_val != val:
                    st.session_state[k] = _int_val
            except Exception:
                st.session_state[k] = v

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
            c3.number_input("Rozmiar (px)", min_value=8, max_value=120,
                            step=1, format="%d", key=s_key)
        st.color_picker("Akcent", key="color_accent")

    # -----------------------------------------------------------------------
    # ZAPISZ / WCZYTAJ PROJEKT
    # -----------------------------------------------------------------------
    elif page == "Zapisz / Wczytaj Projekt":
        proj = _build_proj_dict()
        proj_json = json.dumps(proj, ensure_ascii=False)

        st.markdown("##### Auto-zapis do bazy danych")
        st.info("📊 Twój projekt jest automatycznie zapisywany do bazy Supabase co 5 sekund. Dane przeżywają restart aplikacji i są dostępne zawsze.")

        st.markdown("---")
        st.markdown("##### Plik JSON na dysk / OneDrive")
        st.download_button(
            "POBIERZ PLIK PROJEKTU (JSON)", proj_json,
            get_project_filename(), use_container_width=True,
            help="Zapisz projekt jako plik .json na swój komputer lub OneDrive",
        )
        st.markdown("---")
        st.markdown("**Wczytaj projekt z pliku .json**")
        upf = st.file_uploader(
            "Wgraj projekt z dysku (.json)", type=['json'],
            key="up_export", label_visibility="collapsed",
        )
        if upf and st.button("WCZYTAJ PROJEKT Z PLIKU", use_container_width=True, type="primary"):
            # Bezpieczne ładowanie z walidacją
            data, error = _validate_and_load_json(upf)
            
            if error:
                st.error(f"❌ Nie można wczytać projektu: {error}")
            else:
                try:
                    load_project_data(data)
                    st.success(f"✅ Wczytano projekt ({len(data)} kluczy)")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Błąd ładowania danych: {str(e)[:100]}")

    # -----------------------------------------------------------------------
    # SZYBKIE AKCJE (stałe na dole sidebara)
    # -----------------------------------------------------------------------
    st.divider()
    st.markdown(
        "<div style='font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; "
        "margin-bottom: 10px; letter-spacing: 1px;'>SZYBKIE AKCJE (CAŁA OFERTA)</div>",
        unsafe_allow_html=True,
    )

    # Auto-zapis do Supabase działa w tle co 5 sekund - brak potrzeby ręcznego zapisu

    if st.button("PRZYGOTUJ OFERTĘ DO POBRANIA", type="secondary", use_container_width=True):
        with st.spinner("Generowanie ostatecznego pliku oferty..."):
            export_content = build_presentation(export_mode=True)
            acc = st.session_state.get('color_accent', '#FF6600')
            t_main = st.session_state.get('t_main', 'Oferta')
            client_html = (
                f'<!DOCTYPE html><html lang="pl"><head><meta charset="UTF-8">'
                f'<title>{t_main}</title>'
                f'<link rel="icon" href="data:image/svg+xml,<svg xmlns=\'http://www.w3.org/2000/svg\' '
                f'viewBox=\'0 0 100 100\'><circle cx=\'50\' cy=\'50\' r=\'50\' fill=\'%23FF6600\'/></svg>">'
                f'{get_local_css(return_str=True)}'
                f'<style>body{{background:#f4f5f7;margin:0;}} .presentation-wrapper{{height:100vh;overflow-y:auto;scroll-snap-type:y proximity;}}'
                f'.client-export-btn{{position:fixed;top:20px;left:20px;z-index:9999;background:{acc};color:white;border:none;'
                f'padding:15px 25px;border-radius:4px;font-family:sans-serif;font-size:12px;font-weight:700;'
                f'text-transform:uppercase;cursor:pointer;box-shadow:0 4px 15px rgba(0,0,0,0.3);}}'
                f'@media print{{.client-export-btn{{display:none !important;}} .presentation-wrapper{{height:auto !important;overflow:visible !important;}}}}'
                f'</style></head><body>'
                f'<button class="client-export-btn" onclick="window.print()">POBIERZ JAKO PDF</button>'
                f'<div class="presentation-wrapper">{export_content}</div></body></html>'
            )
            st.session_state['ready_export_html'] = client_html
            st.rerun()

    if st.session_state.get('ready_export_html'):
        st.download_button(
            "POBIERZ GOTOWY PLIK HTML",
            st.session_state['ready_export_html'],
            get_project_filename().replace('.json', '.html'),
            "text/html",
            type="primary",
            use_container_width=True,
        )

    if st.button("GENERUJ LINK DO OFERTY ONLINE", use_container_width=True):
        st.session_state['show_link_info'] = not st.session_state.get('show_link_info', False)
    if st.session_state.get('show_link_info', False):
        st.info(
            "Wyeksportuj plik HTML za pomocą przycisku wyżej i umieść go na serwerze swojej agencji. "
            "Plik jest w pełni autonomiczną stroną WWW – gotowym, bezpiecznym linkiem dla klienta."
        )

    if st.button("PODGLĄD PEŁNOEKRANOWY", use_container_width=True):
        st.session_state['client_mode'] = True
        st.rerun()


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# AUTO-SAVE DO SUPABASE - Bezpieczny upsert z ID
# ---------------------------------------------------------------------------
if 'last_supabase_save' not in st.session_state:
    st.session_state['last_supabase_save'] = 0

current_time = time.time()
# Auto-save co 10 sekund (nie 2s - za częste zapisy obciążają bazę)
if current_time - st.session_state['last_supabase_save'] > 10:
    try:
        project_data = _build_proj_dict()
        project_name = st.session_state.get('t_main', 'Nowy projekt')
        
        # Sprawdź czy istnieje rekord dla tego użytkownika
        existing = supabase.table('projects').select('id').eq(
            'user_email', 'default_user'
        ).order('updated_at', desc=True).limit(1).execute()
        
        if existing.data:
            # UPDATE istniejącego rekordu
            project_id = existing.data[0]['id']
            supabase.table('projects').update({
                'project_name': project_name,
                'data': project_data,
                'updated_at': datetime.now().isoformat()
            }).eq('id', project_id).execute()
        else:
            # INSERT nowego rekordu
            supabase.table('projects').insert({
                'user_email': 'default_user',
                'project_name': project_name,
                'data': project_data,
                'updated_at': datetime.now().isoformat()
            }).execute()
        
        st.session_state['last_supabase_save'] = current_time
        # Status zapisu (widoczny dla użytkownika)
        save_time = datetime.now().strftime('%H:%M:%S')
        st.session_state['last_save_status'] = f"✅ Zapisano {save_time}"
        st.session_state['last_save_count'] = len(project_data)
    except Exception as e:
        # Cichy błąd - nie przerywaj renderowania
        st.session_state['last_save_status'] = f"❌ {str(e)[:50]}"

# Pokaż status load w sidebarze (debug)
if '_debug_loaded' in st.session_state:
    with st.sidebar:
        st.caption(st.session_state['_debug_loaded'])

# ---------------------------------------------------------------------------
# GŁÓWNA ZAWARTOŚĆ — PODGLĄD PREZENTACJI
# ---------------------------------------------------------------------------
with col_preview:
    _acc = st.session_state.get('color_accent', '#FF6600')
    st.markdown(f"<h3 style='color:{_acc};font-size:16px;margin-bottom:20px;'>PODGLĄD SLAJDU</h3>", unsafe_allow_html=True)
    build_presentation(page)
