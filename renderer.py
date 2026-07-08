"""
renderer.py
===========
Zawiera:
- Stałe i dane słownikowe (COUNTRIES_DICT, FONTS_LIST, hotel_icons, icon_map, defaults)
- Helpery obrazów: optimize_img, optimize_logo, get_b64_cached, get_b64, get_logo_b64
- Mapa kafelków OSM + geokodowanie: get_tile_bytes, geocode_place, generate_map_data
- CSS: get_local_css
- Buildy HTML slajdów: build_presentation
- Eksport projektu: get_project_filename
- Narzędzia: create_slug, parse_date_and_days, auto_generate_kosztorys, load_project_data
"""
import io
import re
import json
import base64
import math
import urllib.request
import urllib.parse
import unicodedata
from datetime import datetime, timedelta, date
import streamlit as st
from PIL import Image, ImageOps

# ---------------------------------------------------------------------------
# BEZPIECZNY ODCZYT DANYCH
# ---------------------------------------------------------------------------
def get_data(key, default=None):
    """Bezpieczny odczyt z sesji z fallbackiem do cache'u Supabase."""
    if key in st.session_state and st.session_state[key] is not None:
        return st.session_state[key]
    
    supabase_data = st.session_state.get('_supabase_data', {})
    if isinstance(supabase_data, dict) and key in supabase_data:
        st.session_state[key] = supabase_data[key]
        return supabase_data[key]
        
    return default
# ---------------------------------------------------------------------------
# STAŁE I DANE
# ---------------------------------------------------------------------------
COUNTRIES_DICT = {
    "-- Wybierz kraj --": "",
    "Albania": "ALB", "Andora": "AND", "Arabia Saudyjska": "SAU",
    "Argentyna": "ARG", "Aruba": "ABW", "Australia": "AUS", "Austria": "AUT",
    "Azerbejdżan": "AZE",
    "Belgia": "BEL", "Bhutan": "BTN", "Boliwia": "BOL", "Bonaire": "BES",
    "Bośnia i Hercegowina": "BIH", "Botswana": "BWA", "Brazylia": "BRA",
    "Bułgaria": "BGR",
    "Chile": "CHL", "Chiny": "CHN", "Chorwacja": "HRV", "Cypr": "CYP",
    "Czarnogóra": "MNE", "Czechy": "CZE",
    "Dania": "DNK", "Dominikana": "DOM",
    "Egipt": "EGY", "Ekwador": "ECU", "Estonia": "EST", "Etiopia": "ETH",
    "Fidżi": "FJI", "Filipiny": "PHL", "Finlandia": "FIN", "Francja": "FRA",
    "Grecja": "GRC", "Gruzja": "GEO",
    "Hiszpania": "ESP", "Holandia": "NLD", "Hongkong": "HKG",
    "Indie": "IND", "Indonezja": "IDN", "Irlandia": "IRL", "Islandia": "ISL",
    "Izrael": "ISR",
    "Jamajka": "JAM", "Japonia": "JPN", "Jordania": "JOR",
    "Kambodża": "KHM", "Kanada": "CAN", "Kenia": "KEN", "Kolumbia": "COL",
    "Korea Południowa": "KOR", "Kostaryka": "CRI", "Kuba": "CUB",
    "Laos": "LAO", "Liechtenstein": "LIE", "Litwa": "LTU",
    "Łotwa": "LVA",
    "Macao": "MAC", "Macedonia Pn.": "MKD", "Madagaskar": "MDG",
    "Malediwy": "MDV", "Malezja": "MYS", "Malta": "MLT", "Maroko": "MAR",
    "Mauritius": "MUS", "Meksyk": "MEX", "Monako": "MCO", "Mongolia": "MNG",
    "Namibia": "NAM", "Nepal": "NPL", "Niemcy": "DEU", "Norwegia": "NOR",
    "Nowa Zelandia": "NZL",
    "Oman": "OMN",
    "Panama": "PAN", "Peru": "PER", "Polska": "POL", "Portugalia": "PRT",
    "RPA": "ZAF", "Rumunia": "ROU", "Rwanda": "RWA",
    "Serbia": "SRB", "Seszele": "SYC", "Singapur": "SGP", "Słowacja": "SVK",
    "Słowenia": "SVN", "Sri Lanka": "LKA", "Stany Zjednoczone": "USA",
    "Szwajcaria": "CHE", "Szwecja": "SWE",
    "Tajlandia": "THA", "Tajwan": "TWN", "Tunezja": "TUN", "Turcja": "TUR",
    "Uganda": "UGA", "Urugwaj": "URY",
    "W. Brytania": "GBR", "Węgry": "HUN", "Wenezuela": "VEN",
    "Wietnam": "VNM", "Włochy": "ITA",
    "Wyspy Zielonego Przylądka": "CPV",
    "ZEA": "ARE", "Zimbabwe": "ZWE",
    "Inny": "OTH",
}

# ===========================================================================
# BOUNDING BOX DLA KAŻDEGO KRAJU (dla generowania mapy podróży)
# Format: (SW_lat, SW_lon, NE_lat, NE_lon)
# Wartości obejmują kraj + sensowny margines żeby widać było kraje sąsiednie.
# Małe kraje mają większy margines (~150-200%), duże mniejszy (~20-30%).
#
# Aby dodać/edytować kraj: znajdz na openstreetmap.org granice kraju,
# zobacz bounding box i dodaj margines żeby było widać sąsiadów.
# ===========================================================================
COUNTRY_BBOX = {
    "Albania":              (38.0, 17.5, 44.3, 22.5),
    "Andora":               (41.5, -0.5, 43.7, 3.0),
    "Arabia Saudyjska":     (14.5, 32.0, 33.5, 56.5),
    "Argentyna":            (-56.0, -76.0, -20.0, -52.0),
    "Aruba":                (11.8, -71.5, 13.5, -68.0),
    "Australia":            (-45.0, 110.0, -8.0, 156.0),
    "Austria":              (45.5, 8.5, 50.5, 18.5),
    "Azerbejdżan":          (37.5, 43.5, 42.5, 52.0),
    "Belgia":               (48.5, 1.0, 53.0, 8.5),
    "Bhutan":               (25.5, 86.5, 29.5, 93.5),
    "Boliwia":              (-23.5, -71.0, -8.5, -56.5),
    "Bonaire":              (11.5, -69.0, 12.8, -67.5),
    "Bośnia i Hercegowina": (41.5, 14.5, 46.0, 21.0),
    "Botswana":             (-28.0, 17.5, -15.5, 30.5),
    "Brazylia":             (-35.0, -75.0, 7.0, -32.0),
    "Bułgaria":             (40.0, 21.0, 45.5, 30.0),
    "Chile":                (-57.0, -77.0, -17.0, -65.0),
    "Chiny":                (15.0, 70.0, 55.0, 138.0),
    "Chorwacja":            (41.5, 12.5, 47.0, 20.5),
    "Cypr":                 (33.5, 31.5, 36.5, 35.5),
    "Czarnogóra":           (40.5, 17.5, 44.5, 21.5),
    "Czechy":               (47.5, 11.0, 51.5, 19.5),
    "Dania":                (53.5, 7.0, 58.5, 16.0),
    "Dominikana":           (16.5, -73.0, 21.5, -67.0),
    "Egipt":                (20.0, 23.0, 33.5, 38.5),
    "Ekwador":              (-6.5, -83.0, 3.5, -73.5),
    "Estonia":              (56.5, 20.5, 60.5, 29.5),
    "Etiopia":              (2.0, 31.5, 16.0, 48.5),
    "Fidżi":                (-22.0, 175.0, -12.0, -176.0),
    "Filipiny":             (4.0, 116.0, 21.5, 127.5),
    "Finlandia":            (58.5, 18.5, 71.0, 32.5),
    "Francja":              (41.0, -6.0, 52.0, 10.5),
    "Grecja":               (33.5, 18.5, 42.5, 29.5),
    "Gruzja":               (40.0, 39.0, 44.0, 47.5),
    "Hiszpania":            (34.5, -10.5, 44.5, 5.5),
    "Holandia":             (49.5, 1.5, 54.5, 8.5),
    "Hongkong":             (21.5, 113.0, 23.5, 115.5),
    "Indie":                (5.0, 67.0, 36.5, 98.0),
    "Indonezja":            (-12.0, 93.0, 8.0, 142.0),
    "Irlandia":             (50.5, -11.5, 56.0, -4.5),
    "Islandia":             (62.5, -25.5, 67.5, -12.0),
    "Izrael":               (28.5, 33.0, 34.5, 37.5),
    "Jamajka":              (16.5, -79.5, 19.5, -75.5),
    "Japonia":              (24.0, 122.0, 46.5, 146.5),
    "Jordania":             (28.0, 33.5, 34.5, 40.5),
    "Kambodża":             (9.5, 100.5, 15.5, 108.5),
    "Kanada":                (40.0, -142.0, 72.0, -50.0),
    "Kenia":                (-6.0, 32.5, 6.0, 43.0),
    "Kolumbia":             (-5.5, -82.0, 14.5, -65.0),
    "Korea Południowa":     (32.0, 124.0, 39.5, 132.5),
    "Kostaryka":            (7.5, -86.5, 12.0, -82.0),
    "Kuba":                 (19.0, -85.5, 24.0, -73.5),
    "Laos":                 (12.5, 99.5, 23.5, 108.5),
    "Liechtenstein":        (46.5, 8.5, 47.8, 10.5),
    "Litwa":                (53.0, 20.0, 57.0, 27.5),
    "Łotwa":                (55.0, 20.0, 59.0, 29.0),
    "Macao":                (21.8, 112.5, 23.0, 114.5),
    "Macedonia Pn.":        (39.5, 19.5, 43.5, 24.0),
    "Madagaskar":           (-26.5, 42.0, -10.5, 51.5),
    "Malediwy":             (-2.0, 71.5, 8.0, 75.5),
    "Malezja":              (0.0, 98.0, 8.0, 120.5),
    "Malta":                (35.5, 13.5, 36.5, 15.5),
    "Maroko":               (20.5, -14.5, 36.5, 0.0),
    "Mauritius":            (-21.5, 56.5, -19.0, 58.5),
    "Meksyk":               (13.5, -119.0, 33.5, -85.0),
    "Monako":               (43.5, 7.0, 44.0, 7.8),
    "Mongolia":             (40.5, 86.5, 53.0, 121.0),
    "Namibia":              (-30.5, 10.5, -16.0, 26.0),
    "Nepal":                (25.5, 79.5, 31.5, 89.5),
    "Niemcy":               (46.5, 4.5, 55.5, 16.5),
    "Norwegia":             (57.0, 4.0, 71.5, 32.0),
    "Nowa Zelandia":        (-48.5, 165.5, -33.5, 179.5),
    "Oman":                 (15.5, 51.0, 26.5, 60.5),
    "Panama":               (6.5, -83.5, 10.5, -76.5),
    "Peru":                 (-19.5, -83.5, 0.5, -67.5),
    "Polska":               (47.0, 12.5, 56.0, 25.5),
    "Portugalia":           (35.5, -10.5, 43.5, -5.5),
    "RPA":                  (-37.0, 15.0, -21.5, 34.5),
    "Rumunia":              (42.0, 19.5, 49.0, 30.5),
    "Rwanda":               (-3.5, 27.5, -0.5, 31.5),
    "Serbia":               (41.5, 17.5, 47.5, 24.5),
    "Seszele":              (-11.0, 51.0, -2.0, 58.5),
    "Singapur":             (0.5, 102.5, 2.5, 105.5),
    "Słowacja":             (46.5, 15.5, 50.5, 24.5),
    "Słowenia":             (44.5, 12.5, 47.5, 17.5),
    "Sri Lanka":            (5.0, 78.0, 11.0, 83.5),
    "Stany Zjednoczone":    (24.0, -126.0, 50.0, -65.0),
    "Szwajcaria":           (44.5, 4.5, 49.0, 12.5),
    "Szwecja":              (54.0, 9.0, 70.0, 25.5),
    "Tajlandia":            (4.5, 96.0, 21.5, 107.5),
    "Tajwan":               (20.5, 117.5, 26.5, 124.0),
    "Tunezja":              (29.5, 6.5, 38.5, 13.5),
    "Turcja":               (34.5, 24.5, 43.5, 46.5),
    "Uganda":               (-2.5, 28.5, 5.5, 36.0),
    "Urugwaj":              (-36.5, -60.0, -29.5, -52.5),
    "W. Brytania":          (49.0, -10.5, 61.5, 3.0),
    "Węgry":                (44.5, 14.5, 49.5, 24.5),
    "Wenezuela":            (-1.5, -75.5, 13.5, -58.5),
    "Wietnam":              (7.5, 101.5, 24.0, 110.5),
    "Włochy":               (35.0, 5.5, 48.0, 19.5),
    "Wyspy Zielonego Przylądka": (13.5, -27.0, 18.5, -21.5),
    "ZEA":                  (21.5, 50.5, 27.5, 57.5),
    "Zimbabwe":             (-23.5, 24.5, -14.5, 34.5),
}

FONTS_LIST = [
    "Montserrat", "Open Sans", "Roboto", "Poppins", "Inter", "Nunito", "Lato",
    "Oswald", "Raleway", "Playfair Display", "Merriweather", "Lora",
    "Libre Baskerville", "Libre Franklin", "Marck Script", "La Belle Aurore",
    "Nanum Pen Script", "Alex Brush", "Amatic SC",
]
FONT_WEIGHTS = {
    "Montserrat": "300,400,600,700,800", "Open Sans": "300,400,600,700,800",
    "Roboto": "300,400,500,700", "Poppins": "300,400,500,600,700",
    "Inter": "300,400,500,600,700", "Nunito": "300,400,600,700",
    "Lato": "300,400,700,900", "Oswald": "300,400,500,600,700",
    "Raleway": "300,400,500,600,700", "Playfair Display": "400,500,600,700",
    "Merriweather": "300,400,700", "Lora": "400,500,600,700",
    "Libre Baskerville": "400,700", "Libre Franklin": "300,400,500,600,700",
    "Marck Script": "400", "La Belle Aurore": "400",
    "Nanum Pen Script": "400", "Alex Brush": "400", "Amatic SC": "400,700",
}
hotel_icons = {
    "Basen": "fa-person-swimming", "SPA": "fa-spa", "Siłownia": "fa-dumbbell",
    "Restauracja": "fa-utensils", "Bar": "fa-martini-glass-citrus",
    "Plaża": "fa-umbrella-beach", "Wi-Fi": "fa-wifi", "All inclusive": "fa-wine-glass",
    "Recepcja 24h": "fa-bell-concierge", "Sport": "fa-volleyball",
    "Night club": "fa-champagne-glasses", "Konferencje": "fa-people-roof",
    "Widok na morze": "fa-water",
    "Top lokalizacja": "fa-location-dot",
}
icon_map = {
    "Atrakcja": '<i class="fa-solid fa-camera-retro"></i>',
    "Zwiedzanie / Kultura": '<i class="fa-solid fa-landmark-dome"></i>',
    "Opis miejsca": '<i class="fa-solid fa-map-location-dot"></i>',
    "Opis miejsca (miasto)": '<i class="fa-solid fa-city"></i>',
    "Opis miejsca (zamek/zabytek)": '<i class="fa-solid fa-chess-rook"></i>',
    "Degustacja wina": '<i class="fa-solid fa-wine-glass"></i>',
    "Rejs stateczkiem": '<i class="fa-solid fa-sailboat"></i>',
    "Trekking / Wędrówka": '<i class="fa-solid fa-person-hiking"></i>',
    "Przygoda / Active": '<i class="fa-solid fa-compass"></i>',
    "Rejs": '<i class="fa-solid fa-anchor"></i>',
    "Plaża / Relaks": '<i class="fa-solid fa-umbrella-beach"></i>',
    "SPA / Odnowa": '<i class="fa-solid fa-spa"></i>',
    "Restauracja": '<i class="fa-solid fa-utensils"></i>',
    "Zakwaterowanie": '<i class="fa-solid fa-bed"></i>',
    "Transfer autokarem": '<i class="fa-solid fa-bus"></i>',
    "Przelot samolotem": '<i class="fa-solid fa-plane"></i>',
    "Zabawa": '<i class="fa-solid fa-champagne-glasses"></i>',
}
# ===========================================================================
# IKONY OPISU ATRAKCJI (pas ikon na dole slajdu atrakcji - Model 2)
# Operator dynamicznie dodaje ikony do atrakcji z opisem (max 22 znaki).
# 
# Aby DODAĆ nową ikonę:
#   1. Wybierz Font Awesome (free) na https://fontawesome.com/icons
#   2. Dopisz wpis poniżej: 'id': {'label': 'Nazwa PL', 'icon': 'fa-nazwa'}
#   3. 'id' = unikalny klucz (bez polskich znaków, łączniki dozwolone)
#
# UWAGA: NIE usuwaj istniejących wpisów - złamiesz dane atrakcji zapisanych
# w bazie (atrakcja straci tę ikonę przy renderowaniu).
# Aby "ukryć" ikonę z listy wyboru ale zachować w renderingu - przenieś
# wpis do końca słownika i dopisz komentarz '# nieużywana'.
# ===========================================================================
ATTR_ICONS_AVAILABLE = {
    'clock':              {'label': 'Czas trwania',     'icon': 'fa-clock'},
    'piggy-bank':         {'label': 'Cena (PLN)',       'icon': 'fa-piggy-bank'},
    'euro-sign':          {'label': 'Cena (EUR)',       'icon': 'fa-euro-sign'},
    'dollar-sign':        {'label': 'Cena (USD)',       'icon': 'fa-dollar-sign'},
    'utensils':           {'label': 'Posiłek',          'icon': 'fa-utensils'},
    'truck-pickup':       {'label': 'Pickup 4x4',       'icon': 'fa-truck-pickup'},
    'bus':                {'label': 'Wycieczka',        'icon': 'fa-bus'},
    'ship':               {'label': 'Rejs motorowy',    'icon': 'fa-ship'},
    'sailboat':           {'label': 'Rejs żaglowy',     'icon': 'fa-sailboat'},
    'water':              {'label': 'Aktywności wodne', 'icon': 'fa-water'},
    'person-paddling':    {'label': 'Kajak',            'icon': 'fa-person-paddling'},
    'compass':            {'label': 'Adventure',        'icon': 'fa-compass'},
    'person-biking':      {'label': 'Rower',            'icon': 'fa-person-biking'},
    'person-walking':     {'label': 'Spacer',           'icon': 'fa-person-walking'},
    'map-location-dot':   {'label': 'Zwiedzanie z mapą','icon': 'fa-map-location-dot'},
    'person-hiking':      {'label': 'Trekking',         'icon': 'fa-person-hiking'},
    'mountain':           {'label': 'Góry',             'icon': 'fa-mountain'},
    'person-skiing':      {'label': 'Narty',            'icon': 'fa-person-skiing'},
    'umbrella-beach':     {'label': 'Plaża',            'icon': 'fa-umbrella-beach'},
    'champagne-glasses':  {'label': 'Degustacja',       'icon': 'fa-champagne-glasses'},
    'spa':                {'label': 'SPA / Relaks',     'icon': 'fa-spa'},
    'camera':             {'label': 'Punkt widokowy',   'icon': 'fa-camera'},
    'landmark-dome':      {'label': 'Zabytek / muzeum', 'icon': 'fa-landmark-dome'},
    'tree':               {'label': 'Natura / park',    'icon': 'fa-tree'},
    'fire':               {'label': 'Ognisko / grill',  'icon': 'fa-fire'},
    'music':              {'label': 'Koncert',          'icon': 'fa-music'},
}
pl_days_map = ["Poniedziałek", "Wtorek", "Środa", "Czwartek", "Piątek", "Sobota", "Niedziela"]
# Klucze obrazów — używane przy zapisie/wczytaniu projektu JSON
IMAGE_KEYS = {
    'img_hero_t', 'img_hero_k', 'img_hero_l', 'img_map_bg', 'img_map_bg_auto',
    'logo_az', 'logo_cli', 'img_app_bg', 'img_app_screen',
    'img_brand_1', 'img_brand_2', 'img_brand_3',
    'img_va_1', 'img_va_2', 'img_va_3',
    'img_pg_1', 'img_pg_2', 'img_pg_3',
    'img_koszt_1', 'img_koszt_2', 'img_testim_main', 'img_about_clients',
    'img_k_th1', 'img_k_th2', 'img_k_th3',
}
for _i in range(20):
    IMAGE_KEYS.add(f'sek_{_i}_img')
for _i in range(50):
    IMAGE_KEYS.update({
        f'img_hotel_1_{_i}', f'img_hotel_1b_{_i}',
        f'img_hotel_2_{_i}', f'img_hotel_3_{_i}',
        f'img_d_{_i}', f'ah_{_i}', f'at1_{_i}', f'at2_{_i}', f'at3_{_i}',
        f'pimg1_{_i}', f'pimg2_{_i}', f'pimg3_{_i}', f'pimg4_{_i}',
        f'testim_img_{_i}', f't_img_{_i}',
        f'kimg_{_i}',
    })
