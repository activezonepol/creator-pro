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
# STAŁE I DANE
# ---------------------------------------------------------------------------

COUNTRIES_DICT = {
    "Albania": "ALB", "Austria": "AUT", "Belgia": "BEL", "Brazylia": "BRA",
    "Bułgaria": "BGR", "Chorwacja": "HRV", "Cypr": "CYP", "Czarnogóra": "MNE",
    "Czechy": "CZE", "Dania": "DNK", "Egipt": "EGY", "Francja": "FRA",
    "Grecja": "GRC", "Gruzja": "GEO", "Hiszpania": "ESP", "Indie": "IND",
    "Indonezja": "IDN", "Islandia": "ISL", "Japonia": "JPN", "Malta": "MLT",
    "Meksyk": "MEX", "Niemcy": "DEU", "Norwegia": "NOR", "Polska": "POL",
    "Portugalia": "PRT", "Słowacja": "SVK", "Szwajcaria": "CHE", "Szwecja": "SWE",
    "Tajlandia": "THA", "Turcja": "TUR", "W. Brytania": "GBR", "Wietnam": "VNM",
    "Włochy": "ITA", "ZEA": "ARE", "Inny": "OTH",
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
    # Klucze przycisków i uploaderów które nigdy nie trafiają do JSON
    'pa_add_place_btn', 'pa_add_attr_btn',
    # Klucze wewnętrzne sesji — nie zapisujemy do localStorage
    '_ls_loaded', '_session_id', '_ls_restore', '_attr_focused',
}

