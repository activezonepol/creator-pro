"""
code_generator.py
=================
Generator kodów ofert i modułów wg formatu:
- Oferty: RR-MM-KK-KLIENT-NAZWA (np. 26-04-POL-AGENCJA1-NEXA)
- Moduły: RR-MM-KK-TYP-NAZWA (np. 26-04-POL-HOT-IBEROSTAR)

KK = ISO 3166-1 alfa-3 kod kraju (POL, MNE, ESP, ...)
TYP = HOT (hotel), ATR (atrakcja), KIE (kierunek), TYT (tytułowa)
"""
import re
import unicodedata
from datetime import datetime, date
import streamlit as st


# ---------------------------------------------------------------------------
# TRANSLITERACJA POLSKICH ZNAKÓW
# ---------------------------------------------------------------------------
def transliterate_pl(text: str) -> str:
    """Zamienia polskie znaki diakrytyczne na łacińskie odpowiedniki.
    
    Przykład:
        'Łukasz Żółty' → 'LUKASZ ZOLTY'
    """
    if not text:
        return ""
    
    # Mapa specjalna dla polskich znaków (bo unicodedata nie zawsze działa idealnie)
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
    result = text
    for pl_char, lat_char in pl_map.items():
        result = result.replace(pl_char, lat_char)
    
    # Dodatkowo unicodedata dla innych znaków diakrytycznych (np. niemieckich)
    result = unicodedata.normalize('NFKD', result).encode('ascii', 'ignore').decode('utf-8')
    
    return result


# ---------------------------------------------------------------------------
# CZYSZCZENIE STRINGÓW DO FORMATU NAZWY PLIKU
# ---------------------------------------------------------------------------
def clean_for_code(text: str, max_len: int = 8) -> str:
    """Przygotowuje string do użycia w kodzie oferty/modułu.
    
    - Transliteracja polskich znaków
    - Wielkie litery
    - Tylko alphanumeric (litery i cyfry)
    - Maksymalna długość
    
    Przykład:
        'Łukasz Żółty Sp. z o.o.' → 'LUKASZZO' (max 8 znaków)
    """
    if not text:
        return ""
    
    # 1. Transliteracja
    cleaned = transliterate_pl(str(text).strip())
    
    # 2. Wielkie litery
    cleaned = cleaned.upper()
    
    # 3. Tylko alphanumeric (bez spacji, kropek, myślników)
    cleaned = re.sub(r'[^A-Z0-9]', '', cleaned)
    
    # 4. Obcięcie do max_len
    cleaned = cleaned[:max_len]
    
    return cleaned


# ---------------------------------------------------------------------------
# PARSOWANIE DATY DO RR-MM
# ---------------------------------------------------------------------------
def parse_date_to_rrmm(date_str: str) -> tuple[str, int, int]:
    """Wyciąga rok i miesiąc z pola 'Termin' aplikacji.
    
    Obsługiwane formaty:
        '1-4.10.2026'        → ('26-10', 2026, 10)
        '01-04.10.2026'      → ('26-10', 2026, 10)
        '15.06.2026'         → ('26-06', 2026, 6)
        '28.12-03.01.2027'   → ('26-12', 2026, 12) ← bierze pierwszą datę
    
    Returns:
        tuple: (rrmm_str, year_full, month) - np. ('26-04', 2026, 4)
        
    Jeśli nie można sparsować → fallback do daty dzisiejszej.
    """
    if not date_str or not date_str.strip():
        # Fallback: dziś
        now = datetime.now()
        rrmm = f"{now.year % 100:02d}-{now.month:02d}"
        return rrmm, now.year, now.month
    
    d_str = date_str.strip()
    
    # Format 1: 1-4.10.2026 lub 01-04.10.2026
    m1 = re.search(r'(\d{1,2})\s*-\s*(\d{1,2})\.(\d{1,2})\.(\d{4})', d_str)
    if m1:
        try:
            year = int(m1.group(4))
            month = int(m1.group(3))
            rrmm = f"{year % 100:02d}-{month:02d}"
            return rrmm, year, month
        except (ValueError, IndexError):
            pass
    
    # Format 2: 28.12-03.01.2027 (przełom roku)
    m2 = re.search(r'(\d{1,2})\.(\d{1,2})\s*-\s*(\d{1,2})\.(\d{1,2})\.(\d{4})', d_str)
    if m2:
        try:
            # Bierzemy pierwszą datę (rozpoczęcie wyjazdu)
            day_start = int(m2.group(1))
            month_start = int(m2.group(2))
            year_end = int(m2.group(5))
            
            # Jeśli przełom roku (np. 28.12 → 03.01.2027), 
            # rok rozpoczęcia to year_end - 1
            month_end = int(m2.group(4))
            year_start = year_end - 1 if month_start > month_end else year_end
            
            rrmm = f"{year_start % 100:02d}-{month_start:02d}"
            return rrmm, year_start, month_start
        except (ValueError, IndexError):
            pass
    
    # Format 3: 15.06.2026 (jednodniowa)
    m3 = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', d_str)
    if m3:
        try:
            year = int(m3.group(3))
            month = int(m3.group(2))
            rrmm = f"{year % 100:02d}-{month:02d}"
            return rrmm, year, month
        except (ValueError, IndexError):
            pass
    
    # Fallback: dziś
    now = datetime.now()
    rrmm = f"{now.year % 100:02d}-{now.month:02d}"
    return rrmm, now.year, now.month