EXCLUDE_EXPORT_KEYS = {
    'client_mode', 'scroll_target', 'last_page',
    'show_link_info', 'ready_export_html', 'auto_map_points',
    # Klucze przycisków i widgetów Streamlit które nigdy nie trafiają do JSON
    'pa_add_place_btn', 'pa_add_attr_btn',
    'main_nav_radio', 'btn_add_hotel_main', 'manual_save_btn',
    'btn_add_attraction_main', 'attr_add_btn', 'attr_select',
    'nav_top_radio', 'nav_bot_radio',
    # Klucze wewnętrzne sesji — nie zapisujemy do localStorage
    '_ls_loaded', '_session_id', '_ls_restore', '_attr_focused',
}
defaults = {
    'country_name': '-- Wybierz kraj --', 'country_code': '',
    'font_h1': 'Montserrat', 'font_h2': 'Montserrat', 'font_sub': 'Montserrat',
    'font_text': 'Open Sans', 'font_metric': 'Montserrat',
    'color_h1': '#003366', 'color_h2': '#003366', 'color_sub': '#FF6600',
    'color_accent': '#FF6600', 'color_text': '#333333', 'color_metric': '#003366',
    'font_size_h1': 48, 'font_size_h2': 36, 'font_size_sub': 26,
    'font_size_text': 14, 'font_size_metric': 16,
    't_main': 'NAZWA PROJEKTU', 't_sub': 'PODTYTUŁ PROJEKTU',
    't_klient': 'NAZWA KLIENTA', 't_kierunek': 'KIERUNEK',
    't_date': 'DD.MM-DD.MM.RRRR', 't_pax': '0', 't_hotel': 'WPISZ STANDARD',
    't_trans': 'WPISZ TRANSPORT',
    'hide_logo_cli': False,
    'k_hide': False, 'k_overline': 'NASZ KIERUNEK', 'k_main': 'NAZWA KIERUNKU',
    'k_sub': 'PODTYTUŁ KIERUNKU', 'k_opis': 'Opisz tutaj piękno kierunku...',
    'k_icon_stolica_show': True, 'k_icon_stolica_val': 'Tirana',
    'k_icon_waluta_show': True, 'k_icon_waluta_val': 'lek albański',
    'k_icon_strefa_show': True, 'k_icon_strefa_val': 'brak',
    'k_icon_klimat_show': True, 'k_icon_klimat_val': 'śródziemnomorski',
    'k_icon_temp_show': True, 'k_icon_temp_val': '20-25°C',
    'k_icon_szczepienia_show': False, 'k_icon_szczepienia_val': 'nie wymagane',
    'k_icon_mieszkancy_show': False, 'k_icon_mieszkancy_val': '2,8 mln',
    'k_highlights': 'Riwiera Albańska\nZabytki UNESCO\nAutentyczna kuchnia',
    'l_hide': False, 'l_przesiadka': False, 'l_port': 'Monachium (MUC)',
    'l_czas': '3h 20 min', 'l_overline': 'PRZELOT', 'l_main': 'JAK LECIMY?',
    'l_sub': 'NASZA PROPOZYCJA PRZELOTU',
    'l_desc': 'Komfortowy przelot liniami PLL LOT.',
    'm_route': 'Warszawa (WAW) - Podgorica (TGD)', 'm_luggage': '23kg rejestrowany',
    'f1': 'LO 585, 17MAY, WAW-TGD, 14:25 - 16:25',
    'f2': 'LO 586, 21MAY, TGD-WAW, 17:15 - 19:05', 'f3': '', 'f4': '',
    # === SLAJD "JAK JEDZIEMY?" (alternatywa dla "Jak lecimy?") ===
    'jaj_hide': False,
    'jaj_overline': 'DOJAZD',
    'jaj_main': 'JAK JEDZIEMY?',
    'jaj_sub': 'PROPOZYCJA DOJAZDU',
    'jaj_route': 'Warszawa - Kraków',
    'jaj_desc': 'Komfortowy dojazd autokarem klasy premium.',
    'jaj_extra': '',
    'jaj_dist_title': 'ODLEGŁOŚCI I CZAS DOJAZDU',
    'num_jaj_dist_pairs': 0,
    'map_hide': False, 'map_overline': 'TRASA WYJAZDU',
    'map_title': 'ZARYS\nPODRÓŻY', 'map_subtitle': 'Kluczowe punkty programu',
    'map_desc': 'Zapraszamy do zapoznania się z poglądową mapą naszego wyjazdu.',
    'num_map_points': 3,
    'map_pt_name_0': 'Warszawa', 'map_conn_0': 'Przelot (Linia przerywana + Samolot)',
    'map_pt_sym_0': True, 'map_pt_x_0': 15, 'map_pt_y_0': 15,
    'map_pt_name_1': 'Podgorica', 'map_conn_1': 'Przejazd (Linia ciągła)',
    'map_pt_sym_1': False,
    'map_pt_name_2': 'Kotor', 'map_conn_2': 'Brak', 'map_pt_sym_2': False,
    'map_dist_title': 'ODLEGŁOŚCI I CZAS DOJAZDU',
    'num_dist_pairs': 0,
    'ors_api_key': '',
    'num_hotels': 1,
    'h_hide_0': False, 'h_overline_0': 'ZAKWATEROWANIE',
    'h_title_0': 'NAZWA HOTELU 5*',
    'h_subtitle_0': 'Komfort i elegancja na najwyższym poziomie',
    'h_url_0': 'www.przykładowy-hotel.com', 'h_booking_0': '8.9',
    'h_amenities_0': ["Basen", "SPA", "Wi-Fi", "Restauracja", "Plaża"],
    'h_text_0': 'Zapewniamy zakwaterowanie w starannie wyselekcjonowanym hotelu.',
    'h_advantages_0': 'Położenie tuż przy prywatnej plaży',
    'prg_hide': False, 'num_days': 4, 'num_places': 0, 'num_attr': 0,
    'koszt_hide_1': False, 'koszt_hide_2': False, 'koszt_title': 'KOSZTORYS',
    'koszt_h1_title': 'KOSZTORYS',
    'koszt_pax': 'liczba uczestnikow', 'koszt_price': '10.000 zł / os.',
    'koszt_hotel': 'Nazwa i standard hotelu',
    'koszt_dbl': '12', 'koszt_sgl': '1',
    'koszt_zawiera_1': 'Wybierz z listy auto-uzupełniania',
    'koszt_zawiera_2': '', 'koszt_nie_zawiera': 'Napiwki\nWydatki osobiste\nAtrakcje wymienione jako opcje',
    'koszt_opcje': '',
    'app_hide': False, 'app_overline': 'KOMUNIKACJA I COMPLIANCE',
    'app_title': 'APLIKACJA\nI ZARZĄDZANIE DANYMI',
    'app_subtitle': 'Administracja danych uczestników i komunikacja\n po stronie Activezone',
    'app_features': ('Aplikacja w spersonalizowanej szacie graficznej — pełny branding klienta: logo, kolorystyka, materiały wizerunkowe\n'
                 'Pełne informacje i komunikacja z uczestnikami przez aplikację — program szczegółowy, opisy atrakcji, hotele, kontakty, SMS, powiadomienia push, listy obecności, skanowanie kodów QR\n'
                 'Szyfrowane zbieranie danych osobowych uczestników zgodnie z RODO — dane dietetyczne, alergie, informacje paszportowe i ubezpieczeniowe\n'
                 'Dokumenty imienne w aplikacji — bilet, karta pokładowa, voucher hotelowy, polisa, wiza — cyfrowo, zawsze dostępne\n'
                 'Grywalizacja i ankiety — konkursy, quizy oraz ankiety wewnętrzne zwiększające zaangażowanie uczestników\n'
                 'Badanie satysfakcji NPS — raport dla zarządu i działu HR\n'
                 'Wsparcie celów ESG, materiały cyfrowe zamiast druku'),
    'brand_hide': False, 'brand_overline': 'IDENTYFIKACJA',
    'brand_title': 'MATERIAŁY\nBRANDINGOWE',
    'brand_subtitle': 'Komunikacja przed, w trakcie i po wyjeździe',
    'brand_features': '',
    'brand_groups_font': 'Inter',
    'brand_g1_title': 'PRESTIŻOWY START',
    'brand_g1_items': (
        'Budowanie zaangażowania: proces komunikacji przedwyjazdowej poprzez cykl dedykowanych wiadomości i konkursów tematycznych\n'
        'Dedykowana aplikacja telefoniczna wraz z formularzem zbierającym dane\n'
        'Strona www wyjazdu z informacjami o programie i atrakcjach'
    ),
    'brand_g2_title': 'LOGISTYKA & KOMUNIKACJA',
    'brand_g2_items': (
        'Komunikacja: SMS, e-mail, push w aplikacji przed i w trakcie wyjazdu\n'
        'Dedykowane stanowisko na lotnisku z logo\n'
        'Pakiet powitalny: zawieszka imienna na bagaż, etui z biletam i materiałami'
    ),
    'brand_g3_title': 'STANDARD VIP & PERSONALIZACJA',
    'brand_g3_items': (
        'Dedykowane menu – karty dań z tłumaczeniem na język polski\n'
        'Zarządzanie preferencjami dietetycznymi: uwzględnienie diet i alergii uczestników\n'
        'Personalizowany list powitalny w hotelu\n'
        'Lokalne upomninki (pillow gifts) z opisem'
       
    ),
    'brand_footer': 'Wszystkie materiały logistyczne i upominki zostaną opatrzone Państwa logotypem w standardzie spójnym z identyfikacją wizualną wyjazdu.',
    'va_hide': False, 'va_overline': 'SPRAWNA ORGANIZACJA',
    'va_subtitle': 'Sprawna organizacja i wygoda',
    'va_text': ('Nowatorski system do zarządzania grupami. Składa się z aplikacji, identyfikatorów '
                'z chipem, naklejek z chipem lub kodem z danymi uczestników (np. do naklejenia na walizkę). '
                'System może zawierać dane uczestników, m.in.: imię i nazwisko, numer pokoju, wskazania '
                'dietetyczne, nr telefonu, przydział do grup. Dane z chipa są czytane przy użyciu systemu '
                'NFC przez aplikację telefonu opiekunów grupy. Po zbliżeniu telefonu komórkowego do '
                'bransoletki uczestnika lub oznakowanej walizki aplikacja odnotowuje jego obecność. '
                'Kod na walizce pozwala więc błyskawicznie odnaleźć jej właściciela lub odnotować '
                'zapakowanie walizki do autokaru. Wirtualny asystent umożliwia także łatwy kontakt '
                'z uczestnikami: wysyłkę SMS-ów, ankiety, formularze, czat, konkursy w aplikacji.'),
    'pg_hide': False, 'pg_overline': 'PILLOW GIFTS',
    'pg_title': 'PILLOW GIFTS',
    'pg_subtitle': 'Aby wspólne chwile zatrzymać na dłużej',
    'pg_text': ('Upominki pełnią ważną rolę w budowaniu relacji biznesowych. '
                'Wręczanie podarunków jest podziękowaniem za współpracę, ale także ułatwia '
                'poznanie partnera biznesowego. Przy wręczaniu upominku ważna nie jest jego '
                'wartość, ale pamięć o drugiej stronie i włożenie wysiłku w wybranie prezentu. '
                'Każdy pillow gift będzie miał elegancką fiszkę z opisem i Państwa logo. '
                'Wśród upominków związanych z miejscem wyjazdu lub podróżowaniem proponujemy do wyboru:'),
    'pg_features': '',
    'sek_0_title': 'ZAKWATEROWANIE', 'sek_0_sub': 'NASZE HOTELE', 'sek_0_hide': False,
    'sek_1_title': 'PROGRAM', 'sek_1_sub': 'ATRAKCJE I MIEJSCA', 'sek_1_hide': False,
    'sek_2_title': 'REKOMENDACJE', 'sek_2_sub': 'CO O NAS MÓWIĄ', 'sek_2_hide': False,
    'sek_3_title': 'PROGRAM', 'sek_3_sub': 'NASZ PLAN WYJAZDU', 'sek_3_hide': False,
    'testim_hide': False, 'testim_overline': 'REKOMENDACJE',
    'testim_title': 'CO O NAS\nMÓWIĄ?',
    'testim_subtitle': '100% NASZYCH KLIENTÓW JEST CAŁKOWICIE ZADOWOLONYCH Z NASZYCH USŁUG.',
    'testim_count': 3,
    'testim_head_0': 'PROJEKT INCENTIVE W DUBAJU', 'testim_quote_0': 'Pełen profesjonalizm.',
    'testim_author_0': 'Anna Kowalska', 'testim_role_0': 'Dyrektor Marketingu',
    'testim_head_1': 'WYJAZD INTEGRACYJNY', 'testim_quote_1': 'Niezwykłe zaangażowanie.',
    'testim_author_1': 'Piotr Nowak', 'testim_role_1': 'CEO',
    'testim_head_2': 'NAGRODA DLA KLIENTÓW',
    'testim_quote_2': 'Współpraca na najwyższym poziomie.',
    'testim_author_2': 'Marta Wiśniewska', 'testim_role_2': 'Head of Sales',
    'about_hide': False,
    'about_overline': 'NASZ ZESPÓŁ',
    'about_title': 'PARTNERZY\nZARZĄDZAJĄCY',
    'about_sub': 'ZESPÓŁ ACTIVEZONE',
    'about_desc': (
        'Activezone to agencja MICE z ponad 20-letnim doświadczeniem na 5 kontynentach. '
        'Łączymy wieloletnią ekspertyzę z autorską aplikacją mobilną, automatyzacją procesów '
        'i pełnym wsparciem dla działów zakupów — od kalkulacji śladu węglowego po dokumentację '
        'compliance i raportowanie ESG zgodne z dyrektywą CSRD. Jako agencja zrzeszona w SOIT '
        'uczestniczymy w branżowych szkoleniach ESG oraz programie kompetencyjnym Google AI '
        '"Umiejętności Jutra".'
    ),
    'about_panel_title': 'NASZE WARTOŚCI', 'about_panel_text': 'Bezpieczeństwo\nProfesjonalizm',
    'team_count': 2, 'p_start_dt': date(2026, 10, 1),
    # === NOWE POLA: Joanna ===
    'about_p1_name': 'Joanna Jabłońska',
    'about_p1_role': 'Partner | Członek Zarządu | Dyrektor Zarządzająca',
    'about_p1_bio': (
        'Współzałożycielka i Dyrektor Zarządzająca Activezone. Doktor Nauk (Akademia Wychowania '
        'Fizycznego). Ponad 20 lat doświadczenia w branży MICE — osobiście zrealizowała projekty '
        'na 5 kontynentach, od czarterów samolotów dla międzynarodowych korporacji po kameralne '
        'wyjazdy VIP. W minionych kadencjach pełniła funkcję Wiceprezesa, a następnie Członka '
        'Komisji Etyki Stowarzyszenia Organizatorów Incentive Travel (SOIT). Autorka publikacji '
        'w prasie branżowej (OOH Magazine, Meeting Planner, Think MICE).'
    ),
    'about_p1_bullets': (
        '20+ lat doświadczenia w MICE\n'
        'Wiceprezes SOIT (kadencja 2018-2019), Komisja Etyki SOIT (2020-2021)\n'
        'Doktor Nauk (Akademia Wychowania Fizycznego)'
    ),
    'about_p1_quote': (
        'Incentive to nie koszt, ale inwestycja w ludzką stronę biznesu '
        '— mierzalna, praktyczna, ale też pełna empatii.'
    ),
    'about_p1_quote_source': 'Think MICE, październik 2025',
    # === NOWE POLA: Marcin ===
    'about_p2_name': 'Marcin Łukaszewicz',
    'about_p2_role': 'Partner | Członek Zarządu | Dyrektor Sprzedaży i Marketingu',
    'about_p2_bio': (
        'Współzałożyciel i Dyrektor Sprzedaży i Marketingu Activezone. Ponad 20 lat '
        'doświadczenia w branży MICE — od 2003 roku kreuje strategiczne programy incentive '
        'dla klientów korporacyjnych. Doświadczenie sportu wyczynowego — jako zawodnik '
        'windsurfingu w klasie olimpijskiej oraz trener kadry — ukształtowało w nim precyzję '
        'operacyjną, zarządzanie ryzykiem i umiejętność podejmowania decyzji pod presją. '
        'Odpowiada za strategię produktową i inżynierię finansową projektów B2B. Jako wykładowca '
        'SOIT współtworzy program Certyfikowany Pilot Incentive Travel (CPIT) — uczy '
        'rachunkowości projektów MICE, optymalizacji VAT-marża i compliance budżetowego.'
    ),
    'about_p2_bullets': (
        '20+ lat doświadczenia w MICE\n'
        'Wykładowca SOIT (CPIT) — compliance i rozliczenia MICE\n'
        'Cytowany w prasie branżowej (OOH Magazine, Meeting Planner, Puls Biznesu, Think MICE)'
    ),
    'about_p2_quote': (
        'Prawdziwą wartością wyjazdu incentive jest możliwość skrócenia dystansu z resztą '
        'zespołu. Podczas wyjazdu buduje się kapitał zaufania, który procentuje przez '
        'kolejne miesiące pracy zdalnej.'
    ),
    'about_p2_quote_source': 'OOH Magazine',
    # === POLE METRYK O NAS (8 pól) ===
    'about_m1_number': '724',         'about_m1_value': '',
    # === SLAJD ESG ===
    'esg_hide': False,
    'esg_overline': 'ODPOWIEDZIALNOŚĆ',
    'esg_title': 'ODPOWIEDZIALNY\nPARTNER ESG',
    'esg_subtitle': 'Zgodność z wymaganiami procurement i raportowania ESG',
    'esg_intro': (
        'Standardy ESG są fundamentem naszego modelu operacyjnego. '
        'Działamy zgodnie z najwyższymi normami środowiskowymi, społecznymi '
        'i etycznymi — pomagamy działom zakupów wypełnić wymagania compliance '
        'i wesprzeć raportowanie ESG bez dodatkowego nakładu pracy po Państwa stronie.'
    ),
    # ENVIRONMENTAL
    'esg_e_title': 'ENVIRONMENTAL',
    'esg_e_sub': 'Środowisko',
    'esg_e_items': (
        'Hotele z certyfikatami ekologicznymi (Green Key, BREEAM)\n'
        'Optymalizacja tras i niskoemisyjne środki transportu\n'
        'Zero-waste: cyfrowa logistyka przez aplikację Activezone'
    ),
    # SOCIAL
    'esg_s_title': 'SOCIAL',
    'esg_s_sub': 'Społeczność',
    'esg_s_items': (
        'Współpraca z lokalnymi dostawcami, przewodnikami i rzemieślnikami\n'
        'Inkluzywność: równy dostęp niezależnie od wieku i sprawności\n'
        'Programy CSR: warsztaty z fundacjami, projekty ekosystemowe'
    ),
    # GOVERNANCE
    'esg_g_title': 'GOVERNANCE',
    'esg_g_sub': 'Ład korporacyjny',
    'esg_g_items': (
        'Licencja organizatora turystyki nr 724\n'
        'Gwarancja Compensa >1 000 000 PLN + polisa OC 500 000 PLN\n'
        'Etyczny łańcuch dostaw i pełna transparentność budżetów'
    ),
    # KEY METRICS - 8 pól (4x2). Pola puste = nie renderują się.
    # Każde pole: number (liczba/symbol, opcjonalne), value (główna wartość), label (etykieta)
    # ESG - 6 pól (po 2 na każdy obszar E/S/G)
    'esg_m1_number': '',           'esg_m1_value': 'Green Key', 'esg_m1_label': 'CERTYFIKAT BAZY NOCLEGOWEJ',
    'esg_m2_number': '',           'esg_m2_value': 'BREEAM',    'esg_m2_label': 'CERTYFIKAT BAZY NOCLEGOWEJ',
    'esg_m3_number': '100%',       'esg_m3_value': '',          'esg_m3_label': 'LOKALNI DOSTAWCY I PRZEWODNICY',
    'esg_m4_number': '',           'esg_m4_value': 'Programy CSR', 'esg_m4_label': 'DLA FUNDACJI I EKOSYSTEMÓW',
    'esg_m5_number': '1 000 000', 'esg_m5_value': 'PLN',       'esg_m5_label': 'GWARANCJA UBEZPIECZENIOWA',
    'esg_m6_number': '500 000',   'esg_m6_value': 'PLN',       'esg_m6_label': 'POLISA OC',
    # === CYTAT ESG z Think MICE ===
    'esg_quote': (
        'Agencje zrzeszone w SOIT potrafią przygotować oferty wyjazdów motywacyjnych '
        'z naciskiem na minimalizację śladu węglowego, wodnego oraz wspieranie lokalnych '
        'społeczności odwiedzanych destynacji.'
    ),
    'esg_quote_source': 'Think MICE',
}
# ---------------------------------------------------------------------------
# NARZĘDZIA OGÓLNE
# ---------------------------------------------------------------------------
def clean_str(val, default=""):
    if val is None or str(val).strip() == "None":
        return default
    return str(val)
def create_slug(text):
    if not text:
        return "szablon"
    text = re.sub(r'<[^>]+>', '', str(text))
    text = text.lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')
