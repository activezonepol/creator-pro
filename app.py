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
import hashlib
import base64
import uuid
from datetime import date, datetime
import time
import streamlit as st
from db_utils import save_to_supabase, fetch_all_offers
from supabase import create_client, Client
from data_utils import _build_proj_dict
from my_components import safe_text_input, safe_text_area, safe_checkbox, safe_selectbox, safe_number_input
from renderer import (
    COUNTRIES_DICT, FONTS_LIST, hotel_icons, icon_map, ATTR_ICONS_AVAILABLE, defaults, IMAGE_KEYS,
    EXCLUDE_EXPORT_KEYS, pl_days_map,
    clean_str, create_slug, parse_date_and_days, load_project_data,
    get_project_filename, auto_generate_kosztorys, build_day_options,
    optimize_img, optimize_logo, geocode_place, generate_map_data,
    get_road_distance, format_duration,
    get_local_css, build_presentation,
)
from storage_utils import (
    upload_image, 
    migrate_bytes_to_storage,
    get_image_html, 
    get_logo_html,
    cleanup_session_bytes_to_storage,
    run_migration_flow,
)

# --- INICJALIZACJA UI ---
if "preview_container" not in st.session_state:
    st.session_state.preview_container = st.empty()

# ---------------------------------------------------------------------------
# HELPERY ZARZĄDZANIA PROJEKTAMI
# ---------------------------------------------------------------------------
def _switch_project(project_id):
    """Wczytuje projekt o danym ID z bazy i ustawia jako aktywny."""
    from db_utils import fetch_offer_by_id
    sb = st.session_state.get('supabase')
    if not sb:
        st.error("Brak połączenia z bazą")
        return
    offer = fetch_offer_by_id(sb, project_id)
    if not offer:
        st.error("Nie znaleziono projektu")
        return
    
    # Wyczyść aktualne dane (zachowując kluczowe ustawienia widgetów)
    keys_to_remove = []
    for k in list(st.session_state.keys()):
        # Zachowaj klucze techniczne i widgety, usuń dane projektu
        if k in ('supabase', 'preview_container', 'client_mode', '_loaded_from_supabase',
                 'active_project_id', 'last_supabase_save', 'last_save_status',
                 'last_save_status_type', 'last_save_extra', 'last_save_count',
                 'last_save_project_name', '_upload_counter'):
            continue
        if k.startswith(('up_', 'btn_', 'dl_', 'main_nav_', 'manual_', 'res_', 'attr_up_',
                         'attr_dn_', 'attr_del_', 'hotel_up_', 'hotel_dn_', 'hotel_del_',
                         'ho_', 'del_', 'btn_sek_', 'btn_show_', 'btn_apply_')):
            continue
        keys_to_remove.append(k)
    for k in keys_to_remove:
        del st.session_state[k]
    
    # Wczytaj dane projektu
    project_data = offer.get('data', {})
    if project_data:
        load_project_data(project_data)
    
    # Ustaw aktywny projekt
    st.session_state['active_project_id'] = project_id
    st.session_state['last_supabase_save'] = time.time()  # opóźnij auto-save
    st.rerun()

def _new_project(copy_from_id=None):
    """Tworzy nowy projekt - pusty lub jako kopia istniejącego."""
    from db_utils import fetch_offer_by_id, clone_offer
    sb = st.session_state.get('supabase')
    if not sb:
        st.error("Brak połączenia z bazą")
        return
    
    if copy_from_id:
        # Skopiuj istniejący projekt
        new_id = clone_offer(sb, copy_from_id)
        if new_id:
            _switch_project(new_id)
    else:
        # Wyczyść session_state i utwórz nowy pusty projekt
        keys_to_remove = []
        for k in list(st.session_state.keys()):
            if k in ('supabase', 'preview_container', 'client_mode', '_loaded_from_supabase',
                     'last_supabase_save', '_upload_counter'):
                continue
            if k.startswith(('up_', 'btn_', 'dl_', 'main_nav_', 'manual_', 'res_', 'attr_up_',
                             'attr_dn_', 'attr_del_', 'hotel_up_', 'hotel_dn_', 'hotel_del_',
                             'ho_', 'del_', 'btn_sek_', 'btn_show_', 'btn_apply_')):
                continue
            keys_to_remove.append(k)
        for k in keys_to_remove:
            del st.session_state[k]
        
        # Ustaw defaults
        for k, v in defaults.items():
            st.session_state[k] = v
        
        # Wyczyść active_project_id - auto-save utworzy nowy rekord
        st.session_state['active_project_id'] = None
        st.session_state['last_supabase_save'] = 0  # wymuś natychmiastowy zapis
        save_to_supabase()  # utwórz nowy rekord od razu
        st.rerun()


# ---------------------------------------------------------------------------
# HELPERY INPUTÓW I UPLOADU
# ---------------------------------------------------------------------------
def _make_upload_callback(session_key, is_logo=False):
    """Tworzy callback dla file_uploadera, wywoływany on_change.
    
    Callback wykonuje się PRZED renderingiem skryptu — dzięki temu
    URL nowego zdjęcia trafia do session_state na czas, a renderer
    od razu wyświetla nowy obraz (bez konieczności przeładowania).
    
    Args:
        session_key: docelowy klucz w session_state (np. 'img_hero_t')
        is_logo: True jeśli logo (zapisywane jako PNG)
    
    Returns:
        Funkcja callback do przekazania jako on_change w file_uploader.
        Klucz file_uploadera musi być f"up_{session_key}".
    """
    upload_widget_key = f"up_{session_key}"
    def _callback():
        f = st.session_state.get(upload_widget_key)
        if f:
            _upload_image(f.getvalue(), session_key, is_logo=is_logo)
    return _callback

def _delete_image(session_key):
    """Usuwa zdjęcie z session_state i wymusza odświeżenie podglądu."""
    if session_key in st.session_state:
        del st.session_state[session_key]
    # Inkrementujemy licznik wymuszający przebudowę iframe
    st.session_state['_upload_counter'] = st.session_state.get('_upload_counter', 0) + 1
    st.rerun()

def _render_uploader_with_delete(container, label, session_key, is_logo=False):
    """Renderuje file_uploader + przycisk 'Usuń <label>' (jeśli zdjęcie istnieje).
    
    Args:
        container: Streamlit container (np. st, c1, c2)
        label: Etykieta uploadera (używana też w przycisku Usuń)
        session_key: Klucz w session_state (np. 'logo_az')
        is_logo: True jeśli logo
    """
    container.file_uploader(
        label,
        key=f"up_{session_key}",
        on_change=_make_upload_callback(session_key, is_logo=is_logo)
    )
    # Pokazujemy przycisk Usuń tylko jeśli zdjęcie istnieje w session_state
    if st.session_state.get(session_key):
        if container.button(f"✕ Usuń {label}", key=f"del_{session_key}", use_container_width=True):
            _delete_image(session_key)
def _upload_image(file_bytes, session_key, is_logo=False):
    """Przesyła obraz do Supabase i zapisuje URL w sesji."""
    if not file_bytes:
        return
    
    try:
        sb = init_supabase() 
        # Przesyłamy plik i otrzymujemy publiczny URL
        url = upload_image(sb, session_key, file_bytes, is_logo=is_logo)
        
        if url:
            # ZAPISUJEMY CZYSTY URL (bez base64)
            st.session_state[session_key] = url
            st.session_state["_last_upload_ok"] = True
            # Inkrementujemy licznik wymuszający przebudowę iframe (components.html)
            st.session_state['_upload_counter'] = st.session_state.get('_upload_counter', 0) + 1
            # WAŻNE: wymuszamy natychmiastowy zapis do Supabase (bez czekania na auto-save)
            save_to_supabase()
            # Wymuszamy odświeżenie, żeby podgląd od razu widział nowe logo
            st.rerun()
        else:
            st.error("Nie udało się uzyskać adresu URL po uploadzie.")
    except Exception as e:
        st.error(f"Błąd krytyczny uploadu: {e}")

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
st.session_state['supabase'] = supabase

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
        
        # 5. Walidacja kluczy (łagodna - kompatybilność ze starymi plikami)
        if expected_keys:
            found_keys = set(data.keys())
            expected_set = set(expected_keys)
            overlap = found_keys.intersection(expected_set)
            # Wymagaj co najmniej 30% kluczy (dla kompatybilności wstecznej)
            if len(overlap) < len(expected_set) * 0.3:
                return None, f"Za mało kluczy. Znaleziono: {', '.join(sorted(list(overlap)[:5]))}"
        
        return data, None
        
    except Exception as e:
        return None, f"Błąd odczytu: {str(e)[:100]}"