defaults = {
    'country_name': 'Czarnogóra', 'country_code': 'MNE',
    'font_h1': 'Montserrat', 'font_h2': 'Montserrat', 'font_sub': 'Montserrat',
    'font_text': 'Open Sans', 'font_metric': 'Montserrat',
    'color_h1': '#003366', 'color_h2': '#003366', 'color_sub': '#FF6600',
    'color_accent': '#FF6600', 'color_text': '#333333', 'color_metric': '#003366',
    'font_size_h1': 48, 'font_size_h2': 36, 'font_size_sub': 26,
    'font_size_text': 14, 'font_size_metric': 16,
    't_main': 'BAŁKAŃSKI KLEJNOT', 't_sub': 'MONTENEGRO EXPERIENCE',
    't_klient': 'NAZWA KLIENTA', 't_kierunek': 'CZARNOGÓRA',
    't_date': '1-4.10.2026', 't_pax': '60', 't_hotel': '4* ALL INCLUSIVE',
    't_trans': 'SAMOLOT PLL LOT',
    'hide_logo_cli': False,
    'k_hide': False, 'k_overline': 'NASZ KIERUNEK', 'k_main': 'CZARNOGÓRA',
    'k_sub': 'BAŁKAŃSKI KLEJNOT', 'k_opis': 'Opisz tutaj piękno kierunku...',
    'k_facts': 'Stolica: \nWaluta: \nRóżnica czasu: \nTemperatury: ',
    'k_facts_title': 'FAKTY',
    'k_box_bg': '', 'k_box_txt': '#ffffff',
    'l_hide': False, 'l_przesiadka': False, 'l_port': 'Monachium (MUC)',
    'l_czas': '3h 20 min', 'l_overline': 'PRZELOT', 'l_main': 'JAK LECIMY?',
    'l_sub': 'NASZA PROPOZYCJA PRZELOTU',
    'l_desc': 'Komfortowy przelot liniami PLL LOT.',
    'm_route': 'Warszawa (WAW) - Podgorica (TGD)', 'm_luggage': '23kg rejestrowany',
    'f1': 'LO 585, 17MAY, WAW-TGD, 14:25 - 16:25',
    'f2': 'LO 586, 21MAY, TGD-WAW, 17:15 - 19:05', 'f3': '', 'f4': '',
    'map_hide': False, 'map_overline': 'TRASA WYJAZDU',
    'map_title': 'ZARYS\nPODRÓŻY', 'map_subtitle': 'Kluczowe punkty programu',
    'map_desc': 'Zapraszamy do zapoznania się z poglądową mapą naszego wyjazdu.',
    'map_zoom': 8, 'num_map_points': 3,
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
    'koszt_pax': '25', 'koszt_price': '4.990 zł / os.',
    'koszt_hotel': 'Iberostar Bellevue 4* all inclusive',
    'koszt_dbl': '12', 'koszt_sgl': '1',
    'koszt_zawiera_1': 'Wybierz z listy auto-uzupełniania',
    'koszt_zawiera_2': '', 'koszt_nie_zawiera': 'Napiwki\nWydatki osobiste\nAtrakcje wymienione jako opcje',
    'koszt_opcje': '',
    'app_hide': False, 'app_overline': 'KOMUNIKACJA',
    'app_title': 'APLIKACJA\nNA WYJAZD',
    'app_subtitle': 'Dedykowana na wyjazd aplikacja dla uczestników',
    'app_features': ('Intuicyjna obsługa\n'
                     'Wygoda i nowoczesność / branding\n'
                     'Po pobraniu działa offline\n'
                     'Zawiera program i wszystkie ważne informacje\n'
                     'Formularz danych: dieta, zakwaterowanie, ubezpieczenie\n'
                     'Możliwość dodawania zdjęć i filmów przez uczestników\n'
                     'Możliwość przeprowadzania konkursów\n'
                     'Komunikacja SMS\n'
                     'Komunikacja "push" w aplikacji\n'
                     'Czat w aplikacji dla uczestników'),
    'brand_hide': False, 'brand_overline': 'IDENTYFIKACJA',
    'brand_title': 'MATERIAŁY\nBRANDINGOWE',
    'brand_subtitle': 'Komunikacja przed, w trakcie i po wyjeździe',
    'brand_features': (
        'Komunikacja SMS, e-mail, push w aplikacji przed i w trakcie wyjazdu\n'
        'Atrakcyjne zaproszenie elektroniczne\n'
        'Newsletter dla uczestników, program i materiały oraz koperty z logo na bilety i dokumenty\n'
        'Strona www i aplikacja mobilna z formularzem uczestnika\n'
        'Stanowisko na lotnisku z logo\n'
        'Zawieszka imienna z logo na bagaż\n'
        'Menu na posiłki z logo\n'
        'Zróżnicowanie posiłków do preferencji\n'
        'List powitalny w hotelu\n'
        'Oprawa marketingowa wyjazdu\n'
        'Cztery pillow gifty z opisem i logo (w tym strój)\n'
        'Taśma zabezpieczająca na walizkę z logo (opcja)'
    ),
    'va_hide': False, 'va_overline': 'SPRAWNA ORGANIZACJA',
    'va_title': 'WIRTUALNY\nASYSTENT',
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
    'pg_title': 'PILLOW\nGIFTS',
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
    'about_hide': False, 'about_overline': 'NASZ ZESPÓŁ',
    'about_title': 'POZNAJMY SIĘ', 'about_sub': 'ZESPÓŁ ACTIVEZONE',
    'about_desc': 'Activezone to agencja incentive travel...',
    'about_panel_title': 'NASZE WARTOŚCI', 'about_panel_text': 'Bezpieczeństwo\nProfesjonalizm',
    'team_count': 2, 'p_start_dt': date(2026, 10, 1),
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


# renderer.py
def load_project_data(project_data: dict):
    """
    Wczytuje dane z JSON/Bazy do session_state.
    
    POPRAWIONE 2026-04-23: Kluczowa zmiana — jeśli wartość w bazie jest 
    pustym stringiem, a lokalnie w session_state mamy niepustą wartość,
    ZACHOWUJEMY lokalną. To likwiduje problem znikania tekstów gdy 
    auto-save zapisuje niekompletny stan między interakcjami.
    """
    # Klucze zarezerwowane dla Streamlit (przyciski/widżety) — nie wczytujemy
    forbidden_keys = {
        'manual_save_btn', 'attr_add_btn', 'nav_top_radio', 'nav_bot_radio',
        'btn_add_attraction_main', 'last_page', 'up_export',
        # Klucze wewnętrzne auto-save/auto-load
        '_data_loaded_once', '_debug_loaded', 'last_supabase_save',
        'last_save_status', 'last_save_count',
    }
    forbidden_prefixes = (
        'attrnav_', 'attrup_', 'attrdn_', 'attrdel_',
        'btn_', 'dl_', 'up_',
    )

    for k, v in project_data.items():
        # 1. Pomijamy klucze przycisków i widżetów Streamlit
        if k in forbidden_keys:
            continue
        if any(k.startswith(p) for p in forbidden_prefixes):
            continue

        # 2. None — zachowaj lokalny stan
        if v is None:
            continue

        # 3. BEZPIECZNIK: pusty string z bazy vs niepusty lokalnie → zachowaj lokalny.
        # To jest KLUCZOWA zmiana likwidująca "znikanie tekstów".
        if isinstance(v, str) and v == "":
            current = st.session_state.get(k)
            if isinstance(current, str) and current != "":
                continue

        # 4. Specjalistyczne wczytywanie typów
        if k in IMAGE_KEYS and isinstance(v, str):
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
            # 5. Nadpisz tylko jeśli wartość faktycznie się różni
            # (oszczędzamy niepotrzebne rerunowanie widgetów)
            if st.session_state.get(k) != v:
                st.session_state[k] = v


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


def get_b64(key, ratio=(4, 5)):
    r = st.session_state.get(key)
    if not r:
        return None
    return get_b64_cached(r, ratio)


@st.cache_data(max_entries=20)
def get_logo_b64(raw_bytes):
    if not raw_bytes:
        return None
    try:
        if isinstance(raw_bytes, str):
            return raw_bytes
        return base64.b64encode(raw_bytes).decode('utf-8')
    except Exception:
        return None


# ---------------------------------------------------------------------------
# MAPY OSM
# ---------------------------------------------------------------------------

MAX_ZOOM_RECURSION_DEPTH = 8


@st.cache_data(max_entries=200)
def get_tile_bytes(z, x, y):
    url = f"https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png"
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

    lat_a, lon_a = geocode_place(place_a.strip(), country)
    lat_b, lon_b = geocode_place(place_b.strip(), country)

    if None in (lat_a, lon_a, lat_b, lon_b):
        return None, None, f"Nie znaleziono lokalizacji: {'A' if lat_a is None else 'B'}. Sprawdź pisownię."

    # 1. Próba Google Maps Distance Matrix (obsługuje cały świat)
    google_key = st.secrets.get('google', {}).get('maps_api_key')
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
def generate_map_data(points, zoom=6, _depth=0):
    if not points:
        return None, []
    geo_pts = [p for p in points if not p.get('symbolic')]
    if not geo_pts:
        final_points = [
            {'name': p['name'], 'x': p['x'], 'y': p['y'], 'conn': p['conn']}
            for p in points
        ]
        return None, final_points

    # Auto-zoom: dobierz zoom tak żeby punkty zajmowały rozsądny obszar ekranu.
    # Cel: wszystkie punkty mieszczą się w ~6x6 kafelkach (optymalny widok).
    # Ignorujemy punkty symboliczne przy obliczaniu zoom.
    if len(geo_pts) >= 2 and _depth == 0:
        lats = [p['lat'] for p in geo_pts]
        lons = [p['lon'] for p in geo_pts]
        lat_span = max(lats) - min(lats)
        lon_span = max(lons) - min(lons)
        span = max(lat_span, lon_span)
        # Heurystyka: dobierz zoom na podstawie rozpiętości geograficznej
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
    c_h1 = s.get('color_h1')
    c_h2 = s.get('color_h2')
    c_sub = s.get('color_sub')
    acc = s.get('color_accent')
    c_t = s.get('color_text')
    c_met = s.get('color_metric')
    f_h1 = s.get('font_h1')
    f_h2 = s.get('font_h2')
    f_sub = s.get('font_sub')
    f_txt = s.get('font_text')
    f_met = s.get('font_metric')

    try: fs_h1 = int(float(s.get('font_size_h1', 48)))
    except Exception: fs_h1 = 48
    try: fs_h2 = int(float(s.get('font_size_h2', 36)))
    except Exception: fs_h2 = 36
    try: fs_sub = int(float(s.get('font_size_sub', 26)))
    except Exception: fs_sub = 26
    try: fs_t = int(float(s.get('font_size_text', 14)))
    except Exception: fs_t = 14
    try: fs_met = int(float(s.get('font_size_metric', 16)))
    except Exception: fs_met = 16

    ufonts = {f_h1, f_h2, f_sub, f_txt, f_met, 'Montserrat', 'Open Sans'}
    font_imports = [
        f"@import url('https://fonts.googleapis.com/css?family={f.replace(' ', '+')}:{FONT_WEIGHTS.get(f, '400,700')}&display=swap');"
        for f in ufonts
    ]
    fonts_css = "\n        ".join(font_imports)
    client_css = (
        "[data-testid='stSidebar'] { display: none !important; } header { display: none !important; }"
        if s.get('client_mode') else ""
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
        body {{ counter-reset: slide_counter; background-color: #f4f5f7; scroll-behavior: smooth; margin: 0; }}
        .presentation-wrapper {{ height: 100vh; overflow-y: auto; scroll-snap-type: y proximity; scroll-behavior: smooth; background-color: #f4f5f7; padding: 5vh 0 15vh 0; box-sizing: border-box; }}
        .slide-scaler {{ display: flex; justify-content: center; align-items: center; min-height: 100vh; width: 100%; scroll-snap-align: center; padding: 10vh 0; }}
        .slide-page {{ width: 297mm !important; height: 210mm !important; min-width: 297mm !important; min-height: 210mm !important; margin: auto; box-sizing: border-box !important; background-color: white; box-shadow: 0 15px 45px rgba(0,0,0,0.08); padding: 30px 45px 15px 45px; position: relative; overflow: hidden; display: flex; flex-direction: column; font-family: '{f_txt}', sans-serif; color: {c_t}; transition: transform 0.3s ease, box-shadow 0.3s ease; }}
        @media screen and (max-height: 950px) {{ .slide-page {{ zoom: 0.90; }} }}
        @media screen and (max-height: 800px) {{ .slide-page {{ zoom: 0.80; }} }}
        .title-h1 {{ font-family: '{f_h1}'; font-weight: 800; font-size: {fs_h1}px; line-height: 1.1; text-transform: uppercase; color: {c_h1}; margin-bottom: 5px; }}
        .title-h2 {{ font-family: '{f_h2}'; font-weight: 800; font-size: {fs_h2}px; line-height: 1.1; text-transform: uppercase; color: {c_h2}; margin-bottom: 5px; }}
        .title-sub {{ font-family: '{f_sub}'; font-weight: 300; font-size: {fs_sub}px; color: {c_sub}; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 15px; }}
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
        .top-right-logo-container img {{ max-height: 60px; width: auto; object-fit: contain; opacity: 0.9; }}
        .day-header {{ font-family: '{f_h2}'; font-weight: 800; font-size: {max(12, fs_sub - 4)}px; border-bottom: 2px solid {acc}; color: {c_h2}; padding-bottom: 2px; }}
        .day-date {{ font-family: '{f_txt}'; font-size: {max(10, fs_sub - 12)}px; color: {acc}; font-weight: 600; margin-top: 3px; display: block; margin-bottom: 5px; text-transform: uppercase; }}
        .prog-img-container {{ width: 100%; height: 160px; margin-bottom: 8px; border-radius: 4px; overflow: hidden; border: 1px solid #eee; background-color: #fcfcfc; }}
        .prog-img-container img {{ width: 100%; height: 100%; object-fit: cover; }}
        .prog-attr {{ font-family: '{f_txt}'; font-size: {fs_t + 2}px; color: {acc}; font-weight: 700; margin: 12px 0; border-left: 3px solid {acc}; padding-left: 10px; text-transform: uppercase; line-height: 1.3; }}
        .app-overline-style {{ display: flex; align-items: center; gap: 10px; font-family: '{f_met}'; font-size: {fs_met - 2}px; font-weight: 700; letter-spacing: 4px; color: {acc}; margin-bottom: 10px; text-transform: uppercase; }}
        .app-overline-style::before, .app-overline-style::after {{ content: ""; height: 1px; background-color: {acc}; opacity: 0.5; flex-shrink: 0; }}
        .app-overline-style::before {{ width: 32px; }}
        .app-overline-style::after {{ flex: 1; }}
        .app-list {{ list-style: none; padding: 0; margin-top: 10px; margin-bottom: 10px; }}
        .app-list li {{ position: relative; padding-left: 18px; margin-bottom: 7px; font-family: '{f_txt}'; font-size: {max(10, fs_t-1)}px; line-height: 1.3; color: {c_t}; font-weight: 400; }}
        .app-list li::before {{ content: '■'; position: absolute; left: 0; top: 1px; color: {c_h2}; font-size: 0.7em; }}
        .app-list li.sub-item {{ padding-left: 35px; margin-bottom: 6px; font-size: 0.95em; color: {c_t}; font-weight: 300; }}
        .app-list li.sub-item::before {{ content: '○'; left: 18px; top: 3px; font-size: 0.6em; color: {c_h2}; }}
        .app-image-col {{ position: absolute; top: -30px; right: -45px; bottom: -15px; width: 62%; clip-path: polygon(20% 0, 100% 0, 100% 100%, 0 100%); z-index: 1; background-color: #eff4f8; display: flex; align-items: center; justify-content: center; }}
        .app-image-col img {{ width: 100%; height: 100%; object-fit: cover; }}
        .phone-mockup {{ position: absolute; top: 50%; left: 58%; transform: translate(-50%, -50%); width: 260px; height: 530px; background-color: #111; border-radius: 30px; border: 8px solid #111; box-shadow: -15px 20px 40px rgba(0,0,0,0.4); z-index: 10; overflow: hidden; }}
        .phone-mockup::before {{ content: ''; position: absolute; top: 0; left: 50%; transform: translateX(-50%); width: 110px; height: 20px; background-color: #111; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; z-index: 11; }}
        .phone-screen {{ width: 100%; height: 100%; object-fit: cover; display: block; background: #fff; }}
        .brand-collage {{ display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 45% 55%; gap: 15px; height: 100%; width: 100%; }}
        .brand-img-1 {{ grid-column: 1; grid-row: 1; border-radius: 8px 50px 8px 8px; overflow: hidden; background-color: #fcfcfc; border: 1px solid #eee; display: flex; align-items: center; justify-content: center; }}
        .brand-img-1 img {{ width: 100%; height: 100%; object-fit: cover; }}
        .brand-img-2 {{ grid-column: 2; grid-row: 1; border-radius: 50px 8px 8px 8px; overflow: hidden; background-color: #fcfcfc; border: 1px solid #eee; display: flex; align-items: center; justify-content: center; }}
        .brand-img-2 img {{ width: 100%; height: 100%; object-fit: cover; }}
        .brand-img-3 {{ grid-column: 1 / span 2; grid-row: 2; border-radius: 8px 8px 50px 50px; overflow: hidden; background-color: #fcfcfc; border: 1px solid #eee; display: flex; align-items: center; justify-content: center; position: relative; }}
        .brand-img-3 img {{ width: 100%; height: 100%; object-fit: cover; }}
        .brand-gap {{ position: absolute; top: -10px; left: 50%; transform: translateX(-50%); width: 15px; height: calc(100% + 20px); background-color: #fff; z-index: 5; }}
        .va-collage {{ display: grid; grid-template-columns: repeat(2, 1fr); grid-template-rows: 1.2fr 1fr; gap: 12px; height: 100%; width: 100%; }}
        .va-img-common {{ width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background-color: #fcfcfc; border: 1px solid #eee; }}
        .va-img-common img {{ width: 100%; height: 100%; object-fit: cover; }}
        .va-img-1-wrap {{ grid-column: 1 / span 2; grid-row: 1; border-radius: 8px 60px 8px 8px; overflow: hidden; }}
        .va-img-2-wrap {{ grid-column: 1; grid-row: 2; border-radius: 8px; overflow: hidden; }}
        .va-img-3-wrap {{ grid-column: 2; grid-row: 2; border-radius: 8px; overflow: hidden; }}
        .pg-collage {{ display: grid; grid-template-columns: repeat(2, 1fr); grid-template-rows: repeat(2, 1fr); gap: 15px; height: 100%; width: 100%; }}
        .pg-img-common {{ width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background-color: #fcfcfc; border: 1px solid #eee; }}
        .pg-img-common img {{ width: 100%; height: 100%; object-fit: cover; }}
        .pg-img-1-wrap {{ grid-column: 1; grid-row: 1; border-radius: 8px 8px 50px 8px; overflow: hidden; }}
        .pg-img-2-wrap {{ grid-column: 2; grid-row: 1 / span 2; border-radius: 8px 8px 8px 50px; overflow: hidden; }}
        .pg-img-3-wrap {{ grid-column: 1; grid-row: 2; border-radius: 50px 8px 8px 8px; overflow: hidden; }}
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
        .page-counter::after {{ counter-increment: slide_counter; content: counter(slide_counter); font-family: '{f_met}'; color: {c_met}; }}
        .photo-placeholder {{ width: 100%; height: 100%; background: #fcfcfc; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #aaa; font-weight: bold; font-size: 11px; text-align: center; text-transform: uppercase; }}
        @media print {{
            * {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }}
            @page {{ size: A4 landscape; margin: 0 !important; }}
            body {{ background: white !important; margin: 0 !important; padding: 0 !important; }}
            [data-testid="stSidebar"], header {{ display: none !important; }}
            .presentation-wrapper {{ height: auto !important; overflow: visible !important; scroll-snap-type: none !important; background: white !important; padding: 0 !important; margin: 0 !important; }}
            .slide-scaler {{ height: 210mm !important; width: 297mm !important; min-height: 210mm !important; margin: 0 !important; padding: 0 !important; display: block !important; page-break-after: always !important; page-break-inside: avoid !important; overflow: hidden !important; }}
            .slide-page {{ transform: none !important; box-shadow: none !important; width: 297mm !important; height: 210mm !important; max-height: 210mm !important; padding: 10mm 15mm 5mm 15mm !important; margin: 0 !important; zoom: 1 !important; border-radius: 0 !important; border: none !important; }}
            .floating-btn, .client-export-btn {{ display: none !important; }}
        }}
        </style>"""
    if return_str:
        return css
    st.markdown(css, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# HELPERY SLAJDÓW
# ---------------------------------------------------------------------------

def _lhtml():
    b64 = get_logo_b64(st.session_state.get('logo_az'))
    if not b64:
        return ""
    return f'<div class="top-right-logo-container"><img src="data:image/png;base64,{b64}"></div>'


def _fhtml():
    return (
        f'<div class="page-footer">'
        f'<span>www.activezone.pl | wszystkie prawa zastrzeżone {datetime.today().year}</span>'
        f'<span class="page-counter"></span></div>'
    )


def _shtml(c, sid=""):
    return f'<div class="slide-scaler" id="{sid}"><div class="slide-page">{c}</div></div>'


def _get_ph(t):
    return f'<div class="photo-placeholder">{t}</div>'


# ---------------------------------------------------------------------------
# GŁÓWNA FUNKCJA BUDOWANIA PREZENTACJI
# ---------------------------------------------------------------------------


def build_presentation(current_page="Strona Tytułowa", export_mode=False):
    s = st.session_state
    hp = []

    c_h1 = s.get('color_h1', '#003366')
    c_h2 = s.get('color_h2', '#003366')
    c_sub = s.get('color_sub', '#FF6600')
    acc = s.get('color_accent', '#FF6600')
    c_t = s.get('color_text', '#333333')
    c_met = s.get('color_metric', '#003366')
    f_h1 = s.get('font_h1', 'Montserrat')
    f_h2 = s.get('font_h2', 'Montserrat')
    f_sub = s.get('font_sub', 'Montserrat')
    f_t = s.get('font_text', 'Open Sans')
    f_met = s.get('font_metric', 'Montserrat')

    try: fs_t = int(float(s.get('font_size_text', 14)))
    except Exception: fs_t = 14
    try: fs_h1_val = int(float(s.get('font_size_h1', 48)))
    except Exception: fs_h1_val = 48
    try: fs_sub_val = int(float(s.get('font_size_sub', 26)))
    except Exception: fs_sub_val = 26
    try: fs_met = int(float(s.get('font_size_metric', 16)))
    except Exception: fs_met = 16

    lh = _lhtml()
    fh = _fhtml()

    # --- Przerywniki sekcji (nowy styl: pełnoekranowy overlay z gradientem) ---
    def _render_sek(target_i):
        """Renderuje slajd przerywnikowy sek_i jeśli nie ukryty."""
        i = target_i
        sid = f"sek_{i}"
        if s.get(f'sek_hide_{i}', False):
            return
        _title_defs = {0: 'ZAKWATEROWANIE', 1: 'ATRAKCJE', 2: 'REKOMENDACJE', 3: 'PROGRAM'}
        _sub_defs   = {0: 'NASZE HOTELE', 1: 'PROGRAM WYJAZDU', 2: 'CO O NAS MÓWIĄ', 3: 'NASZ PLAN WYJAZDU'}
        title = str(s.get(f'{sid}_title', _title_defs.get(i, 'SEKCJA'))).replace(chr(10), '<br>')
        sub   = str(s.get(f'{sid}_sub',   _sub_defs.get(i, ''))).replace(chr(10), '<br>')
        box_bg  = str(s.get(f'{sid}_bg')  or c_h1)
        box_txt = str(s.get(f'{sid}_txt') or '#ffffff')
        bg_img  = get_b64(f'{sid}_img', (16, 9))
        bg_html = (
            f'<img src="data:image/jpeg;base64,{bg_img}" style="width:100%;height:100%;object-fit:cover;">' 
            if bg_img else
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
                    <div style="width:32px; height:1px; background:{acc}; opacity:0.7; flex-shrink:0;"></div>
                    <span style="font-family:'{f_met}'; font-weight:700; font-size:{max(10,fs_met-1)}px;
                                 letter-spacing:4px; color:{acc}; text-transform:uppercase;">
                        {sub}
                    </span>
                </div>
                <div style="font-family:'{f_h1}'; font-weight:800; font-size:{min(fs_h1_val+32, 96)}px;
                            color:{box_txt}; line-height:1.0; text-transform:uppercase;
                            text-shadow:0px 4px 15px rgba(0,0,0,0.15);">
                    {title}
                </div>
            </div>
        </div>{fh}""", f"slide-{sid}"))


    # --- Slajd tytułowy ---
    i1 = get_b64('img_hero_t', (4, 5))
    im1 = (f"<img src='data:image/jpeg;base64,{i1}' style='width:100%;height:100%;object-fit:cover;'>"
           if i1 else _get_ph('ZDJĘCIE GŁÓWNE'))
    rcli = s.get('logo_cli')
    hide_cli = s.get('hide_logo_cli', False)
    lcli_b64 = get_logo_b64(rcli)
    lcli = (f"<img src='data:image/png;base64,{lcli_b64}' style='max-height:100%;max-width:150px;object-fit:contain;'>"
            if (lcli_b64 and not hide_cli) else "")
    lcli_container = f"<div style='margin-bottom:40px;height:60px;display:flex;align-items:center;justify-content:flex-start;'>{lcli}</div>"
    hp.append(_shtml(f"""{lh}<div class="premium-layout"><div class="photo-col">{im1}</div><div class="info-col">
        {lcli_container}
        <div class="title-h1">{str(s.get('t_main','')).replace(chr(10),'<br>')}</div>
        <div class="title-sub" style="color:{acc}">{str(s.get('t_sub','')).replace(chr(10),'<br>')}</div>
        <div class="metric-grid">
            <div><div class="metric-label">Klient</div><div class="metric-value">{s.get('t_klient','')}</div></div>
            <div><div class="metric-label">Kierunek</div><div class="metric-value">{s.get('t_kierunek','')}</div></div>
            <div><div class="metric-label">Termin</div><div class="metric-value">{s.get('t_date','')}</div></div>
            <div><div class="metric-label">Liczba osób</div><div class="metric-value">{s.get('t_pax','')}</div></div>
            <div><div class="metric-label">Hotel</div><div class="metric-value">{s.get('t_hotel','')}</div></div>
            <div><div class="metric-label">Dojazd</div><div class="metric-value">{s.get('t_trans','')}</div></div>
        </div></div></div>{fh}""", "slide-title"))

    # --- Opis kierunku (Pojedynczy Slajd Premium) ---
    if not s.get('k_hide', False):
        kimg = get_b64('img_hero_k', (1, 1))

        # Przetwarzanie boxu z faktami
        kfacts = str(s.get('k_facts', 'Stolica: \nWaluta: \nRóżnica czasu: \nTemperatury: ') or '')
        kfacts_title = str(s.get('k_facts_title', 'FAKTY') or '')
        facts_lines = []
        for line in kfacts.split('\n'):
            line = line.strip()
            if not line: continue
            _ktxt = str(s.get('k_box_txt') or '#ffffff')
            if ':' in line:
                lbl, val = line.split(':', 1)
                facts_lines.append(
                    f"<div style='margin-bottom:8px; line-height:1.4; font-size:{max(11, fs_t-1)}px;'>"
                    f"<strong style='font-family:\"{f_t}\"; font-weight:700; color:{_ktxt};'>{lbl.strip()}:</strong> "
                    f"<span style='font-family:\"{f_t}\"; font-weight:400; color:{_ktxt};'>{val.strip()}</span></div>"
                )
            else:
                facts_lines.append(
                    f"<div style='margin-bottom:8px; line-height:1.4; font-size:{max(11, fs_t-1)}px; "
                    f"font-family:\"{f_t}\"; color:{_ktxt};'>{line}</div>"
                )
        facts_html_k = ''.join(facts_lines)

        kbox_bg  = str(s.get('k_box_bg')  or c_h1)
        kbox_txt = str(s.get('k_box_txt') or '#ffffff')

        # Tytuł boksu w stylu overline
        facts_title_html = (
            f"<div style='font-family:\"{f_met}\"; font-weight:700; font-size:{max(10, fs_met-2)}px; "
            f"color:{kbox_txt}; text-transform:uppercase; letter-spacing:3px; "
            f"margin-bottom:12px; padding-bottom:10px; "
            f"border-bottom:1px solid rgba(255,255,255,0.3);'>{kfacts_title}</div>"
            if kfacts_title else ''
        )

        box_html = (
            f"<div style='background-color:{kbox_bg}; color:{kbox_txt}; padding:25px 20px; "
            f"border-bottom-left-radius:40px; border-top-right-radius:8px; "
            f"border-top-left-radius:8px; box-shadow:0 10px 20px rgba(0,0,0,0.05);'>"
            f"{facts_title_html}{facts_html_k}</div>"
            if (facts_html_k or facts_title_html) else
            f"<div style='background-color:{kbox_bg}; height:100px; "
            f"border-bottom-left-radius:40px; border-top-right-radius:8px; "
            f"border-top-left-radius:8px; box-shadow:0 10px 20px rgba(0,0,0,0.05);'></div>"
        )

        k_over = str(s.get('k_overline') or 'NASZ KIERUNEK')
        k_main = str(s.get('k_main') or '').replace(chr(10), '<br>')
        k_sub  = str(s.get('k_sub')  or '').replace(chr(10), '<br>')
        k_opis = str(s.get('k_opis') or '').replace(chr(10), '<br>')

        hp.append(_shtml(f"""{lh}
        <div class="premium-layout" id="slide-kierunek" style="gap:40px; align-items:stretch;">

            <div style="flex:55; display:flex; gap:15px; height:100%;">
                <div style="flex:1.2; height:100%; border-radius:8px; overflow:hidden; position:relative; background:#fcfcfc; border:1px solid #eee;">
                    {f'<img src="data:image/jpeg;base64,{kimg}" style="position:absolute; top:0; left:0; width:200%; height:100%; object-fit:cover; object-position:left center;">' if kimg else _get_ph('ZDJĘCIE')}
                </div>
                <div style="flex:1; display:flex; flex-direction:column; gap:15px; height:100%;">
                    {box_html}
                    <div style="flex-grow:1; border-top-left-radius:40px; border-bottom-left-radius:8px; border-bottom-right-radius:8px; overflow:hidden; position:relative; background:#fcfcfc; border:1px solid #eee;">
                        {f'<img src="data:image/jpeg;base64,{kimg}" style="position:absolute; bottom:0; right:0; width:220%; height:140%; object-fit:cover; object-position:right bottom;">' if kimg else _get_ph('ZDJĘCIE')}
                    </div>
                </div>
            </div>

            <div class="info-col" style="flex:45; padding-left:10px; padding-top:15px; justify-content:flex-start;">
                <div style="display:flex; align-items:center; gap:10px; margin-bottom:10px;">
                    <div style="height:1px; background-color:{acc}; opacity:0.5; width:32px; flex-shrink:0;"></div>
                    <span style="font-family:'{f_met}'; font-size:{max(10,fs_met-2)}px; font-weight:700;
                                 letter-spacing:4px; color:{acc}; text-transform:uppercase; white-space:nowrap;">
                        {k_over}
                    </span>
                    <div style="height:1px; background-color:{acc}; opacity:0.5; flex:1;"></div>
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
            </div>

        </div>{fh}""", "slide-kierunek"))

    # --- Mapa ---
    if not s.get('map_hide', False):
        m_bg = s.get('img_map_bg_auto')
        m_bg_html = (
            f'<img src="data:image/jpeg;base64,{m_bg}" style="width:100%;height:100%;object-fit:fill;opacity:0.85;border-radius:8px;">'
            if m_bg else
            f'<div style="width:100%;height:100%;background:#eef2f5;display:flex;align-items:center;justify-content:center;color:#ccc;font-weight:bold;font-size:14px;text-align:center;border-radius:8px;border:2px dashed {acc};">MAPA ZOSTANIE WYGENEROWANA AUTOMATYCZNIE<br>Wprowadź punkty trasy w panelu sterowania</div>'
        )
        auto_pts = s.get('auto_map_points', [])
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
        num_dp = s.get('num_dist_pairs', 0)
        dist_title = str(s.get('map_dist_title', 'ODLEGŁOŚCI I CZAS DOJAZDU'))
        dist_rows_html = ''
        if num_dp > 0:
            rows_html = ''
            for di in range(num_dp):
                pa = str(s.get(f'dist_a_{di}', ''))
                pb = str(s.get(f'dist_b_{di}', ''))
                dist_val = str(s.get(f'dist_km_{di}', '—'))
                time_val = str(s.get(f'dist_time_{di}', '—'))
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
                <div class="info-col" style="flex: 40; padding-right: 30px; padding-top: 30px; justify-content: flex-start;">
                    <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
                        <div style="width:32px; height:1px; background:{acc}; opacity:0.6; flex-shrink:0;"></div>
                        <span style="font-family:'{f_met}'; font-size:{max(9,fs_met-2)}px; font-weight:700;
                                     letter-spacing:4px; color:{acc}; text-transform:uppercase; white-space:nowrap;">
                            {str(s.get('map_overline','TRASA WYJAZDU'))}
                        </span>
                        <div style="flex:1; height:1px; background:{acc}; opacity:0.6;"></div>
                    </div>
                    <div class="title-h1" style="margin-bottom: 15px; font-size:{fs_h1_val-6}px;">{str(s.get('map_title','ZARYS\\nPODRÓŻY')).replace(chr(10),'<br>')}</div>
                    <div class="title-sub" style="margin-bottom: 15px; font-size:{max(12,fs_sub_val-4)}px;">{str(s.get('map_subtitle','')).replace(chr(10),'<br>')}</div>
                    <div style="font-family: '{f_t}'; font-size: {fs_t}px; line-height: 1.6; color: {c_t}; margin-bottom: 10px;">{str(s.get('map_desc','')).replace(chr(10),'<br>')}</div>
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

    # --- Loty ---
    if not s.get('l_hide', False):
        il = get_b64('img_hero_l', (4, 5))
        iml = (f"<img src='data:image/jpeg;base64,{il}' style='width:100%;height:100%;object-fit:cover;'>"
               if il else _get_ph('FOTO SAMOLOTU'))
        f_keys = ['f1', 'f2']
        if s.get('l_przesiadka', False):
            f_keys.extend(['f3', 'f4'])
        rows = ""
        for f_key in f_keys:
            f_val = str(s.get(f_key, ''))
            parts = f_val.split(',')
            if len(parts) >= 4:
                rows += f"<tr><td>{parts[0]}</td><td>{parts[1]}</td><td>{parts[2]}</td><td>{parts[3]}</td></tr>"
        przesiadka_html = ""
        if s.get('l_przesiadka', False):
            przesiadka_html = f"""<div style="background-color: #f8f9fa; border-left: 4px solid {acc}; padding: 15px 20px; margin-top: 15px; margin-bottom: 15px; border-radius: 4px; display: flex; gap: 40px; align-items: center;">
                <div><div style="font-size: 11px; font-weight: 700; color: {c_h2}; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 3px;">Port przesiadkowy</div><div style="font-size: {fs_t+2}px; font-weight: 600; color: {c_t};"><i class="fa-solid fa-location-dot" style="color:{acc}; margin-right:6px;"></i>{s.get('l_port','')}</div></div>
                <div><div style="font-size: 11px; font-weight: 700; color: {c_h2}; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 3px;">Czas przesiadki</div><div style="font-size: {fs_t+2}px; font-weight: 600; color: {c_t};"><i class="fa-solid fa-clock" style="color:{acc}; margin-right:6px;"></i>{s.get('l_czas','')}</div></div>
            </div>"""
        h_d = f"<p>{str(s.get('l_desc') or '').replace(chr(10),'<br>')}</p>" if str(s.get('l_desc','')).strip() else ""
        h_e = f"<p style='font-size:10px;margin-top:15px;'>{str(s.get('l_extra') or '').replace(chr(10),'<br>')}</p>" if str(s.get('l_extra','')).strip() else ""
        hp.append(_shtml(f"""{lh}<div class="premium-layout"><div class="photo-col">{iml}</div>
            <div class="info-col" style="padding-top:30px; justify-content:flex-start;">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:15px;">
                <div style="width:32px; height:1px; background:{acc}; opacity:0.6; flex-shrink:0;"></div>
                <span style="font-family:'{f_met}'; font-size:{max(9,fs_met-2)}px; font-weight:700;
                             letter-spacing:4px; color:{acc}; text-transform:uppercase; white-space:nowrap;">
                    {str(s.get('l_overline','PRZELOT'))}
                </span>
                <div style="flex:1; height:1px; background:{acc}; opacity:0.6;"></div>
            </div>
            <div class="title-h1" style="margin-bottom:5px; font-size:{fs_h1_val-6}px;">{str(s.get('l_main','JAK LECIMY?')).replace(chr(10),'<br>')}</div>
            <div class="title-sub" style="margin-bottom:15px;">{str(s.get('l_sub','')).replace(chr(10),'<br>')}</div>{h_d}
            <div class="metric-grid">
                <div><div class="metric-label">Trasa</div><div class="flight-val">{s.get('m_route','')}</div></div>
                <div><div class="metric-label">Limit bagażu</div><div class="flight-val">{s.get('m_luggage','')}</div></div>
            </div>
            {przesiadka_html}
            <table class="flight-table"><tr><th>NR LOTU</th><th>DATA</th><th>TRASA</th><th>GODZINY</th></tr>{rows}</table>{h_e}
            </div></div>{fh}""", "slide-loty"))




    # --- Przerywnik sek_0 (przed hotel) ---
    _render_sek(0)  # Przerywnik przed hotelami

        # --- Hotele w kolejności hotel_order ---
    _hotel_order = s.get('hotel_order', [])
    if not _hotel_order:
        _hotel_order = list(range(s.get('num_hotels', 1)))
    for i in _hotel_order:
        if not s.get(f'h_hide_{i}', False):
            h1 = get_b64(f'img_hotel_1_{i}', (16, 9))
            h1b = get_b64(f'img_hotel_1b_{i}', (16, 9))
            h2 = get_b64(f'img_hotel_2_{i}', (16, 9))
            h3 = get_b64(f'img_hotel_3_{i}', (16, 9))
            h1_html = (f'<img src="data:image/jpeg;base64,{h1}" style="width:100%; height:100%; object-fit:cover;">'
                       if h1 else _get_ph('ZDJ. LEWE 1'))
            h1b_html = (f'<img src="data:image/jpeg;base64,{h1b}" style="width:100%; height:100%; object-fit:cover;">'
                        if h1b else _get_ph('ZDJ. LEWE 2'))
            url_val = str(s.get(f'h_url_{i}', '')).strip()

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
            h_amenities = s.get(f'h_amenities_{i}', [])
            am_items = []
            book_val = str(s.get(f'h_booking_{i}', '')).strip()
            if book_val:
                am_items.append(f'<div style="display:flex; align-items:center; gap:6px; margin-right:10px;"><div style="background:#003580; color:white; padding:3px 8px; border-radius:6px; border-bottom-left-radius:0; font-family:\'Montserrat\', sans-serif; font-weight:800; font-size:{max(12,fs_t)}px;">{book_val}</div><span style="font-family:\'Montserrat\', sans-serif; font-weight:700; color:#003580; font-size:{max(10,fs_t-1)}px;">Booking.com</span></div>')
            for a in h_amenities:
                if a in hotel_icons:
                    am_items.append(f'<div style="display:flex; align-items:center; gap:6px; font-size:{max(10,fs_t-1)}px; font-weight:600; color:{c_t};"><i class="fa-solid {hotel_icons[a]}" style="color:{acc}; font-size:{fs_t+4}px;"></i> {a}</div>')
            h_am_html = (f'<div style="display:flex; flex-wrap:wrap; align-items:center; gap:15px; margin-bottom:10px; padding:8px 0; border-top:1px solid #eee; border-bottom:1px solid #eee;">{"".join(am_items)}</div>'
                         if am_items else '')

            # POPRAWKA 1: Atuty jako tagi (jeden wiersz, font overline, kolor akcentu, tło akcentu)
            advs = [f.strip() for f in s.get(f'h_advantages_{i}', '').split('\n') if f.strip()]
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
                <div style="flex:60; padding-left:15px; padding-top:20px; display:flex; flex-direction:column; min-height:0;">
                    <div class="app-overline-style" style="margin-bottom:4px; flex-shrink:0;"><span>{str(s.get(f'h_overline_{i}','ZAKWATEROWANIE'))}</span></div>
                    <div class="title-h1" style="margin-bottom:3px; font-size:{max(20,fs_h1_val-6)}px; flex-shrink:0;">{str(s.get(f'h_title_{i}','')).replace(chr(10),'<br>')}</div>
                    <div style="display:flex; align-items:baseline; justify-content:space-between; gap:10px; margin-bottom:8px; flex-shrink:0;">
                        <div class="title-sub" style="margin:0; font-size:{max(12,fs_sub_val-4)}px;">{str(s.get(f'h_subtitle_{i}','')).replace(chr(10),'<br>')}</div>
                        <div style="flex-shrink:0;">{url_link}</div>
                    </div>
                    <div style="font-size:{fs_t}px; line-height:1.4; margin-bottom:8px; color:{c_t}; flex-shrink:0;">{str(s.get(f'h_text_{i}','')).replace(chr(10),'<br>')}</div>
                    <div style="flex-shrink:0;">{h_am_html}</div>
                    <div style="flex-shrink:0;">{adv_html}</div>
                    <div style="flex:1; min-height:8px;"></div>
                    <div style="display:flex; gap:12px; flex-shrink:0; aspect-ratio:3/1;">
                        <div style="flex:1; border-radius:8px; overflow:hidden; border:1px solid #eee; background:#fcfcfc;">{f'<img src="data:image/jpeg;base64,{h2}" style="width:100%;height:100%;object-fit:cover;">' if h2 else _get_ph('FOT DÓŁ 1')}</div>
                        <div style="flex:1; border-radius:8px; overflow:hidden; border:1px solid #eee; background:#fcfcfc;">{f'<img src="data:image/jpeg;base64,{h3}" style="width:100%;height:100%;object-fit:cover;">' if h3 else _get_ph('FOT DÓŁ 2')}</div>
                    </div>
                </div></div>{fh}""", f"slide-hotel-{i}"))

    # --- Przerywnik sek_3 (przed programem) ---
    _render_sek(3)  # Przerywnik przed programem

    # --- Program wyjazdu ---
    if not s.get('prg_hide', False):
        nd = s.get('num_days', 5)
        start_dt_local = s.get('p_start_dt', date.today())
        for st_idx in range(0, nd, 3):
            ch = ""
            for i in range(3):
                di = st_idx + i
                if di < nd:
                    cdt = start_dt_local + timedelta(days=di)
                    id_img = get_b64(f'img_d_{di}', (16, 9))
                    mh = ""
                    for pi in range(s.get('num_places', 0)):
                        p_day = str(s.get(f"pday_{pi}") or "")
                        d_match = re.search(r'Dzień\s+(\d+)', p_day)
                        if d_match and int(d_match.group(1)) == di + 1:
                            nm = s.get(f"pmain_{pi}", "")
                            if s.get(f"phide_{pi}"):
                                mh += f"<div><div style='display:flex; align-items:center; gap:8px; font-size:15px; font-weight:600; color:{c_t}; margin-bottom:5px;'><span style='font-size:18px; color:{acc};'><i class='fa-solid fa-map-location-dot'></i></span> <span>{nm}</span></div></div>"
                            else:
                                mh += f"<div><a href='#place_{pi}' style='text-decoration:none; color:{acc}; display:flex; align-items:center; gap:8px; font-size:15px; font-weight:600; margin-bottom:5px;'><span style='font-size:18px;'><i class='fa-solid fa-map-location-dot'></i></span> <span>{nm} <span style='font-size:12px; font-weight:400; opacity:0.8;'>(zobacz)</span></span></a></div>"
                    for ai in range(s.get('num_attr', 0)):
                        a_day = str(s.get(f"aday_{ai}") or "")
                        d_match = re.search(r'Dzień\s+(\d+)', a_day)
                        if d_match and int(d_match.group(1)) == di + 1:
                            ic = icon_map.get(s.get(f"atype_{ai}", "Atrakcja"), "")
                            nm = s.get(f"amain_{ai}", "")
                            sub = str(s.get(f"asub_{ai}", "")).strip()
                            sub_html = (f"<div style='font-size:12px; font-weight:400; color:{c_t}; opacity:0.8; margin-top:-2px; margin-left:26px; line-height:1.2; margin-bottom:8px;'>{sub}</div>"
                                        if sub else "<div style='margin-bottom:8px;'></div>")
                            if s.get(f"ahide_{ai}"):
                                mh += f"<div><div style='display:flex; align-items:center; gap:8px; font-size:15px; font-weight:600; color:{c_t};'><span style='font-size:18px; color:{acc};'>{ic}</span> <span>{nm}</span></div>{sub_html}</div>"
                            else:
                                mh += f"<div><a href='#attr_{ai}' style='text-decoration:none; color:{acc}; display:flex; align-items:center; gap:8px; font-size:15px; font-weight:600;'><span style='font-size:18px;'>{ic}</span> <span>{nm} <span style='font-size:12px; font-weight:400; opacity:0.8;'>(zobacz)</span></span></a>{sub_html}</div>"
                    ch += f"""<div style="flex:1;display:flex;flex-direction:column;" id="program_day_{di}">
                        <div class="day-header">DZIEŃ {di+1}</div>
                        <div class="day-date">{cdt.strftime('%d.%m.%Y')} - {pl_days_map[cdt.weekday()]}</div>
                        <div class="prog-img-container">{f'<img src="data:image/jpeg;base64,{id_img}" style="width:100%;height:100%;object-fit:cover;">' if id_img else _get_ph('FOTO DNIA')}</div>
                        <div class="prog-attr">{str(s.get(f'attr_{di}') or '').replace(chr(10),'<br>')}</div>
                        {mh}
                        <p style="font-size:13px; margin-top:10px; line-height: 1.5;">{str(s.get(f'desc_{di}') or '').replace(chr(10),'<br>')}</p>
                    </div>"""
                else:
                    ch += "<div style='flex:1;'></div>"
            hp.append(_shtml(f"""{lh}<div class="title-h2">PROGRAM WYJAZDU</div>
                <div style="display:flex;gap:25px;flex-grow:1;min-height:0;margin-top:15px;margin-bottom:20px;">{ch}</div>{fh}""",
                             "slide-program" if st_idx == 0 else ""))

    # --- Slajd wzorcowy "Opisy miejsc" (tylko w trybie edycji, gdy brak miejsc) ---
    # Pojawia się gdy projektant otwiera sekcję Opisy miejsc a num_places=0.
    # NIE wchodzi do eksportu dla klienta.
    if (not export_mode
            and current_page == "Opisy miejsc"
            and s.get('num_places', 0) == 0):
        hp.append(_shtml(f"""{lh}<div class="premium-layout" id="place_preview">
            <div class="photo-col">{_get_ph('FOTO MIEJSCA')}</div>
            <div class="info-col" style="padding-top:30px; justify-content:flex-start;">
                <div class="app-overline-style" style="margin-bottom:15px;"><span>NASZ KIERUNEK</span></div>
                <div class="title-h1" style="margin-bottom:5px; font-size:{fs_h1_val-6}px;">OPIS MIEJSCA</div>
                <div class="title-sub" style="margin-bottom:15px;">Podtytuł miejsca</div>
                <div style="flex-grow:1;"><p style="font-size:{fs_t}px; line-height:1.6; color:{c_t}; opacity:0.5;">
                    Tu pojawi się opis miejsca. Dodaj pierwsze miejsce w panelu po lewej
                    wpisując liczbę opisów &gt; 0, a następnie wypełnij dane w formularzu.
                </p></div>
                <div class="gallery-row" style="padding-top:0; padding-bottom:5px;">
                    <div class="gallery-thumb">{_get_ph('FOT 1')}</div>
                    <div class="gallery-thumb">{_get_ph('FOT 2')}</div>
                    <div class="gallery-thumb">{_get_ph('FOT 3')}</div>
                </div>
            </div>
        </div>{fh}""", "place_preview"))




    # --- Przerywnik sek_1 (przed attr) ---
    _render_sek(1)  # Przerywnik przed atrakcjami

        # --- Miejsca i atrakcje (posortowane po dniach) ---
    # --- Miejsca i atrakcje w kolejności place_attr_order ---
    _pa_order = s.get('place_attr_order', [])
    if not _pa_order:
        _tmp_p = []
        for _pi in range(s.get('num_places', 0)):
            _pday = str(s.get(f"pday_{_pi}") or "")
            _m = re.search(r'Dzień\s+(\d+)', _pday)
            _tmp_p.append(('place', _pi, int(_m.group(1)) if _m else 999))
        _tmp_a = []
        for _ai in range(s.get('num_attr', 0)):
            _aday = str(s.get(f"aday_{_ai}") or "")
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
            if s.get(f'h_hide_{i}', False):
                continue
            h1 = get_b64(f'img_hotel_1_{i}', (16, 9))
            h1b = get_b64(f'img_hotel_1b_{i}', (16, 9))
            h2 = get_b64(f'img_hotel_2_{i}', (16, 9))
            h3 = get_b64(f'img_hotel_3_{i}', (16, 9))
            h1_html = (f'<img src="data:image/jpeg;base64,{h1}" style="width:100%; height:100%; object-fit:cover;">' if h1 else _get_ph('ZDJ. LEWE 1'))
            h1b_html = (f'<img src="data:image/jpeg;base64,{h1b}" style="width:100%; height:100%; object-fit:cover;">' if h1b else _get_ph('ZDJ. LEWE 2'))
            url_val = str(s.get(f'h_url_{i}', '')).strip()
            h_url_html = (f'<div style="font-size:{max(10,fs_t-2)}px; color:{c_t}; opacity:0.8; margin-bottom:15px;"><i class="fa-solid fa-globe" style="color:{acc}; margin-right:5px;"></i> {url_val}</div>' if url_val else '')
            h_amenities = s.get(f'h_amenities_{i}', [])
            am_items = []
            book_val = str(s.get(f'h_booking_{i}', '')).strip()
            if book_val:
                am_items.append(f'<div style="display:flex; align-items:center; gap:6px; margin-right:10px;"><div style="background:#003580; color:white; padding:3px 8px; border-radius:6px; border-bottom-left-radius:0; font-family:\'Montserrat\', sans-serif; font-weight:800; font-size:{max(12,fs_t)}px;">{book_val}</div><span style="font-family:\'Montserrat\', sans-serif; font-weight:700; color:#003580; font-size:{max(10,fs_t-1)}px;">Booking.com</span></div>')
            for a in h_amenities:
                if a in hotel_icons:
                    am_items.append(f'<div style="display:flex; align-items:center; gap:6px; font-size:{max(10,fs_t-1)}px; font-weight:600; color:{c_t};"><i class="fa-solid {hotel_icons[a]}" style="color:{acc}; font-size:{fs_t+4}px;"></i> {a}</div>')
            h_am_html = (f'<div style="display:flex; flex-wrap:wrap; align-items:center; gap:15px; margin-bottom:15px; padding:10px 0; border-top:1px solid #eee; border-bottom:1px solid #eee;">{"".join(am_items)}</div>' if am_items else '')
            advs = [f.strip() for f in s.get(f'h_advantages_{i}', '').split('\n') if f.strip()]
            adv_html = (f'<ul class="app-list" style="margin-top:0;">{"".join([f"<li>{a}</li>" for a in advs])}</ul>' if advs else '')
            hp.append(_shtml(f"""{lh}<div class="premium-layout" id="slide-hotel-{i}">
                <div style="flex:40; display:flex; flex-direction:column; gap:15px;">
                    <div style="flex:1; border-radius:8px; overflow:hidden; border:1px solid #eee; background-color:#fcfcfc;">{h1_html}</div>
                    <div style="flex:1; border-radius:8px; overflow:hidden; border:1px solid #eee; background-color:#fcfcfc;">{h1b_html}</div>
                </div>
                <div class="info-col" style="flex:60; padding-left:15px; padding-top:30px; justify-content:flex-start;">
                    <div class="app-overline-style" style="margin-bottom:5px;"><span>{str(s.get(f'h_overline_{i}','ZAKWATEROWANIE'))}</span></div>
                    <div class="title-h1" style="margin-bottom:5px; font-size:{max(20,fs_h1_val-6)}px;">{str(s.get(f'h_title_{i}','')).replace(chr(10),'<br>')}</div>
                    <div class="title-sub" style="color:{acc}; font-size:{max(12,fs_sub_val-4)}px; margin-top:0px; margin-bottom:5px;">{str(s.get(f'h_subtitle_{i}','')).replace(chr(10),'<br>')}</div>
                    {h_url_html}
                    <div style="flex-grow:0; font-size:{fs_t}px; line-height:1.4; margin-bottom:10px; color:{c_t};">{str(s.get(f'h_text_{i}','')).replace(chr(10),'<br>')}</div>
                    {h_am_html}
                    <div style="flex-grow:1;">{adv_html}</div>
                    <div class="gallery-row" style="padding-top:0; padding-bottom:5px; gap:15px;">
                        <div class="gallery-thumb" style="aspect-ratio: unset; height:140px;">{f'<img src="data:image/jpeg;base64,{h2}" style="width:100%;height:100%;object-fit:cover;">' if h2 else _get_ph('FOT DÓŁ 1')}</div>
                        <div class="gallery-thumb" style="aspect-ratio: unset; height:140px;">{f'<img src="data:image/jpeg;base64,{h3}" style="width:100%;height:100%;object-fit:cover;">' if h3 else _get_ph('FOT DÓŁ 2')}</div>
                    </div>
                </div></div>{fh}""", f"slide-hotel-{i}"))

        # --- Slajd MIEJSCA (układ: foto pionowe + opis + 3 miniatury) ---
        elif item_type == 'place':
            if s.get(f"phide_{i}"):
                continue

            ik_p = get_b64(f'pimg1_{i}', (4, 5))
            imk_p = (f"<img src='data:image/jpeg;base64,{ik_p}' style='width:100%;height:100%;object-fit:cover;'>"
                     if ik_p else _get_ph('FOTO MIEJSCA'))
            tk1_p = get_b64(f'pimg2_{i}', (1, 1))
            tk2_p = get_b64(f'pimg3_{i}', (1, 1))
            tk3_p = get_b64(f'pimg4_{i}', (1, 1))

            bb_p = ""
            md_p = re.search(r'Dzień (\d+)', str(s.get(f"pday_{i}") or ""))
            if md_p:
                bb_p = f"<a href='#program_day_{int(md_p.group(1)) - 1}' class='floating-btn'>WRÓĆ DO PROGRAMU</a>"

            p_over = str(s.get(f'pover_{i}') or 'NASZ KIERUNEK')
            p_main = str(s.get(f'pmain_{i}') or '').replace(chr(10), '<br>')
            p_sub  = str(s.get(f'psub_{i}')  or '').replace(chr(10), '<br>')
            p_opis = str(s.get(f'popis_{i}') or '').replace(chr(10), '<br>')

            hp.append(_shtml(f"""{lh}<div class="premium-layout" id="place_{i}">
                <div class="photo-col">{imk_p}{bb_p}</div>
                <div class="info-col" style="padding-top:30px; justify-content:flex-start;">
                    <div class="app-overline-style" style="margin-bottom:15px;"><span>{p_over}</span></div>
                    <div class="title-h1" style="margin-bottom:5px; font-size:{fs_h1_val-6}px;">{p_main}</div>
                    <div class="title-sub" style="margin-bottom:15px;">{p_sub}</div>
                    <div style="flex-grow:1;"><p style="font-size:{fs_t}px; line-height:1.6; color:{c_t};">{p_opis}</p></div>
                    <div class="gallery-row" style="padding-top:0; padding-bottom:5px;">
                        <div class="gallery-thumb">{f'<img src="data:image/jpeg;base64,{tk1_p}" style="width:100%;height:100%;object-fit:cover;">' if tk1_p else _get_ph('FOT 1')}</div>
                        <div class="gallery-thumb">{f'<img src="data:image/jpeg;base64,{tk2_p}" style="width:100%;height:100%;object-fit:cover;">' if tk2_p else _get_ph('FOT 2')}</div>
                        <div class="gallery-thumb">{f'<img src="data:image/jpeg;base64,{tk3_p}" style="width:100%;height:100%;object-fit:cover;">' if tk3_p else _get_ph('FOT 3')}</div>
                    </div>
                </div>
            </div>{fh}""", f"place_{i}"))

        # --- Slajd ATRAKCJI ---
        elif item_type == 'attr':
            if s.get(f"ahide_{i}"):
                continue
            iah = get_b64(f'ah_{i}', (4, 5))
            a1 = get_b64(f'at1_{i}', (1, 1))
            a2 = get_b64(f'at2_{i}', (1, 1))
            a3 = get_b64(f'at3_{i}', (1, 1))
            bb_a = ""
            md_a = re.search(r'Dzień (\d+)', str(s.get(f"aday_{i}") or ""))
            if md_a:
                bb_a = f"<a href='#program_day_{int(md_a.group(1)) - 1}' class='floating-btn'>WRÓĆ DO PROGRAMU</a>"
            hp.append(_shtml(f"""{lh}<div class="premium-layout" id="attr_{i}">
                <div class="photo-col">{f'<img src="data:image/jpeg;base64,{iah}" style="width:100%;height:100%;object-fit:cover;">' if iah else _get_ph('FOTO GŁÓWNE')}{bb_a}</div>
                <div class="info-col">
                    {f'<div class="type-icon-box">{icon_map.get(s.get(f"atype_{i}",""),"")}</div>' if s.get(f"atype_{i}") and s.get(f"atype_{i}") != "Brak" else ''}
                    <div class="title-h2">{str(s.get(f'amain_{i}','')).replace(chr(10),'<br>')}</div>
                    <div class="title-sub">{str(s.get(f'asub_{i}','')).replace(chr(10),'<br>')}</div>
                    <div style="flex-grow:1;"><p>{str(s.get(f'aopis_{i}') or '').replace(chr(10),'<br>')}</p></div>
                    <div class="gallery-row">
                        <div class="gallery-thumb">{f'<img src="data:image/jpeg;base64,{a1}" style="width:100%;height:100%;object-fit:cover;">' if a1 else _get_ph('FOT 1')}</div>
                        <div class="gallery-thumb">{f'<img src="data:image/jpeg;base64,{a2}" style="width:100%;height:100%;object-fit:cover;">' if a2 else _get_ph('FOT 2')}</div>
                        <div class="gallery-thumb">{f'<img src="data:image/jpeg;base64,{a3}" style="width:100%;height:100%;object-fit:cover;">' if a3 else _get_ph('FOT 3')}</div>
                    </div></div></div>{fh}""", f"attr_{i}"))
    # --- Aplikacja ---
    if not s.get('app_hide', False):
        ibg = s.get('img_app_bg')
        ibg_b64 = base64.b64encode(ibg).decode() if ibg else None
        bg_html = (f'<img src="data:image/jpeg;base64,{ibg_b64}" style="width:100%;height:100%;object-fit:cover;">'
                   if ibg_b64 else '<div class="photo-placeholder">ZDJĘCIE TŁA</div>')
        iscr = get_b64('img_app_screen', (9, 16))
        # object-fit:contain żeby ekran nie był przycinany, object-position:top żeby góra była widoczna
        scr_html = (f'<img class="phone-screen" src="data:image/jpeg;base64,{iscr}" style="width:100%;height:100%;object-fit:contain;object-position:top;display:block;background:#fff;">'
                    if iscr else '<div class="photo-placeholder" style="background:#fff;">EKRAN APP</div>')
        fh_app = "".join([f"<li>{f.strip()}</li>" for f in s.get('app_features', '').split('\n') if f.strip()])
        hp.append(_shtml(f"""{lh}<div style="position:relative;height:100%;width:100%;display:flex; overflow:hidden;">
            <div style="flex:0 0 52%; max-width:52%; z-index:2; display:flex; flex-direction:column; padding-right:16px; padding-top:24px; justify-content:flex-start;">
                <div class="app-overline-style"><span>{str(s.get('app_overline',''))}</span></div>
                <div class="title-h1" style="margin-bottom:10px; font-size:{fs_h1_val-8}px;">{str(s.get('app_title','')).replace(chr(10),'<br>')}</div>
                <div class="title-sub" style="margin-bottom:14px; font-size:{max(10,fs_sub_val-6)}px;">{str(s.get('app_subtitle','')).replace(chr(10),'<br>')}</div>
                <ul class="app-list" style="margin-top:0;">{fh_app}</ul></div>
            <div class="app-image-col" style="top:-30px;right:-45px;bottom:0;">{bg_html}</div>
            <div class="phone-mockup">{scr_html}</div></div>{fh}""", "slide-app"))

    # --- Branding ---
    if not s.get('brand_hide', False):
        b1 = get_b64('img_brand_1', (1, 1))
        b2 = get_b64('img_brand_2', (1, 1))
        b3 = get_b64('img_brand_3', (16, 9))
        b1h = (f'<img src="data:image/jpeg;base64,{b1}" style="width:100%;height:100%;object-fit:cover;">' if b1 else _get_ph('ZDJ 1'))
        b2h = (f'<img src="data:image/jpeg;base64,{b2}" style="width:100%;height:100%;object-fit:cover;">' if b2 else _get_ph('ZDJ 2'))
        b3h = (f'<img src="data:image/jpeg;base64,{b3}" style="width:100%;height:100%;object-fit:cover;"><div class="brand-gap"></div>' if b3 else _get_ph('ZDJ 3'))
        bfh = "".join([f"<li>{f.strip()}</li>" for f in s.get('brand_features', '').split('\n') if f.strip()])
        hp.append(_shtml(f"""{lh}<div class="premium-layout">
            <div class="info-col" style="flex: 55; padding-right: 30px; padding-top: 24px; justify-content: flex-start;">
                <div class="app-overline-style"><span>{str(s.get('brand_overline',''))}</span></div>
                <div class="title-h1" style="margin-bottom: 10px; font-size:{fs_h1_val-8}px;">{str(s.get('brand_title','')).replace(chr(10),'<br>')}</div>
                <div class="title-sub" style="margin-bottom:14px; font-size:{max(10,fs_sub_val-6)}px;">{str(s.get('brand_subtitle','')).replace(chr(10),'<br>')}</div>
                <ul class="app-list" style="margin-top:0;">{bfh}</ul>
            </div>
            <div style="flex: 50; position: relative; height: 100%;"><div class="brand-collage">
                <div class="brand-img-1">{b1h}</div><div class="brand-img-2">{b2h}</div><div class="brand-img-3">{b3h}</div>
            </div></div></div>{fh}""", "slide-branding"))

    # --- Wirtualny asystent ---
    if not s.get('va_hide', False):
        va1 = get_b64('img_va_1', (16, 9))
        va2 = get_b64('img_va_2', (1, 1))
        va3 = get_b64('img_va_3', (1, 1))
        v1h = (f'<img src="data:image/jpeg;base64,{va1}" style="width:100%;height:100%;object-fit:cover;">' if va1 else _get_ph('ZDJ 1'))
        v2h = (f'<img src="data:image/jpeg;base64,{va2}" style="width:100%;height:100%;object-fit:cover;">' if va2 else _get_ph('ZDJ 2'))
        v3h = (f'<img src="data:image/jpeg;base64,{va3}" style="width:100%;height:100%;object-fit:cover;">' if va3 else _get_ph('ZDJ 3'))
        hp.append(_shtml(f"""{lh}<div class="premium-layout">
            <div style="flex: 45; position: relative; height: 100%;"><div class="va-collage">
                <div class="va-img-1-wrap va-img-common">{v1h}</div>
                <div class="va-img-2-wrap va-img-common">{v2h}</div>
                <div class="va-img-3-wrap va-img-common">{v3h}</div>
            </div></div>
            <div class="info-col" style="flex: 55; padding-left: 40px; padding-top: 30px; justify-content: flex-start;">
                <div class="app-overline-style"><span>{str(s.get('va_overline',''))}</span></div>
                <div class="title-h1" style="margin-bottom: 15px; font-size:{fs_h1_val-6}px;">{str(s.get('va_title','')).replace(chr(10),'<br>')}</div>
                <div class="title-sub" style="margin-bottom:25px; font-size:{max(12,fs_sub_val-4)}px;">{str(s.get('va_subtitle','')).replace(chr(10),'<br>')}</div>
                <div style="font-family: '{f_t}'; font-size: {fs_t}px; line-height: 1.6; color: {c_t}; text-align: justify;">{str(s.get('va_text') or '').replace(chr(10),'<br>')}</div>
            </div></div>{fh}""", "slide-virtual-assistant"))

    # --- Pillow gifts ---
    if not s.get('pg_hide', False):
        pg1 = get_b64('img_pg_1', (1, 1))
        pg2 = get_b64('img_pg_2', (1, 2.1))
        pg3 = get_b64('img_pg_3', (1, 1))
        h1_pg = (f'<img src="data:image/jpeg;base64,{pg1}" style="width:100%;height:100%;object-fit:cover;">' if pg1 else _get_ph('ZDJ 1'))
        h2_pg = (f'<img src="data:image/jpeg;base64,{pg2}" style="width:100%;height:100%;object-fit:cover;">' if pg2 else _get_ph('ZDJ 2 PION'))
        h3_pg = (f'<img src="data:image/jpeg;base64,{pg3}" style="width:100%;height:100%;object-fit:cover;">' if pg3 else _get_ph('ZDJ 3'))
        hp.append(_shtml(f"""{lh}<div class="premium-layout">
            <div style="flex:50;position:relative;height:100%;"><div class="pg-collage">
                <div class="pg-img-1-wrap pg-img-common">{h1_pg}</div>
                <div class="pg-img-2-wrap pg-img-common">{h2_pg}</div>
                <div class="pg-img-3-wrap pg-img-common">{h3_pg}</div>
            </div></div>
            <div class="info-col" style="flex:50;padding-left:40px;padding-top:30px;justify-content:flex-start;">
                <div class="app-overline-style"><span>{str(s.get('pg_overline',''))}</span></div>
                <div class="title-h1" style="margin-bottom:10px; font-size:{fs_h1_val-8}px;">{str(s.get('pg_title','')).replace(chr(10),'<br>')}</div>
                <div class="title-sub" style="margin-bottom:12px; font-size:{max(10,fs_sub_val-6)}px;">{str(s.get('pg_subtitle','')).replace(chr(10),'<br>')}</div>
                <div style="font-family:'{f_t}';font-size:{max(10,fs_t-1)}px;line-height:1.5;color:{c_t};margin-bottom:10px;">{str(s.get('pg_text') or '').replace(chr(10),'<br>')}</div>
                {f'<ul class="app-list" style="margin-top:0;">{"".join([f"<li>{x.strip()}</li>" for x in str(s.get("pg_features","")).split(chr(10)) if x.strip()])}</ul>' if s.get('pg_features','').strip() else ''}
            </div></div>{fh}""", "slide-pillow-gifts"))

    # --- Kosztorys (slajd 1) ---
    if not s.get('koszt_hide_1', False):
        k1 = get_b64('img_koszt_1', (4, 5))
        imk1 = (f"<img src='data:image/jpeg;base64,{k1}' style='width:100%;height:100%;object-fit:cover;'>"
                if k1 else _get_ph('ZDJĘCIE KOSZTORYSU'))
        zaw1_list = []
        for x in s.get('koszt_zawiera_1', '').split('\n'):
            if not x.strip():
                continue
            if x.strip().startswith('--'):
                zaw1_list.append(f"<li class='sub-item'>{x.replace('--','',1).strip()}</li>")
            else:
                zaw1_list.append(f"<li>{x.strip()}</li>")
        zaw1_html = f'<ul class="app-list">{"".join(zaw1_list)}</ul>' if zaw1_list else ''
        hp.append(_shtml(f"""{lh}<div class="premium-layout"><div class="photo-col">{imk1}</div>
            <div class="info-col" style="padding-top:30px; justify-content:flex-start;">
            <div class="app-overline-style" style="margin-bottom:5px;"><span>{str(s.get('koszt_title','KOSZTORYS'))}</span></div>
            <div class="title-h1" style="margin-bottom:15px; font-size:{fs_h1_val}px;">{str(s.get('koszt_h1_title','KOSZTORYS'))}</div>
            <div style="background:{acc}; color:white; padding: 25px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 10px 25px rgba(0,0,0,0.1);">
                <div style="font-size:{max(10,fs_t-2)}px; font-family:'{f_h2}'; font-weight:700; text-transform:uppercase; margin-bottom:5px; opacity:0.9; letter-spacing:1px;">Grupa {s.get('koszt_pax','')} osób | {s.get('koszt_hotel','')}</div>
                <div style="font-size:{fs_h1_val-8}px; font-weight:800; font-family:'{f_h1}';">CENA: {s.get('koszt_price','')}</div>
            </div>
            <div style="font-family:'{f_h2}'; font-weight:800; font-size:{fs_t+4}px; color:{c_h2}; margin-bottom:10px; text-transform:uppercase;">CENA OFERTY OBEJMUJE:</div>
            <div style="flex-grow:1; overflow-y:auto; padding-right:10px;">{zaw1_html}</div>
            </div></div>{fh}""", "slide-kosztorys-1"))

    # --- Kosztorys (slajd 2) ---
    if not s.get('koszt_hide_1', False) and not s.get('koszt_hide_2', False):
        k2 = get_b64('img_koszt_2', (4, 5))
        imk2 = (f"<img src='data:image/jpeg;base64,{k2}' style='width:100%;height:100%;object-fit:cover;'>"
                if k2 else _get_ph('ZDJĘCIE KOSZTORYSU 2'))
        zaw2_list = []
        for x in s.get('koszt_zawiera_2', '').split('\n'):
            if not x.strip():
                continue
            if x.strip().startswith('--'):
                zaw2_list.append(f"<li class='sub-item'>{x.replace('--','',1).strip()}</li>")
            else:
                zaw2_list.append(f"<li>{x.strip()}</li>")
        zaw2_html = f'<ul class="app-list">{"".join(zaw2_list)}</ul>' if zaw2_list else ''
        niezaw_list = [f"<li>{x.strip()}</li>" for x in s.get('koszt_nie_zawiera', '').split('\n') if x.strip()]
        niezaw_html = f'<ul class="app-list" style="margin-top:5px;">{"".join(niezaw_list)}</ul>' if niezaw_list else ''
        opcje = s.get('koszt_opcje', '').strip()
        opcje_html = (f"""<div style="margin-top:20px;"><div style="font-family:'{f_h2}'; font-weight:800; font-size:{fs_t+2}px; color:{c_h2}; margin-bottom:5px; text-transform:uppercase;">KOSZTY OPCJONALNE:</div><div style="font-family:'{f_t}'; font-size:{fs_t}px; color:{c_t}; white-space:pre-line; line-height:1.5;">{opcje}</div></div>"""
                      if opcje else '')
        hp.append(_shtml(f"""{lh}<div class="premium-layout">
            <div class="info-col" style="padding-top:30px; justify-content:flex-start; padding-right:30px;">
                <i class="fa-solid fa-file-invoice" style="color:{acc}; font-size:36px; margin-bottom:15px; display:block;"></i>
                <div class="app-overline-style" style="margin-bottom:15px;"><span>KOSZTORYS - CIĄG DALSZY</span></div>
                {zaw2_html}
                <div style="font-family:'{f_h2}'; font-weight:800; font-size:{fs_t+2}px; color:{c_h2}; margin-top:15px; margin-bottom:5px; text-transform:uppercase;">NIE POLICZONE W CENIE:</div>
                {niezaw_html}
                {opcje_html}
            </div>
            <div class="photo-col">{imk2}</div>
            </div>{fh}""", "slide-kosztorys-2"))




    # --- Przerywnik sek_2 (przed testim) ---
    _render_sek(2)  # Przerywnik przed rekomendacjami

        # --- Rekomendacje ---
    if not s.get('testim_hide', False):
        t_main_img = get_b64('img_testim_main', (4, 5))
        t_main_img_html = (f'<img src="data:image/jpeg;base64,{t_main_img}" style="width:100%;height:100%;object-fit:cover;">'
                           if t_main_img else _get_ph('ZDJĘCIE GŁÓWNE'))
        t_h = ""
        for i in range(s.get('testim_count', 3)):
            it = get_b64(f'testim_img_{i}', (1, 1))
            itg = (f"<img src='data:image/jpeg;base64,{it}' style='width:100%;height:100%;object-fit:cover;'>"
                   if it else _get_ph('LOGO'))
            t_h += f"""<div class="testim-item"><div class="testim-img-wrapper">{itg}</div>
                <div class="testim-content">
                    <div class="testim-head">{str(s.get(f'testim_head_{i}','')).replace(chr(10),'<br>')}</div>
                    <div class="testim-quote">"{s.get(f'testim_quote_{i}','')}"</div>
                    <div class="testim-author"><strong>{s.get(f'testim_author_{i}','')}</strong> | {s.get(f'testim_role_{i}','')}</div>
                </div></div>"""
        hp.append(_shtml(f"""{lh}<div class="premium-layout">
            <div class="info-col" style="flex: 55; padding-right: 40px; padding-top: 30px; justify-content: flex-start;">
                <div class="app-overline-style"><span>{str(s.get('testim_overline','REKOMENDACJE'))}</span></div>
                <div class="title-h1" style="margin-bottom: 15px; font-size:{fs_h1_val-6}px;">{str(s.get('testim_title','')).replace(chr(10),'<br>')}</div>
                <div class="title-sub" style="margin-bottom:25px; font-size:{max(12,fs_sub_val-4)}px;">{str(s.get('testim_subtitle','')).replace(chr(10),'<br>')}</div>
                <div style="display: flex; flex-direction: column;">{t_h}</div>
            </div>
            <div class="photo-col" style="flex: 45;">{t_main_img_html}</div>
            </div>{fh}""", "slide-testimonials"))

    # --- O nas / Zespół ---
    if not s.get('about_hide', False):
        tm_h = ""
        tc = s.get('team_count', 2)
        grid_cols = "1fr 1fr" if tc in (2, 4) else f"repeat({tc}, 1fr)"
        for i in range(tc):
            it = get_b64(f't_img_{i}', (1, 1))
            itg = (f"<img src='data:image/jpeg;base64,{it}' style='width:70px;height:70px;border-radius:50%;border:2px solid {acc};object-fit:cover;'>"
                   if it else f"<div style='width:70px;height:70px;border-radius:50%;border:2px dashed #ccc;display:flex;align-items:center;justify-content:center;margin:0 auto 10px auto;color:#aaa;font-size:10px;'>ZDJĘCIE</div>")
            tm_h += f"""<div style='display:flex; flex-direction:column; align-items:flex-start; text-align:left;'>
                <div style="margin-bottom:8px;">{itg}</div>
                <div style='font-family:Montserrat;font-weight:800;font-size:{max(12,fs_t)}px;color:{c_h2};line-height:1.2;margin-bottom:2px;'>{str(s.get(f't_name_{i}',''))}</div>
                <div style='font-size:{max(9,fs_t-3)}px;color:{acc};font-weight:600;margin-bottom:6px;text-transform:uppercase;'>{str(s.get(f't_role_{i}',''))}</div>
                <div style='font-size:{max(10,fs_t-2)}px;line-height:1.4;color:{c_t};'>{str(s.get(f't_desc_{i}') or '').replace(chr(10),'<br>')}</div>
            </div>"""
        c_img = get_b64('img_about_clients', (4, 5))
        c_img_html = (f'<img src="data:image/jpeg;base64,{c_img}" style="width:100%;height:100%;object-fit:cover;">'
                      if c_img else _get_ph('ZDJĘCIE / LOGA KLIENTÓW'))
        hp.append(_shtml(f"""{lh}<div class="premium-layout">
            <div class="info-col" style="flex: 60; padding-right: 40px; padding-top: 30px; justify-content: flex-start; display: flex; flex-direction: column;">
                <div class="app-overline-style"><span>{str(s.get('about_overline','NASZ ZESPÓŁ'))}</span></div>
                <div class="title-h1" style="margin-bottom: 15px; font-size:{fs_h1_val-6}px;">{str(s.get('about_title','')).replace(chr(10),'<br>')}</div>
                <div class="title-sub" style="margin-bottom:25px; font-size:{max(12,fs_sub_val-4)}px;">{str(s.get('about_sub','')).replace(chr(10),'<br>')}</div>
                <div style="font-family: '{f_t}'; font-size: {fs_t}px; line-height: 1.6; color: {c_t}; text-align: justify; margin-bottom: 15px;">{str(s.get('about_desc') or '').replace(chr(10),'<br>')}</div>
                <div style="display: grid; grid-template-columns: {grid_cols}; gap: 20px; margin-top: auto; border-top: 1px solid #eee; padding-top: 20px;">{tm_h}</div>
            </div>
            <div class="photo-col" style="flex: 40; background-color: #fcfcfc;">{c_img_html}</div>
            </div>{fh}""", "slide-about"))

    # --- Zwróć lub wyświetl ---
    if export_mode:
        return "".join(hp)

    # Budujemy cały CSS + slajdy + scroll w jednym components.html.
    # To jedyne podejście działające na Streamlit Community Cloud:
    # - brak limitu rozmiaru (w przeciwieństwie do st.markdown)
    # - pełny dostęp do DOM własnego dokumentu (w przeciwieństwie do window.parent)
    # - scroll działa na .presentation-wrapper który ma własny overflow:auto
    import streamlit.components.v1 as components

    first_visible_place = next(
        (i for i in range(s.get('num_places', 0)) if not s.get(f'phide_{i}')), None
    )
    # Gdy brak miejsc — scroll do slajdu wzorcowego place_preview (zawsze renderowanego w trybie edycji)
    pid = f"place_{first_visible_place}" if first_visible_place is not None else "place_preview"
    first_visible_attr = next(
        (i for i in range(s.get('num_attr', 0)) if not s.get(f'ahide_{i}')), None
    )
    fid = f"attr_{first_visible_attr}" if first_visible_attr is not None else "slide-title"
    # Pierwszy hotel
    hid = f"slide-hotel-0" if s.get('num_hotels', 1) > 0 and not s.get('h_hide_0') else "slide-title"

    default_tid = {
        "Strona Tytułowa": "slide-title", "Opis Kierunku": "slide-kierunek",
        "Mapa Podróży": "slide-mapa", "Jak lecimy?": "slide-loty",
        "Zakwaterowanie": hid, "Program Wyjazdu": "slide-program",
        "Opisy miejsc": pid, "Opis atrakcji": fid,
        "Kosztorys": "slide-kosztorys-1", "Aplikacja (Komunikacja)": "slide-app",
        "Materiały Brandingowe": "slide-branding",
        "Wirtualny Asystent": "slide-virtual-assistant",
        "Pillow Gifts": "slide-pillow-gifts",
        "Co o nas mówią": "slide-testimonials", "O Nas (Zespół)": "slide-about",
        "  ↳ Przerywnik hotel":    "slide-sek_0",
        "  ↳ Przerywnik program":  "slide-sek_3",
        "  ↳ Przerywnik atrakcje": "slide-sek_1",
        "Opis atrakcji i miejsc": "slide-sek_1",
        "  ↳ Przerywnik o nas":    "slide-sek_2",
    }.get(current_page, "")

    tid = s.get('scroll_target') or default_tid
    if 'scroll_target' in s:
        s['scroll_target'] = ""

    css_str = get_local_css(return_str=True)
    slides_html = "".join(hp)

    scroll_js = f"""
    <script>
    (function() {{
        var targetId = "{tid if tid else ''}";
        var wrapper = document.getElementById('main-wrapper');
        if (!wrapper || !targetId) return;

        function getOffset(id) {{
            var el = document.getElementById(id);
            if (!el) return null;
            return Math.max(0, el.offsetTop - (wrapper.clientHeight / 2) + (el.offsetHeight / 2));
        }}

        // Iframe po rerunie startuje od scrollTop=0 i jest niewidoczny (opacity:0).
        // 1. Instant skok do slajdu tuż przed celem (jeden slajd wyżej)
        // 2. Ciało staje się widoczne (opacity:1, transition 0.15s)
        // 3. Smooth scroll do właściwego slajdu
        // Efekt: widoczne jest tylko krótkie płynne przewinięcie o jeden slajd.
        var targetOffset = getOffset(targetId);
        if (targetOffset === null) return;

        // Skocz instant do pozycji jeden ekran przed celem
        var slideH = wrapper.clientHeight;
        wrapper.scrollTo({{ top: Math.max(0, targetOffset - slideH), behavior: 'instant' }});

        // Pokaż ciało i płynnie dojedź do celu
        document.body.style.transition = 'opacity 0.15s ease';
        document.body.style.opacity = '1';
        setTimeout(function() {{
            wrapper.scrollTo({{ top: targetOffset, behavior: 'smooth' }});
        }}, 50);
    }})();
    </script>"""

    full_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
{css_str}
<style>
  @keyframes fadein {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
  body {{ margin: 0; padding: 0; background: transparent; overflow: hidden; opacity: 0; }}
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

    components.html(full_html, height=900, scrolling=False)