def parse_date_and_days():
    d_str = st.session_state.get('t_date', '').strip()
    m1 = re.search(r'(\d{1,2})\s*-\s*(\d{1,2})\.(\d{1,2})\.(\d{4})', d_str)
    m2 = re.search(r'^(\d{1,2})\.(\d{1,2})\s*-\s*(\d{1,2})\.(\d{1,2})\.(\d{4})$', d_str)
    m3 = re.search(r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$', d_str)
    try:
        if m1:
            s_dt = date(int(m1.group(4)), int(m1.group(3)), int(m1.group(1)))
            st.session_state['num_days'] = (
                date(int(m1.group(4)), int(m1.group(3)), int(m1.group(2))) - s_dt
            ).days + 1
            st.session_state['p_start_dt'] = s_dt
        elif m2:
            s_dt = date(int(m2.group(5)), int(m2.group(2)), int(m2.group(1)))
            st.session_state['num_days'] = (
                date(int(m2.group(5)), int(m2.group(4)), int(m2.group(3))) - s_dt
            ).days + 1
            st.session_state['p_start_dt'] = s_dt
        elif m3:
            s_dt = date(int(m3.group(3)), int(m3.group(2)), int(m3.group(1)))
            st.session_state['num_days'] = 1
            st.session_state['p_start_dt'] = s_dt
    except Exception:
        pass
_COLOR_KEYS = {'color_h1', 'color_h2', 'color_sub', 'color_accent', 'color_text', 'color_metric'}
_SIZE_KEYS = {'font_size_h1', 'font_size_h2', 'font_size_sub', 'font_size_text', 'font_size_metric'}
def load_project_data(project_data: dict):
    """
    Wczytuje dane do session_state — TYLKO dla kluczy które jeszcze
    nie istnieją. Po pierwszym wczytaniu (przy starcie sesji) session_state
    staje się samodzielnym źródłem prawdy. Widgety zachowują swój stan
    przez stabilne klucze, a baza służy wyłącznie do persystencji.
    Specjalny przypadek: gdy klucz JUŻ istnieje w session_state z None,
    a w bazie jest poprawna wartość — wczytujemy (bo None oznacza "brak
    inicjalizacji", nie "świadomy wybór użytkownika").
    """
    # Klucze zarezerwowane dla Streamlit (przyciski/widżety) — nie wczytujemy
    forbidden_keys = {
        'manual_save_btn', 'attr_add_btn', 'nav_top_radio', 'nav_bot_radio',
        'btn_add_attraction_main', 'last_page', 'up_export',
        '_data_loaded_once', '_debug_loaded',
    }
    forbidden_prefixes = (
        'attrnav_', 'attrup_', 'attrdn_', 'attrdel_',
        'btn_', 'up_', 'dl_',
    )
    for k, v in project_data.items():
        # 1. Pomijamy klucze przycisków i kontrolek Streamlit
        if k in forbidden_keys:
            continue
        if any(k.startswith(p) for p in forbidden_prefixes):
            continue
        # 2. None w bazie nie nadpisuje niczego
        if v is None:
            continue
        # 3. KLUCZOWA ZASADA: wczytujemy TYLKO jeśli klucza jeszcze nie ma
        # w session_state. Jeśli widget już go ustawił — zostawiamy w spokoju.
        # Wyjątek: jeśli klucz istnieje ale ma wartość None, traktujemy to
        # jak brak inicjalizacji.
        current = st.session_state.get(k, '__MISSING__')
        if current != '__MISSING__' and current is not None:
            continue
        # 4. Specjalistyczne typy
        if k in IMAGE_KEYS and isinstance(v, str):
            # Jeśli to URL (Supabase Storage) - zapisujemy jako string
            if v.startswith('http://') or v.startswith('https://') or v.startswith('data:'):
                st.session_state[k] = v
            else:
                # Stara wersja: base64-encoded bytes
                try:
                    st.session_state[k] = base64.b64decode(v)
                except Exception:
                    st.session_state[k] = v
        elif k == 'p_start_dt' and isinstance(v, str):
            try:
                st.session_state[k] = date.fromisoformat(v)
            except Exception:
                pass
        else:
            st.session_state[k] = v
def get_project_filename():
    d_str = st.session_state.get('t_date', '')
    yy, mm = "XX", "XX"
    m_date = re.search(r'\.(\d{1,2})\.(\d{4})', d_str)
    if m_date:
        mm = m_date.group(1).zfill(2)
        yy = m_date.group(2)[-2:]
    cc = st.session_state.get('country_code', 'OTH')
    cli = str(st.session_state.get('t_klient', 'KLI')).strip()[:3].upper() or "KLI"
    tit = re.sub(r'[^A-Za-z0-9_-]', '',
                 str(st.session_state.get('t_main', 'OFERTA')).replace(' ', '_'))
    return f"{yy}-{mm}-{cc}-{cli}-{tit}.json"
def auto_generate_kosztorys():
    s = st.session_state
    
    # === CZĘŚĆ 1 (slajd 1) ===
    part1 = []
    route = get_data('m_route', '')
    luggage = get_data('m_luggage', '')
    if route:
        if luggage:
            part1.append(f"Przelot samolotem na trasie {route}, bagaż {luggage}")
        else:
            part1.append(f"Przelot samolotem na trasie {route}")
    part1 += [
        "Zakwaterowanie",
        "Wyżywienie wg programu",
        "Ubezpieczenie",
        "Transfery z/na lotniska",
        "Transfery na miejscu",
        "Woda podczas wycieczek i transferów (1 but./os.)",
        "Opieka profesjonalnego tour leadera Activezone",
    ]
    # Atrakcje niezhide'owane (z prefiksem "Atrakcja: ")
    for i in range(get_data('num_attr', 0)):
        if not get_data(f'ahide_{i}', False):
            name = str(get_data(f'amain_{i}', '')).strip()
            opt_label = str(get_data(f'aopt_label_{i}', '') or '').strip()
            if name:
                if opt_label:
                    part1.append(f"Atrakcja: {name} ({opt_label})")
                else:
                    part1.append(f"Atrakcja: {name}")
    
    # === CZĘŚĆ 2 (slajd 2) ===
    part2 = []
    # Wszystkie punkty z grup brandingu (bez tytułów grup)
    for _items_key in ('brand_g1_items', 'brand_g2_items', 'brand_g3_items'):
        for _line in str(get_data(_items_key, '') or '').split('\n'):
            _line = _line.strip()
            if _line:
                part2.append(_line)
    # Pillow gifts (zawsze)
    part2.append("Pillow gift dla każdego uczestnika na przywitanie")
    # Opłaty i VAT
    part2 += [
        "Obowiązkowa opłata na fundusze TFP i TFG",
        "VAT",
    ]
    
    # Zapisz do session_state
    s['koszt_zawiera_1'] = "\n".join(part1)
    s['koszt_zawiera_2'] = "\n".join(part2)
    s['koszt_nie_zawiera'] = "Napiwki\nWydatki osobiste\nAtrakcje wymienione jako opcje"
@st.cache_data
def build_day_options(start_dt: date, num_days: int) -> list:
    options = ["Brak przypisania"]
    for d in range(num_days):
        curr_date = start_dt + timedelta(days=d)
        options.append(
            f"Dzień {d+1} ({curr_date.strftime('%d.%m.%Y')} - {pl_days_map[curr_date.weekday()]})"
        )
    return options
# ---------------------------------------------------------------------------
# OBSŁUGA OBRAZÓW
# ---------------------------------------------------------------------------
@st.cache_data(max_entries=50)
def optimize_logo(raw_bytes, max_dim=600):
    if not raw_bytes:
        return None
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass
            resample = getattr(Image, 'Resampling', Image).LANCZOS
            img.thumbnail((max_dim, max_dim), resample)
            buf = io.BytesIO()
            img.save(buf, format="PNG", optimize=True)
            return buf.getvalue()
    except Exception:
        return raw_bytes
@st.cache_data(max_entries=50)
def optimize_img(raw_bytes, max_dim=1000):
    if not raw_bytes:
        return None
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass
            if img.mode in ("RGBA", "P"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "RGBA":
                    bg.paste(img, mask=img.split()[3])
                else:
                    bg.paste(img)
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")
            resample = getattr(Image, 'Resampling', Image).LANCZOS
            img.thumbnail((max_dim, max_dim), resample)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=80, optimize=True)
            return buf.getvalue()
    except Exception:
        return None
@st.cache_data(max_entries=200)
def get_b64_cached(raw_bytes, ratio):
    if not raw_bytes:
        return None
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass
            w, h = img.size
            tw = h * ratio[0] / ratio[1]
            if w > tw:
                left = (w - tw) / 2
                cropped = img.crop((left, 0, left + tw, h))
            else:
                th = w * ratio[1] / ratio[0]
                top = (h - th) / 2
                cropped = img.crop((0, top, w, top + th))
            max_w = 400 if ratio == (1, 1) else 800
            if cropped.size[0] > max_w:
                target_h = int(max_w * (ratio[1] / ratio[0]))
                resample = getattr(Image, 'Resampling', Image).LANCZOS
                resized = cropped.resize((max_w, target_h), resample)
                cropped.close()
                cropped = resized
            buf = io.BytesIO()
            cropped.save(buf, format="JPEG", quality=75, optimize=True)
            cropped.close()
            return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None

def get_b64(key: str, ratio: tuple = (4, 5)) -> str | None:
    """Zwraca gotowy src dla <img>: URL Supabase lub data URI z base64."""
    val = st.session_state.get(key)
    if not val:
        return None
    
    # URL Supabase — zwracamy bezpośrednio
    if isinstance(val, str) and val.startswith('http'):
        return val
        
    # Base64 string z bazy — wracamy bez prefiksu (już jest base64)
    if isinstance(val, str):
        return f"data:image/jpeg;base64,{val}"
        
    # Bajty — konwersja przez cache
    if isinstance(val, bytes):
        cached = get_b64_cached(val, ratio)
        return f"data:image/jpeg;base64,{cached}" if cached else None
            
    return None
# ---------------------------------------------------------------------------
# MAPY OSM
# ---------------------------------------------------------------------------
MAX_ZOOM_RECURSION_DEPTH = 8
@st.cache_data(max_entries=200)
def get_tile_bytes(z, x, y):
    # OpenStreetMap standard - klasyczne kolorowe kafelki z żywymi kolorami:
    # zielone tereny, niebieskie wody, wyraźne drogi i nazwy miast.
    # Alternatywy gdyby kiedyś:
    #   - voyager (pastelowy) - basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png
    #   - light_all (szary) - basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png
    #   - dark_all (ciemny) - basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png
    url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'ActivezoneMap/1.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.read()
    except Exception:
        return None
@st.cache_data(max_entries=200, show_spinner=False)
def geocode_place(name, country=None):
    if not name or not str(name).strip():
        return None, None
    try:
        query = str(name).strip()
        if country:
            query = f"{query}, {country}"
        params = urllib.parse.urlencode({'q': query, 'format': 'json', 'limit': 1})
        url = f"https://nominatim.openstreetmap.org/search?{params}"
        req = urllib.request.Request(url, headers={'User-Agent': 'ActivezoneOfferBuilder/1.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception:
        pass
    return None, None
def get_road_distance(place_a: str, place_b: str, ors_api_key: str = '', country: str = ''):
    """
    Zwraca (dystans_km, czas_min, komunikat) dla trasy A→B.
    Próbuje kolejno: Google Maps → ORS → Haversine fallback.
    Zwraca (None, None, opis_błędu) przy całkowitym niepowodzeniu.
    """
    if not place_a.strip() or not place_b.strip():
        return None, None, "Podaj obie nazwy miejscowości."
    # Próba z krajem (jeśli podany)
    lat_a, lon_a = geocode_place(place_a.strip(), country)
    lat_b, lon_b = geocode_place(place_b.strip(), country)
    # Fallback: bez kraju (gdy nie znaleziono z krajem lub kraj to placeholder)
    if lat_a is None:
        lat_a, lon_a = geocode_place(place_a.strip())
    if lat_b is None:
        lat_b, lon_b = geocode_place(place_b.strip())
    if None in (lat_a, lon_a, lat_b, lon_b):
        missing = []
        if lat_a is None: missing.append(place_a)
        if lat_b is None: missing.append(place_b)
        return None, None, f"Nie znaleziono lokalizacji: {', '.join(missing)}. Sprawdź pisownię."
    # 1. Próba Google Maps Distance Matrix (obsługuje cały świat)
    google_key = st.secrets.get('google', {}).get('maps_api_key') if hasattr(st, 'secrets') else None
    if google_key:
        try:
            origin = f"{lat_a},{lon_a}"
            dest = f"{lat_b},{lon_b}"
            url = f"https://maps.googleapis.com/maps/api/distancematrix/json?origins={origin}&destinations={dest}&key={google_key}"
            
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            
            if data.get('status') == 'OK' and data.get('rows'):
                element = data['rows'][0]['elements'][0]
                if element.get('status') == 'OK':
                    dist_km = int(round(element['distance']['value'] / 1000, 0))
                    time_min = int(round(element['duration']['value'] / 60, 0))
                    return dist_km, time_min, None
                else:
                    google_error = element.get('status', 'Unknown error')
            else:
                google_error = data.get('status', 'Unknown error')
        except Exception as e:
            google_error = str(e)
    else:
        google_error = "Brak klucza Google Maps"
    # 2. Próba ORS (Europa głównie)
    if ors_api_key:
        try:
            url = 'https://api.openrouteservice.org/v2/directions/driving-car'
            body = json.dumps({'coordinates': [[lon_a, lat_a], [lon_b, lat_b]]})
            req = urllib.request.Request(
                url,
                data=body.encode('utf-8'),
                headers={
                    'Authorization': ors_api_key,
                    'Content-Type': 'application/json',
                },
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
            if 'routes' in data and data['routes']:
                summary = data['routes'][0]['summary']
                dist_km = int(round(summary['distance'] / 1000, 0))
                time_min = int(round(summary['duration'] / 60, 0))
                return dist_km, time_min, None
            elif 'error' in data:
                ors_error = data['error'].get('message', str(data['error']))
            else:
                ors_error = "Nieznany błąd ORS"
        except Exception as e:
            ors_error = str(e)
    else:
        ors_error = "Brak klucza ORS API"
    # 3. Fallback: haversine (linia prosta) z przybliżeniem drogowym *1.3
    try:
        import math as _math
        R = 6371.0
        φ1, φ2 = _math.radians(lat_a), _math.radians(lat_b)
        Δφ = _math.radians(lat_b - lat_a)
        Δλ = _math.radians(lon_b - lon_a)
        a = _math.sin(Δφ/2)**2 + _math.cos(φ1)*_math.cos(φ2)*_math.sin(Δλ/2)**2
        straight_km = R * 2 * _math.atan2(_math.sqrt(a), _math.sqrt(1-a))
        road_km = int(round(straight_km * 1.3, 0))
        time_min = int(round(road_km / 60 * 60, 0))  # Średnia 60 km/h
        msg = f"Szacunek (linia prosta ×1.3). Google: {google_error}, ORS: {ors_error}"
        return road_km, time_min, msg
    except Exception as e2:
        return None, None, f"Google: {google_error} | ORS: {ors_error} | Haversine: {e2}"
def format_duration(minutes: int) -> str:
    """Formatuje minuty jako 'X h Y min' lub 'Y min'."""
    if minutes is None:
        return '—'
    h = minutes // 60
    m = minutes % 60
    if h > 0 and m > 0:
        return f'{h} h {m} min'
    elif h > 0:
        return f'{h} h'
    return f'{m} min'
@st.cache_data(max_entries=20, show_spinner=False)
def generate_map_data(points, _depth=0):
    zoom = 6  # wartość domyślna; nadpisywana niżej z bbox kraju lub punktów
    if not points:
        return None, []
    geo_pts = [p for p in points if not p.get('symbolic')]
    if not geo_pts:
        final_points = [
            {'name': p['name'], 'x': p['x'], 'y': p['y'], 'conn': p['conn']}
            for p in points
        ]
        return None, final_points

    # === AUTO-ZOOM: priorytet 1 = bbox kraju docelowego (z COUNTRY_BBOX) ===
    # Jeśli kraj jest w słowniku COUNTRY_BBOX, używamy jego granic +
    # sensownego marginesu. Pokazuje cały kraj + kraje sąsiednie.
    # Niezależne od wpisanych punktów - mapa zawsze pokazuje pełny kraj docelowy.
    country_bbox_used = False
    _country = st.session_state.get('country_name', '')
    _country_bbox = COUNTRY_BBOX.get(_country) if _country else None
    if _country_bbox and _depth == 0:
        sw_lat, sw_lon, ne_lat, ne_lon = _country_bbox
        lat_span = ne_lat - sw_lat
        lon_span = ne_lon - sw_lon
        span = max(lat_span, lon_span)
        # Heurystyka: dobierz zoom na podstawie rozpiętości bbox kraju
        if span < 0.5:
            zoom = 11
        elif span < 1.5:
            zoom = 10
        elif span < 3:
            zoom = 9
        elif span < 6:
            zoom = 8
        elif span < 12:
            zoom = 7
        elif span < 25:
            zoom = 6
        elif span < 50:
            zoom = 5
        else:
            zoom = 4
        country_bbox_used = True

    # === AUTO-ZOOM: priorytet 2 = rozpiętość wpisanych punktów (fallback) ===
    # Używany gdy kraju nie ma w słowniku COUNTRY_BBOX (np. "Inny")
    # lub gdy operator nie wybrał kraju.
    if not country_bbox_used and len(geo_pts) >= 2 and _depth == 0:
        lats = [p['lat'] for p in geo_pts]
        lons = [p['lon'] for p in geo_pts]
        lat_span = max(lats) - min(lats)
        lon_span = max(lons) - min(lons)
        span = max(lat_span, lon_span)
        if span < 0.5:
            zoom = 11
        elif span < 1.5:
            zoom = 10
        elif span < 3:
            zoom = 9
        elif span < 6:
            zoom = 8
        elif span < 12:
            zoom = 7
        elif span < 25:
            zoom = 6
        elif span < 50:
            zoom = 5
        else:
            zoom = 4
    # Wyznaczamy zakres kafelków:
    # - gdy używamy bbox kraju: obejmujemy cały bbox (cały kraj + sąsiedzi)
    # - gdy używamy punktów: obejmujemy wszystkie punkty z marginesem
    if country_bbox_used:
        sw_lat, sw_lon, ne_lat, ne_lon = _country_bbox
        n = 2.0 ** zoom
        # SW = lewy dolny róg bbox, NE = prawy górny róg
        x_sw = (sw_lon + 180.0) / 360.0 * n
        x_ne = (ne_lon + 180.0) / 360.0 * n
        y_sw = (1.0 - math.asinh(math.tan(math.radians(sw_lat))) / math.pi) / 2.0 * n
        y_ne = (1.0 - math.asinh(math.tan(math.radians(ne_lat))) / math.pi) / 2.0 * n
        min_tx = int(min(x_sw, x_ne)) - 1
        max_tx = int(max(x_sw, x_ne)) + 1
        min_ty = int(min(y_sw, y_ne)) - 1
        max_ty = int(max(y_sw, y_ne)) + 1
    else:
        tiles = []
        for p in geo_pts:
            n = 2.0 ** zoom
            x = (p['lon'] + 180.0) / 360.0 * n
            y = (1.0 - math.asinh(math.tan(math.radians(p['lat']))) / math.pi) / 2.0 * n
            tiles.append((x, y))
        min_tx = int(min(t[0] for t in tiles)) - 1
        max_tx = int(max(t[0] for t in tiles)) + 1
        min_ty = int(min(t[1] for t in tiles)) - 1
        max_ty = int(max(t[1] for t in tiles)) + 1
    # Ogranicz do max 9x9 kafelków żeby nie pobierać za dużo
    if (max_tx - min_tx + 1) * (max_ty - min_ty + 1) > 81:
        cx = (min_tx + max_tx) // 2
        cy = (min_ty + max_ty) // 2
        min_tx, max_tx = cx - 4, cx + 4
        min_ty, max_ty = cy - 4, cy + 4
    w = (max_tx - min_tx + 1) * 256
    h = (max_ty - min_ty + 1) * 256
    stitched = Image.new('RGB', (w, h), color="#eef2f5")
    for tx in range(min_tx, max_tx + 1):
        for ty in range(min_ty, max_ty + 1):
            t_bytes = get_tile_bytes(zoom, tx, ty)
            if t_bytes:
                try:
                    with Image.open(io.BytesIO(t_bytes)) as tile_img:
                        stitched.paste(tile_img, ((tx - min_tx) * 256, (ty - min_ty) * 256))
                except Exception:
                    pass
    pixel_points = []
    for p in geo_pts:
        n = 2.0 ** zoom
        px = ((p['lon'] + 180.0) / 360.0 * n - min_tx) * 256.0
        py = ((1.0 - math.asinh(math.tan(math.radians(p['lat']))) / math.pi) / 2.0 * n - min_ty) * 256.0
        pixel_points.append({'name': p['name'], 'px': px, 'py': py})
    pts_min_x = min(p['px'] for p in pixel_points)
    pts_max_x = max(p['px'] for p in pixel_points)
    pts_min_y = min(p['py'] for p in pixel_points)
    pts_max_y = max(p['py'] for p in pixel_points)
    pts_cx = (pts_min_x + pts_max_x) / 2
    pts_cy = (pts_min_y + pts_max_y) / 2
    pad = 80
    pts_w = pts_max_x - pts_min_x
    pts_h = pts_max_y - pts_min_y
    crop_w = max(pts_w + pad * 2, 500)
    crop_h = crop_w * 0.85
    if crop_h < pts_h + pad * 2:
        crop_h = pts_h + pad * 2
        crop_w = crop_h / 0.85
    left = pts_cx - crop_w / 2
    top = pts_cy - crop_h / 2
    right = left + crop_w
    bottom = top + crop_h
    if left < 0:
        right -= left; left = 0
    if top < 0:
        bottom -= top; top = 0
    if right > w:
        left -= (right - w); right = w
    if bottom > h:
        top -= (bottom - h); bottom = h
    left, top, right, bottom = max(0, left), max(0, top), min(w, right), min(h, bottom)
    final_img = stitched.crop((int(left), int(top), int(right), int(bottom)))
    final_w, final_h = final_img.size
    final_points = []
    geo_idx = 0
    for p in points:
        if p.get('symbolic'):
            final_points.append({'name': p['name'], 'x': p['x'], 'y': p['y'], 'conn': p['conn']})
        else:
            px = pixel_points[geo_idx]['px']
            py = pixel_points[geo_idx]['py']
            geo_idx += 1
            x_pct = (px - left) / max(1, final_w) * 100
            y_pct = (py - top) / max(1, final_h) * 100
            final_points.append({'name': p['name'], 'x': x_pct, 'y': y_pct, 'conn': p['conn']})
    buf = io.BytesIO()
    final_img.save(buf, format="JPEG", quality=85)
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    stitched.close()
    final_img.close()
    return img_b64, final_points
# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
def get_local_css(return_str=False):
    s = st.session_state
    c_h1 = get_data('color_h1')
    c_h2 = get_data('color_h2')
    c_sub = get_data('color_sub')
    acc = get_data('color_accent')
    c_t = get_data('color_text')
    c_met = get_data('color_metric')
    f_h1 = get_data('font_h1')
    f_h2 = get_data('font_h2')
    f_sub = get_data('font_sub')
    f_txt = get_data('font_text')
    f_met = get_data('font_metric')
    try: fs_h1 = int(float(get_data('font_size_h1', 48)))
    except Exception: fs_h1 = 48
    try: fs_h2 = int(float(get_data('font_size_h2', 36)))
    except Exception: fs_h2 = 36
    try: fs_sub = int(float(get_data('font_size_sub', 26)))
    except Exception: fs_sub = 26
    try: fs_t = int(float(get_data('font_size_text', 14)))
    except Exception: fs_t = 14
    try: fs_met = int(float(get_data('font_size_metric', 16)))
    except Exception: fs_met = 16
    ufonts = {f_h1, f_h2, f_sub, f_txt, f_met, 'Montserrat', 'Open Sans', get_data('brand_groups_font', 'Inter')}
    font_imports = [
        f"@import url('https://fonts.googleapis.com/css?family={f.replace(' ', '+')}:{FONT_WEIGHTS.get(f, '400,700')}&display=swap');"
        for f in ufonts
    ]
    fonts_css = "\n        ".join(font_imports)
    client_css = (
        "[data-testid='stSidebar'] { display: none !important; } header { display: none !important; }"
        if get_data('client_mode') else ""
    )
    css = f"""<style>{fonts_css}@import url('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css');{client_css}
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ font-family: 'Montserrat', sans-serif !important; font-weight: 700 !important; }}
        [data-testid="stSidebar"] label, [data-testid="stSidebar"] div.stMarkdown p, [data-testid="stSidebar"] li {{ font-family: 'Open Sans', sans-serif !important; }}
        div[data-baseweb="radio"] > div:first-child {{ border-radius: 6px !important; border-width: 2px !important; }}
        div[data-baseweb="radio"] input:checked + div {{ background-color: {acc} !important; border-color: {acc} !important; }}
        div[data-baseweb="radio"] input:checked + div > div {{ background-color: white !important; }}
        div[data-baseweb="checkbox"] input:checked + div {{ background-color: {acc} !important; border-color: {acc} !important; }}
        .stButton button[kind="primary"] {{ background-color: {acc} !important; border-color: {acc} !important; color: white !important; font-weight: 700 !important; }}
        .stButton button[kind="secondary"] {{ background-color: transparent !important; border-color: {acc} !important; color: {acc} !important; border-width: 2px !important; font-weight: 600 !important; }}
        .stButton button[kind="secondary"]:hover {{ background-color: {acc} !important; color: white !important; }}
        .stDownloadButton button {{ background-color: transparent !important; border-color: {acc} !important; color: {acc} !important; border-width: 2px !important; font-weight: 600 !important; width: 100%; }}
        .stDownloadButton button:hover {{ background-color: {acc} !important; color: white !important; }}
        .stDownloadButton button[kind="primary"] {{ background-color: {acc} !important; border-color: {acc} !important; color: white !important; }}
        [data-testid="stFileUploadDropzone"] {{ padding: 15px !important; }}
        [data-testid="stFileUploadDropzone"] * {{ font-size: 11px !important; line-height: 1.3 !important; }}
        [data-testid="stFileUploadDropzone"] small {{ display: none !important; }}
        [data-testid="stFileUploadDropzone"] button {{ padding: 4px 8px !important; min-height: 25px !important; margin-top: 5px !important; }}
        [data-testid="stAppViewContainer"] > .block-container {{ max-width: 100% !important; padding: 0 !important; margin: 0 !important; }}

        /* 1. NAPRAWA JPG - Reset efektów */
        img {{ mix-blend-mode: normal !important; opacity: 1 !important; visibility: visible !important; }}

        body {{ counter-reset: slide_counter; background-color: #f4f5f7; scroll-behavior: smooth; margin: 0; }}
        .presentation-wrapper {{ height: 100vh; overflow-y: auto; scroll-snap-type: y proximity; scroll-behavior: smooth; background-color: #f4f5f7; padding: 5vh 0 15vh 0; box-sizing: border-box; }}
        .slide-scaler {{ display: flex; justify-content: center; align-items: center; min-height: 100vh; width: 100%; scroll-snap-align: center; padding: 10vh 0; }}
        .slide-page {{ width: 297mm !important; height: 210mm !important; min-width: 297mm !important; min-height: 210mm !important; margin: auto; box-sizing: border-box !important; background-color: white; box-shadow: 0 15px 45px rgba(0,0,0,0.08); padding: 30px 45px 15px 45px; position: relative; overflow: hidden; display: flex; flex-direction: column; font-family: '{f_txt}', sans-serif; color: {c_t}; transition: transform 0.3s ease, box-shadow 0.3s ease; }}
        @media screen and (max-height: 950px) {{ .slide-page {{ zoom: 0.90; }} }}
        @media screen and (max-height: 800px) {{ .slide-page {{ zoom: 0.80; }} }}
        .title-h1 {{ font-family: '{f_h1}'; font-weight: 800; font-size: {fs_h1}px; line-height: 1.1; text-transform: uppercase; color: {c_h1}; margin-bottom: 5px; }}
        .title-h2 {{ font-family: '{f_h2}'; font-weight: 800; font-size: {fs_h2}px; line-height: 1.1; text-transform: uppercase; color: {c_h2}; margin-bottom: 5px; }}
        
        /* 2. POPRAWIONA KRESKA PODTYTUŁU - 1px */
        .title-sub {{ font-family: '{f_sub}'; font-weight: 300; font-size: {fs_sub}px; color: {c_sub}; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 15px; border-bottom: 1px solid {acc}; padding-bottom: 10px; display: block; width: 100%; }}
        
        .type-icon-box {{ color: transparent; -webkit-text-stroke: 1.5px {acc}; font-size: {fs_h2}px; margin-bottom: 5px; display: inline-block; }}
        .metric-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; border-top: 1px solid #eee; padding-top: 10px; }}
        .metric-label {{ font-size: {fs_met}px; text-transform: uppercase; letter-spacing: 1px; color: {c_met}; font-family: '{f_met}'; font-weight: 600; margin-bottom: 2px; display: block; }}
        .metric-value {{ font-size: {max(14, fs_sub - 8)}px; font-weight: 700; color: {c_t}; font-family: '{f_sub}'; display: block; margin-bottom: 8px; }}
        .flight-val {{ font-size: {fs_t}px; font-weight: 600; color: {c_t}; font-family: '{f_txt}'; display: block; margin-bottom: 8px; }}
        .flight-table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        .flight-table th {{ text-align: left; padding: 6px 10px; border-bottom: 2px solid {acc}; font-family: '{f_h2}'; font-weight: 700; font-size: {fs_t}px; color: {c_h2}; }}
        .flight-table td {{ padding: 6px 10px; border-bottom: 1px solid #eee; font-size: {fs_t}px; }}
        .premium-layout {{ display: flex; gap: 40px; flex-grow: 1; min-height: 0; width: 100%; margin-bottom: 20px; overflow: hidden; }}
        .photo-col {{ flex: 45; position: relative; height: 100%; border-radius: 8px; overflow: hidden; border: 1px solid #eee; display: flex; align-items: center; justify-content: center; background-color: #fcfcfc; }}
        .photo-col img {{ width: 100%; height: 100%; object-fit: cover; }}
        .info-col {{ flex: 55; display: flex; flex-direction: column; height: 100%; }}
        .info-col p {{ font-size: {fs_t}px; line-height: 1.5; }}
        .floating-btn {{ position: absolute; bottom: 25px; left: 25px; background: {acc}; color: white !important; padding: 12px 24px; border-radius: 40px; text-decoration: none !important; font-family: '{f_h2}'; font-weight: 700; font-size: 10px; text-transform: uppercase; box-shadow: 0 4px 15px rgba(0,0,0,0.3); z-index: 10; transition: opacity 0.2s; opacity: 0.9; }}
        .floating-btn:hover {{ opacity: 1; }}
        .gallery-row {{ display: flex; justify-content: space-between; gap: 15px; margin-top: auto; padding-top: 15px; }}
        .gallery-thumb {{ flex: 1; aspect-ratio: 1/1; border: 1px solid #eee; border-radius: 6px; overflow: hidden; background-color: #fcfcfc; }}
        .gallery-thumb img {{ width: 100%; height: 100%; object-fit: cover; }}
        .top-right-logo-container {{ position: absolute; top: 15px; right: 25px; z-index: 100; text-align: right; }}
        .top-right-logo-container img {{ max-height: 60px; width: auto; object-fit: contain; opacity: 0.9; mix-blend-mode: multiply !important; }}
        .day-header {{ font-family: '{f_h2}'; font-weight: 800; font-size: {max(12, fs_sub - 4)}px; border-bottom: 2px solid {acc}; color: {c_h2}; padding-bottom: 2px; }}
        .day-date {{ font-family: '{f_txt}'; font-size: {max(10, fs_sub - 12)}px; color: {acc}; font-weight: 600; margin-top: 3px; display: block; margin-bottom: 5px; text-transform: uppercase; }}
        .prog-img-container {{ width: 100%; height: 160px; margin-bottom: 8px; border-radius: 4px; overflow: hidden; border: 1px solid #eee; background-color: #fcfcfc; }}
        .prog-img-container img {{ width: 100%; height: 100%; object-fit: cover; }}
        .prog-attr {{ font-family: '{f_txt}'; font-size: {fs_t + 2}px; color: {acc}; font-weight: 700; margin: 12px 0; border-left: 3px solid {acc}; padding-left: 10px; text-transform: uppercase; line-height: 1.3; }}
        .app-overline-style {{ display: flex; align-items: center; gap: 12px; width: 100%; box-sizing: border-box; margin-bottom: 10px; white-space: nowrap; font-family: '{f_met}'; font-size: {max(10, fs_met - 2)}px; font-weight: 700; letter-spacing: 4px; color: {acc}; text-transform: uppercase; }}
        .app-overline-style::before, .app-overline-style::after {{ content: ""; height: 1px; background-color: {acc}; opacity: 0.5; }}
        .app-overline-style::before {{ width: 32px; flex-shrink: 0; }}
        .app-overline-style::after {{ flex: 1; margin-right: 120px; min-width: 20px; }}
        .app-list {{ list-style: none; padding: 0; margin-top: 10px; margin-bottom: 10px; }}
        .app-list li {{ position: relative; padding-left: 18px; margin-bottom: 7px; font-family: '{f_txt}'; font-size: {max(10, fs_t-1)}px; line-height: 1.3; color: {c_t}; font-weight: 400; }}
        .app-list li::before {{ content: '\\203A'; position: absolute; left: 0; top: 0px; color: {acc}; font-weight: 700; font-size: 1.1em; line-height: 1; }}
        .app-list li.sub-item {{ padding-left: 35px; margin-bottom: 6px; font-size: 0.95em; color: {c_t}; font-weight: 300; }}
        .app-list li.sub-item::before {{ content: '○'; left: 18px; top: 3px; font-size: 0.6em; color: {c_h2}; }}
        .app-image-col {{ position: absolute; top: -30px; right: -45px; bottom: -15px; width: 62%; clip-path: polygon(20% 0, 100% 0, 100% 100%, 0 100%); z-index: 1; background-color: #eff4f8; display: flex; align-items: center; justify-content: center; }}
        .app-image-col img {{ width: 100%; height: 100%; object-fit: cover; }}
        /* Telefon mockup - pusta ramka, obraz ekranu jest wstawiany INLINE
   przez background-image w renderze slajdu Aplikacji (Python, renderer.py).
   Na ekranie: transform:translate(-50%,-50%) + 260x480 (ustawiane inline).
   W PRINCIE: nadpisujemy na calc()+transform:none - patrz uzasadnienie niżej. */
.phone-mockup {{
    /* pozostaje puste poza ekranowym ::before (kropka głośnika) -
       wszystkie wymiary/pozycja na ekranie pochodzą z inline style w Pythonie */
}}
.phone-mockup::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 50%;
    transform: translateX(-50%);
    width: 110px;
    height: 20px;
    background-color: #111;
    border-bottom-left-radius: 12px;
    border-bottom-right-radius: 12px;
    z-index: 11;
}}

@media print {{
    /* Bug Skia w Chromium print: transform:translate() promuje element
       do osobnej warstwy GPU, co w print powoduje rozbicie rasteryzacji
       na kafle (element rozdzielony w połowie, cień na krawędziach
       segmentów, obraz obcięty). Rozwiązanie: pozycjonowanie przez
       calc() zamiast transform - TYLKO w print, ekran zostaje bez zmian.
       Wymiary 260x480 (te same co na ekranie) - offset to połowa wymiarów. */
    .phone-mockup {{
        position: absolute !important;
        top: calc(50% - 240px) !important;
        left: calc(58% - 130px) !important;
        transform: none !important;
        width: 260px !important;
        height: 480px !important;
        border: 8px solid #111 !important;
        border-radius: 30px !important;
        background-size: cover !important;
        background-position: top center !important;
        background-repeat: no-repeat !important;
        page-break-inside: avoid !important;
        break-inside: avoid !important;
        page-break-before: avoid !important;
        page-break-after: avoid !important;
        z-index: 10 !important;
    }}
    .phone-mockup::before {{
        content: '' !important;
        position: absolute !important;
        top: 0 !important;
        left: 50% !important;
        transform: translateX(-50%) !important;
        width: 110px !important;
        height: 20px !important;
        background-color: #111 !important;
        border-bottom-left-radius: 12px !important;
        border-bottom-right-radius: 12px !important;
        z-index: 11 !important;
    }}
}}
        .brand-collage {{ display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 45% 55%; gap: 15px; height: 100%; width: 100%; }}
        .brand-img-1 {{ grid-column: 1; grid-row: 1; border-radius: 8px 50px 8px 8px; overflow: hidden; background-color: #fcfcfc; border: 1px solid #eee; display: flex; align-items: center; justify-content: center; }}
        .brand-img-1 img {{ width: 100%; height: 100%; object-fit: cover; }}
        .brand-img-2 {{ grid-column: 2; grid-row: 1; border-radius: 50px 8px 8px 8px; overflow: hidden; background-color: #fcfcfc; border: 1px solid #eee; display: flex; align-items: center; justify-content: center; }}
        .brand-img-2 img {{ width: 100%; height: 100%; object-fit: cover; }}
        .brand-img-3 {{ grid-column: 1 / span 2; grid-row: 2; border-radius: 8px 8px 50px 50px; overflow: hidden; background-color: #fcfcfc; border: 1px solid #eee; display: flex; align-items: center; justify-content: center; position: relative; }}
        .brand-img-3 img {{ width: 100%; height: 100%; object-fit: cover; }}
        .brand-gap {{ position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 15px; height: 100%; background-color: #fff; z-index: 5; }}
        .va-collage {{ display: grid; grid-template-columns: repeat(2, 1fr); grid-template-rows: 1.2fr 1fr; gap: 12px; height: 100%; width: 100%; }}
        .va-img-common {{ width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background-color: #fcfcfc; border: 1px solid #eee; }}
        .va-img-common img {{ width: 100%; height: 100%; object-fit: cover; }}
        .va-img-1-wrap {{ grid-column: 1 / span 2; grid-row: 1; border-radius: 8px 60px 8px 8px; overflow: hidden; }}
        .va-img-2-wrap {{ grid-column: 1; grid-row: 2; border-radius: 8px; overflow: hidden; }}
        .va-img-3-wrap {{ grid-column: 2; grid-row: 2; border-radius: 8px; overflow: hidden; }}
        .pg-collage {{ display: grid; grid-template-columns: repeat(2, 1fr); grid-template-rows: repeat(2, 1fr); gap: 15px; height: 100%; width: 100%; }}
        .pg-img-common {{ width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background-color: #fcfcfc; border: 1px solid #eee; }}
        .pg-img-common img {{ width: 100%; height: 100%; object-fit: cover; }}
        .pg-img-1-wrap {{ grid-column: 2; grid-row: 1; border-radius: 8px 50px 8px 8px; overflow: hidden; }}
        .pg-img-2-wrap {{ grid-column: 1; grid-row: 1 / span 2; border-radius: 50px 8px 8px 8px; overflow: hidden; }}
        .pg-img-3-wrap {{ grid-column: 2; grid-row: 2; border-radius: 8px 8px 50px 8px; overflow: hidden; }}
        .testim-item {{ display: flex; gap: 15px; padding: 12px 0; border-top: 1px solid #eaeaea; align-items: center; }}
        .testim-item:first-of-type {{ border-top: 2px solid #eee; }}
        .testim-item:last-of-type {{ border-bottom: 2px solid #eee; }}
        .testim-img-wrapper {{ flex: 0 0 80px; height: 80px; background: #fcfcfc; border: 1px solid #eee; border-radius: 8px; overflow: hidden; display: flex; align-items: center; justify-content: center; }}
        .testim-img-wrapper img {{ width: 100%; height: 100%; object-fit: cover; }}
        .testim-content {{ flex: 1; display: flex; flex-direction: column; gap: 4px; }}
        .testim-head {{ font-family: '{f_h2}'; font-size: {max(10, fs_t - 2)}px; font-weight: 700; color: {c_h2}; text-transform: uppercase; letter-spacing: 1px; }}
        .testim-quote {{ font-family: '{f_txt}'; font-size: {fs_t}px; font-style: italic; color: {c_t}; line-height: 1.4; }}
        .testim-author {{ font-family: '{f_txt}'; font-size: {max(10, fs_t - 2)}px; color: {c_t}; margin-top: 2px; }}
        .testim-author strong {{ font-weight: 700; color: {c_h2}; }}
        .page-footer {{ width: 100%; border-top: 1px solid {acc}; padding-top: 8px; margin-top: auto; display: flex; justify-content: space-between; font-size: 9px; text-transform: uppercase; font-weight: 600; color: {c_met}; font-family: '{f_met}'; position: relative; z-index: 10; }}
        .hide-footer .page-footer {{ display: none !important; }}
        .hide-footer .page-counter::after {{ counter-increment: slide_counter; }}
        .page-counter::after {{ counter-increment: slide_counter; content: counter(slide_counter); font-family: '{f_met}'; color: {c_met}; }}
        /* Globalna reguła - zapobieganie bękartom (pojedynczym słowom na końcu wersa) */
        .info-col p, .info-col div:not(.title-h1):not(.title-h2):not(.app-overline-style),
        .title-sub, .app-list li, .testim-quote, .testim-author,
        .premium-layout p, .premium-layout div[style*="font-family"] {{
            text-wrap: pretty;
        }}
        .photo-placeholder {{ width: 100%; height: 100%; background: #fcfcfc; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #aaa; font-weight: bold; font-size: 11px; text-align: center; text-transform: uppercase; }}
        @media print {{
            * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
            @page {{ size: A4 landscape; margin: 0 !important; }}
            body {{ background: white !important; margin: 0 !important; padding: 0 !important; }}
            [data-testid="stSidebar"], header {{ display: none !important; }}
            .presentation-wrapper {{ height: auto !important; overflow: visible !important; scroll-snap-type: none !important; background: white !important; padding: 0 !important; margin: 0 !important; }}
            .slide-scaler {{ height: 210mm !important; width: 297mm !important; min-height: 210mm !important; margin: 0 !important; padding: 0 !important; display: block !important; page-break-after: always !important; page-break-inside: avoid !important; overflow: hidden !important; }}
            .slide-page {{ transform: none !important; box-shadow: none !important; width: 297mm !important; height: 210mm !important; max-height: 210mm !important; padding: 10mm 15mm 5mm 15mm !important; margin: 0 !important; zoom: 1 !important; border-radius: 0 !important; border: none !important; }}
            .client-export-btn {{ display: none !important; }}
        }}</style>"""
    if return_str:
        return css
    st.markdown(css, unsafe_allow_html=True)
    
# ---------------------------------------------------------------------------
# HELPERY SLAJDÓW
# ---------------------------------------------------------------------------
def _lhtml():
    src = get_logo_b64(st.session_state.get('logo_az'))
    if not src:
        return ""
    return f'<div class="top-right-logo-container"><img src="{src}"></div>'

def _fhtml():
    return (
        f'<div class="page-footer">'
        f'<span>www.activezone.pl | wszystkie prawa zastrzeżone {datetime.today().year}</span>'
        f'<span class="page-counter"></span></div>'
    )

def _shtml(c, sid="", hide_footer=False):
    extra_class = " hide-footer" if hide_footer else ""
    return f'<div class="slide-scaler{extra_class}" id="{sid}"><div class="slide-page">{c}</div></div>'

def _get_ph(t):
    return f'<div class="photo-placeholder">{t}</div>'

def _img_tag(b64_or_url, placeholder_text='ZDJĘCIE', style='width:100%;height:100%;object-fit:cover;', extra_class=''):
    """Generuje tag <img>. Automatycznie rozpoznaje czy dostał URL czy Base64."""
    if not b64_or_url:
        return _get_ph(placeholder_text)
    src = b64_or_url if str(b64_or_url).startswith(('http', 'data:image')) else f'data:image/png;base64,{b64_or_url}'
    cls = f' class="{extra_class}"' if extra_class else ''
    return f'<img{cls} src="{src}" style="{style}">'
           
def _logo_tag(b64_or_url, style='max-height:100%; max-width:150px; object-fit:contain;'):
    """Helper: generuje tag img dla logotypów (PNG)."""
    if not b64_or_url:
        return ''
    src = b64_or_url if str(b64_or_url).startswith(('http', 'data:image')) else f'data:image/png;base64,{b64_or_url}'
    return f'<img src="{src}" style="{style}">'

def get_logo_b64(raw):
    if not raw:
        return None
        
    # 1. Jeśli to nowoczesny link URL (z Supabase)
    if isinstance(raw, str) and raw.startswith('http'):
        return raw
        
    # 2. Jeśli to tekst (już zakodowany kod Base64 z bazy danych)
    if isinstance(raw, str):
        return f"data:image/png;base64,{raw}"
        
    # 3. Jeśli to surowe bajty (świeżo wgrany plik z pamięci)
    if isinstance(raw, bytes):
        try:
            import base64
            encoded = base64.b64encode(raw).decode('utf-8')
            return f"data:image/png;base64,{encoded}"
        except Exception:
            return None
            
    return None

# ---------------------------------------------------------------------------
# GŁÓWNA FUNKCJA BUDOWANIA PREZENTACJI
# ---------------------------------------------------------------------------

def _should_render(slide_id, current_page, export_mode):
    """
    Centralna logika decydująca czy renderować slajd.
    
    Zasada: w trybie edycji renderujemy TYLKO aktywny slajd.
    - Konkretny slajd (Strona tytułowa, Mapa, etc.) -> tylko ten slajd
    - Konkretna atrakcja (★ Nazwa) -> tylko ten attr_X
    - Konkretny hotel (❯ Hotel N) -> tylko ten slide-hotel-X
    - Przerywnik (↳ Przerywnik X) -> tylko ten przerywnik
    - "Opis atrakcji" -> wszystkie atrakcje (lista)
    - "Opis hoteli" / "Zakwaterowanie" -> wszystkie hotele (lista)
    """
    # Słownik: slide_id -> klucz "hide" w session_state
    _HIDE_KEYS = {
        "slide-kierunek":           "k_hide",
        "slide-mapa":               "map_hide",
        "slide-loty":               "l_hide",
        "slide-jak-jedziemy":       "jaj_hide",
        "slide-program":            "prg_hide",
        "slide-app":                "app_hide",
        "slide-branding":           "brand_hide",
        "slide-virtual-assistant":  "va_hide",
        "slide-pillow-gifts":       "pg_hide",
        "slide-kosztorys-1":        "koszt_hide_1",
        "slide-kosztorys-2":        "koszt_hide_2",
        "slide-testimonials":       "testim_hide",
        "slide-about":              "about_hide",
        "slide-esg":                "esg_hide",
    }

    # Słownik: nazwa strony -> dokładny ID slajdu (statyczne strony)
    _PAGE_TO_SLIDE = {
        "Strona tytułowa":          "slide-title",
        "Opis kierunku":            "slide-kierunek",
        "Mapa podróży":             "slide-mapa",
        "Jak lecimy?":              "slide-loty",
        "Jak jedziemy?":            "slide-jak-jedziemy",
        "Program wyjazdu":          "slide-program",
        "Aplikacja (komunikacja)":  "slide-app",
        "Materiały brandingowe":    "slide-branding",
        "Pillow gifts":             "slide-pillow-gifts",
        "Wirtualny asystent":       "slide-virtual-assistant",
        "Kosztorys str. 1":         "slide-kosztorys-1",
        "Kosztorys str. 2":         "slide-kosztorys-2",
        "ESG":                      "slide-esg",
        "O nas":                    "slide-about",
        "Referencje":               "slide-testimonials",
    }

    # Przerywniki: nazwa strony -> dokładny ID slajdu przerywnika
    _PRZERYWNIK_MAP = {
        "  ↳ Przerywnik hotel":             "slide-sek_0",
        "  ↳ Przerywnik atrakcje":          "slide-sek_1",
        "  ↳ Przerywnik nasza agencja":     "slide-sek_2",
        "  ↳ Przerywnik program":           "slide-sek_3",
        "  ↳ Przerywnik serwisy dodatkowe": "slide-sek_4",
    }

    # 1. Sprawdź czy slajd jest ukryty (dotyczy edycji i eksportu)
    hide_key = _HIDE_KEYS.get(slide_id)
    if hide_key and get_data(hide_key, False):
        return False

    # 2. Tryb eksportu: renderuj wszystko co nie jest ukryte
    if export_mode:
        return True

    # 3. Tryb edycji: renderuj TYLKO aktywny slajd

    # 3a. Przerywnik -> tylko ten przerywnik (slide-sek_X)
    if current_page in _PRZERYWNIK_MAP:
        return slide_id == _PRZERYWNIK_MAP[current_page]

    # 3b. Konkretna atrakcja (★ NazwaAtrakcji) -> tylko ten attr_X
    if "★" in current_page:
        # Wyciągnij nazwe atrakcji i znajdz jej indeks
        attr_name = current_page.replace("★", "").strip()
        attr_order = get_data('attr_order', [])
        if not attr_order:
            attr_order = list(range(get_data('num_attr', 0)))
        for pos, idx in enumerate(attr_order):
            display_name = str(get_data(f'amain_{idx}', '')).split('\n')[0][:25].strip() or f"Atrakcja {pos + 1}"
            if display_name == attr_name:
                return slide_id == f"attr_{idx}"
        return False  # nie znaleziono -> nic nie renderuj

    # 3c. Konkretny hotel (❯ Hotel N) -> tylko ten slide-hotel-X
    if "❯" in current_page:
        # "    ❯ Hotel 1" -> wyciagnij numer
        m = re.search(r'Hotel\s+(\d+)', current_page)
        if m:
            hotel_pos = int(m.group(1)) - 1  # 1-based -> 0-based
            return slide_id == f"slide-hotel-{hotel_pos}"
        return False

    # 3d. "Opis atrakcji" -> wszystkie atrakcje (lista)
    if current_page == "Opis atrakcji":
        return slide_id.startswith("attr_")

    # 3e. "Opis hoteli" / "Zakwaterowanie" -> wszystkie hotele (lista)
    if current_page in ("Opis hoteli", "Zakwaterowanie"):
        return slide_id.startswith("slide-hotel-")

    # 3f. Standardowe strony -> tylko jej slajd (dokladne dopasowanie)
    expected = _PAGE_TO_SLIDE.get(current_page, "")
    if expected:
        return slide_id == expected

    # 3g. Nieznana strona -> nic nie renderuj
    return False

def build_presentation(current_page="Strona Tytułowa", export_mode=False):
    """
    Renderuje prezentację używając get_data() - jedynego źródła prawdy.
    Dane pochodzą z session_state z fallback do Supabase.
    """
    hp = []
        
    # Kolory - używaj get_data() zamiast get_data()
    c_h1 = get_data('color_h1', '#003366')
    c_h2 = get_data('color_h2', '#003366')
    c_sub = get_data('color_sub', '#FF6600')
    acc = get_data('color_accent', '#FF6600')
    c_t = get_data('color_text', '#333333')
    c_met = get_data('color_metric', '#003366')
    
    # Fonty
    f_h1 = get_data('font_h1', 'Montserrat')
    f_h2 = get_data('font_h2', 'Montserrat')
    f_sub = get_data('font_sub', 'Montserrat')
    f_t = get_data('font_text', 'Open Sans')
    f_met = get_data('font_metric', 'Montserrat')
    # Rozmiary czcionek
    try: fs_t = int(float(get_data('font_size_text', 14)))
    except Exception: fs_t = 14
    try: fs_h1_val = int(float(get_data('font_size_h1', 48)))
    except Exception: fs_h1_val = 48
    try: fs_sub_val = int(float(get_data('font_size_sub', 26)))
    except Exception: fs_sub_val = 26
    try: fs_met = int(float(get_data('font_size_metric', 16)))
    except Exception: fs_met = 16
    lh = _lhtml()
    fh = _fhtml()
    # --- Przerywniki sekcji (nowy styl: pełnoekranowy overlay z gradientem) ---
    def _render_sek(target_i):
        """Renderuje slajd przerywnikowy sek_i jeśli nie ukryty."""
        i = target_i
        sid = f"sek_{i}"
        if get_data(f'sek_hide_{i}', False):
            return
        # NAPRAWA: Renderuj przerywnik tylko gdy aktywna strona to wymaga
        if not _should_render(f"slide-sek_{i}", current_page, export_mode):
            return
        _title_defs = {0: 'ZAKWATEROWANIE', 1: 'ATRAKCJE', 2: 'NASZA AGENCJA', 3: 'PROGRAM', 4: 'SERWISY DODATKOWE'}
        _sub_defs   = {0: 'NASZE HOTELE', 1: 'PROGRAM WYJAZDU', 2: 'O NAS', 3: 'NASZ PLAN WYJAZDU', 4: 'USŁUGI DODATKOWE'}
        title = str(get_data(f'{sid}_title', _title_defs.get(i, 'SEKCJA'))).replace(chr(10), '<br>')
        sub   = str(get_data(f'{sid}_sub',   _sub_defs.get(i, ''))).replace(chr(10), '<br>')
        box_bg  = str(get_data(f'{sid}_bg')  or c_h1)
        box_txt = str(get_data(f'{sid}_txt') or '#ffffff')
        bg_img  = get_b64(f'{sid}_img', (16, 9))
        bg_html = (
            _img_tag(bg_img) if bg_img else
            f'<div style="width:100%;height:100%;background:{box_bg};"></div>'
        )
        hp.append(_shtml(f"""{lh}
        <div id="slide-{sid}" style="position:relative; width:100%; height:100%; overflow:hidden; background:{box_bg};">
            <div style="position:absolute; top:0; left:0; width:100%; height:100%; z-index:1;">
                {bg_html}
            </div>
            <div style="position:absolute; top:0; left:0; width:65%; height:100%; z-index:2;
                        background:linear-gradient(to right, {box_bg} 35%, transparent 100%);">
            </div>
            <div style="position:absolute; top:50%; left:8%; transform:translateY(-50%); z-index:3; max-width:58%;">
                <div style="display:flex; align-items:center; gap:12px; margin-bottom:18px;">
                    <div style="width:32px; height:3px; background:{acc}; opacity:0.7; flex-shrink:0;"></div>
                    <span style="font-family:'{f_met}'; font-weight:700; font-size:{max(10,fs_met-1)}px;
                                 letter-spacing:4px; color:{acc}; text-transform:uppercase;">
                        {sub}
                    </span>
                    <div style="width:32px; height:3px; background:{acc}; opacity:0.7; flex-shrink:0;"></div>
                </div>
                <div style="font-family:'{f_h1}'; font-weight:800; font-size:{min(fs_h1_val+32, 96)}px;
                            color:{box_txt}; line-height:1.0; text-transform:uppercase;
                            text-shadow:0px 4px 15px rgba(0,0,0,0.15);">
                    {title}
                </div>
            </div>
        </div>{fh}""", f"slide-{sid}"))
    # --- Slajd tytułowy (elegancki, luksusowy układ - Playfair Display) ---
    if _should_render('slide-title', current_page, export_mode):
        i1 = get_b64('img_hero_t', (4, 5))
        im1 = _img_tag(i1, 'ZDJĘCIE GŁÓWNE')
        
        rcli = get_data('logo_cli')
        hide_cli = get_data('hide_logo_cli', False)
        lcli_val = get_logo_b64(rcli)
        
        # Logo klienta (PNG)
        lcli = f"<img src='{lcli_val}' style='max-height:100%;max-width:150px;object-fit:contain;'>" if lcli_val and not hide_cli else ""
        lcli_container = f"<div class='logo-container' style='margin-bottom:40px;height:60px;display:flex;align-items:center;'>{lcli}</div>"
        
        # Import Playfair Display
        playfair_import = "<style>@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&display=swap');</style>"
        
        # Tytuł i podtytuł - elegancka typografia
        title_html = f"""
        <div style="font-family:'Playfair Display', serif; font-weight:900; font-size:{fs_h1_val+12}px;
                    line-height:1.0; color:{c_h1}; text-transform:uppercase; letter-spacing:-1px;
                    margin-bottom:18px;">
            {str(get_data('t_main','')).replace(chr(10),'<br>')}
        </div>
        <div style="font-family:'{f_sub}'; font-weight:300; font-size:{max(13, fs_sub_val-2)}px;
                    color:{acc}; letter-spacing:6px; text-transform:uppercase;
                    margin-bottom:40px;">
            {str(get_data('t_sub','')).replace(chr(10),'<br>')}
        </div>
        """
        
        # Subtelne metryczki - etykiety w kolorze akcentu, wartości regular weight
        metrics_html = f"""
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:24px 30px; margin-top:10px;">
            <div>
                <div style="font-family:'{f_met}'; font-weight:600; font-size:{max(9, fs_met-4)}px;
                            color:{acc}; text-transform:uppercase; letter-spacing:2.5px; margin-bottom:6px;">KLIENT</div>
                <div style="font-family:'{f_t}'; font-weight:400; font-size:{fs_t+2}px; color:{c_t};">{get_data('t_klient','')}</div>
            </div>
            <div>
                <div style="font-family:'{f_met}'; font-weight:600; font-size:{max(9, fs_met-4)}px;
                            color:{acc}; text-transform:uppercase; letter-spacing:2.5px; margin-bottom:6px;">KIERUNEK</div>
                <div style="font-family:'{f_t}'; font-weight:400; font-size:{fs_t+2}px; color:{c_t};">{get_data('t_kierunek','')}</div>
            </div>
            <div>
                <div style="font-family:'{f_met}'; font-weight:600; font-size:{max(9, fs_met-4)}px;
                            color:{acc}; text-transform:uppercase; letter-spacing:2.5px; margin-bottom:6px;">TERMIN</div>
                <div style="font-family:'{f_t}'; font-weight:400; font-size:{fs_t+2}px; color:{c_t};">{get_data('t_date','')}</div>
            </div>
            <div>
                <div style="font-family:'{f_met}'; font-weight:600; font-size:{max(9, fs_met-4)}px;
                            color:{acc}; text-transform:uppercase; letter-spacing:2.5px; margin-bottom:6px;">LICZBA OSÓB</div>
                <div style="font-family:'{f_t}'; font-weight:400; font-size:{fs_t+2}px; color:{c_t};">{get_data('t_pax','')}</div>
            </div>
            <div>
                <div style="font-family:'{f_met}'; font-weight:600; font-size:{max(9, fs_met-4)}px;
                            color:{acc}; text-transform:uppercase; letter-spacing:2.5px; margin-bottom:6px;">HOTEL</div>
                <div style="font-family:'{f_t}'; font-weight:400; font-size:{fs_t+2}px; color:{c_t};">{get_data('t_hotel','')}</div>
            </div>
            <div>
                <div style="font-family:'{f_met}'; font-weight:600; font-size:{max(9, fs_met-4)}px;
                            color:{acc}; text-transform:uppercase; letter-spacing:2.5px; margin-bottom:6px;">DOJAZD</div>
                <div style="font-family:'{f_t}'; font-weight:400; font-size:{fs_t+2}px; color:{c_t};">{get_data('t_trans','')}</div>
            </div>
        </div>
        """
        
        # Layout: zdjęcie szersze (65% lewa kolumna), info 35% prawa
        hp.append(_shtml(f"""{playfair_import}{lh}
        <div style="display:flex; gap:0; flex-grow:1; min-height:0; width:100%; overflow:hidden; margin:-30px -45px -15px -45px; padding:0;">
            <div style="flex:62 1 0; position:relative; height:100%; overflow:hidden; background:#fcfcfc;">
                <div style="position:absolute; top:0; left:0; width:100%; height:100%;">
                    {im1}
                </div>
            </div>
            <div style="flex:38 1 0; display:flex; flex-direction:column; height:100%; justify-content:center; padding:30px 45px 15px 50px;">
                {lcli_container}
                {title_html}
                {metrics_html}
            </div>
        </div>{fh}""", "slide-title", hide_footer=True))
    
    # --- Opis kierunku (Pojedynczy Slajd Premium) ---
    if _should_render('slide-kierunek', current_page, export_mode):
        kimg = get_b64('img_hero_k', (1, 1))
        
        k_over = str(get_data('k_overline') or 'NASZ KIERUNEK')
        k_main = str(get_data('k_main') or '').replace(chr(10), '<br>')
        k_sub  = str(get_data('k_sub')  or '').replace(chr(10), '<br>')
        k_opis = str(get_data('k_opis') or '').replace(chr(10), '<br>')

        # === Pas ikon faktów kierunku ===
        _k_icons_config = [
            ('stolica', 'landmark'),
            ('waluta', 'wallet'),
            ('strefa', 'clock'),
            ('klimat', 'sun'),
            ('temp', 'temperature-half'),
            ('szczepienia', 'syringe'),
            ('mieszkancy', 'users'),
        ]
        _k_icon_items = []
        for _slug, _icon in _k_icons_config:
            if get_data(f'k_icon_{_slug}_show', False):
                _val = str(get_data(f'k_icon_{_slug}_val', '') or '').strip()
                if _val:
                    _k_icon_items.append(
                        f'<div style="display:flex; align-items:center; gap:8px; '
                        f'font-size:{max(10,fs_t-1)}px; font-weight:600; color:{c_t}; '
                        f'min-width:0;">'
                        f'<i class="fa-solid fa-{_icon}" style="color:{acc}; font-size:{fs_t+4}px; flex-shrink:0;"></i>'
                        f'<span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{_val}</span>'
                        f'</div>'
                    )
        _k_icons_html = (
            f'<div style="display:grid; grid-template-columns:repeat(3, 1fr); '
            f'gap:12px 16px; margin-top:20px; padding:14px 0; '
            f'border-top:1px solid {acc};">'
            f'{"".join(_k_icon_items)}</div>'
            if _k_icon_items else ''
        )
        
        # === Chipy z atutami kierunku ===
        _k_highlights = [x.strip() for x in str(get_data('k_highlights', '') or '').split('\n') if x.strip()]
        _k_chips_html = (
            f'<div style="display:flex; flex-wrap:wrap; gap:8px; margin-top:10px;">'
            + ''.join([
                f'<span style="background:{acc}; color:#fff; padding:6px 14px; '
                f'border-radius:4px; font-family:\'{f_met}\'; font-size:{max(9,fs_met-3)}px; '
                f'font-weight:700; letter-spacing:1.5px; text-transform:uppercase; '
                f'white-space:nowrap;">{_chip}</span>'
                for _chip in _k_highlights
            ])
            + '</div>'
            if _k_highlights else ''
        )
        
        # === Trzy zdjęcia w lewej kolumnie ===
        _kth1 = get_b64('img_k_th1', (1, 1))
        _kth2 = get_b64('img_k_th2', (1, 1))
        _kth1_html = _img_tag(_kth1, 'ZDJĘCIE 2', style='width:100%; height:100%; object-fit:cover;')
        _kth2_html = _img_tag(_kth2, 'ZDJĘCIE 3', style='width:100%; height:100%; object-fit:cover;')
        
        hp.append(_shtml(f"""{lh}
        <div class="premium-layout" id="slide-kierunek" style="gap:30px; align-items:stretch;">
            <div style="flex:42; display:flex; flex-direction:column; gap:12px; height:100%;">
                <div style="flex:3; border-radius:8px; overflow:hidden; background:#fcfcfc; border:1px solid #eee;">
                    {_img_tag(kimg, 'ZDJĘCIE GŁÓWNE', style='width:100%; height:100%; object-fit:cover; object-position:center;')}
                </div>
                <div style="flex:2; display:flex; gap:12px;">
                    <div style="flex:1; border-radius:8px; overflow:hidden; background:#fcfcfc; border:1px solid #eee;">
                        {_kth1_html}
                    </div>
                    <div style="flex:1; border-radius:8px; overflow:hidden; background:#fcfcfc; border:1px solid #eee;">
                        {_kth2_html}
                    </div>
                </div>
            </div>
            
            <div class="info-col" style="flex:58; padding-left:10px; padding-top:15px; justify-content:flex-start;">
                
                <div class="app-overline-style">
                    {k_over}
                </div>

                <div class="title-h1" style="text-align:left; margin-bottom:5px; font-size:{fs_h1_val}px; color:{c_h1}; line-height:1.1;">
                    {k_main}
                </div>
                <div class="title-sub" style="text-align:left; margin-bottom:25px;">
                    {k_sub}
                </div>
                <div style="font-family:'{f_t}'; font-size:{fs_t}px; line-height:1.7; color:{c_t}; text-align:justify;">
                    {k_opis}
                </div>
                {_k_icons_html}
                {_k_chips_html}
            </div>
        </div>{fh}""", "slide-kierunek"))
    # --- Mapa ---
    if _should_render('slide-mapa', current_page, export_mode):
        m_bg = get_data('img_map_bg_auto')
        if m_bg:
            m_bg_html = _img_tag(m_bg, 'MAPA', style='width:100%;height:100%;object-fit:fill;opacity:0.85;border-radius:8px;')
        else:
            m_bg_html = f'<div style="width:100%;height:100%;background:#eef2f5;display:flex;align-items:center;justify-content:center;color:#ccc;font-weight:bold;font-size:14px;text-align:center;border-radius:8px;border:2px dashed {acc};">MAPA ZOSTANIE WYGENEROWANA AUTOMATYCZNIE<br>Wprowadź punkty trasy w panelu sterowania</div>'
        auto_pts = get_data('auto_map_points', [])
        svg_lines = ""
        html_markers = ""
        ul_points = []
        for i, pt in enumerate(auto_pts):
            name = pt['name']
            x1 = pt['x']
            y1 = pt['y']
            conn = pt['conn']
            ul_points.append(f'<li>{name}</li>')
            html_markers += f'''
                <div style="position:absolute; top:{y1}%; left:{x1}%; z-index:3; transform:translate(-50%, -50%); display:flex; flex-direction:column; align-items:center;">
                    <div style="font-family:'{f_h2}'; font-weight:800; color:{c_h2}; text-shadow:2px 2px 0 #fff, -2px -2px 0 #fff, 2px -2px 0 #fff, -2px 2px 0 #fff, 0 2px 0 #fff, 0 -2px 0 #fff; white-space:nowrap; font-size:{fs_t+2}px; margin-bottom:2px;">{name}</div>
                    <div style="width:14px; height:14px; background:{acc}; border-radius:50%; border:3px solid #fff; box-shadow:0 3px 6px rgba(0,0,0,0.3);"></div>
                </div>'''
            if i < len(auto_pts) - 1 and conn != 'Brak':
                x2 = auto_pts[i + 1]['x']
                y2 = auto_pts[i + 1]['y']
                is_flight = "Przelot" in conn
                stroke_dash = "8,8" if is_flight else "none"
                svg_lines += f'<line x1="{x1}%" y1="{y1}%" x2="{x2}%" y2="{y2}%" stroke="{acc}" stroke-width="3" stroke-dasharray="{stroke_dash}" stroke-linecap="round"/>'
                if is_flight:
                    dx = x2 - x1
                    dy = y2 - y1
                    angle = math.degrees(math.atan2(dy, dx))
                    rot = angle + 45
                    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
                    html_markers += f'''
                        <div style="position:absolute; top:{my}%; left:{mx}%; z-index:2; transform:translate(-50%, -50%) rotate({rot}deg); color:{acc}; font-size:18px; background:#fff; border-radius:50%; width:28px; height:28px; display:flex; align-items:center; justify-content:center; box-shadow:0 0 10px rgba(0,0,0,0.2);">
                            <i class="fa-solid fa-plane"></i>
                        </div>'''
        ul_points_html = f'<ul class="app-list" style="margin-top:10px;">{"".join(ul_points)}</ul>' if ul_points else ''
        # --- Siatka odległości ---
        num_dp = get_data('num_dist_pairs', 0)
        dist_title = str(get_data('map_dist_title', 'ODLEGŁOŚCI I CZAS DOJAZDU'))
        dist_rows_html = ''
        if num_dp > 0:
            rows_html = ''
            for di in range(num_dp):
                pa = str(get_data(f'dist_a_{di}', ''))
                pb = str(get_data(f'dist_b_{di}', ''))
                dist_val = str(get_data(f'dist_km_{di}', '—'))
                time_val = str(get_data(f'dist_time_{di}', '—'))
                if not pa and not pb:
                    continue
                label = f'{pa} → {pb}' if pa and pb else (pa or pb)
                rows_html += f"""
                <tr>
                    <td style="font-family:'{f_t}'; font-size:{fs_t}px; color:white;
                               font-weight:400; line-height:1.3; padding:7px 10px 7px 0;
                               border-bottom:1px solid rgba(255,255,255,0.12);
                               width:50%; max-width:0; overflow:hidden;
                               text-overflow:ellipsis; white-space:nowrap;">
                        {label}
                    </td>
                    <td style="width:25%; padding:7px 8px; text-align:right;
                               border-bottom:1px solid rgba(255,255,255,0.12);
                               white-space:nowrap;">
                        <div style="font-family:'{f_h2}'; font-weight:800;
                                    font-size:{fs_t+3}px; color:white; line-height:1;">
                            {dist_val} km
                        </div>
                        <div style="font-family:'{f_t}'; font-size:{max(9,fs_t-3)}px;
                                    color:rgba(255,255,255,0.65); margin-top:2px;">
                            odległość
                        </div>
                    </td>
                    <td style="width:1px; padding:7px 0;
                               border-bottom:1px solid rgba(255,255,255,0.12);">
                        <div style="width:1px; background:rgba(255,255,255,0.2); height:100%;"></div>
                    </td>
                    <td style="width:25%; padding:7px 0 7px 8px; text-align:right;
                               border-bottom:1px solid rgba(255,255,255,0.12);
                               white-space:nowrap;">
                        <div style="font-family:'{f_h2}'; font-weight:800;
                                    font-size:{fs_t+3}px; color:{acc}; line-height:1;">
                            {time_val}
                        </div>
                        <div style="font-family:'{f_t}'; font-size:{max(9,fs_t-3)}px;
                                    color:rgba(255,255,255,0.65); margin-top:2px;">
                            czas dojazdu
                        </div>
                    </td>
                </tr>"""
            if rows_html:
                dist_rows_html = f"""
                <div style="background-color:{c_h2}; border-radius:8px; padding:12px 14px;
                            margin-top:10px; box-shadow:0 4px 12px rgba(0,0,0,0.12);">
                    <div style="font-family:'{f_h2}'; font-weight:800; font-size:{fs_t}px;
                                color:white; text-transform:uppercase; letter-spacing:1px;
                                margin-bottom:8px; opacity:0.85;">
                        {dist_title}
                    </div>
                    <table style="width:100%; border-collapse:collapse; table-layout:fixed;">
                        {rows_html}
                    </table>
                </div>"""
        hp.append(_shtml(f"""{lh}
            <div class="premium-layout">
                <div class="info-col" style="flex: 40; padding-right: 30px; padding-top: 15px; justify-content: flex-start;">
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
                        <div style="width:32px; height:1px; background:{acc}; opacity:0.6; flex-shrink:0;"></div>
                        <span style="font-family:'{f_met}'; font-size:{max(9,fs_met-2)}px; font-weight:700;
                                     letter-spacing:4px; color:{acc}; text-transform:uppercase; white-space:nowrap;">
                            {str(get_data('map_overline','TRASA WYJAZDU'))}
                        </span>
                        <div style="flex:1; height:1px; background:{acc}; opacity:0.6;"></div>
                    </div>
                    <div class="title-h1" style="margin-bottom: 15px; font-size:{fs_h1_val-6}px;">{str(get_data('map_title','ZARYS\\nPODRÓŻY')).replace(chr(10),'<br>')}</div>
                    <div class="title-sub" style="margin-bottom: 15px; font-size:{max(12,fs_sub_val-4)}px;">{str(get_data('map_subtitle','')).replace(chr(10),'<br>')}</div>
                    <div style="font-family: '{f_t}'; font-size: {fs_t}px; line-height: 1.6; color: {c_t}; margin-bottom: 10px;">{str(get_data('map_desc','')).replace(chr(10),'<br>')}</div>
                    <div style="font-family:'{f_h2}'; font-weight:800; font-size:{fs_t+2}px; color:{c_h2}; margin-bottom:5px; text-transform:uppercase;">PUNKTY NA TRASIE:</div>
                    {ul_points_html}
                    {dist_rows_html}
                </div>
                <div class="photo-col" style="flex: 60; position:relative; overflow:hidden; border: 2px solid #eee; border-radius:8px; background-color: #fcfcfc;">
                    {m_bg_html}
                    <svg style="position:absolute; top:0; left:0; width:100%; height:100%; z-index:2; pointer-events:none; overflow:visible;">{svg_lines}</svg>
                    {html_markers}
                </div>
            </div>{fh}""", "slide-mapa"))
    # --- Jak lecimy ---
    if _should_render('slide-loty', current_page, export_mode):
        il = get_b64('img_hero_l', (4, 5))
        iml = _img_tag(il, 'FOTO SAMOLOTU')
        
        f_keys = ['f1', 'f2']
        if get_data('l_przesiadka', False):
            f_keys.extend(['f3', 'f4'])
            
        rows = ""
        for f_key in f_keys:
            f_val = str(get_data(f_key, ''))
            parts = f_val.split(',')
            if len(parts) >= 4:
                rows += f"<tr><td>{parts[0]}</td><td>{parts[1]}</td><td>{parts[2]}</td><td>{parts[3]}</td></tr>"
                
        przesiadka_html = ""
        if get_data('l_przesiadka', False):
            przesiadka_html = f"""<div style="background-color: #f8f9fa; border-left: 4px solid {acc}; padding: 15px 20px; margin-top: 15px; margin-bottom: 15px; border-radius: 4px; display: flex; gap: 40px; align-items: center;">
                <div><div style="font-size: 11px; font-weight: 700; color: {c_h2}; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 3px;">Port przesiadkowy</div><div style="font-size: {fs_t+2}px; font-weight: 600; color: {c_t};"><i class="fa-solid fa-location-dot" style="color:{acc}; margin-right:6px;"></i>{get_data('l_port','')}</div></div>
                <div><div style="font-size: 11px; font-weight: 700; color: {c_h2}; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 3px;">Czas przesiadki</div><div style="font-size: {fs_t+2}px; font-weight: 600; color: {c_t};"><i class="fa-solid fa-clock" style="color:{acc}; margin-right:6px;"></i>{get_data('l_czas','')}</div></div>
            </div>"""
            
        h_d = f"<p>{str(get_data('l_desc') or '').replace(chr(10),'<br>')}</p>" if str(get_data('l_desc','')).strip() else ""
        h_e = f"<p style='font-size:10px;margin-top:15px;'>{str(get_data('l_extra') or '').replace(chr(10),'<br>')}</p>" if str(get_data('l_extra','')).strip() else ""
        
        hp.append(_shtml(f"""{lh}
        <div class="premium-layout">
            <div class="photo-col">{iml}</div>
            <div class="info-col" style="padding-top:15px; justify-content:flex-start;">
                
                <div class="app-overline-style">
                    {str(get_data('l_overline','PRZELOT'))}
                </div>

                <div class="title-h1" style="margin-bottom:5px; font-size:{fs_h1_val-6}px;">{str(get_data('l_main','JAK LECIMY?')).replace(chr(10),'<br>')}</div>
                <div class="title-sub" style="margin-bottom:15px;">{str(get_data('l_sub','')).replace(chr(10),'<br>')}</div>
                {h_d}
                
                <div class="metric-grid">
                    <div><div class="metric-label">Trasa</div><div class="flight-val">{get_data('m_route','')}</div></div>
                    <div><div class="metric-label">Limit bagażu</div><div class="flight-val">{get_data('m_luggage','')}</div></div>
                </div>
                
                {przesiadka_html}
                
                <table class="flight-table">
                    <tr><th>NR LOTU</th><th>DATA</th><th>TRASA</th><th>GODZINY</th></tr>
                    {rows}
                </table>
                
                {h_e}
            </div>
        </div>{fh}""", "slide-loty"))

    # --- Jak jedziemy ---
    if _should_render('slide-jak-jedziemy', current_page, export_mode):
        ij = get_b64('img_hero_j', (4, 5))
        imj = _img_tag(ij, 'FOTO TRANSPORTU')
        
        # Tabela odległości (osobne pola jaj_dist_*)
        jaj_dist_rows = ""
        for di in range(int(get_data('num_jaj_dist_pairs', 0) or 0)):
            _a = str(get_data(f'jaj_dist_a_{di}', '') or '').strip()
            _b = str(get_data(f'jaj_dist_b_{di}', '') or '').strip()
            _km = str(get_data(f'jaj_dist_km_{di}', '—') or '—')
            _time = str(get_data(f'jaj_dist_time_{di}', '—') or '—')
            if not _a or not _b:
                continue
            jaj_dist_rows += f"<tr><td>{_a} → {_b}</td><td style='text-align:right;'>{_km} km</td><td style='text-align:right;'>{_time}</td></tr>"
        
        jaj_dist_title = str(get_data('jaj_dist_title', 'ODLEGŁOŚCI I CZAS DOJAZDU') or '')
        jaj_table_html = ''
        if jaj_dist_rows:
            jaj_table_html = f"""
                <div style="margin-top:15px;">
                    <div style="font-family:'{f_h2}'; font-weight:800; font-size:{fs_t+2}px; color:{c_h2}; margin-bottom:8px; text-transform:uppercase;">{jaj_dist_title}</div>
                    <table class="flight-table">
                        <tr><th>TRASA</th><th style='text-align:right;'>ODLEGŁOŚĆ</th><th style='text-align:right;'>CZAS</th></tr>
                        {jaj_dist_rows}
                    </table>
                </div>
            """
        
        h_d_j = f"<p>{str(get_data('jaj_desc') or '').replace(chr(10),'<br>')}</p>" if str(get_data('jaj_desc','')).strip() else ""
        h_e_j = f"<p style='font-size:10px;margin-top:15px;'>{str(get_data('jaj_extra') or '').replace(chr(10),'<br>')}</p>" if str(get_data('jaj_extra','')).strip() else ""
        
        hp.append(_shtml(f"""{lh}
        <div class="premium-layout">
            <div class="photo-col">{imj}</div>
            <div class="info-col" style="padding-top:15px; justify-content:flex-start;">
                
                <div class="app-overline-style">
                    {str(get_data('jaj_overline','DOJAZD'))}
                </div>
                <div class="title-h1" style="margin-bottom:5px; font-size:{fs_h1_val-6}px;">{str(get_data('jaj_main','JAK JEDZIEMY?')).replace(chr(10),'<br>')}</div>
                <div class="title-sub" style="margin-bottom:15px;">{str(get_data('jaj_sub','')).replace(chr(10),'<br>')}</div>
                {h_d_j}
                
                <div class="metric-grid">
                    <div><div class="metric-label">Trasa</div><div class="flight-val">{get_data('jaj_route','')}</div></div>
                </div>
                
                {jaj_table_html}
                
                {h_e_j}
            </div>
        </div>{fh}""", "slide-jak-jedziemy"))
    # --- Przerywnik sek_0 (przed hotel) ---
    _render_sek(0)  # Przerywnik przed hotelami
    # --- Hotele w kolejności hotel_order ---
    _hotel_order = get_data('hotel_order', [])
    if not _hotel_order:
        _hotel_order = list(range(get_data('num_hotels', 1)))
    for i in _hotel_order:
        if _should_render(f'slide-hotel-{i}', current_page, export_mode) and not get_data(f'h_hide_{i}', False):
            h1 = get_b64(f'img_hotel_1_{i}', (16, 9))
            h1b = get_b64(f'img_hotel_1b_{i}', (16, 9))
            h2 = get_b64(f'img_hotel_2_{i}', (16, 9))
            h3 = get_b64(f'img_hotel_3_{i}', (16, 9))
            h1_html = _img_tag(h1, 'ZDJ. LEWE 1')
            h1b_html = _img_tag(h1b, 'ZDJ. LEWE 2')
            url_val = str(get_data(f'h_url_{i}', '')).strip()
            # POPRAWKA 2: URL w linii z podtytułem (wyrównany do prawej), podlinkowany
            _url_clean = url_val.replace('https://', '').replace('http://', '') if url_val else ''
            url_link = (
                f'<a href="https://{_url_clean}" target="_blank" '
                f'style="color:{c_t};opacity:0.75;text-decoration:none;'
                f'font-size:{max(10,fs_t-2)}px;white-space:nowrap;" '
                f'onmouseover="this.style.color=&quot;{acc}&quot;" '
                f'onmouseout="this.style.color=&quot;{c_t}&quot;">'
                f'<i class="fa-solid fa-globe" style="color:{acc};margin-right:4px;"></i>{url_val}</a>'
                if url_val else ''
            )
            h_amenities = get_data(f'h_amenities_{i}', [])
            am_items = []
            book_val = str(get_data(f'h_booking_{i}', '')).strip()
            if book_val:
                am_items.append(f'<div style="display:flex; align-items:center; gap:6px; margin-right:10px;"><div style="background:#003580; color:white; padding:3px 8px; border-radius:6px; border-bottom-left-radius:0; font-family:\'Montserrat\', sans-serif; font-weight:800; font-size:{max(12,fs_t)}px;">{book_val}</div><span style="font-family:\'Montserrat\', sans-serif; font-weight:700; color:#003580; font-size:{max(10,fs_t-1)}px;">Booking.com</span></div>')
            for a in h_amenities:
                if a in hotel_icons:
                    am_items.append(f'<div style="display:flex; align-items:center; gap:6px; font-size:{max(10,fs_t-1)}px; font-weight:600; color:{c_t};"><i class="fa-solid {hotel_icons[a]}" style="color:{acc}; font-size:{fs_t+4}px;"></i> {a}</div>')
            h_am_html = (f'<div style="display:flex; flex-wrap:wrap; align-items:center; gap:15px; margin-bottom:10px; padding:8px 0; border-top:1px solid #eee; border-bottom:1px solid #eee;">{"".join(am_items)}</div>'
                         if am_items else '')
            # POPRAWKA 1: Atuty jako tagi (jeden wiersz, font overline, kolor akcentu, tło akcentu)
            advs = [f.strip() for f in get_data(f'h_advantages_{i}', '').split('\n') if f.strip()]
            adv_html = (
                f'<div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:8px;">' +
                ''.join([
                    f'<span style="background:{acc}; color:#fff; padding:3px 10px; border-radius:20px; '
                    f'font-family:{f_met}; font-size:{max(9,fs_met-3)}px; font-weight:700; '
                    f'letter-spacing:1px; text-transform:uppercase; white-space:nowrap;">{a}</span>'
                    for a in advs
                ]) +
                '</div>'
                if advs else ''
            )
            hp.append(_shtml(f"""{lh}<div class="premium-layout" id="slide-hotel-{i}" style="align-items:stretch;">
                <div style="flex:40; display:flex; flex-direction:column; gap:12px;">
                    <div style="flex:3; border-radius:8px; overflow:hidden; border:1px solid #eee; background-color:#fcfcfc;">{h1_html}</div>
                    <div style="flex:2; border-radius:8px; overflow:hidden; border:1px solid #eee; background-color:#fcfcfc;">{h1b_html}</div>
                </div>
                <div style="flex:60; padding-left:15px; padding-top:15px; display:flex; flex-direction:column; min-height:0;">
                    <div class="app-overline-style" style="margin-bottom:4px; flex-shrink:0;"><span>{str(get_data(f'h_overline_{i}','ZAKWATEROWANIE'))}</span></div>
                    <div class="title-h1" style="margin-bottom:3px; font-size:{max(20,fs_h1_val-6)}px; flex-shrink:0;">{str(get_data(f'h_title_{i}','')).replace(chr(10),'<br>')}</div>
                    <div style="display:flex; align-items:baseline; justify-content:space-between; gap:10px; margin-bottom:8px; flex-shrink:0;">
                        <div class="title-sub" style="margin:0; font-size:{max(12,fs_sub_val-4)}px;">{str(get_data(f'h_subtitle_{i}','')).replace(chr(10),'<br>')}</div>
                        <div style="flex-shrink:0;">{url_link}</div>
                    </div>
                    <div style="font-size:{fs_t}px; line-height:1.4; margin-bottom:8px; color:{c_t}; flex-shrink:0;">{str(get_data(f'h_text_{i}','')).replace(chr(10),'<br>')}</div>
                    <div style="flex-shrink:0;">{h_am_html}</div>
                    <div style="flex-shrink:0;">{adv_html}</div>
                    <div style="flex:1; min-height:8px;"></div>
                    <div style="display:flex; gap:12px; flex-shrink:0; aspect-ratio:3/1;">
                        <div style="flex:1; border-radius:8px; overflow:hidden; border:1px solid #eee; background:#fcfcfc;">{_img_tag(h2, 'FOT DÓŁ 1')}</div>
                        <div style="flex:1; border-radius:8px; overflow:hidden; border:1px solid #eee; background:#fcfcfc;">{_img_tag(h3, 'FOT DÓŁ 2')}</div>
                    </div>
                </div></div>{fh}""", f"slide-hotel-{i}"))
    # --- Przerywnik sek_3 (przed programem) ---
    _render_sek(3)  # Przerywnik przed programem
    # --- Program wyjazdu ---
    if _should_render('slide-program', current_page, export_mode) and not get_data('prg_hide', False):
        nd = get_data('num_days', 5)
        start_dt_local = get_data('p_start_dt', date.today())
        for st_idx in range(0, nd, 3):
            ch = ""
            for i in range(3):
                di = st_idx + i
                if di < nd:
                    cdt = start_dt_local + timedelta(days=di)
                    id_img = get_b64(f'img_d_{di}', (16, 9))
                    mh = ""
                    for pi in range(get_data('num_places', 0)):
                        p_day = str(get_data(f"pday_{pi}") or "")
                        d_match = re.search(r'Dzień\s+(\d+)', p_day)
                        if d_match and int(d_match.group(1)) == di + 1:
                            nm = get_data(f"pmain_{pi}", "")
                            if get_data(f"phide_{pi}"):
                                mh += f"<div><div style='display:flex; align-items:center; gap:8px; font-size:15px; font-weight:600; color:{c_t}; margin-bottom:5px;'><span style='font-size:18px; color:{acc};'><i class='fa-solid fa-map-location-dot'></i></span> <span>{nm}</span></div></div>"
                            else:
                                mh += f"<div><a href='#place_{pi}' style='text-decoration:none; color:{acc}; display:flex; align-items:center; gap:8px; font-size:15px; font-weight:600; margin-bottom:5px;'><span style='font-size:18px;'><i class='fa-solid fa-map-location-dot'></i></span> <span>{nm} <span style='font-size:12px; font-weight:400; opacity:0.8;'>(zobacz)</span></span></a></div>"
                    for ai in range(get_data('num_attr', 0)):
                        a_day = str(get_data(f"aday_{ai}") or "")
                        d_match = re.search(r'Dzień\s+(\d+)', a_day)
                        if d_match and int(d_match.group(1)) == di + 1:
                            ic = icon_map.get(get_data(f"atype_{ai}", "Atrakcja"), "")
                            nm = get_data(f"amain_{ai}", "")
                            sub = str(get_data(f"asub_{ai}", "")).strip()
                            opt_label_p = str(get_data(f"aopt_label_{ai}", "") or "").strip()
                            opt_suffix = f" <span style='color:{acc}; font-weight:600;'>({opt_label_p})</span>" if opt_label_p else ""
                            sub_html = (f"<div style='font-size:12px; font-weight:400; color:{c_t}; opacity:0.8; margin-top:-2px; margin-left:26px; line-height:1.2; margin-bottom:8px;'>{sub}</div>"
                                        if sub else "<div style='margin-bottom:8px;'></div>")
                            if get_data(f"ahide_{ai}"):
                                mh += f"<div><div style='display:flex; align-items:center; gap:8px; font-size:15px; font-weight:600; color:{c_t};'><span style='font-size:18px; color:{acc};'>{ic}</span> <span>{nm}{opt_suffix}</span></div>{sub_html}</div>"
                            else:
                                mh += f"<div><a href='#attr_{ai}' style='text-decoration:none; color:{acc}; display:flex; align-items:center; gap:8px; font-size:15px; font-weight:600;'><span style='font-size:18px;'>{ic}</span> <span>{nm}{opt_suffix} <span style='font-size:12px; font-weight:400; opacity:0.8;'>(zobacz)</span></span></a>{sub_html}</div>"
                    ch += f"""<div style="flex:1;display:flex;flex-direction:column;" id="program_day_{di}">
                        <div class="day-header">DZIEŃ {di+1}</div>
                        <div class="day-date">{cdt.strftime('%d.%m.%Y')} - {pl_days_map[cdt.weekday()]}</div>
                        <div class="prog-img-container">{_img_tag(id_img, 'FOTO DNIA')}</div>
                        <div class="prog-attr">{str(get_data(f'attr_{di}') or '').replace(chr(10),'<br>')}</div>
                        {mh}
                        <p style="font-size:13px; margin-top:10px; line-height: 1.5;">{str(get_data(f'desc_{di}') or '').replace(chr(10),'<br>')}</p>
                    </div>"""
                else:
                    ch += "<div style='flex:1;'></div>"
            hp.append(_shtml(f"""{lh}<div class="title-h2">PROGRAM WYJAZDU</div>
                <div style="display:flex;gap:25px;flex-grow:1;min-height:0;margin-top:15px;margin-bottom:20px;">{ch}</div>{fh}""",
                             "slide-program" if st_idx == 0 else ""))
    
    # --- Przerywnik sek_1 (przed attr) ---
    _render_sek(1)  # Przerywnik przed atrakcjami
    # --- Miejsca i atrakcje w kolejności place_attr_order ---
    _pa_order = get_data('place_attr_order', [])
    if not _pa_order:
        _tmp_p = []
        for _pi in range(get_data('num_places', 0)):
            _pday = str(get_data(f"pday_{_pi}") or "")
            _m = re.search(r'Dzień\s+(\d+)', _pday)
            _tmp_p.append(('place', _pi, int(_m.group(1)) if _m else 999))
        _tmp_a = []
        for _ai in range(get_data('num_attr', 0)):
            _aday = str(get_data(f"aday_{_ai}") or "")
            _m = re.search(r'Dzień\s+(\d+)', _aday)
            _tmp_a.append(('attr', _ai, int(_m.group(1)) if _m else 999))
        _pa_order = [
            [t, idx] for t, idx, _ in sorted(
                _tmp_p + _tmp_a,
                key=lambda x: (x[2], 0 if x[0] == 'place' else 1, x[1])
            )
        ]
    for item_type, i in [(str(t), int(idx)) for t, idx in _pa_order]:
        
        # --- Slajd HOTELU (zachowany dla kompatybilności) ---
        if item_type == 'hotel':
            if get_data(f'h_hide_{i}', False):
                continue
                
            # ✅ KRYTYCZNA OPTYMALIZACJA: Leniwe renderowanie (odcina lagi)
            if not export_mode and not _should_render(f"slide-hotel-{i}", current_page, export_mode):
                continue
                
            h1 = get_b64(f'img_hotel_1_{i}', (16, 9))
            h1b = get_b64(f'img_hotel_1b_{i}', (16, 9))
            h2 = get_b64(f'img_hotel_2_{i}', (16, 9))
            h3 = get_b64(f'img_hotel_3_{i}', (16, 9))
            h1_html = _img_tag(h1, 'ZDJ. LEWE 1')
            h1b_html = _img_tag(h1b, 'ZDJ. LEWE 2')
            url_val = str(get_data(f'h_url_{i}', '')).strip()
            h_url_html = (f'<div style="font-size:{max(10,fs_t-2)}px; color:{c_t}; opacity:0.8; margin-bottom:15px;"><i class="fa-solid fa-globe" style="color:{acc}; margin-right:5px;"></i> {url_val}</div>' if url_val else '')
            h_amenities = get_data(f'h_amenities_{i}', [])
            am_items = []
            book_val = str(get_data(f'h_booking_{i}', '')).strip()
            if book_val:
                am_items.append(f'<div style="display:flex; align-items:center; gap:6px; margin-right:10px;"><div style="background:#003580; color:white; padding:3px 8px; border-radius:6px; border-bottom-left-radius:0; font-family:\'Montserrat\', sans-serif; font-weight:800; font-size:{max(12,fs_t)}px;">{book_val}</div><span style="font-family:\'Montserrat\', sans-serif; font-weight:700; color:#003580; font-size:{max(10,fs_t-1)}px;">Booking.com</span></div>')
            for a in h_amenities:
                if a in hotel_icons:
                    am_items.append(f'<div style="display:flex; align-items:center; gap:6px; font-size:{max(10,fs_t-1)}px; font-weight:600; color:{c_t};"><i class="fa-solid {hotel_icons[a]}" style="color:{acc}; font-size:{fs_t+4}px;"></i> {a}</div>')
            h_am_html = (f'<div style="display:flex; flex-wrap:wrap; align-items:center; gap:15px; margin-bottom:15px; padding:10px 0; border-top:1px solid #eee; border-bottom:1px solid #eee;">{"".join(am_items)}</div>' if am_items else '')
            advs = [f.strip() for f in get_data(f'h_advantages_{i}', '').split('\n') if f.strip()]
            adv_html = (f'<ul class="app-list" style="margin-top:0;">{"".join([f"<li>{a}</li>" for a in advs])}</ul>' if advs else '')
            hp.append(_shtml(f"""{lh}<div class="premium-layout" id="slide-hotel-{i}">
                <div style="flex:40; display:flex; flex-direction:column; gap:15px;">
                    <div style="flex:1; border-radius:8px; overflow:hidden; border:1px solid #eee; background-color:#fcfcfc;">{h1_html}</div>
                    <div style="flex:1; border-radius:8px; overflow:hidden; border:1px solid #eee; background-color:#fcfcfc;">{h1b_html}</div>
                </div>
                <div class="info-col" style="flex:60; padding-left:15px; padding-top:30px; justify-content:flex-start;">
                    <div class="app-overline-style" style="margin-bottom:5px;"><span>{str(get_data(f'h_overline_{i}','ZAKWATEROWANIE'))}</span></div>
                    <div class="title-h1" style="margin-bottom:5px; font-size:{max(20,fs_h1_val-6)}px;">{str(get_data(f'h_title_{i}','')).replace(chr(10),'<br>')}</div>
                    <div class="title-sub" style="color:{acc}; font-size:{max(12,fs_sub_val-4)}px; margin-top:0px; margin-bottom:5px;">{str(get_data(f'h_subtitle_{i}','')).replace(chr(10),'<br>')}</div>
                    {h_url_html}
                    <div style="flex-grow:0; font-size:{fs_t}px; line-height:1.4; margin-bottom:10px; color:{c_t};">{str(get_data(f'h_text_{i}','')).replace(chr(10),'<br>')}</div>
                    {h_am_html}
                    <div style="flex-grow:1;">{adv_html}</div>
                    <div class="gallery-row" style="padding-top:0; padding-bottom:5px; gap:15px;">
                        <div class="gallery-thumb" style="aspect-ratio: unset; height:140px;">{_img_tag(h2, 'FOT DÓŁ 1')}</div>
                        <div class="gallery-thumb" style="aspect-ratio: unset; height:140px;">{_img_tag(h3, 'FOT DÓŁ 2')}</div>
                    </div>
                </div></div>{fh}""", f"slide-hotel-{i}"))

    # --- Slajd MIEJSCA (układ: foto pionowe + opis + 3 miniatury) ---
        elif item_type == 'place':
            if get_data(f"phide_{i}"):
                continue
                
            # ✅ POPRAWNA BLOKADA (ZGODNA Z MENU):
            if not export_mode and not _should_render(f"place_{i}", current_page, export_mode):
                continue

            ik_p = get_b64(f'pimg1_{i}', (4, 5))
            imk_p = _img_tag(ik_p, 'FOTO MIEJSCA')
            tk1_p = get_b64(f'pimg2_{i}', (1, 1))
            tk2_p = get_b64(f'pimg3_{i}', (1, 1))
            tk3_p = get_b64(f'pimg4_{i}', (1, 1))
            bb_p = ""
            md_p = re.search(r'Dzień (\d+)', str(get_data(f"pday_{i}") or ""))
            if md_p:
                bb_p = f"<a href='#program_day_{int(md_p.group(1)) - 1}' class='floating-btn'>WRÓĆ DO PROGRAMU</a>"
            p_over = str(get_data(f'pover_{i}') or 'NASZ KIERUNEK')
            p_main = str(get_data(f'pmain_{i}') or '').replace(chr(10), '<br>')
            p_sub  = str(get_data(f'psub_{i}')  or '').replace(chr(10), '<br>')
            p_opis = str(get_data(f'popis_{i}') or '').replace(chr(10), '<br>')
            hp.append(_shtml(f"""{lh}<div class="premium-layout" id="place_{i}">
                <div class="photo-col">{imk_p}{bb_p}</div>
                <div class="info-col" style="padding-top:30px; justify-content:flex-start;">
                    <div class="app-overline-style" style="margin-bottom:15px;"><span>{p_over}</span></div>
                    <div class="title-h1" style="margin-bottom:5px; font-size:{fs_h1_val-6}px;">{p_main}</div>
                    <div class="title-sub" style="margin-bottom:15px;">{p_sub}</div>
                    <div style="flex-grow:1;"><p style="font-size:{fs_t}px; line-height:1.6; color:{c_t};">{p_opis}</p></div>
                    <div class="gallery-row" style="padding-top:0; padding-bottom:5px;">
                        <div class="gallery-thumb">{_img_tag(tk1_p, 'FOT 1')}</div>
                        <div class="gallery-thumb">{_img_tag(tk2_p, 'FOT 2')}</div>
                        <div class="gallery-thumb">{_img_tag(tk3_p, 'FOT 3')}</div>
                    </div>
                </div>
            </div>{fh}""", f"place_{i}"))
            
    # --- Slajd ATRAKCJI ---
        elif item_type == 'attr':
            if get_data(f"ahide_{i}"):
                continue
            
            # ✅ POPRAWNA BLOKADA (ZGODNA Z MENU):
            if not export_mode and not _should_render(f"attr_{i}", current_page, export_mode):
                continue
                        
            iah = get_b64(f'ah_{i}', (4, 5))
            a1 = get_b64(f'at1_{i}', (1, 1))
            a2 = get_b64(f'at2_{i}', (1, 1))
            a3 = get_b64(f'at3_{i}', (1, 1))
            bb_a = ""
            md_a = re.search(r'Dzień (\d+)', str(get_data(f"aday_{i}") or ""))
            if md_a:
                # W trybie edycji przycisk wizualny bez działania (klient w HTML eksporcie ma działający href)
                if export_mode:
                    bb_a = f"<a href='#program_day_{int(md_a.group(1)) - 1}' class='floating-btn'>WRÓĆ DO PROGRAMU</a>"
                else:
                    bb_a = f"<span class='floating-btn' style='cursor:default;'>WRÓĆ DO PROGRAMU</span>"
            # Pas ikon opisu atrakcji (Model 2)
            _attr_icons = get_data(f'aicons_{i}', []) or []
            _attr_icons_items = []
            for _entry in _attr_icons:
                if not isinstance(_entry, dict):
                    continue
                _ic_id = _entry.get('icon_id', '')
                _ic_val = str(_entry.get('value', '') or '').strip()
                _ic_data = ATTR_ICONS_AVAILABLE.get(_ic_id)
                if not _ic_data:
                    continue
                _ic_fa = _ic_data['icon']
                _attr_icons_items.append(
                    f'<div style="display:flex; align-items:center; gap:8px; '
                    f'font-size:{max(10,fs_t-1)}px; font-weight:600; color:{c_t}; '
                    f'min-width:0;">'
                    f'<i class="fa-solid {_ic_fa}" style="color:{acc}; font-size:{fs_t+4}px; flex-shrink:0;"></i>'
                    f'<span style="white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{_ic_val if _ic_val else _ic_data["label"]}</span>'
                    f'</div>'
                )
            _attr_icons_html = (
                f'<div style="display:grid; grid-template-columns:repeat(3, 1fr); '
                f'gap:10px 14px; margin-top:14px; padding:12px 0; '
                f'border-top:1px solid {acc}; flex-shrink:0;">'
                f'{"".join(_attr_icons_items)}</div>'
                if _attr_icons_items else ''
            )
            
            # Chip "OPCJA" (lub inna etykieta) - prawy górny róg zdjęcia
            _aopt_text = str(get_data(f'aopt_label_{i}', '') or '').strip()
            _aopt_chip = (
                f'<div style="position:absolute; top:14px; right:14px; '
                f'background:{acc}; color:#fff; padding:6px 14px; '
                f'border-radius:4px; font-family:\'{f_met}\'; '
                f'font-size:11px; font-weight:700; letter-spacing:1.5px; '
                f'text-transform:uppercase; white-space:nowrap; '
                f'box-shadow:0 2px 8px rgba(0,0,0,0.15); z-index:5;">'
                f'{_aopt_text}</div>'
                if _aopt_text else ''
            )
            
            hp.append(_shtml(f"""{lh}<div class="premium-layout" id="attr_{i}">
                <div class="photo-col" style="position:relative;">{_img_tag(iah, 'FOTO GŁÓWNE')}{bb_a}{_aopt_chip}</div>
                <div class="info-col" style="display:flex; flex-direction:column; height:100%; min-height:0;">
                    {f'<div class="type-icon-box" style="flex-shrink:0;">{icon_map.get(get_data(f"atype_{i}",""),"")}</div>' if get_data(f"atype_{i}") and get_data(f"atype_{i}") not in ("Brak", "Wybierz ikonę") else ''}
                    <div class="title-h2" style="flex-shrink:0;">{str(get_data(f'amain_{i}','')).replace(chr(10),'<br>')}</div>
                    <div class="title-sub" style="flex-shrink:0;">{str(get_data(f'asub_{i}','')).replace(chr(10),'<br>')}</div>
                    <div style="flex:1 1 0; min-height:0; overflow:hidden;"><p style="margin:0;">{str(get_data(f'aopis_{i}') or '').replace(chr(10),'<br>')}</p></div>
                    {_attr_icons_html}
                    <div class="gallery-row" style="flex-shrink:0; min-height:110px; margin-top:14px;">
                        <div class="gallery-thumb">{_img_tag(a1, 'FOT 1')}</div>
                        <div class="gallery-thumb">{_img_tag(a2, 'FOT 2')}</div>
                        <div class="gallery-thumb">{_img_tag(a3, 'FOT 3')}</div>
                    </div></div></div>{fh}""", f"attr_{i}"))
                    
    # --- Serwisy dodatkowe (nowy przerywnik) ---
    _render_sek(4)     
    
    # --- 12. Aplikacja ---
    if _should_render('slide-app', current_page, export_mode):
        ibg = get_b64('img_app_bg', (16, 9))
        bg_html = _img_tag(ibg, 'ZDJĘCIE TŁA')
        iscr = get_b64('img_app_screen', (9, 16))
        # Systemowe rozwiązanie: obraz ekranu jako background-image telefonu.
        # Eliminuje problem overlay <img> w @media print - background-image działa
        # niezawodnie w Chrome/Opera print gdy włączona "Grafika w tle".
        # Style pozycjonowania INLINE - specyficzność wyższa niż @media print,
        # co gwarantuje że telefon zawsze jest w tym samym miejscu (ekran/druk).
        if iscr:
            _phone_style = (
                f"position:absolute; top:50%; left:58%; "
                f"transform:translate(-50%,-50%); width:260px; height:480px; "
                f"border:8px solid #111; border-radius:30px; "
                f"box-shadow:-15px 20px 40px rgba(0,0,0,0.4); z-index:10; "
                f"background-image:url({iscr}); background-size:cover; "
                f"background-position:top center; background-repeat:no-repeat; "
                f"background-color:#fff;"
            )
        else:
            _phone_style = (
                "position:absolute; top:50%; left:58%; "
                "transform:translate(-50%,-50%); width:260px; height:480px; "
                "border:8px solid #111; border-radius:30px; "
                "box-shadow:-15px 20px 40px rgba(0,0,0,0.4); z-index:10; "
                "background-color:#fff;"
            )
        fh_app = "".join([f"<li>{f.strip()}</li>" for f in get_data('app_features', '').split('\n') if f.strip()])
        hp.append(_shtml(f"""{lh}<div style="position:relative;height:100%;width:100%;display:flex; overflow:hidden;">
            <div style="flex:0 0 44%; max-width:44%; z-index:2; display:flex; flex-direction:column; padding-right:16px; padding-top:15px; justify-content:flex-start;">
                <div class="app-overline-style"><span>{str(get_data('app_overline',''))}</span></div>
                <div class="title-h1" style="margin-bottom:10px; font-size:{fs_h1_val-8}px;">{str(get_data('app_title','')).replace(chr(10),'<br>')}</div>
                <div class="title-sub" style="margin-bottom:14px; font-size:{max(10,fs_sub_val-6)}px;">{str(get_data('app_subtitle','')).replace(chr(10),'<br>')}</div>
                <ul class="app-list" style="margin-top:0;">{fh_app}</ul></div>
            <div class="app-image-col" style="top:-30px;right:-45px;bottom:0;">{bg_html}</div>
            <div class="phone-mockup" style="{_phone_style}"></div></div>{fh}""", "slide-app"))
            
    # --- Branding ---
    if _should_render('slide-branding', current_page, export_mode):
        b1 = get_b64('img_brand_1', (1, 1))
        b2 = get_b64('img_brand_2', (1, 1))
        b3 = get_b64('img_brand_3', (16, 9))
        b1h = _img_tag(b1, 'ZDJ 1')
        b2h = _img_tag(b2, 'ZDJ 2')
        b3h = (_img_tag(b3, 'ZDJ 3') + '<div class="brand-gap"></div>') if b3 else _get_ph('ZDJ 3')

        _bg_font = str(get_data('brand_groups_font', 'Inter'))

        def _brand_group(title_key, items_key):
            _title = str(get_data(title_key, '') or '').strip()
            _items = [x.strip() for x in str(get_data(items_key, '') or '').split('\n') if x.strip()]
            if not _title and not _items:
                return ''
            _title_html = (
                f"<div style='font-family:\"{_bg_font}\"; font-weight:600; font-size:{max(11, fs_t)}px; "
                f"color:#333333; text-transform:uppercase; letter-spacing:2px; "
                f"margin-bottom:14px;'>{_title}</div>"
                if _title else ''
            )
            _items_html = (
                f"<ul class='app-list' style='margin-top:0; margin-bottom:0;'>"
                + "".join([f"<li>{x}</li>" for x in _items]) + "</ul>"
                if _items else ''
            )
            return f"<div style='margin-bottom:24px;'>{_title_html}{_items_html}</div>"

        groups_html = (
            _brand_group('brand_g1_title', 'brand_g1_items')
            + _brand_group('brand_g2_title', 'brand_g2_items')
            + _brand_group('brand_g3_title', 'brand_g3_items')
        )

        hp.append(_shtml(f"""{lh}<div class="premium-layout">
            <div class="info-col" style="flex: 55; padding-right: 30px; padding-top: 15px; justify-content: flex-start;">
                <div class="app-overline-style"><span>{str(get_data('brand_overline',''))}</span></div>
                <div class="title-h1" style="margin-bottom: 10px; font-size:{fs_h1_val-8}px;">{str(get_data('brand_title','')).replace(chr(10),'<br>')}</div>
                <div class="title-sub" style="margin-bottom:12px; font-size:{max(10,fs_sub_val-6)}px;">{str(get_data('brand_subtitle','')).replace(chr(10),'<br>')}</div>
                <div style="margin-top:20px;">{groups_html}</div>
                {f'<div style="margin-top:20px; font-family:\'{f_t}\'; font-size:{max(12, fs_t)}px; font-style:italic; color:{c_t}; line-height:1.5;">{str(get_data("brand_footer","")).replace(chr(10),"<br>")}</div>' if str(get_data("brand_footer","")).strip() else ''}
            </div>
            <div style="flex: 50; position: relative; height: 100%;"><div class="brand-collage">
                <div class="brand-img-1">{b1h}</div><div class="brand-img-2">{b2h}</div><div class="brand-img-3">{b3h}</div>
            </div></div></div>{fh}""", "slide-branding"))
    # --- Wirtualny asystent ---
    if _should_render('slide-virtual-assistant', current_page, export_mode):
        va1 = get_b64('img_va_1', (16, 9))
        va2 = get_b64('img_va_2', (1, 1))
        va3 = get_b64('img_va_3', (1, 1))
        v1h = _img_tag(va1, 'ZDJ 1')
        v2h = _img_tag(va2, 'ZDJ 2')
        v3h = _img_tag(va3, 'ZDJ 3')
        hp.append(_shtml(f"""{lh}<div class="premium-layout">
            <div style="flex: 45; position: relative; height: 100%;"><div class="va-collage">
                <div class="va-img-1-wrap va-img-common">{v1h}</div>
                <div class="va-img-2-wrap va-img-common">{v2h}</div>
                <div class="va-img-3-wrap va-img-common">{v3h}</div>
            </div></div>
            <div class="info-col" style="flex: 55; padding-left: 40px; padding-top: 15px; justify-content: flex-start;">
                <div class="app-overline-style"><span>{str(get_data('va_overline',''))}</span></div>
                <div class="title-h1" style="margin-bottom: 15px; font-size:{fs_h1_val-6}px;">{str(get_data('va_title','')).replace(chr(10),'<br>')}</div>
                <div class="title-sub" style="margin-bottom:25px; font-size:{max(12,fs_sub_val-4)}px;">{str(get_data('va_subtitle','')).replace(chr(10),'<br>')}</div>
                <div style="font-family: '{f_t}'; font-size: {fs_t}px; line-height: 1.6; color: {c_t}; text-align: justify;">{str(get_data('va_text') or '').replace(chr(10),'<br>')}</div>
            </div></div>{fh}""", "slide-virtual-assistant"))
    # --- Pillow gifts ---
    if _should_render('slide-pillow-gifts', current_page, export_mode):
        pg1 = get_b64('img_pg_1', (1, 1))
        pg2 = get_b64('img_pg_2', (1, 2.1))
        pg3 = get_b64('img_pg_3', (1, 1))
        h1_pg = _img_tag(pg1, 'ZDJ 1')
        h2_pg = _img_tag(pg2, 'ZDJ 2 PION')
        h3_pg = _img_tag(pg3, 'ZDJ 3')
        hp.append(_shtml(f"""{lh}<div class="premium-layout">
            <div style="flex:50;position:relative;height:100%;"><div class="pg-collage">
                <div class="pg-img-1-wrap pg-img-common">{h1_pg}</div>
                <div class="pg-img-2-wrap pg-img-common">{h2_pg}</div>
                <div class="pg-img-3-wrap pg-img-common">{h3_pg}</div>
            </div></div>
            <div class="info-col" style="flex:50;padding-left:40px;padding-top:15px;justify-content:flex-start;">
                <div class="app-overline-style">{str(get_data('pg_overline',''))}</div>
                <div class="title-h1" style="margin-bottom:10px; font-size:{fs_h1_val-8}px;">{str(get_data('pg_title','')).replace(chr(10),'<br>')}</div>
                <div class="title-sub" style="margin-bottom:12px; font-size:{max(10,fs_sub_val-6)}px;">{str(get_data('pg_subtitle','')).replace(chr(10),'<br>')}</div>
                <div style="font-family:'{f_t}';font-size:{max(10,fs_t-1)}px;line-height:1.5;color:{c_t};margin-bottom:10px;">{str(get_data('pg_text') or '').replace(chr(10),'<br>')}</div>
                {f'<ul class="app-list" style="margin-top:0;">{"".join([f"<li>{x.strip()}</li>" for x in str(get_data("pg_features","")).split(chr(10)) if x.strip()])}</ul>' if get_data('pg_features','').strip() else ''}
            </div></div>{fh}""", "slide-pillow-gifts"))
    # --- Kosztorys (slajd 1) ---
    if _should_render('slide-kosztorys-1', current_page, export_mode):
        k1 = get_b64('img_koszt_1', (4, 5))
        imk1 = _img_tag(k1, 'ZDJĘCIE KOSZTORYSU')
        zaw1_list = []
        for x in get_data('koszt_zawiera_1', '').split('\n'):
            if not x.strip(): continue
            if x.strip().startswith('--'):
                zaw1_list.append(f"<li class='sub-item'>{x.replace('--','',1).strip()}</li>")
            else:
                zaw1_list.append(f"<li>{x.strip()}</li>")
        zaw1_html = f'<ul class="app-list">{"".join(zaw1_list)}</ul>' if zaw1_list else ''
        hp.append(_shtml(f"""{lh}<div class="premium-layout"><div class="photo-col">{imk1}</div>
            <div class="info-col" style="padding-top:15px; justify-content:flex-start;">
            <div class="app-overline-style" style="margin-bottom:5px;"><span>{str(get_data('koszt_title','KOSZTORYS'))}</span></div>
            <div class="title-h1" style="margin-bottom:15px; font-size:{fs_h1_val}px;">{str(get_data('koszt_h1_title','KOSZTORYS'))}</div>
            <div style="background:{acc}; color:white; padding: 25px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 10px 25px rgba(0,0,0,0.1);">
                <div style="font-size:{max(10,fs_t-2)}px; font-family:'{f_h2}'; font-weight:700; text-transform:uppercase; margin-bottom:5px; opacity:0.9; letter-spacing:1px;">Grupa {get_data('koszt_pax','')} osób | {get_data('koszt_hotel','')}</div>
                <div style="font-size:{fs_h1_val-8}px; font-weight:800; font-family:'{f_h1}';">CENA: {get_data('koszt_price','')}</div>
            </div>
            <div style="font-family:'{f_h2}'; font-weight:800; font-size:{fs_t+4}px; color:{c_h2}; margin-bottom:10px; text-transform:uppercase;">CENA OFERTY OBEJMUJE:</div>
            <div style="flex-grow:1; overflow-y:auto; padding-right:10px;">{zaw1_html}</div>
            </div></div>{fh}""", "slide-kosztorys-1"))
    # --- Kosztorys (slajd 2) ---
    if _should_render('slide-kosztorys-2', current_page, export_mode):
        k2 = get_b64('img_koszt_2', (4, 5))
        imk2 = _img_tag(k2, 'ZDJĘCIE KOSZTORYSU 2')
        zaw2_list = []
        for x in get_data('koszt_zawiera_2', '').split('\n'):
            if not x.strip(): continue
            if x.strip().startswith('--'):
                zaw2_list.append(f"<li class='sub-item'>{x.replace('--','',1).strip()}</li>")
            else:
                zaw2_list.append(f"<li>{x.strip()}</li>")
        zaw2_html = f'<ul class="app-list">{"".join(zaw2_list)}</ul>' if zaw2_list else ''
        niezaw_list = [f"<li>{x.strip()}</li>" for x in get_data('koszt_nie_zawiera', '').split('\n') if x.strip()]
        niezaw_html = f'<ul class="app-list" style="margin-top:5px;">{"".join(niezaw_list)}</ul>' if niezaw_list else ''
        opcje = get_data('koszt_opcje', '').strip()
        opcje_html = (f"""<div style="margin-top:20px;"><div style="font-family:'{f_h2}'; font-weight:800; font-size:{fs_t+2}px; color:{c_h2}; margin-bottom:5px; text-transform:uppercase;">KOSZTY OPCJONALNE:</div><div style="font-family:'{f_t}'; font-size:{fs_t}px; color:{c_t}; white-space:pre-line; line-height:1.5;">{opcje}</div></div>"""
                      if opcje else '')
        hp.append(_shtml(f"""{lh}<div class="premium-layout">
            <div class="info-col" style="padding-top:15px; justify-content:flex-start; padding-right:30px;">
                <div class="app-overline-style" style="margin-bottom:15px;"><span>KOSZTORYS - CIĄG DALSZY</span></div>
                {zaw2_html}
                <div style="font-family:'{f_h2}'; font-weight:800; font-size:{fs_t+2}px; color:{c_h2}; margin-top:15px; margin-bottom:5px; text-transform:uppercase;">NIE POLICZONE W CENIE:</div>
                {niezaw_html}
                {opcje_html}
            </div>
            <div class="photo-col">{imk2}</div>
            </div>{fh}""", "slide-kosztorys-2"))
    # --- 18. Przerywnik nasza agencja (sek_2) ---
    _render_sek(2)
   
    # --- 18b. ESG (Odpowiedzialny partner) ---
    if _should_render('slide-esg', current_page, export_mode):
        _esg_overline = str(get_data('esg_overline', 'ODPOWIEDZIALNOŚĆ'))
        _esg_title = str(get_data('esg_title', '')).replace(chr(10), '<br>')
        _esg_subtitle = str(get_data('esg_subtitle', '')).replace(chr(10), '<br>')
        _esg_intro = str(get_data('esg_intro', '')).replace(chr(10), '<br>')
        
        # Helper: karta ESG z watermark literą w tle
        def _esg_card(letter, icon_fa, title, sub, items_raw):
            _items = [x.strip() for x in str(items_raw or '').split('\n') if x.strip()]
            _items_html = ''.join([
                f'<li style="margin-bottom:8px; font-family:\'{f_t}\'; '
                f'font-size:{fs_t}px; color:{c_t}; line-height:1.4; '
                f'padding-left:18px; position:relative;">'
                f'<span style="position:absolute; left:0; top:0; color:{acc}; '
                f'font-weight:700; font-size:1.1em;">›</span>{x}</li>'
                for x in _items
            ])
            return (
                f'<div style="flex:1; background:#fff; border:1px solid {acc}; '
                f'border-radius:8px; padding:18px 22px 16px 22px; position:relative; '
                f'overflow:hidden; display:flex; flex-direction:column;">'
                # Watermark litera w tle (E/S/G) - bardzo jasna, duża
                f'<div style="position:absolute; top:-30px; right:-15px; '
                f'font-family:\'{f_h1}\'; font-weight:900; font-size:180px; '
                f'color:{acc}; opacity:0.08; line-height:1; pointer-events:none; '
                f'user-select:none;">{letter}</div>'
                # Ikona
                f'<div style="margin-bottom:14px; position:relative; z-index:1;">'
                f'<i class="fa-solid {icon_fa}" style="color:{acc}; '
                f'font-size:32px;"></i></div>'
                # Tytuł kategorii
                f'<div style="font-family:\'{f_h2}\'; font-weight:800; '
                f'font-size:{fs_t+4}px; color:{c_h2}; text-transform:uppercase; '
                f'letter-spacing:1.5px; margin-bottom:2px; position:relative; z-index:1;">'
                f'{title}</div>'
                # Podtytuł kategorii (PL)
                f'<div style="font-family:\'{f_t}\'; font-size:{fs_t}px; '
                f'color:{acc}; font-weight:600; margin-bottom:10px; '
                f'position:relative; z-index:1;">{sub}</div>'
                # Linia separatora
                f'<div style="width:40px; height:2px; background:{acc}; '
                f'margin-bottom:14px; position:relative; z-index:1;"></div>'
                # Lista punktów
                f'<ul style="list-style:none; padding:0; margin:0; '
                f'position:relative; z-index:1; flex:1;">{_items_html}</ul>'
                f'</div>'
            )
        
        _card_e = _esg_card(
            'E', 'fa-leaf',
            str(get_data('esg_e_title', 'ENVIRONMENTAL')),
            str(get_data('esg_e_sub', 'Środowisko')),
            get_data('esg_e_items', ''),
        )
        _card_s = _esg_card(
            'S', 'fa-people-group',
            str(get_data('esg_s_title', 'SOCIAL')),
            str(get_data('esg_s_sub', 'Społeczność')),
            get_data('esg_s_items', ''),
        )
        _card_g = _esg_card(
            'G', 'fa-shield-halved',
            str(get_data('esg_g_title', 'GOVERNANCE')),
            str(get_data('esg_g_sub', 'Ład korporacyjny')),
            get_data('esg_g_items', ''),
        )
        
        # Helper: pole metryki ESG (pomarańczowe tło, biały tekst)
        # Wszystkie 3 pola opcjonalne — pole renderuje się jeśli ma cokolwiek.
        # 'number' = duża górna treść (może być liczbą lub tekstem)
        # 'value' = mniejsza jednostka/dopełnienie obok
        # 'label' = mała etykieta u dołu
        def _esg_metric(number, value, label):
            number = str(number or '').strip()
            value = str(value or '').strip()
            label = str(label or '').strip()
            if not number and not value and not label:
                return ''
            # Górny rząd (number + ewentualnie value obok)
            if number and value:
                top_html = (
                    f'<div style="display:flex; align-items:baseline; gap:4px; '
                    f'margin-bottom:2px; flex-wrap:wrap; line-height:1;">'
                    f'<span style="font-family:\'{f_h1}\'; font-weight:800; '
                    f'font-size:{fs_t+3}px; color:#ffffff; line-height:1;">{number}</span>'
                    f'<span style="font-family:\'{f_t}\'; font-weight:600; '
                    f'font-size:{max(9,fs_t-3)}px; color:#ffffff; line-height:1;">{value}</span>'
                    f'</div>'
                )
            elif number:
                top_html = (
                    f'<div style="font-family:\'{f_h1}\'; font-weight:800; '
                    f'font-size:{fs_t+3}px; color:#ffffff; margin-bottom:2px; '
                    f'line-height:1.1;">{number}</div>'
                )
            elif value:
                top_html = (
                    f'<div style="font-family:\'{f_h2}\'; font-weight:700; '
                    f'font-size:{max(10,fs_t-1)}px; color:#ffffff; margin-bottom:2px; '
                    f'line-height:1.2;">{value}</div>'
                )
            else:
                top_html = ''
            label_html = (
                f'<div style="font-family:\'{f_met}\'; font-size:{max(8,fs_met-6)}px; '
                f'font-weight:700; letter-spacing:1px; color:#ffffff; '
                f'text-transform:uppercase; line-height:1.2;">{label}</div>'
                if label else ''
            )
            return (
                f'<div style="background:{acc}; padding:6px 10px; '
                f'border-radius:5px; min-height:40px; display:flex; '
                f'flex-direction:column; justify-content:center;">'
                f'{top_html}{label_html}</div>'
            )
        
        _metrics_html_parts = []
        for _i in range(1, 7):  # 6 pól (po 2 na każdy obszar E/S/G)
            _m = _esg_metric(
                get_data(f'esg_m{_i}_number', ''),
                get_data(f'esg_m{_i}_value', ''),
                get_data(f'esg_m{_i}_label', ''),
            )
            if _m:
                _metrics_html_parts.append(_m)
        
        # Pasek metryk - siatka 3×2 (6 pól)
        # margin-top:10px - mniejszy odstęp od kart żeby pasek był wyżej
        # margin-bottom:8px - mniejszy odstęp od cytatu poniżej
        _metrics_section_html = ''
        if _metrics_html_parts:
            _metrics_section_html = (
                f'<div style="display:grid; grid-template-columns:repeat(3, 1fr); '
                f'gap:8px; margin-top:10px; margin-bottom:8px;">'
                + ''.join(_metrics_html_parts) +
                '</div>'
            )
        
        # === CYTAT z Think MICE ===
        _esg_quote_text = str(get_data('esg_quote', '')).strip()
        _esg_quote_src = str(get_data('esg_quote_source', '')).strip()
        _esg_quote_html = ''
        if _esg_quote_text:
            _src_html = (
                f'<span style="font-family:\'{f_t}\'; font-size:{max(9,fs_t-3)}px; '
                f'color:{acc}; font-weight:700; letter-spacing:0.5px; '
                f'text-transform:uppercase;"> — {_esg_quote_src}</span>'
                if _esg_quote_src else ''
            )
            _esg_quote_html = (
                f'<div style="margin-top:6px; padding:10px 16px; '
                f'border-left:3px solid {acc}; background:#f8fafc; '
                f'font-family:\'{f_t}\'; font-size:{max(11,fs_t-1)}px; '
                f'font-style:italic; color:{c_t}; line-height:1.4;">'
                f'"{_esg_quote_text}"{_src_html}'
                f'</div>'
            )
        
        hp.append(_shtml(f"""{lh}
        <div style="display:flex; flex-direction:column; height:100%; width:100%; padding-top:8px;">
            <div class="app-overline-style">{_esg_overline}</div>
            <div class="title-h1" style="margin-bottom:5px; font-size:{fs_h1_val-8}px;">{_esg_title}</div>
            <div class="title-sub" style="margin-bottom:14px; font-size:{max(11,fs_sub_val-8)}px;">{_esg_subtitle}</div>
            <div style="font-family:'{f_t}'; font-size:{fs_t}px; line-height:1.55;
                        color:{c_t}; margin-bottom:18px; max-width:92%;">
                {_esg_intro}
            </div>
            <div style="display:flex; gap:16px; flex:1; min-height:0;">
                {_card_e}
                {_card_s}
                {_card_g}
            </div>
            {_metrics_section_html}
            {_esg_quote_html}
        </div>{fh}""", "slide-esg"))
   
    # --- 19. O nas / Partnerzy Zarządzający ---
    if _should_render('slide-about', current_page, export_mode):
        _about_overline = str(get_data('about_overline', 'NASZ ZESPÓŁ'))
        _about_title = str(get_data('about_title', '')).replace(chr(10), '<br>')
        _about_sub = str(get_data('about_sub', ''))
        _about_desc = str(get_data('about_desc', '')).replace(chr(10), '<br>')
        
        # Helper: pole metryki About (pomarańczowe tło, biały tekst)
        # Wszystkie 3 pola opcjonalne — pole renderuje się jeśli ma cokolwiek.
        # 'number' = duża górna treść (może być liczbą lub tekstem)
        # 'value' = mniejsza jednostka/dopełnienie obok
        # 'label' = mała etykieta u dołu
        def _about_metric(number, value, label):
            number = str(number or '').strip()
            value = str(value or '').strip()
            label = str(label or '').strip()
            if not number and not value and not label:
                return ''
            # Górny rząd (number + ewentualnie value obok)
            if number and value:
                top_html = (
                    f'<div style="display:flex; align-items:baseline; gap:4px; '
                    f'margin-bottom:2px; flex-wrap:wrap; line-height:1;">'
                    f'<span style="font-family:\'{f_h1}\'; font-weight:800; '
                    f'font-size:{fs_t+3}px; color:#ffffff; line-height:1;">{number}</span>'
                    f'<span style="font-family:\'{f_t}\'; font-weight:600; '
                    f'font-size:{max(9,fs_t-3)}px; color:#ffffff; line-height:1;">{value}</span>'
                    f'</div>'
                )
            elif number:
                top_html = (
                    f'<div style="font-family:\'{f_h1}\'; font-weight:800; '
                    f'font-size:{fs_t+3}px; color:#ffffff; margin-bottom:2px; '
                    f'line-height:1.1;">{number}</div>'
                )
            elif value:
                top_html = (
                    f'<div style="font-family:\'{f_h2}\'; font-weight:700; '
                    f'font-size:{max(10,fs_t-1)}px; color:#ffffff; margin-bottom:2px; '
                    f'line-height:1.2;">{value}</div>'
                )
            else:
                top_html = ''
            # Etykieta - mała, biała
            label_html = (
                f'<div style="font-family:\'{f_met}\'; font-size:{max(8,fs_met-6)}px; '
                f'font-weight:700; letter-spacing:1px; color:#ffffff; '
                f'text-transform:uppercase; line-height:1.2;">{label}</div>'
                if label else ''
            )
            return (
                f'<div style="background:{acc}; padding:6px 10px; '
                f'border-radius:5px; min-height:40px; display:flex; '
                f'flex-direction:column; justify-content:center;">'
                f'{top_html}{label_html}</div>'
            )
        
        # Helper: kolumna osoby (zdjęcie + nazwisko + funkcja + biogram + bullety + cytat)
        def _about_person(idx):
            _name = str(get_data(f'about_p{idx}_name', '')).strip()
            _role = str(get_data(f'about_p{idx}_role', '')).strip()
            _bio = str(get_data(f'about_p{idx}_bio', '')).strip()
            _bullets_raw = str(get_data(f'about_p{idx}_bullets', '')).strip()
            _quote = str(get_data(f'about_p{idx}_quote', '')).strip()
            _quote_src = str(get_data(f'about_p{idx}_quote_source', '')).strip()
            _img_key = f't_img_{idx-1}'  # zachowuje kompatybilność z istniejącym mechanizmem zdjęć t_img_0/t_img_1
            _img_b64 = get_b64(_img_key, (1, 1))
            
            # Zdjęcie - okrągłe, 130x130
            if _img_b64:
                _photo_html = _img_tag(
                    _img_b64, _name or f'Osoba {idx}',
                    style=('width:130px; height:130px; border-radius:50%; '
                           'object-fit:cover; display:block; border:3px solid #fff; '
                           'box-shadow:0 4px 12px rgba(0,0,0,0.15); flex-shrink:0;')
                )
            else:
                _photo_html = (
                    f'<div style="width:130px; height:130px; border-radius:50%; '
                    f'background:#e2e8f0; display:flex; align-items:center; '
                    f'justify-content:center; color:#94a3b8; font-family:\'{f_t}\'; '
                    f'font-size:11px; flex-shrink:0;">ZDJĘCIE</div>'
                )
            
            # Bullety
            _bullet_items = [x.strip() for x in _bullets_raw.split('\n') if x.strip()]
            _bullets_html = ''
            if _bullet_items:
                _bullets_html = (
                    '<ul style="list-style:none; padding:0; margin:8px 0 0 0;">'
                    + ''.join([
                        f'<li style="margin-bottom:5px; font-family:\'{f_t}\'; '
                        f'font-size:{max(10,fs_t-2)}px; color:{c_t}; line-height:1.35; '
                        f'padding-left:14px; position:relative;">'
                        f'<span style="position:absolute; left:0; top:0; color:{acc}; '
                        f'font-weight:700;">›</span>{x}</li>'
                        for x in _bullet_items
                    ])
                    + '</ul>'
                )
            
            # Cytat - kursywa, lewy border akcent
            _quote_html = ''
            if _quote:
                _src_html = (
                    f'<div style="margin-top:4px; font-size:{max(8,fs_t-5)}px; '
                    f'color:{acc}; font-weight:700; letter-spacing:0.5px; '
                    f'text-transform:uppercase; font-style:normal;">— {_quote_src}</div>'
                    if _quote_src else ''
                )
                _quote_html = (
                    f'<div style="margin-top:8px; padding:8px 12px; '
                    f'border-left:3px solid {acc}; background:#f8fafc; '
                    f'font-family:\'{f_t}\'; font-size:{max(10,fs_t-2)}px; '
                    f'font-style:italic; color:{c_t}; line-height:1.35;">'
                    f'"{_quote}"{_src_html}'
                    f'</div>'
                )
            
            return (
                f'<div style="flex:1; min-width:0; display:flex; flex-direction:column;">'
                # Górny rząd: zdjęcie + nazwisko/funkcja
                f'<div style="display:flex; gap:14px; align-items:center; margin-bottom:10px;">'
                f'{_photo_html}'
                f'<div style="flex:1; min-width:0;">'
                f'<div style="font-family:\'{f_h2}\'; font-weight:800; '
                f'font-size:{fs_t+3}px; color:{c_h2}; text-transform:uppercase; '
                f'letter-spacing:0.8px; line-height:1.1; margin-bottom:4px;">{_name}</div>'
                f'<div style="font-family:\'{f_t}\'; font-size:{max(9,fs_t-3)}px; '
                f'color:{acc}; font-weight:600; line-height:1.3;">{_role}</div>'
                f'<div style="width:30px; height:2px; background:{acc}; '
                f'margin-top:5px;"></div>'
                f'</div>'
                f'</div>'
                # Biogram
                f'<div style="font-family:\'{f_t}\'; font-size:{max(10,fs_t-2)}px; '
                f'color:{c_t}; line-height:1.4; text-align:justify;">{_bio}</div>'
                # Bullety
                f'{_bullets_html}'
                # Cytat
                f'{_quote_html}'
                f'</div>'
            )
        
        _person1_html = _about_person(1)
        _person2_html = _about_person(2)
        
        # Pasek metryk (8 pól, układ 4x2) - warunkowy render
        _about_metrics_parts = []
        for _i in range(1, 9):
            _m = _about_metric(
                get_data(f'about_m{_i}_number', ''),
                get_data(f'about_m{_i}_value', ''),
                get_data(f'about_m{_i}_label', ''),
            )
            if _m:
                _about_metrics_parts.append(_m)
        
        _about_metrics_html = ''
        if _about_metrics_parts:
            _about_metrics_html = (
                f'<div style="display:grid; grid-template-columns:repeat(4, 1fr); '
                f'gap:8px; margin-top:10px; margin-bottom:8px;">'
                + ''.join(_about_metrics_parts) +
                '</div>'
            )
        
        hp.append(_shtml(f"""{lh}
        <div style="display:flex; flex-direction:column; height:100%; width:100%; padding-top:8px;">
            <div class="app-overline-style">{_about_overline}</div>
            <div class="title-h1" style="margin-bottom:5px; font-size:{fs_h1_val-8}px;">{_about_title}</div>
            <div class="title-sub" style="margin-bottom:12px; font-size:{max(11,fs_sub_val-8)}px;">{_about_sub}</div>
            <div style="font-family:'{f_t}'; font-size:{max(10,fs_t-1)}px; line-height:1.5;
                        color:{c_t}; margin-bottom:14px; max-width:96%;">
                {_about_desc}
            </div>
            {_about_metrics_html}
            <div style="display:flex; gap:20px; flex:1; min-height:0; margin-top:6px;">
                {_person1_html}
                {_person2_html}
            </div>
        </div>{fh}""", "slide-about"))
    # --- 20. Rekomendacje ---
    if _should_render('slide-testimonials', current_page, export_mode):
        t_main_img = get_b64('img_testim_main', (4, 5))
        t_main_img_html = _img_tag(t_main_img, 'ZDJĘCIE GŁÓWNE')
        t_h = ""
        for i in range(get_data('testim_count', 3)):
            it = get_b64(f'testim_img_{i}', (1, 1))
            
            # --- POPRAWIONE WCIĘCIA TUTAJ ---
            if it:
                itg = f"<img src='{it}' style='width:100%;height:100%;object-fit:contain;'>"
            else:
                itg = _get_ph('LOGO')
            # -------------------------------
            
            t_h += f"""<div class="testim-item"><div class="testim-img-wrapper">{itg}</div>
                <div class="testim-content">
                    <div class="testim-head">{str(get_data(f'testim_head_{i}','')).replace(chr(10),'<br>')}</div>
                    <div class="testim-quote">"{get_data(f'testim_quote_{i}','')}"</div>
                    <div class="testim-author"><strong>{get_data(f'testim_author_{i}','')}</strong> | {get_data(f'testim_role_{i}','')}</div>
                </div></div>"""
                
        hp.append(_shtml(f"""{lh}<div class="premium-layout">
            <div class="info-col" style="flex: 55; padding-right: 40px; padding-top: 15px; justify-content: flex-start;">
                <div class="app-overline-style"><span>{str(get_data('testim_overline','REKOMENDACJE'))}</span></div>
                <div class="title-h1" style="margin-bottom: 15px; font-size:{fs_h1_val-6}px;">{str(get_data('testim_title','')).replace(chr(10),'<br>')}</div>
                <div class="title-sub" style="margin-bottom:25px; font-size:{max(12,fs_sub_val-4)}px;">{str(get_data('testim_subtitle','')).replace(chr(10),'<br>')}</div>
                <div style="display: flex; flex-direction: column;">{t_h}</div>
            </div>
            <div class="photo-col" style="flex: 45;">{t_main_img_html}</div>
            </div>{fh}""", "slide-testimonials"))
            
    # --- Zwróć lub wyświetl ---
    import streamlit.components.v1 as components
    
    try:
        css_str = get_local_css(return_str=True)
    except Exception:
        css_str = ""

    slides_html = "".join(hp)

    if export_mode:
        return slides_html
        
    # TWOJA LOGIKA IDENTYFIKATORÓW (zostawiamy nienaruszoną)
    first_visible_place = next((i for i in range(get_data('num_places', 0)) if not get_data(f'phide_{i}')), None)
    pid = f"place_{first_visible_place}" if first_visible_place is not None else "place_preview"
    first_visible_attr = next((i for i in range(get_data('num_attr', 0)) if not get_data(f'ahide_{i}')), None)
    fid = f"attr_{first_visible_attr}" if first_visible_attr is not None else "slide-title"
    hid = f"slide-hotel-0" if get_data('num_hotels', 1) > 0 and not get_data('h_hide_0') else "slide-title"

    default_tid = {
        "Strona tytułowa":                  "slide-title",
        "Opis kierunku":                    "slide-kierunek",
        "Mapa podróży":                     "slide-mapa",
        "Jak lecimy?":                      "slide-loty",
        "  ↳ Przerywnik program":           "slide-sek_3",
        "Program wyjazdu":                  "slide-program",
        "  ↳ Przerywnik atrakcje":          "slide-sek_1",
        "Opis atrakcji":                    fid,
        "  ↳ Przerywnik hotel":             "slide-sek_0",
        "Opis hoteli":                      hid,
        "  ↳ Przerywnik serwisy dodatkowe": "slide-sek_4",
        "Aplikacja (komunikacja)":          "slide-app",
        "Materiały brandingowe":            "slide-branding",
        "Pillow gifts":                     "slide-pillow-gifts",
        "Wirtualny asystent":               "slide-virtual-assistant",
        "Kosztorys str. 1":                 "slide-kosztorys-1",
        "Kosztorys str. 2":                 "slide-kosztorys-2",
        "  ↳ Przerywnik nasza agencja":     "slide-sek_2",
        "ESG":                              "slide-esg",
        "O nas":                            "slide-about",
        "Referencje":                       "slide-testimonials"
    }.get(current_page, "")
    
    tid = get_data('scroll_target') or default_tid
    if 'scroll_target' in st.session_state:
        del st.session_state['scroll_target']

    scroll_js = f"""
    <script>
    (function() {{
        document.body.style.transition = 'opacity 0.15s ease';
        document.body.style.opacity = '1';
        var targetId = "{tid if tid else ''}";
        if (!targetId) return;
        var el = document.getElementById(targetId);
        if (el) {{
            setTimeout(function() {{
                el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
            }}, 50);
        }}
    }})();
    </script>"""

    full_html = f"""<!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    {css_str}
    <style>
      body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; }}
      .presentation-wrapper {{
          height: 100vh;
          overflow-y: auto;
          scroll-snap-type: y proximity;
          scroll-behavior: smooth;
          background-color: #f4f5f7;
          padding: 5vh 0 15vh 0;
          box-sizing: border-box;
      }}
    </style>
    </head>
    <body>
    <div class="presentation-wrapper" id="main-wrapper">
    {slides_html}
    </div>
    {scroll_js}
    </body>
    </html>"""

    # WYŚWIETL: Rysujemy podgląd w jednym, jedynym oknie
    # Marker HTML z licznikiem wymusza zmianę hash → Streamlit przebudowuje iframe
    _marker = f"<!-- u{st.session_state.get('_upload_counter', 0)} -->"
    components.html(_marker + full_html, height=800, scrolling=False)
    
    return ""