def section_template_manager(section_keys, file_prefix, default_filename, uploader_key, index=None):
    ATR_KEY_MAP = {"atype": "type", "amain": "main", "asub": "sub", "aopis": "opis"}
    _acc = st.session_state.get('color_accent', '#FF6600')
    
    # CSS dla expandera szablonu: kolor akcentu + wysokość 48px + uppercase
    st.markdown(
        f"<style>"
        f"[data-testid='stExpander'] summary {{"
        f"min-height: 48px !important;"
        f"background-color: {_acc} !important;"
        f"color: white !important;"
        f"border-radius: 4px !important;"
        f"font-family: 'Montserrat', sans-serif !important;"
        f"text-transform: uppercase !important;"
        f"font-size: 12px !important;"
        f"letter-spacing: 1px !important;"
        f"font-weight: 600 !important;"
        f"padding: 0 16px !important;"
        f"}}"
        f"[data-testid='stExpander'] summary svg {{"
        f"fill: white !important;"
        f"}}"
        f"[data-testid='stExpander'] summary p {{"
        f"color: white !important;"
        f"}}"
        f"[data-testid='stDownloadButton'] button {{"
        f"background-color: {_acc} !important;"
        f"border-color: {_acc} !important;"
        f"color: white !important;"
        f"min-height: 48px !important;"
        f"}}"
        f"[data-testid='stDownloadButton'] button:hover {{"
        f"background-color: {_acc} !important;"
        f"opacity: 0.9 !important;"
        f"}}"
        f"</style>",
        unsafe_allow_html=True
    )
    
    exp = st.expander("ZARZĄDZANIE SZABLONEM SLAJDU", expanded=False)
    
    if not exp.expanded:
        return

    with exp:
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
                f"<div style='font-size:10px;font-weight:700;color:{_acc};"
                f"text-transform:uppercase;letter-spacing:1px;font-family:Montserrat,sans-serif;"
                f"padding:4px 0 2px 0;'>NAZWA SLAJDU:</div>"
                f"<div style='font-size:13px;font-weight:600;color:#334155;'>{_display}</div>",
                unsafe_allow_html=True,
            )
        
        with col2:
            st.download_button(
                "↓ ZAPISZ", json_str, full_filename,
                key=f"dl_{uploader_key}", use_container_width=True, type="primary",
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
                expected_keys_no_index = [re.sub(f'_{index}$', '', k) if index else k for k in section_keys]
                data, error = _validate_and_load_json(uploaded_file, expected_keys=expected_keys_no_index)
                
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
# AUTO-LOAD Z SUPABASE przy starcie sesji
# ---------------------------------------------------------------------------
if '_loaded_from_supabase' not in st.session_state:
    try:
        # Pobierz aktywny projekt (z session_state) lub najnowszy
        _active_id = st.session_state.get('active_project_id')
        if _active_id:
            result = supabase.table('projects').select('data, id').eq(
                'id', _active_id
            ).execute()
        else:
            result = supabase.table('projects').select('data, id').eq(
                'user_email', 'default_user'
            ).order('updated_at', desc=True).limit(1).execute()
        
        if result.data and result.data[0].get('data'):
            project_data = result.data[0]['data']
            st.session_state['active_project_id'] = result.data[0].get('id')
            
            # KLUCZOWE: Usuń klucze widgetów zanim wczytasz do session_state
            # (kolizja z Streamlit widget management)
            widget_keys = [
                'attr_add_btn', 'attr_select', 'nav_top_radio', 'nav_bot_radio',
                '_supabase_data', 'last_supabase_save', 'last_save_status',
                'btn_add_hotel_main', 'main_nav_radio', 'manual_save_btn'
            ]
            # Usuń też prefiksy widgetów (przyciskami i innymi widgetami Streamlita)
            widget_prefixes = [
                'attrnav_', 'attrup_', 'attrdn_', 'attrdel_',
                'hotel_up_', 'hotel_dn_', 'hotel_del_',
                'btn_', 'ho_up_', 'ho_dn_', 'ho_del_',
                'res_sek_', 'btn_sek_', 'btn_show_hot_', 'btn_apply_',
                'dl_', 'up_', 'del_', 'attr_up_', 'attr_dn_', 'attr_del_',
                'prep_', 'proj_', 'dup_', 'new_proj_'
            ]
            
            keys_to_remove = []
            for key in project_data.keys():
                if key in widget_keys:
                    keys_to_remove.append(key)
                elif any(key.startswith(prefix) for prefix in widget_prefixes):
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                project_data.pop(key, None)
            
            load_project_data(project_data)
            st.session_state['_loaded_from_supabase'] = True
        else:
            # Brak zapisanego projektu — załaduj defaults
            st.session_state['_loaded_from_supabase'] = True
    except Exception as e:
        # Błąd połączenia — kontynuuj z defaults
        print(f"Błąd ładowania projektu z Supabase: {e}")
        st.session_state['_loaded_from_supabase'] = True
# Ładuj defaults dla kluczy których nie ma w bazie
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v
# Wymagane dla 4 przerywników zdefiniowanych na sztywno
st.session_state.setdefault('num_sekcje', 4)
# Wymuszenie poprawnych typów — color_picker wymaga #RRGGBB, number_input wymaga int.
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
    # NAPRAWA BUG #5: Reset jeśli czarny (błąd) LUB niepoprawny format
    if _cur == '#000000' or not (isinstance(_cur, str) and _cur.startswith('#') and len(_cur) == 7):
        st.session_state[_k] = _v
for _k, _v in _SIZE_DEFS.items():
    _cur = st.session_state.setdefault(_k, _v)
    try:
        _int_val = max(8, int(float(_cur or _v)))
        # NAPRAWA BUG #5: Reset jeśli wartość = 8 (minimum, prawdopodobnie błąd zapisu)
        if _int_val == 8 and _v != 8:
            st.session_state[_k] = _v
        elif _int_val != _cur:
            st.session_state[_k] = _int_val
    except Exception:
        st.session_state[_k] = _v
# ---------------------------------------------------------------------------
# OCHRONA DANYCH PRZY ZMIANIE STRONY
# ---------------------------------------------------------------------------
def _guard(keys):
    """Przywraca klucze do session_state jeśli Streamlit je usunął.
    Nie ustawia '' dla nieznanych kluczy - mogą być różnych typów (list, dict, bool itp.)."""
    for _k in keys:
        if _k not in st.session_state and _k in defaults:
            st.session_state[_k] = defaults[_k]
            
# ---------------------------------------------------------------------------
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

def _hotel_count():
    """Liczba hoteli."""
    return st.session_state.get('num_hotels', 0)

def _hotel_add():
    """Dodaje nowy hotel. Zostajemy na 'Opis hoteli' (synchronizacja z radio)."""
    n = st.session_state.get('num_hotels', 0)
    st.session_state['num_hotels'] = n + 1
    # _get_hotel_order() automatycznie doda nowy indeks (bo num_hotels wzrosło)
    _get_hotel_order()
    # Zostajemy na 'Opis hoteli' aby uniknąć konfliktu z main_nav_radio
    st.session_state['last_page'] = "Opis hoteli"

def _hotel_delete(pos):
    """Usuwa hotel i wraca na stronę 'Opis hoteli'."""
    order = _get_hotel_order()
    if pos < len(order):
        order.pop(pos)
        st.session_state['num_hotels'] = max(0, st.session_state.get('num_hotels', 1) - 1)
        st.session_state['hotel_order'] = order
        st.session_state['last_page'] = "Opis hoteli"
# -----------------------------------------------------------------------
# PROSTY SYSTEM ATRAKCJI — jedna lista attr_order = [0, 1, 2, ...]
# -----------------------------------------------------------------------
def _attr_count():
    """Liczba dodanych atrakcji."""
    return st.session_state.get('num_attr', 0)

def _attr_order():
    """Kolejność atrakcji — lista indeksów."""
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
    """Dodaje nową atrakcję i ustawia ją jako aktywną."""
    n = st.session_state.get('num_attr', 0)
    st.session_state['num_attr'] = n + 1
    order = _attr_order()
    order.append(n)
    st.session_state['attr_order'] = order
    # Ustawiamy nową stronę używając poprawnego formatu dla menu
    new_name = _attr_display_name(len(order)-1)
    st.session_state['last_page'] = f"   ★ {new_name}"

def _attr_move(pos, direction):
    """Przesuwa atrakcję i aktualizuje last_page."""
    order = _attr_order()
    new_pos = pos + direction
    if 0 <= new_pos < len(order):
        order[pos], order[new_pos] = order[new_pos], order[pos]
        st.session_state['attr_order'] = order
        # Po przesunięciu ustawiamy last_page na nową pozycję
        st.session_state['last_page'] = f"   ★ {_attr_display_name(new_pos)}"

def _attr_delete(pos):
    """Usuwa atrakcję i wraca do przerywnika."""
    order = _attr_order()
    if pos < len(order):
        order.pop(pos)
        st.session_state['num_attr'] = st.session_state.get('num_attr', 1) - 1
        st.session_state['attr_order'] = order
        st.session_state['last_page'] = "  ↳ Przerywnik atrakcje"
        st.session_state['_attr_focused'] = None

def _attr_display_name(pos):
    """Wyświetlana nazwa atrakcji na pozycji pos."""
    order = _attr_order()
    if pos >= len(order): return f"Atrakcja {pos + 1}"
    idx = order[pos]
    name = str(st.session_state.get(f'amain_{idx}', '')).split('\n')[0][:25].strip()
    return name or f"Atrakcja {pos + 1}"

# Wsteczna kompatybilność z renderer.py
def _get_place_attr_order():
    return [['attr', i] for i in _attr_order()]

def _move_place_attr(pos, direction):
    _attr_move(pos, direction)

def _rebuild_slide_order():
    _attr_order()
# ---------------------------------------------------------------------------
# TRYB KLIENTA
# ---------------------------------------------------------------------------
if st.session_state['client_mode']:
    # ... (Twój kod ze stylem CSS zostaje bez zmian) ...
    
    if st.button("ZAKOŃCZ PODGLĄD"):
        st.session_state['client_mode'] = False
        st.rerun()
    
    # --- ZMIANA W TYM MIEJSCU ---
    # Zamiast bezpośredniego wywołania, używamy kontenera:
    if "client_preview" not in st.session_state:
        st.session_state.client_preview = st.empty()
    
    with st.session_state.client_preview.container():
        build_presentation()
        
    st.stop()
    
# ---------------------------------------------------------------------------
# AUTO-SAVE DO SUPABASE
# ---------------------------------------------------------------------------
if not st.session_state.get('client_mode', False):
    if 'last_supabase_save' not in st.session_state:
        st.session_state['last_supabase_save'] = 0
    current_time = time.time()
    if current_time - st.session_state['last_supabase_save'] > 20:
        save_to_supabase()

# --- DEFINICJA ZMIENNYCH GLOBALNYCH (Bez spacji na początku!) ---
_n_attr = st.session_state.get('num_attr', 0)
_n_hotels = st.session_state.get('num_hotels', 0)

# ---------------------------------------------------------------------------
# SIDEBAR — NAWIGACJA (WERSJA CZYSTA I KOMPLETNA)
# ---------------------------------------------------------------------------
with st.sidebar:
    # Pokaż status load w sidebarze (debug)
    if '_debug_loaded' in st.session_state:
        st.caption(st.session_state['_debug_loaded'])
    # 1. STATUS AUTO-SAVE
    save_status = st.session_state.get('last_save_status', '⏳ Czekam na zmiany...')
    save_count = st.session_state.get('last_save_count', 0)
    # Kolorowe pola statusu - 3 stany (success/warning/info)
    save_status_type = st.session_state.get('last_save_status_type', 'success')
    save_extra = st.session_state.get('last_save_extra', '')
    project_name = st.session_state.get('last_save_project_name', '')
    
    if save_status_type == 'warning':
        # Pomaranczowe pole - kraj do uzupelnienia
        bg_color = '#fff7ed'
        border_color = '#f97316'
        text_color = '#9a3412'
        secondary_color = '#c2410c'
    elif save_status_type == 'info':
        # Niebieskie pole - kraj Inny
        bg_color = '#eff6ff'
        border_color = '#3b82f6'
        text_color = '#1e40af'
        secondary_color = '#2563eb'
    elif save_status_type == 'error':
        # Czerwone pole - blad
        bg_color = '#fef2f2'
        border_color = '#ef4444'
        text_color = '#991b1b'
        secondary_color = '#b91c1c'
    else:
        # Zielone pole - sukces (default)
        bg_color = '#ecfdf5'
        border_color = '#10b981'
        text_color = '#065f46'
        secondary_color = '#047857'
    
    # Linia 2: Tytul projektu (jesli jest)
    project_html = f"<div style='font-size:11px;color:{secondary_color};margin-top:2px;'>Projekt: \"{project_name}\"</div>" if project_name else ""
    
    # Linia 3: Liczba pol w bazie
    count_html = f"<div style='font-size:10px;color:{secondary_color};margin-top:2px;'>{save_count} pól w bazie</div>"
    
    # Linia 4 (warunkowa): Komunikat o kraju (tylko dla warning/info)
    extra_html = f"<div style='font-size:10px;color:{secondary_color};margin-top:2px;font-weight:600;'>{save_extra}</div>" if save_extra else ""
    
    st.markdown(
        f"<div style='background:{bg_color};border-left:4px solid {border_color};padding:8px 12px;margin-bottom:10px;border-radius:4px;'>"
        f"<div style='font-size:13px;font-weight:600;color:{text_color};margin-bottom:4px;'>{save_status}</div>"
        f"{project_html}"
        f"{count_html}"
        f"{extra_html}"
        f"</div>",
        unsafe_allow_html=True
    )
    
    # AKTUALNIE EDYTUJESZ
    _acc_top = st.session_state.get('color_accent', '#FF6600')
    _editing_name = st.session_state.get('t_main', '').strip() or '(bez nazwy)'
    if _editing_name == 'NAZWA PROJEKTU':
        _editing_name = '(bez nazwy)'
    st.markdown(
        f"<div style='background:#fff7ed;border-left:3px solid {_acc_top};padding:8px 12px;"
        f"margin-bottom:15px;border-radius:4px;'>"
        f"<div style='font-size:9px;font-weight:700;color:#9a3412;text-transform:uppercase;"
        f"letter-spacing:1px;margin-bottom:2px;'>Aktualnie edytujesz:</div>"
        f"<div style='font-size:12px;font-weight:600;color:#1e293b;line-height:1.3;'>{_editing_name}</div>"
        f"</div>",
        unsafe_allow_html=True
    )
    
    # 2. MIGRACJA ZDJĘĆ
    if any(isinstance(st.session_state.get(k), bytes) for k in IMAGE_KEYS):
        st.warning("⚠️ Wykryto zdjęcia w pamięci.")
        if st.button("🔄 Migruj zdjęcia do Storage", type="primary"):
            migrated_count, failed = cleanup_session_bytes_to_storage(supabase)
            if migrated_count > 0:
                save_to_supabase()
                st.success(f"✅ Zmigrowano {migrated_count} zdjęć.")
                st.rerun()

    st.markdown("---")
    
    # 3. BUDOWANIE LISTY STRON (ZGODNIE ZE SPISEM TREŚCI)
    # Sufiksy menu: ikony po nazwie, kolorowane przez Streamlit markdown.
    # Aby dodać nowy sufiks: zdefiniuj stałą i dopisz do _MENU_SUFFIXES.
    _HIDE_SUFFIX = "  :red[✖]"
    _OPT_SUFFIX  = "  :blue[◆]"
    _MENU_SUFFIXES = (_HIDE_SUFFIX, _OPT_SUFFIX)
    
    def _strip_hide_suffix(name):
        """Usuwa wszystkie sufiksy menu (kolejność dowolna, ilość dowolna)."""
        if not name:
            return name
        for _ in range(5):
            changed = False
            for _sfx in _MENU_SUFFIXES:
                if name.endswith(_sfx):
                    name = name[:-len(_sfx)]
                    changed = True
            if not changed:
                break
        return name
    
    def _label_with_hide(name, hide_key):
        """Dodaje suffix do nazwy jeśli slajd jest ukryty."""
        if st.session_state.get(hide_key, False):
            return f"{name}{_HIDE_SUFFIX}"
        return name
    
    def _label_attr(name, hide_key, opt_label_key):
        """Dodaje sufiksy menu dla atrakcji: ukryta (✖) + opcjonalna (◆)."""
        suffix = ""
        if st.session_state.get(hide_key, False):
            suffix += _HIDE_SUFFIX
        opt_text = str(st.session_state.get(opt_label_key, "") or "").strip()
        if opt_text:
            suffix += _OPT_SUFFIX
        return f"{name}{suffix}"
    
    _all_pages = [
        "⚙ WYGLĄD I KOLORY",
        "Strona tytułowa", 
        _label_with_hide("Opis kierunku", "k_hide"), 
        _label_with_hide("Mapa podróży", "map_hide"), 
        _label_with_hide("Jak lecimy?", "l_hide"),
        _label_with_hide("Jak jedziemy?", "jaj_hide"),
        _label_with_hide("  ↳ Przerywnik program", "sek_hide_3"), 
        _label_with_hide("Program wyjazdu", "prg_hide"),
        _label_with_hide("  ↳ Przerywnik atrakcje", "sek_hide_1"), 
        "Opis atrakcji"
    ]
    # Atrakcje dynamiczne
    for _ap in range(_n_attr):
        _ai = _attr_order()[_ap]
        _all_pages.append(_label_attr(f"    ★ {_attr_display_name(_ap)}", f"ahide_{_ai}", f"aopt_label_{_ai}"))
    
    _all_pages.append(_label_with_hide("  ↳ Przerywnik hotel", "sek_hide_0"))
    _all_pages.append("Opis hoteli")
    # Hotele dynamiczne
    for _hp in range(_n_hotels):
        _all_pages.append(_label_with_hide(f"    ❯ Hotel {_hp+1}", f"h_hide_{_hp}"))
    
    _all_pages.extend([
        _label_with_hide("  ↳ Przerywnik serwisy dodatkowe", "sek_hide_4"), 
        _label_with_hide("Aplikacja (komunikacja)", "app_hide"), 
        _label_with_hide("Materiały brandingowe", "brand_hide"),
        _label_with_hide("Pillow gifts", "pg_hide"), 
        _label_with_hide("Wirtualny asystent", "va_hide"), 
        _label_with_hide("Kosztorys str. 1", "koszt_hide_1"), 
        _label_with_hide("Kosztorys str. 2", "koszt_hide_2"),
        _label_with_hide("  ↳ Przerywnik nasza agencja", "sek_hide_2"), 
        _label_with_hide("ESG", "esg_hide"),
        _label_with_hide("O nas", "about_hide"), 
        _label_with_hide("Referencje", "testim_hide")
    ])

    # 4. GŁÓWNE MENU RADIO
    _last_p = st.session_state.get('last_page', "Strona tytułowa")
    # Jeśli last_page to "Jak jedziemy?" a w _all_pages jest "Jak jedziemy?  :red[✕]" (ukryty),
    # znajdz pasujący element po stripowaniu suffixu
    _idx = 0
    for _ii, _ll in enumerate(_all_pages):
        if _strip_hide_suffix(_ll) == _strip_hide_suffix(_last_p):
            _idx = _ii
            break
    
    def _handle_nav():
        # Zapisujemy do last_page wartość BEZ suffixu - dzięki temu elif page == "..." działa
        st.session_state['last_page'] = _strip_hide_suffix(st.session_state['main_nav_radio'])
        if 'scroll_target' in st.session_state:
            del st.session_state['scroll_target']
    page = st.radio("Nawigacja", _all_pages, index=_idx, key="main_nav_radio", 
                    label_visibility="collapsed", on_change=_handle_nav)
    # Normalizujemy page - usuwamy suffix ukrytego slajdu, żeby elif page == "..." działało
    page = _strip_hide_suffix(page)

# ---------------------------------------------------------------------------
# PRZYCISK: ZAPISZ TERAZ (wąski)
# ---------------------------------------------------------------------------
# Przycisk "Zapisz w bazie" - wąski, w sidebarze
if "manual_save_btn" in st.session_state: del st.session_state["manual_save_btn"]
with st.sidebar:
    _acc_save = st.session_state.get('color_accent', '#FF6600')
    # CSS dla wszystkich primary buttonów w sidebarze - kolor akcentu + wysokość jak expander
    st.markdown(
        f"<style>"
        f"[data-testid='stSidebar'] button[kind='primary'] {{"
        f"background-color: {_acc_save} !important;"
        f"border-color: {_acc_save} !important;"
        f"color: white !important;"
        f"min-height: 48px !important;"
        f"height: 48px !important;"
        f"padding: 0 16px !important;"
        f"}}"
        f"[data-testid='stSidebar'] [data-testid='stExpander'] summary {{"
        f"min-height: 48px !important;"
        f"height: 48px !important;"
        f"padding: 0 16px !important;"
        f"background-color: {_acc_save} !important;"
        f"color: white !important;"
        f"border-radius: 4px !important;"
        f"font-family: 'Montserrat', sans-serif !important;"
        f"text-transform: uppercase !important;"
        f"font-size: 12px !important;"
        f"letter-spacing: 1px !important;"
        f"font-weight: 600 !important;"
        f"}}"
        f"[data-testid='stSidebar'] [data-testid='stExpander'] summary svg {{"
        f"fill: white !important;"
        f"}}"
        f"</style>",
        unsafe_allow_html=True
    )
    
    # === SEKCJA ZARZĄDZANIE PROJEKTAMI ===
    st.markdown(
        f"<h3 style='color:{_acc_save};font-size:16px;margin-bottom:15px;font-weight:400 !important;letter-spacing:normal !important;'>ZARZĄDZANIE PROJEKTAMI</h3>",
        unsafe_allow_html=True,
    )
    
    # 1. ZAPISZ W BAZIE
    if st.button("ZAPISZ W BAZIE", use_container_width=True, type="primary", key="manual_save_btn"):
        save_to_supabase()
        st.rerun()
    
    # Pobierz listę projektów
    _all_offers = fetch_all_offers(supabase)
    _current_proj_id = st.session_state.get('active_project_id')
    
    # 2. OSTATNI PROJEKT (Font Awesome zegar historii)
    if _all_offers and st.button("OSTATNI PROJEKT", use_container_width=True, key="btn_last_proj", type="primary"):
        _sorted = sorted(_all_offers, key=lambda x: x.get('updated_at', ''), reverse=True)
        if _sorted:
            _switch_project(_sorted[0]['id'])
    
    # 3. NOWY PROJEKT - expander
    with st.expander("NOWY PROJEKT", expanded=False):
        _new_type = st.radio(
            "Typ nowego projektu:",
            ["Pusty (z szablonu)", "Duplikuj istniejący"],
            key="new_proj_type",
            label_visibility="collapsed",
        )
        
        if _new_type == "Pusty (z szablonu)":
            if st.button("UTWÓRZ PUSTY", use_container_width=True, key="btn_new_empty", type="primary"):
                _new_project()
        else:
            if _all_offers:
                _dup_options = [
                    f"{o.get('project_code', '???')} | {o.get('project_name', 'bez nazwy')[:30]}"
                    for o in _all_offers
                ]
                _dup_ids = [o['id'] for o in _all_offers]
                _dup_selected = st.selectbox(
                    "Wybierz źródło:",
                    _dup_options,
                    key="dup_select",
                    label_visibility="collapsed",
                )
                _dup_idx = _dup_options.index(_dup_selected)
                if st.button("DUPLIKUJ", use_container_width=True, key="btn_duplicate", type="primary"):
                    _new_project(copy_from_id=_dup_ids[_dup_idx])
            else:
                st.caption("Brak projektów do duplikowania.")
    
    # 4. WYBIERZ PROJEKT Z BAZY
    st.markdown(
        f"<div style='color:{_acc_save};font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-top:15px;margin-bottom:5px;font-family:Montserrat,sans-serif;'>Wybierz projekt z bazy:</div>",
        unsafe_allow_html=True,
    )
    if _all_offers:
        _proj_options = ["-- Wybierz --"] + [
            f"{o.get('project_code', '???')} | {o.get('project_name', 'bez nazwy')[:30]}"
            for o in _all_offers
        ]
        _proj_ids = [None] + [o['id'] for o in _all_offers]
        
        _curr_idx = 0
        if _current_proj_id and _current_proj_id in _proj_ids:
            _curr_idx = _proj_ids.index(_current_proj_id)
        
        _selected_proj = st.selectbox(
            "Wybierz projekt:",
            _proj_options,
            index=_curr_idx,
            key="proj_select",
            label_visibility="collapsed",
        )
        _sel_idx = _proj_options.index(_selected_proj)
        if _sel_idx > 0 and _proj_ids[_sel_idx] != _current_proj_id:
            if st.button("WCZYTAJ WYBRANY", use_container_width=True, key="btn_load_proj", type="primary"):
                _switch_project(_proj_ids[_sel_idx])
    else:
        st.caption("Brak projektów w bazie.")
    
    st.markdown("---")
    
    # === SEKCJA ZARZĄDZANIE DYSK LOKALNY ===
    st.markdown(
        f"<h3 style='color:{_acc_save};font-size:16px;margin-bottom:15px;font-weight:400 !important;letter-spacing:normal !important;'>ZARZĄDZANIE DYSK LOKALNY</h3>",
        unsafe_allow_html=True,
    )
    
    # Pobierz prezentację na dysk
    if st.button("POBIERZ PREZENTACJĘ NA DYSK", use_container_width=True, key="prep_download_btn", type="primary"):
        with st.spinner("Przygotowywanie pliku..."):
            proj = _build_proj_dict()
            st.session_state['temp_proj_json'] = json.dumps(proj, ensure_ascii=False)
    
    if 'temp_proj_json' in st.session_state:
        st.download_button(
            "📥 POBIERZ PLIK",
            st.session_state['temp_proj_json'],
            get_project_filename(),
            use_container_width=True,
            key="dl_proj_sidebar",
            help="Zapisz prezentację jako plik na swój komputer",
        )
    
    # Wczytaj prezentację z dysku
    upf_sidebar = st.file_uploader(
        "WCZYTAJ PREZENTACJĘ Z DYSKU",
        type=['json'],
        key="up_proj_sidebar",
    )
    st.markdown(
        "<div style='font-size:10px;color:#64748b;font-style:italic;"
        "margin:5px 0 10px 0;padding:6px 10px;background:#f1f5f9;border-radius:4px;"
        "border-left:3px solid #94a3b8;'>"
        "💡 Zarządzanie pojedynczymi slajdami znajduje się na panelu slajdów."
        "</div>",
        unsafe_allow_html=True
    )
    if upf_sidebar and st.button("📤 WCZYTAJ", use_container_width=True, key="btn_load_sidebar"):
        data, error = _validate_and_load_json(upf_sidebar)
        if error:
            st.error(f"❌ {error}")
        else:
            try:
                load_project_data(data)
                st.success(f"✅ Wczytano prezentację ({len(data)} pól)")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Błąd: {str(e)[:100]}")

_acc_global = st.session_state.get('color_accent', '#FF6600')
st.markdown(f"""<style>
button[kind="primary"],
button[data-testid="baseButton-primary"],
.stButton button[kind="primary"] {{
    background-color: {_acc_global} !important;
    border-color: {_acc_global} !important;
    color: white !important;
}}
</style>""", unsafe_allow_html=True)

st.markdown("""<style>
button[data-testid="baseButton-primary"] { color: white !important; }
/* Ukryj ikonkę kopiowania pojawiającą się przy najechaniu na radio/markdown */
[data-testid="stMarkdown"] button[title="Copy to clipboard"],
[data-testid="stMarkdown"] [aria-label="Copy"],
[data-testid="stMarkdown"] [data-testid="stCodeCopyButton"],
[data-baseweb="radio"] button[title="Copy to clipboard"],
[data-baseweb="radio"] [aria-label="Copy"],
[data-testid="stSidebar"] button[title="Copy to clipboard"],
[data-testid="stSidebar"] [aria-label="Copy"],
[data-testid="stSidebar"] [data-testid="stCodeCopyButton"],
button[kind="copyButton"],
[data-testid="copy-button"],
.stMarkdown button:has(svg[viewBox="0 0 24 24"]),
[data-testid="stCode"] button { 
    display: none !important; 
}
</style>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# NAGŁÓWKI STRON (POPRAWIONA LOGIKA Z FONT AWESOME)
# ---------------------------------------------------------------------------
with st.container():
    _p = st.session_state.get('last_page', "Strona tytułowa")
    _h_col = st.session_state.get("color_h1", "#003366")
    _acc_col = st.session_state.get("color_accent", "#FF6600")

    # 1. Jeśli to Atrakcja (★) lub konkretny Hotel (❯)
    if "★" in _p or "❯" in _p:
        # Zamieniamy znaki z menu na prawdziwe ikony wektorowe Font Awesome
        _display = _p.replace("★", f"<i class='fa-solid fa-star' style='font-size:16px; margin-right:6px; color:{_acc_col};'></i>")
        _display = _display.replace("❯", f"<i class='fa-solid fa-chevron-right' style='font-size:16px; margin-right:6px; color:{_acc_col};'></i>")
        
        st.markdown(f"<h2 style='color:{_acc_col};margin-bottom:0;font-size:20px;font-weight:700;font-family:Montserrat,sans-serif;margin-left:12px;border-left:3px solid {_acc_col};padding-left:10px; display:flex; align-items:center;'>{_display.strip()}</h2>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:13px;color:#64748b;margin-bottom:15px;font-family:Open Sans,sans-serif;margin-left:12px;'>Edytuj treść slajdu poniżej.</div>", unsafe_allow_html=True)
    
    # 2. Jeśli to Przerywnik (↳)
    elif "↳" in _p:
        _page_label = _p.strip().lstrip('↳').strip()
        st.markdown(f"<h2 style='color:{_h_col};margin-bottom:0;font-size:20px;font-weight:700;font-family:Montserrat,sans-serif;text-transform:uppercase;margin-left:12px;border-left:3px solid {_h_col};padding-left:10px;'>{_page_label}</h2>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:13px;color:#64748b;margin-bottom:15px;font-family:Open Sans,sans-serif;margin-left:12px;'>Slajd przerywnikowy — edytuj treść i wygląd poniżej.</div>", unsafe_allow_html=True)
    
    # 3. Standardowe strony
    else:
        _display_p = _p.replace("⚙ ", "").strip() if _p.startswith("⚙") else _p
        st.markdown(f"<h2 style='color:#003366;margin-bottom:0;font-size:22px;font-weight:700;font-family:Montserrat,sans-serif;text-transform:uppercase;'>{_display_p}</h2>", unsafe_allow_html=True)
        st.markdown("<div style='font-size:13px;color:#64748b;margin-bottom:15px;font-family:Open Sans,sans-serif;'>Wprowadź dane dla tej sekcji poniżej:</div>", unsafe_allow_html=True)
        
# ---------------------------------------------------------------------------
# LAYOUT 2 KOLUMNY: Formularz edycji | Podgląd slajdu
# ---------------------------------------------------------------------------
col_form, col_preview = st.columns([0.3, 0.7], gap="medium")
with col_form:
    _acc = st.session_state.get('color_accent', '#FF6600')
    st.markdown(f"<h3 style='color:{_acc};font-size:16px;margin-bottom:20px;'>EDYCJA SLAJDU</h3>", unsafe_allow_html=True)
  
    # -----------------------------------------------------------------------
    # 1. STRONA TYTUŁOWA
    # -----------------------------------------------------------------------
    if page == "Strona tytułowa":
        _guard(["t_date", "country_name", "country_code", "t_main", "t_sub",  
                "t_klient", "t_kierunek", "t_pax", "t_hotel", "t_trans", "hide_logo_cli"])  
        tit_keys = [
            't_date', 'country_name', 'country_code', 't_main', 't_sub',
            't_klient', 't_kierunek', 't_pax', 't_hotel', 't_trans',
            'img_hero_t', 'logo_az', 'logo_cli', 'hide_logo_cli',
        ]
        section_template_manager(tit_keys, "TYT", "strona-tytulowa", "tit")
        safe_text_input("Termin:", key="t_date",
                        help="Wpisz datę w formacie DD.MM-DD.MM.RRRR (np. 30.11-4.12.2026)",
                        on_change=lambda: (parse_date_and_days(), save_to_supabase()))
        # Callback do synchronizacji country_code z country_name
        def _sync_country_code():
            name = st.session_state.get('country_name', '')
            st.session_state['country_code'] = COUNTRIES_DICT.get(name, '')
        
        # Wymuszamy index zamiast key zeby selectbox zachowal wartosc 
        # po przelaczeniu strony (znany bug Streamlit)
        _country_options = list(COUNTRIES_DICT.keys())
        _current_country = st.session_state.get('country_name', '-- Wybierz kraj --')
        try:
            _current_index = _country_options.index(_current_country)
        except ValueError:
            _current_index = 0  # fallback - placeholder
        
        _selected_country = st.selectbox(
            "Kraj docelowy:", 
            _country_options,
            index=_current_index,
        )
        # Aktualizujemy session_state RECZNIE (bez key=)
        st.session_state['country_name'] = _selected_country
        # Aktualizujemy country_code od razu
        _sync_country_code()
        for k, l in [
            ('t_main', 'Tytuł H1'), ('t_sub', 'Podtytuł'), ('t_klient', 'Klient'),
            ('t_kierunek', 'Kierunek'), ('t_pax', 'Liczba osób'),
            ('t_hotel', 'Hotel'), ('t_trans', 'Dojazd'),
        ]:
            safe_text_input(l, key=k)
        st.file_uploader(
            "Zdjęcie główne (4:5)",
            key="up_img_hero_t",
            on_change=_make_upload_callback('img_hero_t')
        )
        
        c1, c2 = st.columns(2)
        _render_uploader_with_delete(c1, "Logo Firmy", "logo_az", is_logo=True)
        _render_uploader_with_delete(c2, "Logo Klienta", "logo_cli", is_logo=True)
            
        c2.checkbox("Ukryj logo klienta na stronie tytułowej", key="hide_logo_cli")

    # -----------------------------------------------------------------------
    # 2. OPIS KIERUNKU
    # -----------------------------------------------------------------------
    elif page == "Opis kierunku":
        _guard(["k_hide", "k_overline", "k_main", "k_sub", "k_opis",
                "k_highlights",
                "k_icon_stolica_show", "k_icon_stolica_val",
                "k_icon_waluta_show", "k_icon_waluta_val",
                "k_icon_strefa_show", "k_icon_strefa_val",
                "k_icon_klimat_show", "k_icon_klimat_val",
                "k_icon_temp_show", "k_icon_temp_val",
                "k_icon_szczepienia_show", "k_icon_szczepienia_val",
                "k_icon_mieszkancy_show", "k_icon_mieszkancy_val"])
        k_keys = [
            'k_hide', 'k_overline', 'k_main', 'k_sub', 'k_opis',
            'k_highlights',
            'k_icon_stolica_show', 'k_icon_stolica_val',
            'k_icon_waluta_show', 'k_icon_waluta_val',
            'k_icon_strefa_show', 'k_icon_strefa_val',
            'k_icon_klimat_show', 'k_icon_klimat_val',
            'k_icon_temp_show', 'k_icon_temp_val',
            'k_icon_szczepienia_show', 'k_icon_szczepienia_val',
            'k_icon_mieszkancy_show', 'k_icon_mieszkancy_val',
            'img_hero_k', 'img_k_th1', 'img_k_th2',
        ]
        section_template_manager(k_keys, "KIE", st.session_state.get('k_main', 'czarnogora'), "kie")
        safe_checkbox("Ukryj ten slajd w PDF", key="k_hide")
        safe_text_input("Mały nadtytuł (overline):", key="k_overline")
        safe_text_input("Nazwa kierunku (duży tytuł H1):", key="k_main")
        safe_text_input("Podtytuł:", key="k_sub")
        safe_text_area("Opis (prawa kolumna):", height=160, key="k_opis",
                     help="Główny opis kierunku po prawej stronie slajdu.")
        
        _section_header("FAKTY KIERUNKU (ikony pod tekstem)")
        st.caption("Zaznacz ikony do pokazania. Limit wartości: 21 znaków. Układ: rząd po 3 ikony.")
        
        _icons_config = [
            ('stolica', 'Stolica', 'landmark'),
            ('waluta', 'Waluta', 'wallet'),
            ('strefa', 'Różnica czasu', 'clock'),
            ('klimat', 'Klimat', 'sun'),
            ('temp', 'Temperatury', 'temperature-half'),
            ('szczepienia', 'Szczepienia', 'syringe'),
            ('mieszkancy', 'Mieszkańców', 'users'),
        ]
        for _slug, _label, _icon in _icons_config:
            _ck = f'k_icon_{_slug}_show'
            _vk = f'k_icon_{_slug}_val'
            _c1, _c2 = st.columns([1, 3])
            with _c1:
                safe_checkbox(_label, key=_ck)
            with _c2:
                safe_text_input(
                    f"Wartość ({_label.lower()}):",
                    key=_vk,
                    max_chars=21,
                    label_visibility="collapsed",
                )
        
        _section_header("ATUTY KIERUNKU (pomarańczowe chipy na dole slajdu)")
        safe_text_area(
            "Atuty (każda linia = jeden chip):",
            height=100,
            key="k_highlights",
            help="Każda linia tekstu zostanie wyświetlona jako osobny pomarańczowy chip. Zalecane krótkie hasła.",
        )
        
        _section_header("ZDJĘCIA KIERUNKU (jedno duże u góry + dwa mniejsze pod spodem)")
        st.file_uploader(
            "Zdjęcie główne (duże, góra):",
            key="up_img_hero_k",
            on_change=_make_upload_callback('img_hero_k')
        )
        _c1, _c2 = st.columns(2)
        _c1.file_uploader(
            "Zdjęcie 2 (lewy dół):",
            key="up_img_k_th1",
            on_change=_make_upload_callback('img_k_th1')
        )
        _c2.file_uploader(
            "Zdjęcie 3 (prawy dół):",
            key="up_img_k_th2",
            on_change=_make_upload_callback('img_k_th2')
        )
    
    # -----------------------------------------------------------------------
    # 3. MAPA PODRÓŻY (Całość)
    # -----------------------------------------------------------------------
    elif page == "Mapa podróży":
        _guard(["map_hide", "map_overline", "map_title", "map_subtitle", "map_desc",
                "num_map_points", "map_dist_title",             
                "ors_api_key", "num_dist_pairs"])                                      
        map_keys = [
            'map_hide', 'map_overline', 'map_title', 'map_subtitle', 'map_desc',
            'img_map_bg', 'num_map_points', 'img_map_bg_auto', 'auto_map_points',
        ]
        for i in range(st.session_state.get('num_map_points', 3)):
            map_keys.extend([f'map_pt_name_{i}', f'map_conn_{i}', f'map_pt_sym_{i}',
                              f'map_pt_x_{i}', f'map_pt_y_{i}'])
        section_template_manager(map_keys, "MAP", "mapa-podrozy", "map")
        safe_checkbox("Ukryj slajd", key="map_hide")
        safe_text_input("Mały nadtytuł:", key="map_overline")
        safe_text_area("Główny tytuł H1:", key="map_title")
        safe_text_input("Podtytuł:", key="map_subtitle")
        safe_text_area("Opis pod mapą:", height=100, key="map_desc")
        
        _section_header("AUTOMATYCZNY KREATOR MAPY")
        st.number_input("Liczba punktów na trasie:", 1, 10, step=1, key="num_map_points")
        points_data = []
        for i in range(st.session_state['num_map_points']):
            for dk, dv in [(f'map_pt_name_{i}', f'Punkt {i+1}'), (f'map_conn_{i}', 'Brak'),
                           (f'map_pt_sym_{i}', False), (f'map_pt_x_{i}', 15), (f'map_pt_y_{i}', 10)]:
                if dk not in st.session_state:
                    st.session_state[dk] = dv
            with st.expander(f"Punkt {i+1}", expanded=True):
                safe_text_input("Nazwa (np. Rzym, Hiszpania):", key=f"map_pt_name_{i}")
                conn_opts = ["Brak", "Przejazd (Linia ciągła)", "Przelot (Linia przerywana + Samolot)"]
                safe_selectbox("Połączenie z NASTĘPNYM punktem:", conn_opts, key=f"map_conn_{i}")
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
                        # Zoom jest liczony automatycznie wewnątrz generate_map_data
                        # (z bbox kraju lub z rozpiętości punktów - fallback)
                        bg_b64, final_pts = generate_map_data(valid_pts)
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
        safe_text_input("Tytuł sekcji na slajdzie:", key="map_dist_title")
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
            safe_text_input("Klucz ORS API:", key="ors_api_key", type="password",
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
    # 4. JAK LECIMY?
    # -----------------------------------------------------------------------
    elif page == "Jak lecimy?":
        _guard(["l_hide", "l_przesiadka", "l_port", "l_czas", "l_overline",  
                "l_main", "l_sub", "m_route", "m_luggage",                   
                "f1", "f2", "f3", "f4", "l_desc", "l_extra"])                
        l_keys = [
            'l_hide', 'l_przesiadka', 'l_port', 'l_czas', 'l_overline', 'l_main',
            'l_sub', 'm_route', 'm_luggage', 'f1', 'f2', 'f3', 'f4',
            'l_desc', 'l_extra', 'img_hero_l',
        ]
        section_template_manager(l_keys, "LOT", "jak-lecimy", "lot")
        safe_checkbox("Ukryj ten slajd w PDF", key="l_hide")
        safe_text_input("Mały nadtytuł:", key="l_overline")
        safe_text_input("Tytuł (H1):", key="l_main")
        for k, l in [('l_sub', 'Podtytuł'), ('m_route', 'Trasa'), ('m_luggage', 'Bagaż'),
                     ('f1', 'Lot 1'), ('f2', 'Lot 2')]:
            safe_text_input(l, key=k)
        if safe_checkbox("Lot z przesiadką", key="l_przesiadka"):
            _section_header("DANE PRZESIADKI I KOLEJNE ODCINKI LOTU")
            c1, c2 = st.columns(2)
            c1.text_input("Port przesiadkowy:", key="l_port")
            c2.text_input("Długość przesiadki:", key="l_czas")
            for k, l in [('f3', 'Lot 3'), ('f4', 'Lot 4')]:
                safe_text_input(l, key=k)
        for k, l in [('l_desc', 'Opis'), ('l_extra', 'Dodatkowe info')]:
            safe_text_area(l, key=k)
        st.file_uploader(
            "Foto Samolotu",
            key="up_img_hero_l",
            on_change=_make_upload_callback('img_hero_l')
        )

    # -----------------------------------------------------------------------
    # 4b. JAK JEDZIEMY? (alternatywny slajd transportowy)
    # -----------------------------------------------------------------------
    elif page == "Jak jedziemy?":
        _guard(["jaj_hide", "jaj_overline", "jaj_main", "jaj_sub",
                "jaj_route", "jaj_desc", "jaj_extra",
                "jaj_dist_title", "num_jaj_dist_pairs", "ors_api_key"])
        jaj_keys = [
            'jaj_hide', 'jaj_overline', 'jaj_main', 'jaj_sub',
            'jaj_route', 'jaj_desc', 'jaj_extra', 'img_hero_j',
            'jaj_dist_title', 'num_jaj_dist_pairs',
        ]
        for i in range(st.session_state.get('num_jaj_dist_pairs', 2)):
            jaj_keys.extend([f'jaj_dist_a_{i}', f'jaj_dist_b_{i}',
                            f'jaj_dist_km_{i}', f'jaj_dist_time_{i}'])
        section_template_manager(jaj_keys, "JAJ", "jak-jedziemy", "jaj")
        safe_checkbox("Ukryj ten slajd w PDF", key="jaj_hide")
        safe_text_input("Mały nadtytuł:", key="jaj_overline")
        safe_text_input("Tytuł (H1):", key="jaj_main")
        safe_text_input("Podtytuł:", key="jaj_sub")
        safe_text_input("Trasa:", key="jaj_route")
        safe_text_area("Opis:", key="jaj_desc")
        safe_text_area("Dodatkowe info:", key="jaj_extra")
        st.file_uploader(
            "Zdjęcie (np. autokar):",
            key="up_img_hero_j",
            on_change=_make_upload_callback('img_hero_j')
        )
        
        # === SEKCJA ODLEGŁOŚCI (analogicznie do mapy) ===
        _section_header("ODLEGŁOŚCI I CZAS DOJAZDU")
        safe_text_input("Tytuł sekcji na slajdzie:", key="jaj_dist_title")
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
                "Klucz API OpenRouteService (wspólny z 'Mapą podróży').</div>",
                unsafe_allow_html=True,
            )
            safe_text_input("Klucz ORS API:", key="ors_api_key", type="password")
        
        st.number_input("Liczba par miejscowości:", 0, 10, step=1, key="num_jaj_dist_pairs")
        for di in range(st.session_state.get('num_jaj_dist_pairs', 0)):
            for dk, dv in [
                (f'jaj_dist_a_{di}', ''), (f'jaj_dist_b_{di}', ''),
                (f'jaj_dist_km_{di}', '—'), (f'jaj_dist_time_{di}', '—'),
            ]:
                if dk not in st.session_state:
                    st.session_state[dk] = dv
            with st.expander(f"Para {di+1}: {st.session_state.get(f'jaj_dist_a_{di}','')} → {st.session_state.get(f'jaj_dist_b_{di}','')}",
                             expanded=True):
                ca, cb = st.columns(2)
                ca.text_input("Miejsce A:", key=f"jaj_dist_a_{di}", value=st.session_state.get(f"jaj_dist_a_{di}", ""))
                cb.text_input("Miejsce B:", key=f"jaj_dist_b_{di}", value=st.session_state.get(f"jaj_dist_b_{di}", ""))
                if st.button("POBIERZ ODLEGŁOŚĆ", key=f"btn_jaj_dist_{di}",
                             use_container_width=True):
                    ors_key = (st.secrets.get("ORS_API_KEY", "") if hasattr(st, 'secrets') else "") \
                              or st.session_state.get('ors_api_key', '').strip()
                    a = st.session_state.get(f'jaj_dist_a_{di}', '').strip()
                    b = st.session_state.get(f'jaj_dist_b_{di}', '').strip()
                    if not a or not b:
                        st.warning("Wpisz obie nazwy miejscowości.")
                    else:
                        with st.spinner(f"Szukam trasy {a} → {b}..."):
                            km, mins, err = get_road_distance(
                                a, b, ors_key,
                                st.session_state.get('country_name', ''),
                            )
                        if km is not None:
                            st.session_state[f'jaj_dist_km_{di}'] = f'{km}'
                            st.session_state[f'jaj_dist_time_{di}'] = format_duration(mins)
                            if err:
                                st.warning(f"✓ Zapisano: {km} km, {format_duration(mins)}\n\n⚠️ {err}")
                            else:
                                st.success(f"✓ Trasa drogowa: {km} km, {format_duration(mins)}")
                            st.rerun()
                        else:
                            st.error(f"Nie udało się pobrać trasy.\n\n{err}")
                cd1, cd2 = st.columns(2)
                cd1.text_input("Odległość (km) — edytowalna:", key=f"jaj_dist_km_{di}")
                cd2.text_input("Czas dojazdu — edytowalny:", key=f"jaj_dist_time_{di}")

    # -----------------------------------------------------------------------
    # 5. PRZERYWNIK PROGRAMU (Wstawiony z Twojego kodu)
    # -----------------------------------------------------------------------
    elif page == "  ↳ Przerywnik program":
        _guard(["sek_3_title", "sek_3_sub", "sek_hide_3", "sek_3_bg", "sek_3_txt", "sek_3_sub_color"]) 
        if not isinstance(st.session_state.get("sek_hide_3"), bool):
            st.session_state["sek_hide_3"] = False

        _bg_default = st.session_state.get('color_h1', '#003366')
        _sub_default = st.session_state.get('color_sub', '#FF6600')
        
        if st.button("🔄 Resetuj kolory przerywnika", use_container_width=True, key="res_sek_3"):
            st.session_state["sek_3_bg"] = _bg_default
            st.session_state["sek_3_txt"] = "#ffffff"
            st.session_state["sek_3_sub_color"] = _sub_default
            st.rerun()

        # Ujednolicony wzorzec walidacji kolorów (jak w innych przerywnikach)
        for _ck, _cv in [("sek_3_bg", _bg_default), ("sek_3_txt", '#ffffff'), ("sek_3_sub_color", _sub_default)]:
            _v = st.session_state.get(_ck)
            # Reset jeśli brak, czarny (#000000) lub niepoprawny format
            if not _v or _v == '#000000' or not (isinstance(_v, str) and _v.startswith('#') and len(_v) == 7):
                st.session_state[_ck] = _cv
                
        st.button("POKAŻ PODGLĄD", key=f"btn_sek_3", on_click=set_focus, args=("slide-sek_3",), use_container_width=True)
        safe_checkbox("Ukryj ten slajd w prezentacji", key=f"sek_hide_3")
        st.markdown("---") 
        
        safe_text_input("Duży tytuł (uppercase):", key=f"sek_3_title")
        safe_text_input("Nadtytuł (overline, kolor akcentu):", key=f"sek_3_sub")
        
        _ic1, _ic2, _ic3 = st.columns(3)
        _ic1.color_picker("Kolor tła:", key="sek_3_bg", value=st.session_state.get("sek_3_bg", _bg_default))
        _ic2.color_picker("Kolor tytułu:", key="sek_3_txt", value=st.session_state.get("sek_3_txt", "#ffffff"))
        _ic3.color_picker("Kolor nadtytułu:", key="sek_3_sub_color", value=st.session_state.get("sek_3_sub_color", _sub_default))
        
        st.file_uploader(
            "Zdjęcie tła (16:9):",
            key="up_sek_3_img",
            on_change=_make_upload_callback('sek_3_img')
        )

    # -----------------------------------------------------------------------
    # 6. PROGRAM WYJAZDU
    # -----------------------------------------------------------------------
    elif page == "Program wyjazdu":
        _guard(["prg_hide", "num_days", "p_start_dt"])                               
        for _d in range(st.session_state.get("num_days", 4)):                        
            _guard([f"attr_{_d}", f"desc_{_d}"])                                     
        safe_checkbox("Ukryj CAŁĄ sekcję Programu w PDF", key="prg_hide")
        safe_number_input("Ilość dni:", key="num_days", default=4, min_value=1, max_value=15, step=1)
        st.date_input("Data startu:", key="p_start_dt")
        for d in range(st.session_state.get("num_days", 4)):
            with st.expander(f"Dzień {d+1}"):
                for dk in [f"attr_{d}", f"desc_{d}"]:
                    if dk not in st.session_state:
                        st.session_state[dk] = ""
                d_keys = [f'img_d_{d}', f'attr_{d}', f'desc_{d}']
                section_template_manager(d_keys, "PRG", f"Dzien_{d+1}", f"prg_{d}", index=d)
                
                st.file_uploader(
                    f"Foto D{d+1} (16:9)",
                    key=f"up_img_d_{d}",
                    on_change=_make_upload_callback(f'img_d_{d}')
                )
                safe_text_input("Wyróżnienie dnia (nagłówek):", key=f"attr_{d}")
                safe_text_area("Opis dnia:", height=100, key=f"desc_{d}")

    # -----------------------------------------------------------------------
    # 7. PRZERYWNIK ATRAKCJE
    # -----------------------------------------------------------------------
    elif page == "  ↳ Przerywnik atrakcje":
        _guard(["sek_1_title", "sek_1_sub", "sek_hide_1", "sek_1_bg", "sek_1_txt", "sek_1_sub_color"])  
        if not isinstance(st.session_state.get("sek_hide_1"), bool):
            st.session_state["sek_hide_1"] = False

        _bg_default = st.session_state.get('color_h1', '#003366')
        _sub_default = st.session_state.get('color_accent', '#FF6600')

        # Usunięto 'key', aby uniknąć konfliktu w session_state
        if st.button("🔄 Resetuj kolory przerywnika", use_container_width=True):
            st.session_state["sek_1_bg"] = _bg_default
            st.session_state["sek_1_txt"] = "#ffffff"
            st.session_state["sek_1_sub_color"] = _sub_default
            st.rerun()

        # Upewnienie się, że wartości w session_state są poprawne
        for _ck, _cv in [("sek_1_bg", _bg_default), ("sek_1_txt", '#ffffff'), ("sek_1_sub_color", _sub_default)]:
            if not st.session_state.get(_ck):
                st.session_state[_ck] = _cv

        st.button("POKAŻ PODGLĄD", key="btn_sek_1", on_click=set_focus, args=("slide-sek_1",), use_container_width=True)
        safe_checkbox("Ukryj ten slajd w prezentacji", key="sek_hide_1")
        st.markdown("---")

        safe_text_input("Duży tytuł (uppercase):", key="sek_1_title")
        safe_text_input("Nadtytuł (overline, kolor akcentu):", key="sek_1_sub")
        
        _ic1, _ic2, _ic3 = st.columns(3)
        _ic1.color_picker("Kolor tła:", key="sek_1_bg", value=st.session_state.get("sek_1_bg", _bg_default))
        _ic2.color_picker("Kolor tytułu:", key="sek_1_txt", value=st.session_state.get("sek_1_txt", "#ffffff"))
        _ic3.color_picker("Kolor nadtytułu:", key="sek_1_sub_color", value=st.session_state.get("sek_1_sub_color", _sub_default))

        st.file_uploader(
            "Zdjęcie tła (16:9):",
            key="up_sek_1_img",
            on_change=_make_upload_callback('sek_1_img')
        )
            
    # -----------------------------------------------------------------------
    # 8. OPIS ATRAKCJI (kontener — przycisk dodawania + lista atrakcji)
    # -----------------------------------------------------------------------
    elif page == "Opis atrakcji":
        _guard(["num_attr", "attr_order"])
        
        # PRZYCISK DODAWANIA ATRAKCJI
        if st.button("✚ DODAJ ATRAKCJĘ", key="btn_add_attr_main", type="primary", use_container_width=True):
            _attr_add()
            st.rerun()
        
        st.markdown("---")
        
        # LISTA ATRAKCJI (z przyciskami zarządzania ▲▼✕)
        _attr_order_list = _attr_order()
        _n_attr_curr = _attr_count()
        
        if _n_attr_curr == 0:
            st.info("Nie dodano jeszcze żadnej atrakcji. Kliknij '➕ DODAJ ATRAKCJĘ' powyżej.")
        else:
            _section_header(f"LISTA ATRAKCJI ({_n_attr_curr})")
            _acc_color = st.session_state.get('color_accent', '#FF6600')
            for pos, ai in enumerate(_attr_order_list):
                name = str(st.session_state.get(f'amain_{ai}', '')).split('\n')[0][:35] or f'Atrakcja {ai+1}'
                col_lbl, col_up, col_dn, col_del = st.columns([6, 1, 1, 1])
                col_lbl.markdown(
                    f"<div style='padding:6px 10px; background:#fef3ec; border-radius:4px; "
                    f"border-left:3px solid {_acc_color}; font-size:12px; color:#1e293b;'>"
                    f"<strong style='color:{_acc_color}; font-size:10px; text-transform:uppercase; "
                    f"letter-spacing:1px;'>★ Atrakcja {pos+1}</strong><br>{name}</div>",
                    unsafe_allow_html=True,
                )
                if pos > 0:
                    if col_up.button("▲", key=f"attr_up_{pos}", use_container_width=True):
                        _attr_move(pos, -1)
                        st.rerun()
                if pos < len(_attr_order_list) - 1:
                    if col_dn.button("▼", key=f"attr_dn_{pos}", use_container_width=True):
                        _attr_move(pos, 1)
                        st.rerun()
                if col_del.button("✕", key=f"attr_del_{pos}", use_container_width=True):
                    _attr_delete(pos)
                    st.rerun()
            
            st.markdown("---")
            st.caption("💡 Kliknij '★ Nazwa atrakcji' w menu nawigacji aby edytować szczegóły konkretnej atrakcji.")
    # -----------------------------------------------------------------------
    # DYNAMICZNE OPISY MIEJSC-ATRAKCJI (Poprawiona logika)
    # -----------------------------------------------------------------------
    elif "★" in page:
        # Znajdź pozycję atrakcji w _all_pages.
        # page jest stripowane (bez sufiksów), _all_pages zawiera labele Z sufiksami.
        # Porównanie po stripowaniu — spójne z zasadą "label = wyświetlanie, stripped = identyfikator".
        _pos = -1
        _opis_idx = -1
        _page_idx = -1
        for _ii, _ll in enumerate(_all_pages):
            _ll_stripped = _strip_hide_suffix(_ll)
            if _ll_stripped == "Opis atrakcji":
                _opis_idx = _ii
            if _ll_stripped == page:
                _page_idx = _ii
        if _opis_idx >= 0 and _page_idx >= 0:
            _pos = _page_idx - _opis_idx - 1 
        
        if _pos >= 0 and _pos < _n_attr:
            # Pobierz rzeczywisty indeks z naszej listy kolejności
            _i = _attr_order()[_pos]
            
            # Formularz edycji (pozostała część kodu taka sama jak miałaś)
            day_options_global = build_day_options(
                st.session_state.get('p_start_dt', date.today()),
                int(st.session_state.get('num_days', 5)),
            )    
            for _dk, _dv in [
                (f"amain_{_i}", ""), (f"asub_{_i}", ""),
                (f"aday_{_i}", "Brak przypisania"), (f"atype_{_i}", "Wybierz ikonę"),
                (f"aopis_{_i}", ""), (f"ahide_{_i}", False),
                (f"aopt_label_{_i}", ""),
            ]:
                if _dk not in st.session_state:
                    st.session_state[_dk] = _dv
            
            if st.session_state.get('_attr_focused') != _i:
                st.session_state['_attr_focused'] = _i
                set_focus(f"attr_{_i}")
            a_keys = [f'ahide_{_i}', f'amain_{_i}', f'asub_{_i}',
                      f'aday_{_i}', f'atype_{_i}', f'aopis_{_i}',
                      f'aopt_label_{_i}',
                      f'ah_{_i}', f'at1_{_i}', f'at2_{_i}', f'at3_{_i}']
            section_template_manager(a_keys, "ATR",
                st.session_state.get(f"amain_{_i}") or f"Atrakcja_{_pos+1}",
                f"atr_{_i}", index=_i)
            safe_checkbox("Ukryj ten slajd w PDF", key=f"ahide_{_i}", on_change=set_focus, args=(f"attr_{_i}",))
            safe_text_input("Nazwa:", key=f"amain_{_i}", on_change=set_focus, args=(f"attr_{_i}",))
            safe_text_input("Podtytuł:", key=f"asub_{_i}", on_change=set_focus, args=(f"attr_{_i}",))
            safe_text_input("Wpisz gdy atrakcja opcjonalna lub alternatywna:", 
                          key=f"aopt_label_{_i}", max_chars=25,
                          help="Np. opcjonalna, alternatywa, dodatkowa opłata. Puste = brak oznaczenia.",
                          on_change=set_focus, args=(f"attr_{_i}",))
            
            safe_selectbox("Przypisz do dnia:", day_options_global, key=f"aday_{_i}", on_change=set_focus, args=(f"attr_{_i}",))

            assigned_day = st.session_state.get(f"aday_{_i}", "Brak przypisania")
            if assigned_day != "Brak przypisania":
                if st.button(f"⬅️ Wróć do Programu ({assigned_day})", key=f"back_to_program_{_i}", use_container_width=True, type="secondary"):
                    st.session_state['last_page'] = "Program wyjazdu"
                    st.rerun()

            safe_selectbox("Ikona wiodąca (wyświetla się w programie):", ["Wybierz ikonę"] + list(icon_map.keys()), key=f"atype_{_i}", on_change=set_focus, args=(f"attr_{_i}",))
            safe_text_area("Opis:", key=f"aopis_{_i}", on_change=set_focus, args=(f"attr_{_i}",))
            
            # === IKONY OPISU ATRAKCJI (Model 2 - dynamiczne dodawanie) ===
            _section_header("IKONY OPISU ATRAKCJI")
            st.caption("Dodaj 2-5 ikon opisujących atrakcję (czas trwania, cena, typ, dodatkowe cechy). Max 22 znaki opisu.")
            
            _aicons_key = f"aicons_{_i}"
            # Inicjalizuj pustą listę jeśli nie istnieje
            if _aicons_key not in st.session_state or not isinstance(st.session_state.get(_aicons_key), list):
                st.session_state[_aicons_key] = []
            
            # UI dodawania nowej ikony
            _icon_options = list(ATTR_ICONS_AVAILABLE.keys())
            _icon_labels = [ATTR_ICONS_AVAILABLE[k]['label'] for k in _icon_options]
            
            _add_col1, _add_col2, _add_col3 = st.columns([2, 3, 1])
            with _add_col1:
                _selected_icon_label = st.selectbox(
                    "Wybierz ikonę:",
                    _icon_labels,
                    key=f"aicon_select_{_i}",
                    label_visibility="collapsed",
                )
                _selected_icon_id = _icon_options[_icon_labels.index(_selected_icon_label)]
            with _add_col2:
                _new_icon_value = st.text_input(
                    "Opis ikony:",
                    key=f"aicon_value_input_{_i}",
                    max_chars=22,
                    placeholder="np. 3 godziny, lunch w cenie",
                    label_visibility="collapsed",
                )
            with _add_col3:
                if st.button("✚ DODAJ", key=f"aicon_add_btn_{_i}", use_container_width=True, type="primary"):
                    st.session_state[_aicons_key].append({
                        "icon_id": _selected_icon_id,
                        "value": _new_icon_value.strip(),
                    })
                    st.rerun()
            
            # Podgląd wybranej ikony pod selectboxem
            _preview_fa = ATTR_ICONS_AVAILABLE[_selected_icon_id]['icon']
            _acc_color = st.session_state.get('color_accent', '#FF6600')
            st.markdown(
                f'<div style="margin-top:-8px; margin-bottom:8px; padding:8px 12px; '
                f'background:#f8fafc; border-radius:4px; border-left:3px solid {_acc_color}; '
                f'font-size:12px; color:#64748b;">'
                f'Podgląd: <i class="fa-solid {_preview_fa}" style="color:{_acc_color}; font-size:16px; margin:0 6px;"></i> '
                f'<strong style="color:#1e293b;">{ATTR_ICONS_AVAILABLE[_selected_icon_id]["label"]}</strong>'
                f'</div>'
                f'<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">',
                unsafe_allow_html=True,
            )
            
            # Lista dodanych ikon (z edycją opisu i usuwaniem)
            _added = st.session_state.get(_aicons_key, [])
            if _added:
                st.markdown(
                    f'<div style="font-size:10px; font-weight:700; color:#94a3b8; '
                    f'text-transform:uppercase; letter-spacing:1px; margin-top:12px; margin-bottom:6px;">'
                    f'DODANE IKONY ({len(_added)})</div>',
                    unsafe_allow_html=True,
                )
                for _pos, _entry in enumerate(_added):
                    _ic_id = _entry.get("icon_id", "")
                    _ic_data = ATTR_ICONS_AVAILABLE.get(_ic_id)
                    if not _ic_data:
                        _ic_data = {'label': f'(brak: {_ic_id})', 'icon': 'fa-circle-exclamation'}
                    _row_col1, _row_col2, _row_col3 = st.columns([2, 3, 1])
                    with _row_col1:
                        st.markdown(
                            f'<div style="padding:6px 10px; background:#fff7ed; border-radius:4px; '
                            f'border-left:3px solid {_acc_color}; font-size:12px; line-height:1.4;">'
                            f'<i class="fa-solid {_ic_data["icon"]}" style="color:{_acc_color}; '
                            f'font-size:14px; margin-right:6px;"></i>'
                            f'<strong>{_ic_data["label"]}</strong>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    with _row_col2:
                        _new_val = st.text_input(
                            f"Opis #{_pos}",
                            value=_entry.get("value", ""),
                            key=f"aicon_edit_{_i}_{_pos}",
                            max_chars=22,
                            label_visibility="collapsed",
                        )
                        if _new_val != _entry.get("value", ""):
                            st.session_state[_aicons_key][_pos]["value"] = _new_val
                    with _row_col3:
                        if st.button("✕", key=f"aicon_del_{_i}_{_pos}", use_container_width=True):
                            st.session_state[_aicons_key].pop(_pos)
                            st.rerun()
            
            st.file_uploader(
                "Foto Główne",
                key=f"up_ah_{_i}",
                on_change=_make_upload_callback(f"ah_{_i}")
            )

            _ac1, _ac2, _ac3 = st.columns(3)
            
            _ac1.file_uploader(
                "Fot. 1",
                key=f"up_at1_{_i}",
                on_change=_make_upload_callback(f"at1_{_i}")
            )
            _ac2.file_uploader(
                "Fot. 2",
                key=f"up_at2_{_i}",
                on_change=_make_upload_callback(f"at2_{_i}")
            )
            _ac3.file_uploader(
                "Fot. 3",
                key=f"up_at3_{_i}",
                on_change=_make_upload_callback(f"at3_{_i}")
            )

    # -----------------------------------------------------------------------
    # 9. PRZERYWNIK HOTEL
    # -----------------------------------------------------------------------
    elif page == "  ↳ Przerywnik hotel":
        _guard(["sek_0_title", "sek_0_sub", "sek_hide_0", "sek_0_bg", "sek_0_txt", "sek_0_sub_color"]) 
        if not isinstance(st.session_state.get("sek_hide_0"), bool):
            st.session_state["sek_hide_0"] = False

        _bg_default = st.session_state.get('color_h1', '#003366')
        _sub_default = st.session_state.get('color_accent', '#FF6600')

        if st.button("🔄 Resetuj kolory przerywnika", use_container_width=True, key="res_sek_0"):
            st.session_state["sek_0_bg"] = _bg_default
            st.session_state["sek_0_txt"] = "#ffffff"
            st.session_state["sek_0_sub_color"] = _sub_default
            st.rerun()

        # Upewnienie się, że wartości w session_state są poprawne
        for _ck, _cv in [("sek_0_bg", _bg_default), ("sek_0_txt", '#ffffff'), ("sek_0_sub_color", _sub_default)]:
            if not st.session_state.get(_ck):
                st.session_state[_ck] = _cv

        st.button("POKAŻ PODGLĄD", key="btn_sek_0", on_click=set_focus, args=("slide-sek_0",), use_container_width=True)
        safe_checkbox("Ukryj ten slajd w prezentacji", key=f"sek_hide_0")
        st.markdown("---") 

        safe_text_input("Duży tytuł (uppercase):", key=f"sek_0_title")
        safe_text_input("Nadtytuł (overline, kolor akcentu):", key=f"sek_0_sub")
        
        _ic1, _ic2, _ic3 = st.columns(3)
        _ic1.color_picker("Kolor tła:", key="sek_0_bg", value=st.session_state.get("sek_0_bg", _bg_default))
        _ic2.color_picker("Kolor tytułu:", key="sek_0_txt", value=st.session_state.get("sek_0_txt", "#ffffff"))
        _ic3.color_picker("Kolor nadtytułu:", key="sek_0_sub_color", value=st.session_state.get("sek_0_sub_color", _sub_default))

        st.file_uploader(
            "Zdjęcie tła (16:9):",
            key="up_sek_0_img",
            on_change=_make_upload_callback('sek_0_img')
        )
            
    # -----------------------------------------------------------------------
    # 10. OPIS HOTELI (kontener — przycisk dodawania + lista hoteli + edycja)
    # -----------------------------------------------------------------------
    elif page == "Opis hoteli":
        _guard(["num_hotels", "hotel_order"])
        for _hi in range(st.session_state.get("num_hotels", 0)):
            _guard([f"h_hide_{_hi}", f"h_overline_{_hi}", f"h_title_{_hi}",
                    f"h_subtitle_{_hi}", f"h_url_{_hi}", f"h_booking_{_hi}",
                    f"h_amenities_{_hi}", f"h_text_{_hi}", f"h_advantages_{_hi}"])
        # TYMCZASOWY PRZYCISK RESET (do diagnozy)
        if st.button("🔄 RESET WSZYSTKICH HOTELI (DIAGNOZA)", use_container_width=True):
            # Usuń wszystkie klucze związane z hotelami
            keys_to_remove = []
            for k in list(st.session_state.keys()):
                if k.startswith('h_') or k == 'num_hotels' or k == 'hotel_order' or k.startswith('hotel_') or k.startswith('img_hotel_') or k.startswith('up_uh') or k.startswith('btn_show_hot_') or k.startswith('ho_'):
                    keys_to_remove.append(k)
            for k in keys_to_remove:
                del st.session_state[k]
            st.session_state['num_hotels'] = 0
            st.session_state['hotel_order'] = []
            save_to_supabase()
            st.success(f"Wyczyszczono {len(keys_to_remove)} kluczy. Ładowanie...")
            st.rerun()
        
        st.markdown("---")
        # PRZYCISK DODAWANIA HOTELU
        if st.button("✚ DODAJ HOTEL", key="btn_add_hotel_main", type="primary", use_container_width=True):
            _hotel_add()
            st.rerun()
        
        st.markdown("---")
        
        # LISTA HOTELI (z przyciskami zarządzania ▲▼✕)
        _hotel_order_list = _get_hotel_order()
        _n_hotels_curr = _hotel_count()
        
        if _n_hotels_curr == 0:
            st.info("Nie dodano jeszcze żadnego hotelu. Kliknij '➕ DODAJ HOTEL' powyżej.")
        else:
            _section_header(f"LISTA HOTELI ({_n_hotels_curr})")
            for pos, hi in enumerate(_hotel_order_list):
                name = str(st.session_state.get(f'h_title_{hi}', f'Hotel {hi+1}')).split('\n')[0][:35] or f'Hotel {hi+1}'
                col_lbl, col_up, col_dn, col_del = st.columns([6, 1, 1, 1])
                col_lbl.markdown(
                    f"<div style='padding:6px 10px; background:#f1f5f9; border-radius:4px; "
                    f"border-left:3px solid #003366; font-size:12px; color:#1e293b;'>"
                    f"<strong style='color:#003366; font-size:10px; text-transform:uppercase; "
                    f"letter-spacing:1px;'>Hotel {pos+1}</strong><br>{name}</div>",
                    unsafe_allow_html=True,
                )
                if pos > 0:
                    if col_up.button("▲", key=f"hotel_up_{pos}", use_container_width=True):
                        _move_hotel(pos, -1)
                        st.rerun()
                if pos < len(_hotel_order_list) - 1:
                    if col_dn.button("▼", key=f"hotel_dn_{pos}", use_container_width=True):
                        _move_hotel(pos, 1)
                        st.rerun()
                if col_del.button("✕", key=f"hotel_del_{pos}", use_container_width=True):
                    _hotel_delete(pos)
                    st.rerun()
            
            st.markdown("---")
            st.caption("💡 Kliknij '❯ Hotel N' w menu nawigacji aby edytować szczegóły konkretnego hotelu.")

    # -----------------------------------------------------------------------
    # 10b. EDYCJA KONKRETNEGO HOTELU (po kliknięciu "❯ Hotel N" w menu)
    # -----------------------------------------------------------------------
    elif "❯" in page:
        # Wyciągnij numer hotelu z nazwy strony "    ❯ Hotel N"
        _hm = re.search(r'Hotel\s+(\d+)', page)
        if not _hm:
            st.warning("Nie udało się rozpoznać numeru hotelu z nazwy strony.")
        else:
            i = int(_hm.group(1)) - 1  # 1-based -> 0-based
            
            # Sprawdź czy hotel istnieje
            if i >= st.session_state.get('num_hotels', 0):
                st.warning(f"Hotel {i+1} nie istnieje. Wróć na 'Opis hoteli' aby dodać hotele.")
            else:
                # Inicjalizuj klucze tylko jeśli BRAK ich w session_state.
                # WAŻNE: 'st.session_state.get(dk) is None' usunięte — bo np. multiselect
                # po przełączeniu strony może zwracać None, ale dane są zachowane w buforze.
                _h_defaults = [
                    (f'h_hide_{i}', False), (f'h_overline_{i}', 'ZAKWATEROWANIE'),
                    (f'h_title_{i}', f'NAZWA HOTELU {i+1} 5*'),
                    (f'h_subtitle_{i}', 'Komfort i elegancja na najwyższym poziomie'),
                    (f'h_url_{i}', 'www.przykładowy-hotel.com'), (f'h_booking_{i}', '8.9'),
                    (f'h_amenities_{i}', ["Basen", "SPA", "Wi-Fi", "Restauracja", "Plaża"]),
                    (f'h_text_{i}', 'Zapewniamy zakwaterowanie w starannie wyselekcjonowanym hotelu.'),
                    (f'h_advantages_{i}', 'Położenie tuż przy prywatnej plaży'),
                ]
                for dk, dv in _h_defaults:
                    # Buforujemy do _buffer_KEY przed pierwszym widgetem żeby Streamlit nie wyrzucił
                    buf_key = f"_buffer_{dk}"
                    # Jeśli widget zniknął (None), ale w buforze jest wartość — przywróć
                    if st.session_state.get(dk) is None and buf_key in st.session_state:
                        st.session_state[dk] = st.session_state[buf_key]
                    # Jeśli klucza w ogóle nie ma — ustaw default
                    elif dk not in st.session_state:
                        st.session_state[dk] = dv
                    # Po inicjalizacji — zapisz do bufora (do następnego rerun)
                    if dk in st.session_state and st.session_state[dk] is not None:
                        st.session_state[buf_key] = st.session_state[dk]
                # Wymuszamy poprawny typ bool dla h_hide
                if not isinstance(st.session_state.get(f'h_hide_{i}'), bool):
                    st.session_state[f'h_hide_{i}'] = False
                
                # Template manager (zapisz/wczytaj szablon)
                h_keys = [
                    f'h_hide_{i}', f'h_overline_{i}', f'h_title_{i}', f'h_subtitle_{i}',
                    f'h_url_{i}', f'h_booking_{i}', f'h_amenities_{i}', f'h_text_{i}',
                    f'h_advantages_{i}', f'img_hotel_1_{i}', f'img_hotel_1b_{i}',
                    f'img_hotel_2_{i}', f'img_hotel_3_{i}',
                ]
                section_template_manager(h_keys, "HOT", st.session_state.get(f'h_title_{i}', f'hotel-{i+1}'), f"hot_{i}", index=i)
                
                # EDYCJA POL
                safe_checkbox("Ukryj ten slajd w PDF", key=f"h_hide_{i}")
                safe_text_input("Mały nadtytuł:", key=f"h_overline_{i}")
                safe_text_area("Nazwa hotelu (H1):", key=f"h_title_{i}")
                safe_text_input("Podtytuł:", key=f"h_subtitle_{i}")
                
                c1, c2 = st.columns(2)
                # safe wrapper dla text_input i multiselect - chroni przed kasowaniem stanu
                # przez Streamlit przy rerunie (analogicznie do safe_text_input w my_components.py)
                
                # h_url_{i}
                _hurl_buffer = f"buffer_h_url_{i}"
                _hurl_main = st.session_state.get(f"h_url_{i}", "")
                if _hurl_buffer not in st.session_state:
                    st.session_state[_hurl_buffer] = _hurl_main
                def _sync_hurl():
                    st.session_state[f"h_url_{i}"] = st.session_state[_hurl_buffer]
                c1.text_input("Strona www:", value=_hurl_main, key=_hurl_buffer, on_change=_sync_hurl)
                
                # h_booking_{i}
                _hb_buffer = f"buffer_h_booking_{i}"
                _hb_main = st.session_state.get(f"h_booking_{i}", "")
                if _hb_buffer not in st.session_state:
                    st.session_state[_hb_buffer] = _hb_main
                def _sync_hb():
                    st.session_state[f"h_booking_{i}"] = st.session_state[_hb_buffer]
                c2.text_input("Ocena Booking.com:", value=_hb_main, key=_hb_buffer, on_change=_sync_hb)
                
                # h_amenities_{i} - multiselect
                _ham_buffer = f"buffer_h_amenities_{i}"
                _ham_main = st.session_state.get(f"h_amenities_{i}", [])
                if _ham_buffer not in st.session_state:
                    st.session_state[_ham_buffer] = _ham_main
                def _sync_ham():
                    st.session_state[f"h_amenities_{i}"] = st.session_state[_ham_buffer]
                st.multiselect("Udogodnienia (ikonki):", list(hotel_icons.keys()),
                               default=_ham_main, key=_ham_buffer, on_change=_sync_ham)
                safe_text_area("Opis hotelu:", height=200, key=f"h_text_{i}")
                safe_text_area("Atuty hotelu:", height=100, key=f"h_advantages_{i}")
                
                # ZDJĘCIA
                cl1, cl2 = st.columns(2)
                cl1.file_uploader(
                    "Zdj. Lewe Górne",
                    key=f"up_img_hotel_1_{i}",
                    on_change=_make_upload_callback(f'img_hotel_1_{i}')
                )
                cl2.file_uploader(
                    "Zdj. Dolne 1",
                    key=f"up_img_hotel_1b_{i}",
                    on_change=_make_upload_callback(f'img_hotel_1b_{i}')
                )
                
                c3, c4 = st.columns(2)
                c3.file_uploader(
                    "Zdj. Dolne 2",
                    key=f"up_img_hotel_2_{i}",
                    on_change=_make_upload_callback(f'img_hotel_2_{i}')
                )
                c4.file_uploader(
                    "Zdj. Dolne 3",
                    key=f"up_img_hotel_3_{i}",
                    on_change=_make_upload_callback(f'img_hotel_3_{i}')
                )
    
    # -----------------------------------------------------------------------
    # 11. PRZERYWNIK SERWISY DODATKOWE
    # -----------------------------------------------------------------------
    elif page == "  ↳ Przerywnik serwisy dodatkowe":
        # Używamy unikalnych kluczy dla tej sekcji (sek_4)
        _guard(["sek_4_title", "sek_4_sub", "sek_hide_4", "sek_4_bg", "sek_4_txt", "sek_4_sub_color"])  
        
        # Ustawienie wartości domyślnych, jeśli są puste
        if "sek_4_title" not in st.session_state: st.session_state["sek_4_title"] = "SERWISY DODATKOWE"
        if "sek_4_sub" not in st.session_state: st.session_state["sek_4_sub"] = "WYMIAR KOMFORTU PREMIUM"
        
        if not isinstance(st.session_state.get("sek_hide_4"), bool):
            st.session_state["sek_hide_4"] = False

        _bg_default = st.session_state.get('color_h1', '#003366')
        _sub_default = st.session_state.get('color_sub', '#FF6600')

        if st.button("🔄 Resetuj kolory przerywnika", use_container_width=True, key="res_sek_4"):
            st.session_state["sek_4_bg"] = _bg_default
            st.session_state["sek_4_txt"] = "#ffffff"
            st.session_state["sek_4_sub_color"] = _sub_default
            st.rerun()

        for _ck, _cv in [("sek_4_bg", _bg_default), ("sek_4_txt", '#ffffff'), ("sek_4_sub_color", _sub_default)]:
            _v = st.session_state.get(_ck)
            if not _v or _v == '#000000' or not (isinstance(_v, str) and _v.startswith('#') and len(_v) == 7):
                st.session_state[_ck] = _cv
                
        st.button("POKAŻ PODGLĄD", key="btn_sek_4", on_click=set_focus, args=("slide-sek_4",), use_container_width=True)
        safe_checkbox("Ukryj ten slajd w prezentacji", key="sek_hide_4")
        st.markdown("---") 

        safe_text_input("Duży tytuł (uppercase):", key="sek_4_title")
        safe_text_input("Nadtytuł (overline):", key="sek_4_sub")
        
        _ic1, _ic2, _ic3 = st.columns(3)
        _ic1.color_picker("Kolor tła:", key="sek_4_bg")
        _ic2.color_picker("Kolor tytułu:", key="sek_4_txt")
        _ic3.color_picker("Kolor nadtytułu:", key="sek_4_sub_color")

        st.file_uploader(
            "Zdjęcie tła (16:9):",
            key="up_sek_4_img",
            on_change=_make_upload_callback('sek_4_img')
        )
    # -----------------------------------------------------------------------
    # 12. APLIKACJA (KOMUNIKACJA)
    # -----------------------------------------------------------------------
    elif page == "Aplikacja (komunikacja)":
        _guard(["app_hide", "app_overline", "app_title",  
                "app_subtitle", "app_features"])           
        app_keys = [
            'app_hide', 'app_overline', 'app_title', 'app_subtitle',
            'app_features', 'img_app_bg', 'img_app_screen',
        ]
        section_template_manager(app_keys, "APP", "Aplikacja", "app")
        safe_checkbox("Ukryj slajd w PDF", key="app_hide")
        safe_text_input("Mały nadtytuł:", key="app_overline")
        safe_text_area("Główny tytuł H1:", key="app_title")
        safe_text_input("Podtytuł:", key="app_subtitle")
        safe_text_area("Punkty na liście (Enter = nowy punkt):", height=200, key="app_features")
        
        c1, c2 = st.columns(2)
        c1.file_uploader(
            "Zdj. tła (Prawa str.)",
            key="up_img_app_bg",
            on_change=_make_upload_callback('img_app_bg')
        )
        c2.file_uploader(
            "Ekran Aplikacji",
            key="up_img_app_screen",
            on_change=_make_upload_callback('img_app_screen')
        )
    # -----------------------------------------------------------------------
    # 13. MATERIAŁY BRANDINGOWE
    # -----------------------------------------------------------------------
    elif page == "Materiały brandingowe":
        _guard(["brand_hide", "brand_overline", "brand_title",  
                "brand_subtitle", "brand_features", "brand_groups_font",
                "brand_g1_title", "brand_g1_items", "brand_g2_title", "brand_g2_items",
                "brand_g3_title", "brand_g3_items", "brand_footer"])             
        bra_keys = [
            'brand_hide', 'brand_overline', 'brand_title', 'brand_subtitle',
            'brand_groups_font',
            'brand_g1_title', 'brand_g1_items', 'brand_g2_title', 'brand_g2_items',
            'brand_g3_title', 'brand_g3_items', 'brand_footer',
            'img_brand_1', 'img_brand_2', 'img_brand_3',
        ]
        section_template_manager(bra_keys, "BRA", "Branding", "bra")
        safe_checkbox("Ukryj slajd", key="brand_hide")
        safe_text_input("Mały nadtytuł:", key="brand_overline")
        safe_text_area("Główny tytuł H1:", key="brand_title")
        safe_text_input("Podtytuł:", key="brand_subtitle")

        _section_header("PODTYTUŁY GRUP")
        _bgf_opts = FONTS_LIST
        _bgf_cur = st.session_state.get('brand_groups_font', 'Inter')
        try:
            _bgf_idx = _bgf_opts.index(_bgf_cur)
        except ValueError:
            _bgf_idx = _bgf_opts.index('Inter') if 'Inter' in _bgf_opts else 0
        st.selectbox("Font podtytułów grup:", _bgf_opts, index=_bgf_idx, key="brand_groups_font")

        _section_header("GRUPA 1")
        safe_text_input("Podtytuł grupy 1:", key="brand_g1_title")
        safe_text_area("Punkty grupy 1 (Enter = nowy punkt):", height=180, key="brand_g1_items")

        _section_header("GRUPA 2")
        safe_text_input("Podtytuł grupy 2:", key="brand_g2_title")
        safe_text_area("Punkty grupy 2 (Enter = nowy punkt):", height=180, key="brand_g2_items")

        _section_header("GRUPA 3")
        safe_text_input("Podtytuł grupy 3:", key="brand_g3_title")
        safe_text_area("Punkty grupy 3 (Enter = nowy punkt):", height=180, key="brand_g3_items")
        _section_header("TEKST KOŃCOWY")
        safe_text_area("Tekst na dole slajdu:", height=100, key="brand_footer")
        _section_header("ZDJĘCIA")
        c1, c2, c3 = st.columns(3)
        c1.file_uploader(
            "Zdj 1 (Lewa góra)",
            key="up_img_brand_1",
            on_change=_make_upload_callback('img_brand_1')
        )
        c2.file_uploader(
            "Zdj 2 (Prawa góra)",
            key="up_img_brand_2",
            on_change=_make_upload_callback('img_brand_2')
        )
        c3.file_uploader(
            "Zdj 3 (Dół)",
            key="up_img_brand_3",
            on_change=_make_upload_callback('img_brand_3')
        )

    # -----------------------------------------------------------------------
    # 14. PILLOW GIFTS
    # -----------------------------------------------------------------------
    elif page == "Pillow gifts":
        _guard(["pg_hide", "pg_overline", "pg_title", "pg_subtitle",  
                "pg_text", "pg_features"])                             
        gif_keys = [
            'pg_hide', 'pg_overline', 'pg_title', 'pg_subtitle',
            'pg_text', 'pg_features', 'img_pg_1', 'img_pg_2', 'img_pg_3',
        ]
        section_template_manager(gif_keys, "GIF", "Gifts", "gif")
        safe_checkbox("Ukryj slajd", key="pg_hide")
        safe_text_input("Mały nadtytuł:", key="pg_overline")
        safe_text_area("Główny tytuł H1:", key="pg_title")
        safe_text_input("Podtytuł:", key="pg_subtitle")
        safe_text_area("Opis (tekst główny):", height=200, key="pg_text")
        safe_text_area("Punktory (każda linia = jeden punkt):", height=150, key="pg_features",
                     help="Każda linia to jeden punkt z kwadratowym punktorkiem ■")
        c1, c2, c3 = st.columns(3)
        c1.file_uploader(
            "Zdjęcie 1",
            key="up_img_pg_1",
            on_change=_make_upload_callback('img_pg_1')
        )
        c2.file_uploader(
            "Zdjęcie 2 (Pionowe)",
            key="up_img_pg_2",
            on_change=_make_upload_callback('img_pg_2')
        )
        c3.file_uploader(
            "Zdjęcie 3",
            key="up_img_pg_3",
            on_change=_make_upload_callback('img_pg_3')
        )

    # -----------------------------------------------------------------------
    # 15. WIRTUALNY ASYSTENT
    # -----------------------------------------------------------------------
    elif page == "Wirtualny asystent":
        _guard(["va_hide", "va_overline", "va_title", 
                "va_subtitle", "va_text"])              
        va_keys = [
            'va_hide', 'va_overline', 'va_title', 'va_subtitle',
            'va_text', 'img_va_1', 'img_va_2', 'img_va_3',
        ]
        section_template_manager(va_keys, "VA", "Asystent", "va")
        safe_checkbox("Ukryj slajd", key="va_hide")
        safe_text_input("Mały nadtytuł:", key="va_overline")
        safe_text_area("Główny tytuł H1:", key="va_title")
        safe_text_input("Podtytuł:", key="va_subtitle")
        safe_text_area("Treść oferty:", height=300, key="va_text")
        c1, c2, c3 = st.columns(3)
        c1.file_uploader(
            "Zdj 1 (Szerokie)",
            key="up_img_va_1",
            on_change=_make_upload_callback('img_va_1')
        )
        c2.file_uploader(
            "Zdj 2 (Lewy dół)",
            key="up_img_va_2",
            on_change=_make_upload_callback('img_va_2')
        )
        c3.file_uploader(
            "Zdj 3 (Prawy dół)",
            key="up_img_va_3",
            on_change=_make_upload_callback('img_va_3')
        )

    # -----------------------------------------------------------------------
    # 16-17. KOSZTORYS
    # -----------------------------------------------------------------------
    elif page == "Kosztorys str. 1" or page == "Kosztorys str. 2":
        # Ten sam kod obsługuje obie zakładki (masz tam checkboxy do ukrywania poszczególnych stron)
        _guard(["koszt_hide_1", "koszt_hide_2", "koszt_h1_title", "koszt_title",
                "koszt_pax", "koszt_price", "koszt_hotel", "koszt_dbl", "koszt_sgl",
                "koszt_zawiera_1", "koszt_zawiera_2", "koszt_nie_zawiera", "koszt_opcje"])
        koszt_keys = [
            'koszt_hide_1', 'koszt_hide_2', 'koszt_h1_title', 'koszt_title',
            'koszt_pax', 'koszt_price', 'koszt_hotel', 'koszt_dbl', 'koszt_sgl',
            'koszt_zawiera_1', 'koszt_zawiera_2', 'koszt_nie_zawiera',
            'koszt_opcje', 'img_koszt_1', 'img_koszt_2',
        ]
        section_template_manager(koszt_keys, "KOS", "Kosztorys", "koszt")
        st.info("Poniższe opcje zarządzają obydwoma slajdami kosztorysu.")
        c1, c2 = st.columns(2)
        with c1:
            safe_checkbox("Ukryj CAŁY Kosztorys (Slajd 1 i 2)", key="koszt_hide_1")
        with c2:
            safe_checkbox("Ukryj TYLKO Slajd 2 (Ciąg dalszy)", key="koszt_hide_2")
        safe_text_input("Tytuł H1 (duży, górna część):", key="koszt_h1_title")
        safe_text_input("Overline (mały nadtytuł):", key="koszt_title")
        _section_header("GŁÓWNE DANE TABELI")
        c1, c2 = st.columns(2)
        with c1:
            safe_text_input("Wielkość grupy:", key="koszt_pax")
        with c2:
            safe_text_input("Cena:", key="koszt_price")
        safe_text_input("Wybrany Hotel / Standard:", key="koszt_hotel")
        c1, c2 = st.columns(2)
        with c1:
            safe_text_input("Ilość pokoi DBL:", key="koszt_dbl")
        with c2:
            safe_text_input("Ilość pokoi SGL:", key="koszt_sgl")
        _section_header("AUTO-UZUPEŁNIANIE")
        if st.button("GENERUJ LISTĘ KOSZTÓW Z OFERTY", type="primary", use_container_width=True):
            auto_generate_kosztorys()
            st.success("Lista kosztów wygenerowana pomyślnie.")
            st.rerun()
        _section_header("TREŚĆ KOSZTORYSU")
        safe_text_area("Cena zawiera (Część 1 - Slajd 1):", height=200, key="koszt_zawiera_1")
        safe_text_area("Cena zawiera (Część 2 - Slajd 2):", height=150, key="koszt_zawiera_2")
        safe_text_area("Nie policzone w cenie:", height=100, key="koszt_nie_zawiera")
        safe_text_area("Koszty opcjonalne:", height=100, key="koszt_opcje")
        _section_header("ZDJĘCIA")
        c1, c2 = st.columns(2)
        c1.file_uploader(
            "Zdjęcie (Slajd 1)",
            key="up_img_koszt_1",
            on_change=_make_upload_callback('img_koszt_1')
        )
        c2.file_uploader(
            "Zdjęcie (Slajd 2)",
            key="up_img_koszt_2",
            on_change=_make_upload_callback('img_koszt_2')
        )

    # -----------------------------------------------------------------------
    # 18. PRZERYWNIK NASZA AGENCJA
    # -----------------------------------------------------------------------
    elif page == "  ↳ Przerywnik nasza agencja":
        _guard(["sek_2_title", "sek_2_sub", "sek_hide_2", "sek_2_bg", "sek_2_txt", "sek_2_sub_color"]) 
        if not isinstance(st.session_state.get("sek_hide_2"), bool):
            st.session_state["sek_hide_2"] = False

        _bg_default = st.session_state.get('color_h1', '#003366')
        _sub_default = st.session_state.get('color_accent', '#FF6600')

        if st.button("🔄 Resetuj kolory przerywnika", use_container_width=True, key="res_sek_2"):
            st.session_state["sek_2_bg"] = _bg_default
            st.session_state["sek_2_txt"] = "#ffffff"
            st.session_state["sek_2_sub_color"] = _sub_default
            st.rerun()

        # Upewnienie się, że wartości w session_state są poprawne
        for _ck, _cv in [("sek_2_bg", _bg_default), ("sek_2_txt", '#ffffff'), ("sek_2_sub_color", _sub_default)]:
            if not st.session_state.get(_ck):
                st.session_state[_ck] = _cv

        st.button("POKAŻ PODGLĄD", key="btn_sek_2", on_click=set_focus, args=("slide-sek_2",), use_container_width=True)
        safe_checkbox("Ukryj ten slajd w prezentacji", key="sek_hide_2")
        st.markdown("---") 

        safe_text_input("Duży tytuł (uppercase):", key="sek_2_title")
        safe_text_input("Nadtytuł (overline, kolor akcentu):", key="sek_2_sub")
        
        _ic1, _ic2, _ic3 = st.columns(3)
        _ic1.color_picker("Kolor tła:", key="sek_2_bg", value=st.session_state.get("sek_2_bg", _bg_default))
        _ic2.color_picker("Kolor tytułu:", key="sek_2_txt", value=st.session_state.get("sek_2_txt", "#ffffff"))
        _ic3.color_picker("Kolor nadtytułu:", key="sek_2_sub_color", value=st.session_state.get("sek_2_sub_color", _sub_default))

        st.file_uploader(
            "Zdjęcie tła (16:9):",
            key="up_sek_2_img",
            on_change=_make_upload_callback('sek_2_img')
        )

    # -----------------------------------------------------------------------
    # 18b. ESG (Odpowiedzialny partner)
    # -----------------------------------------------------------------------
    elif page == "ESG":
        _guard(["esg_hide", "esg_overline", "esg_title", "esg_subtitle", "esg_intro",
                "esg_e_title", "esg_e_sub", "esg_e_items",
                "esg_s_title", "esg_s_sub", "esg_s_items",
                "esg_g_title", "esg_g_sub", "esg_g_items",
                "esg_quote", "esg_quote_source"])
        for _mi in range(1, 7):  # 6 pól
            _guard([f'esg_m{_mi}_number', f'esg_m{_mi}_value', f'esg_m{_mi}_label'])
        
        esg_keys = [
            'esg_hide', 'esg_overline', 'esg_title', 'esg_subtitle', 'esg_intro',
            'esg_e_title', 'esg_e_sub', 'esg_e_items',
            'esg_s_title', 'esg_s_sub', 'esg_s_items',
            'esg_g_title', 'esg_g_sub', 'esg_g_items',
            'esg_quote', 'esg_quote_source',
        ]
        for _mi in range(1, 7):  # 6 pól
            esg_keys.extend([f'esg_m{_mi}_number', f'esg_m{_mi}_value', f'esg_m{_mi}_label'])
        section_template_manager(esg_keys, "ESG", "ESG", "esg")
        
        safe_checkbox("Ukryj slajd w PDF", key="esg_hide")
        safe_text_input("Mały nadtytuł (overline):", key="esg_overline")
        safe_text_area("Główny tytuł H1:", key="esg_title", height=80)
        safe_text_input("Podtytuł:", key="esg_subtitle")
        safe_text_area("Tekst wprowadzający (pod tytułem):", height=120, key="esg_intro",
                       help="Krótki opis 2-4 zdania. Wyjaśnia rolę ESG w pracy agencji.")
        
        _section_header("KARTA 1 — ENVIRONMENTAL (E)")
        c1, c2 = st.columns(2)
        with c1:
            safe_text_input("Tytuł karty (EN):", key="esg_e_title")
        with c2:
            safe_text_input("Podtytuł (PL):", key="esg_e_sub")
        safe_text_area("Punkty karty (każda linia = jeden punkt):", height=110, key="esg_e_items",
                       help="Maksymalnie 3-4 punkty. Każda linia to osobny punkt z punktorem.")
        
        _section_header("KARTA 2 — SOCIAL (S)")
        c1, c2 = st.columns(2)
        with c1:
            safe_text_input("Tytuł karty (EN):", key="esg_s_title")
        with c2:
            safe_text_input("Podtytuł (PL):", key="esg_s_sub")
        safe_text_area("Punkty karty (każda linia = jeden punkt):", height=110, key="esg_s_items")
        
        _section_header("KARTA 3 — GOVERNANCE (G)")
        c1, c2 = st.columns(2)
        with c1:
            safe_text_input("Tytuł karty (EN):", key="esg_g_title")
        with c2:
            safe_text_input("Podtytuł (PL):", key="esg_g_sub")
        safe_text_area("Punkty karty (każda linia = jeden punkt):", height=110, key="esg_g_items")
        
        _section_header("METRYKI (8 pól, układ 4×2)")
        st.caption("Każde pole ma trzy fragmenty: Liczba (np. '1 000 000+'), Wartość (np. 'PLN' lub nazwa certyfikatu), Etykieta (kategoria). Pola puste — nie wyświetlają się.")
        for _mi in range(1, 9):
            with st.expander(f"Pole {_mi}", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    safe_text_input(f"Liczba/symbol:", key=f"esg_m{_mi}_number",
                                    help="np. '1 000 000+', '724', '100%'. Puste = pole bez liczby.")
                with c2:
                    safe_text_input(f"Wartość główna:", key=f"esg_m{_mi}_value",
                                    help="np. 'PLN', 'Green Key', nazwa certyfikatu.")
                safe_text_input(f"Etykieta (mała):", key=f"esg_m{_mi}_label",
                                help="np. 'GWARANCJA UBEZPIECZENIOWA', 'CERTYFIKAT'.")

    # -----------------------------------------------------------------------
    # 19. O NAS / PARTNERZY ZARZĄDZAJĄCY
    # -----------------------------------------------------------------------
    elif page == "O nas":
        _guard(["about_hide", "about_overline", "about_title", "about_sub", "about_desc",
                "about_p1_name", "about_p1_role", "about_p1_bio", "about_p1_bullets",
                "about_p1_quote", "about_p1_quote_source",
                "about_p2_name", "about_p2_role", "about_p2_bio", "about_p2_bullets",
                "about_p2_quote", "about_p2_quote_source"])
        for _mi in range(1, 9):
            _guard([f'about_m{_mi}_number', f'about_m{_mi}_value', f'about_m{_mi}_label'])
        
        nas_keys = [
            'about_hide', 'about_overline', 'about_title', 'about_sub', 'about_desc',
            'about_p1_name', 'about_p1_role', 'about_p1_bio', 'about_p1_bullets',
            'about_p1_quote', 'about_p1_quote_source', 't_img_0',
            'about_p2_name', 'about_p2_role', 'about_p2_bio', 'about_p2_bullets',
            'about_p2_quote', 'about_p2_quote_source', 't_img_1',
        ]
        for _mi in range(1, 9):
            nas_keys.extend([f'about_m{_mi}_number', f'about_m{_mi}_value', f'about_m{_mi}_label'])
        section_template_manager(nas_keys, "NAS", "Zespol", "nas")
        
        safe_checkbox("Ukryj ten slajd w PDF", key="about_hide")
        safe_text_input("Mały nadtytuł:", key="about_overline")
        safe_text_area("Główny tytuł H1:", key="about_title", height=80)
        safe_text_input("Podtytuł:", key="about_sub")
        safe_text_area("Paragraf wprowadzający o firmie:", height=160, key="about_desc",
                       help="Krótki opis firmy zorientowany na działy zakupów - lata, kontynenty, ESG, compliance.")
        
        _section_header("PARTNER 1 — JOANNA JABŁOŃSKA")
        safe_text_input("Imię i nazwisko:", key="about_p1_name")
        safe_text_input("Funkcja (Partner | Członek Zarządu | ...):", key="about_p1_role")
        safe_text_area("Biogram:", height=160, key="about_p1_bio")
        safe_text_area("Bullety (każda linia = jeden punkt, max 3-4):", height=100, key="about_p1_bullets",
                       help="Krótkie konkretne fakty - lata doświadczenia, role branżowe, tytuły.")
        safe_text_area("Cytat (bez cudzysłowów):", height=80, key="about_p1_quote",
                       help="Krótki cytat z artykułu/wypowiedzi w prasie branżowej.")
        safe_text_input("Źródło cytatu (np. 'Think MICE, październik 2025'):", key="about_p1_quote_source")
        st.file_uploader(
            "Zdjęcie (kwadratowe, najlepiej 400x400 lub większe):",
            key="up_t_img_0",
            on_change=_make_upload_callback('t_img_0')
        )
        
        _section_header("PARTNER 2 — MARCIN ŁUKASZEWICZ")
        safe_text_input("Imię i nazwisko:", key="about_p2_name")
        safe_text_input("Funkcja:", key="about_p2_role")
        safe_text_area("Biogram:", height=160, key="about_p2_bio")
        safe_text_area("Bullety (każda linia = jeden punkt, max 3-4):", height=100, key="about_p2_bullets")
        safe_text_area("Cytat (bez cudzysłowów):", height=80, key="about_p2_quote")
        safe_text_input("Źródło cytatu (np. 'OOH Magazine'):", key="about_p2_quote_source")
        st.file_uploader(
            "Zdjęcie (kwadratowe, najlepiej 400x400 lub większe):",
            key="up_t_img_1",
            on_change=_make_upload_callback('t_img_1')
        )
        
        _section_header("METRYKI / CERTYFIKATY (8 pól, układ 4×2)")
        st.caption("Każde pole ma trzy fragmenty: Liczba (np. '724', '1997'), Wartość (np. 'Raport ESG' lub 'Pracodawca'), Etykieta (kategoria). Pola puste — nie wyświetlają się.")
        for _mi in range(1, 9):
            with st.expander(f"Pole {_mi}", expanded=False):
                c1, c2 = st.columns(2)
                with c1:
                    safe_text_input(f"Liczba/symbol:", key=f"about_m{_mi}_number",
                                    help="np. '724', '1997', 'SOIT'. Puste = pole bez liczby.")
                with c2:
                    safe_text_input(f"Wartość główna:", key=f"about_m{_mi}_value",
                                    help="np. 'PLN', 'Raport ESG', 'Pakiet compliance'.")
                safe_text_input(f"Etykieta (mała):", key=f"about_m{_mi}_label",
                                help="np. 'LICENCJA ORGANIZATORA TOT', 'CZŁONEK STOWARZYSZENIA'.")

    # -----------------------------------------------------------------------
    # 20. REFERENCJE (Co o nas mówią)
    # -----------------------------------------------------------------------
    elif page == "Referencje":
        _guard(["testim_hide", "testim_overline", "testim_title", 
                "testim_subtitle", "testim_count"])                 
        opi_keys = [
            'testim_hide', 'testim_overline', 'testim_title', 'testim_subtitle',
            'img_testim_main', 'testim_count',
        ]
        for i in range(st.session_state.get('testim_count', 3)):
            opi_keys.extend([f'testim_img_{i}', f'testim_head_{i}',
                             f'testim_quote_{i}', f'testim_author_{i}', f'testim_role_{i}'])
        section_template_manager(opi_keys, "OPI", "Opinie", "opi")
        safe_checkbox("Ukryj ten slajd w PDF", key="testim_hide")
        safe_text_input("Mały nadtytuł:", key="testim_overline")
        safe_text_area("Główny tytuł H1:", key="testim_title")
        safe_text_area("Podtytuł:", key="testim_subtitle")
        st.file_uploader(
            "Zdjęcie główne slajdu",
            key="up_img_testim_main",
            on_change=_make_upload_callback('img_testim_main')
        )
        st.number_input("Liczba opinii:", 1, 4, step=1, key="testim_count")
        for i in range(st.session_state['testim_count']):
            for dk in [f"testim_head_{i}", f"testim_quote_{i}",
                       f"testim_author_{i}", f"testim_role_{i}"]:
                if dk not in st.session_state:
                    st.session_state[dk] = ""
            with st.expander(f"Opinia {i+1}"):
                st.file_uploader(
                    "Zdjęcie / Logo",
                    key=f"up_testim_img_{i}",
                    on_change=_make_upload_callback(f"testim_img_{i}")
                )
                safe_text_input("Nagłówek", key=f"testim_head_{i}")
                safe_text_area("Treść rekomendacji", key=f"testim_quote_{i}")
                c1, c2 = st.columns(2)
                c1.text_input("Autor (Pogrubiony)", key=f"testim_author_{i}")
                c2.text_input("Stanowisko", key=f"testim_role_{i}")
    # -----------------------------------------------------------------------
    # WYGLĄD I KOLORY
    # -----------------------------------------------------------------------
    elif page == "⚙ WYGLĄD I KOLORY":
        # 1. Dokładnie Twoje kolory z kodu
        color_defaults = {
            'color_h1': '#003366', 'color_h2': '#003366', 'color_sub': '#FF6600',
            'color_accent': '#FF6600', 'color_text': '#333333', 'color_metric': '#003366',
        }
        size_defaults = {
            'font_size_h1': 48, 'font_size_h2': 36, 'font_size_sub': 26,
            'font_size_text': 14, 'font_size_metric': 16,
        }

        # Zabezpieczenie: Przycisk resetu (gdyby znów wszystko zrobiło się czarne)
        if st.button("🔄 RESETUJ KOLORY DO DOMYŚLNYCH"):
            for k, v in color_defaults.items():
                st.session_state[k] = v
            st.rerun()

        # Blokada czarnych kolorów zepsutych przez bazę danych
        for k, v in color_defaults.items():
            val = st.session_state.get(k, v)
            if val == '#000000' or val == '#000' or not (isinstance(val, str) and val.startswith('#') and len(val) == 7):
                st.session_state[k] = v
                
        for k, v in size_defaults.items():
            val = st.session_state.get(k, v)
            try:
                _int_val = int(float(val)) if val else v
                if _int_val <= 8:
                    st.session_state[k] = v
                elif _int_val != val:
                    st.session_state[k] = _int_val
            except Exception:
                st.session_state[k] = v

        # Defaults dla fontów (musi być przed renderem widgetów)
        _font_defaults = {
            'font_h1': 'Montserrat', 'font_h2': 'Montserrat', 'font_sub': 'Montserrat',
            'font_text': 'Open Sans', 'font_metric': 'Montserrat',
        }
        for f_key, f_def in _font_defaults.items():
            cur = st.session_state.get(f_key)
            if not cur or cur not in FONTS_LIST:
                st.session_state[f_key] = f_def
        
        for (f_key, c_key, s_key, label) in [
            ('font_h1', 'color_h1', 'font_size_h1', 'H1'),
            ('font_h2', 'color_h2', 'font_size_h2', 'H2'),
            ('font_sub', 'color_sub', 'font_size_sub', 'Podt.'),
            ('font_text', 'color_text', 'font_size_text', 'Tekstu'),
            ('font_metric', 'color_metric', 'font_size_metric', 'Wyr.'),
        ]:
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.selectbox(f"Czcionka {label}", FONTS_LIST, key=f_key)
            # color_picker nie czyta session_state przy pierwszym renderze (bug Streamlit)
            # więc używamy value= bez key= i przypisujemy wynik ręcznie
            _new_color = c2.color_picker(
                f"Kolor {label}",
                value=st.session_state.get(c_key, color_defaults[c_key]),
            )
            st.session_state[c_key] = _new_color
            c3.number_input("Rozmiar (px)", min_value=8, max_value=120,
                            step=1, format="%d", key=s_key)
        
        _new_acc = st.color_picker(
            "Akcent",
            value=st.session_state.get('color_accent', '#FF6600'),
        )
        st.session_state['color_accent'] = _new_acc
    # -----------------------------------------------------------------------
    # ZAPISZ / WCZYTAJ PROJEKT
    # -----------------------------------------------------------------------
    elif page == "Zapisz / Wczytaj Projekt":
        st.markdown("##### Auto-zapis do bazy danych")
        # Poprawiony tekst na 30 sekund
        st.info("📊 Twój projekt jest automatycznie zapisywany do bazy Supabase co 30 sekund. Dane przeżywają restart aplikacji i są dostępne zawsze.")
        st.markdown("---")
        st.markdown("##### Plik JSON na dysk / OneDrive")
        
        # KRYTYCZNA ZMIANA: Generujemy ciężki plik JSON TYLKO, gdy klikniesz przycisk
        if st.button("PRZYGOTUJ PLIK JSON DO POBRANIA", type="primary"):
            with st.spinner("Generowanie pliku..."):
                proj = _build_proj_dict()
                st.session_state['temp_proj_json'] = json.dumps(proj, ensure_ascii=False)
                
        # Pokazujemy przycisk pobierania dopiero, gdy plik jest gotowy
        if 'temp_proj_json' in st.session_state:
            st.download_button(
                "📥 POBIERZ PLIK PROJEKTU (JSON)", 
                st.session_state['temp_proj_json'],
                get_project_filename(), 
                use_container_width=True,
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
    # Auto-zapis do Supabase działa w tle co 30 sekund - brak potrzeby ręcznego zapisu
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
# GŁÓWNA ZAWARTOŚĆ — PODGLĄD PREZENTACJI
# ---------------------------------------------------------------------------
with col_preview:
    _acc = st.session_state.get('color_accent', '#FF6600')
    st.markdown(f"<h3 style='color:{_acc};font-size:16px;margin-bottom:20px;'>PODGLĄD SLAJDU</h3>", unsafe_allow_html=True)
    
    @st.fragment
    def _preview():
        # current_page (logika filtrowania) ZAWSZE z last_page (nazwa strony z menu)
        # scroll_target (przewijanie do slajdu) jest osobnym mechanizmem
        _current_p = st.session_state.get('last_page', "Strona tytułowa")
        build_presentation(_current_p)
                
    _preview()
    
