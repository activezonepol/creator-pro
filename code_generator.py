"""
code_generator.py
=================
Generator kodów ofert i modulow.

Format: RR-MM-KK-KLIENT-NAZWA
Dla pustego/Inny: KK = OTH
"""
import re
import unicodedata
from datetime import datetime
import streamlit as st


# ---------------------------------------------------------------------------
# TRANSLITERACJA POLSKICH ZNAKOW
# ---------------------------------------------------------------------------
def transliterate_pl(text):
    """Zamienia polskie znaki na lacinskie."""
    if not text:
        return ""
    
    pl_map = {
        'ą': 'a', 'Ą': 'A',
        'ć': 'c', 'Ć': 'C',
        'ę': 'e', 'Ę': 'E',
        'ł': 'l', 'Ł': 'L',
        'ń': 'n', 'Ń': 'N',
        'ó': 'o', 'Ó': 'O',
        'ś': 's', 'Ś': 'S',
        'ź': 'z', 'Ź': 'Z',
        'ż': 'z', 'Ż': 'Z',
    }
    result = str(text)
    for pl_char, lat_char in pl_map.items():
        result = result.replace(pl_char, lat_char)
    
    result = unicodedata.normalize('NFKD', result).encode('ascii', 'ignore').decode('utf-8')
    return result


# ---------------------------------------------------------------------------
# CZYSZCZENIE STRINGOW
# ---------------------------------------------------------------------------
def clean_for_code(text, max_len=8):
    """Czysci string do uzycia w kodzie oferty."""
    if not text:
        return ""
    
    cleaned = transliterate_pl(str(text).strip())
    cleaned = cleaned.upper()
    cleaned = re.sub(r'[^A-Z0-9]', '', cleaned)
    cleaned = cleaned[:max_len]
    
    return cleaned


# ---------------------------------------------------------------------------
# PARSOWANIE DATY
# ---------------------------------------------------------------------------
def parse_date_to_rrmm(date_str):
    """Wyciaga rok i miesiac z pola Termin."""
    if not date_str or not str(date_str).strip():
        now = datetime.now()
        rrmm = "{:02d}-{:02d}".format(now.year % 100, now.month)
        return rrmm, now.year, now.month
    
    d_str = str(date_str).strip()
    
    # Format: 1-4.10.2026 lub 01-04.10.2026
    m1 = re.search(r'(\d{1,2})\s*-\s*(\d{1,2})\.(\d{1,2})\.(\d{4})', d_str)
    if m1:
        try:
            year = int(m1.group(4))
            month = int(m1.group(3))
            rrmm = "{:02d}-{:02d}".format(year % 100, month)
            return rrmm, year, month
        except (ValueError, IndexError):
            pass
    
    # Format: 28.12-03.01.2027 (przelom roku)
    m2 = re.search(r'(\d{1,2})\.(\d{1,2})\s*-\s*(\d{1,2})\.(\d{1,2})\.(\d{4})', d_str)
    if m2:
        try:
            day_start = int(m2.group(1))
            month_start = int(m2.group(2))
            year_end = int(m2.group(5))
            month_end = int(m2.group(4))
            year_start = year_end - 1 if month_start > month_end else year_end
            
            rrmm = "{:02d}-{:02d}".format(year_start % 100, month_start)
            return rrmm, year_start, month_start
        except (ValueError, IndexError):
            pass
    
    # Format: 15.06.2026
    m3 = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', d_str)
    if m3:
        try:
            year = int(m3.group(3))
            month = int(m3.group(2))
            rrmm = "{:02d}-{:02d}".format(year % 100, month)
            return rrmm, year, month
        except (ValueError, IndexError):
            pass
    
    # Fallback: dzis
    now = datetime.now()
    rrmm = "{:02d}-{:02d}".format(now.year % 100, now.month)
    return rrmm, now.year, now.month


# ---------------------------------------------------------------------------
# STAN KRAJU - 3 MOZLIWE STANY
# ---------------------------------------------------------------------------
def get_country_status():
    """Zwraca aktualny stan kraju.
    
    Returns:
        'empty'    - placeholder "-- Wybierz kraj --"
        'other'    - wybrane "Inny"
        'concrete' - konkretny kraj (Polska, Hiszpania, ...)
    """
    country_name = str(st.session_state.get('country_name', '')).strip()
    country_iso = str(st.session_state.get('country_code', '')).strip()
    
    if country_name == '-- Wybierz kraj --' or not country_iso:
        return 'empty'
    
    if country_iso == 'OTH':
        return 'other'
    
    return 'concrete'

def is_country_selected():
    """[DEPRECATED] Zachowane dla kompatybilnosci.
    
    Po Commit 2 NIE BLOKUJEMY zapisu.
    """
    return get_country_status() == 'concrete'


def get_country_warning_message():
    """Zwraca komunikat informacyjny zalezny od stanu kraju."""
    status = get_country_status()
    
    if status == 'empty':
        return "Kraj do uzupelnienia"
    elif status == 'other':
        return "Kraj: Inny (kod OTH)"
    else:
        return ""


# ---------------------------------------------------------------------------
# GLOWNA FUNKCJA: GENEROWANIE KODU OFERTY
# ---------------------------------------------------------------------------
def generate_project_code():
    """Generuje kod oferty.
    
    Format: RR-MM-KK-KLIENT-NAZWA
    Dla pustego/Inny: KK = OTH (zawsze zwraca kod, nigdy None).
    """
    status = get_country_status()
    country_iso = str(st.session_state.get('country_code', '')).strip()
    country_name = str(st.session_state.get('country_name', '')).strip()
    
    if status in ('empty', 'other'):
        country_iso_for_code = 'OTH'
    else:
        country_iso_for_code = country_iso
    
    date_str = st.session_state.get('t_date', '')
    rrmm, year, month = parse_date_to_rrmm(date_str)
    
    client_raw = str(st.session_state.get('client_short', '')).strip()
    if not client_raw:
        client_raw = str(st.session_state.get('t_klient', '')).strip()
    
    client_short = clean_for_code(client_raw, max_len=8)
    if not client_short:
        client_short = 'KLIENT'
    
    name_raw = str(st.session_state.get('t_main', '')).strip()
    project_name = clean_for_code(name_raw, max_len=20)
    if not project_name:
        project_name = 'NAZWA'
    
    code = "{}-{}-{}-{}".format(rrmm, country_iso_for_code, client_short, project_name)
    
    return {
        'code': code,
        'country_iso': country_iso_for_code,
        'country_name': country_name,
        'year': year,
        'month': month,
        'client_short': client_short,
        'project_name': project_name,
        'status': status,
    }


# ---------------------------------------------------------------------------
# KOD MODULU
# ---------------------------------------------------------------------------
def generate_module_code(module_type, module_name):
    """Generuje kod modulu (slajdu).
    
    Format: RR-MM-KK-TYP-NAZWA
    """
    country_iso = str(st.session_state.get('country_code', '')).strip()
    if not country_iso:
        country_iso = 'OTH'
    
    date_str = st.session_state.get('t_date', '')
    rrmm, _, _ = parse_date_to_rrmm(date_str)
    
    module_type = clean_for_code(module_type, max_len=3)
    if not module_type:
        module_type = 'MOD'
    
    name_clean = clean_for_code(module_name, max_len=20)
    if not name_clean:
        name_clean = 'NAZWA'
    
    return "{}-{}-{}-{}".format(rrmm, country_iso, module_type, name_clean)
