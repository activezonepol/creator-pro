"""
code_generator.py
=================
Generator kodów ofert i modułów wg formatu:
- Oferty: RR-MM-KK-KLIENT-NAZWA (np. 26-04-POL-AGENCJA1-NEXA)
- Moduły: RR-MM-KK-TYP-NAZWA (np. 26-04-POL-HOT-IBEROSTAR)

KK = ISO 3166-1 alfa-3 kod kraju (POL, MNE, ESP, ...)
TYP = HOT (hotel), ATR (atrakcja), KIE (kierunek), TYT (tytułowa)

LOGIKA OFERT BEZ KRAJU:
- Pusty kraj ("-- Wybierz kraj --") → kod oferty z OTH (zapisuje, kraj do uzupełnienia)
- "Inny" → kod oferty z OTH (zapisuje, świadomy wybór)
- Konkretny kraj (Polska, ...) → kod oferty z konkretnym ISO (POL, ...)
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
    
    # Mapa specjalna dla polskich znaków
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
    
    # Dodatkowo unicodedata dla innych znaków diakrytycznych
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
    
    Przy