# ---------------------------------------------------------------------------
# GŁÓWNA FUNKCJA: GENEROWANIE KODU OFERTY
# ---------------------------------------------------------------------------
def generate_project_code() -> dict | None:
    """Generuje kod oferty na podstawie danych z session_state.
    
    Format: RR-MM-KK-KLIENT-NAZWA
    Przykład: 26-04-POL-AGENCJA1-NEXA
    
    Returns:
        dict z polami:
            'code': str - pełny kod oferty
            'country_iso': str - kod kraju (POL)
            'country_name': str - nazwa kraju (Polska)
            'year': int - rok (2026)
            'month': int - miesiąc (4)
            'client_short': str - skrót klienta (AGENCJA1)
            'project_name': str - skrócona nazwa (NEXA)
        
        None - jeśli kraj nie jest wybrany (krytyczny błąd)
    """
    # 1. KRAJ — wymagany!
    country_iso = st.session_state.get('country_code', '').strip()
    country_name = st.session_state.get('country_name', '').strip()
    
    if not country_iso or country_iso == 'OTH':
        return None  # Bez kraju nie generujemy kodu
    
    # 2. DATA → RR-MM
    date_str = st.session_state.get('t_date', '')
    rrmm, year, month = parse_date_to_rrmm(date_str)
    
    # 3. SKRÓT KLIENTA (z fallbackiem)
    client_raw = st.session_state.get('client_short', '').strip()
    
    # Jeśli pusty - sprawdzamy 't_klient' jako alternatywę
    if not client_raw:
        client_raw = st.session_state.get('t_klient', '').strip()
    
    client_short = clean_for_code(client_raw, max_len=8)
    if not client_short:
        client_short = 'KLIENT'
    
    # 4. NAZWA OFERTY (z fallbackiem)
    name_raw = st.session_state.get('t_main', '').strip()
    project_name = clean_for_code(name_raw, max_len=20)
    if not project_name:
        project_name = 'NAZWA'
    
    # 5. SKŁADAMY KOD
    code = f"{rrmm}-{country_iso}-{client_short}-{project_name}"
    
    return {
        'code': code,
        'country_iso': country_iso,
        'country_name': country_name,
        'year': year,
        'month': month,
        'client_short': client_short,
        'project_name': project_name,
    }


# ---------------------------------------------------------------------------
# GENEROWANIE KODU MODUŁU
# ---------------------------------------------------------------------------
def generate_module_code(module_type: str, module_name: str) -> str | None:
    """Generuje kod modułu (slajdu).
    
    Format: RR-MM-KK-TYP-NAZWA
    Przykład: 26-04-POL-HOT-IBEROSTAR
    
    Args:
        module_type: typ modułu - 'HOT', 'ATR', 'KIE', 'TYT'
        module_name: nazwa modułu (np. nazwa hotelu)
    
    Returns:
        str - kod modułu, lub None jeśli kraj nie jest wybrany
    """
    country_iso = st.session_state.get('country_code', '').strip()
    if not country_iso or country_iso == 'OTH':
        return None
    
    date_str = st.session_state.get('t_date', '')
    rrmm, _, _ = parse_date_to_rrmm(date_str)
    
    # Czyszczenie typu
    module_type = clean_for_code(module_type, max_len=3)
    if not module_type:
        module_type = 'MOD'
    
    # Czyszczenie nazwy
    name_clean = clean_for_code(module_name, max_len=20)
    if not name_clean:
        name_clean = 'NAZWA'
    
    return f"{rrmm}-{country_iso}-{module_type}-{name_clean}"


# ---------------------------------------------------------------------------
# WALIDACJA
# ---------------------------------------------------------------------------
def is_country_selected() -> bool:
    """Sprawdza czy użytkownik wybrał kraj (nie 'Inny').
    
    Returns:
        True - kraj jest wybrany prawidłowo
        False - brak kraju lub wybrane 'OTH' (Inny)
    """
    country_iso = st.session_state.get('country_code', '').strip()
    return bool(country_iso) and country_iso != 'OTH'


def get_country_warning_message() -> str:
    """Zwraca komunikat ostrzegawczy dla użytkownika gdy brak kraju."""
    return (
        "⚠️ Wybierz kraj na Stronie Tytułowej, "
        "aby oferta zaczęła się zapisywać w bazie."
    )
