import streamlit as st
import streamlit.components.v1 as components
import json, base64, re
from datetime import datetime, timedelta, date

from renderer import (
    optimize_img, optimize_logo, geocode_place, generate_map_data,
    build_presentation, get_project_filename, get_local_css, create_slug,
    icon_map, hotel_icons, pl_days_map, COUNTRIES_DICT, FONTS_LIST, FONT_WEIGHTS
)

# Minimalistyczna konfiguracja
st.set_page_config(layout="wide", page_title="Activezone Oferta", initial_sidebar_state="expanded")

st.markdown("""
<style>
div.stButton > button { border-radius: 4px !important; font-family: 'Montserrat', sans-serif !important; text-transform: uppercase !important; font-size: 12px !important; letter-spacing: 1px !important; font-weight: 600 !important; }
div.stDownloadButton > button { border-radius: 4px !important; font-family: 'Montserrat', sans-serif !important; text-transform: uppercase !important; font-size: 12px !important; letter-spacing: 1px !important; font-weight: 600 !important; }
div.stDownloadButton > button svg { display: none !important; }
div[data-testid="stExpander"] { border-radius: 4px !important; border: 1px solid #e2e8f0 !important; }
</style>
""", unsafe_allow_html=True)

if 'client_mode' not in st.session_state: st.session_state['client_mode'] = False

def clean_str(val, default=""):
    return default if val is None or str(val).strip() == "None" else str(val)

def set_focus(target_id):
    st.session_state['scroll_target'] = target_id

def parse_date_and_days():
    d_str = st.session_state.get('t_date', '').strip()
    m1 = re.search(r'^(\d{1,2})\s*-\s*(\d{1,2})\.(\d{1,2})\.(\d{4})$', d_str)
    m2 = re.search(r'^(\d{1,2})\.(\d{1,2})\s*-\s*(\d{1,2})\.(\d{1,2})\.(\d{4})$', d_str)
    m3 = re.search(r'^(\d{1,2})\.(\d{1,2})\.(\d{4})$', d_str)
    try:
        if m1:
            s_dt = date(int(m1.group(4)), int(m1.group(3)), int(m1.group(1)))
            st.session_state['num_days'] = (date(int(m1.group(4)), int(m1.group(3)), int(m1.group(2))) - s_dt).days + 1
            st.session_state['p_start_dt'] = s_dt
        elif m2:
            s_dt = date(int(m2.group(5)), int(m2.group(2)), int(m2.group(1)))
            st.session_state['num_days'] = (date(int(m2.group(5)), int(m2.group(4)), int(m2.group(3))) - s_dt).days + 1
            st.session_state['p_start_dt'] = s_dt
        elif m3:
            s_dt = date(int(m3.group(3)), int(m3.group(2)), int(m3.group(1)))
            st.session_state['num_days'] = 1
            st.session_state['p_start_dt'] = s_dt
    except Exception: pass

IMAGE_KEYS = {
    'img_hero_t', 'img_hero_k', 'img_hero_l', 'img_map_bg', 'img_map_bg_auto',
    'logo_az', 'logo_cli', 'img_app_bg', 'img_app_screen',
    'img_brand_1', 'img_brand_2', 'img_brand_3',
    'img_va_1', 'img_va_2', 'img_va_3',
    'img_pg_1', 'img_pg_2', 'img_pg_3',
    'img_koszt_1', 'img_koszt_2', 'img_testim_main', 'img_about_clients',
    'img_k_th1', 'img_k_th2', 'img_k_th3',
}
for _i in range(50):
    IMAGE_KEYS.update({
        f'img_hotel_1_{_i}', f'img_hotel_1b_{_i}', f'img_hotel_2_{_i}', f'img_hotel_3_{_i}',
        f'img_d_{_i}', f'ah_{_i}', f'at1_{_i}', f'at2_{_i}', f'at3_{_i}',
        f'pimg1_{_i}', f'pimg2_{_i}', f'testim_img_{_i}', f't_img_{_i}',
    })

def load_project_data(data: dict):
    for k, v in data.items():
        if k in IMAGE_KEYS and isinstance(v, str):
            try: st.session_state[k] = base64.b64decode(v)
            except Exception: st.session_state[k] = v
        elif k == 'p_start_dt' and isinstance(v, str):
            try: st.session_state[k] = date.fromisoformat(v)
            except Exception: pass
        else:
            st.session_state[k] = v

def section_template_manager(section_keys, file_prefix, default_filename, uploader_key, index=None):
    ATR_KEY_MAP = {"atype": "type", "amain": "main", "asub": "sub", "aopis": "opis"}
    st.markdown("<div style='font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-top: 15px; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; letter-spacing: 1px;'>Zarządzanie Szablonem Sekcji</div>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        uploaded_file = st.file_uploader("Wgraj plik JSON", type=['json'], key=f"up_{uploader_key}", label_visibility="collapsed")
        if st.button("WCZYTAJ SZABLON", key=f"btn_apply_{uploader_key}", use_container_width=True, disabled=not uploaded_file):
            try:
                data = json.load(uploaded_file)
                filtered_data = {}
                for k in section_keys:
                    save_key = k
                    load_key = k if index is None else re.sub(f'_{index}$', '', k)
                    if file_prefix == "ATR": load_key = ATR_KEY_MAP.get(load_key, load_key)
                    if load_key in data: filtered_data[save_key] = data[load_key]
                load_project_data(filtered_data)
                st.success("Szablon wczytany pomyślnie.")
                st.rerun()
            except Exception: st.error("Błąd odczytu pliku szablonu.")

    with c2:
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
        custom_name = st.text_input("Nazwa pliku:", value=base_slug, key=f"fn_{uploader_key}", label_visibility="collapsed")
        full_filename = f"{cc}-{file_prefix}-{create_slug(custom_name)}.json"
        st.download_button("POBIERZ SZABLON", json_str, full_filename, key=f"dl_{uploader_key}", use_container_width=True)
    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

defaults = {
    'country_name': 'Czarnogóra', 'country_code': 'MNE',
    'font_h1': 'Montserrat', 'font_h2': 'Montserrat', 'font_sub': 'Montserrat', 'font_text': 'Open Sans', 'font_metric': 'Montserrat',
    'color_h1': '#003366', 'color_h2': '#003366', 'color_sub': '#FF6600', 'color_accent': '#FF6600', 'color_text': '#333333', 'color_metric': '#003366',
    'font_size_h1': 48, 'font_size_h2': 36, 'font_size_sub': 26, 'font_size_text': 14, 'font_size_metric': 16,
    't_main': 'BAŁKAŃSKI KLEJNOT', 't_sub': 'MONTENEGRO EXPERIENCE', 't_klient': 'NAZWA KLIENTA',
    't_kierunek': 'CZARNOGÓRA', 't_date': '1-4.10.2026', 't_pax': '60', 't_hotel': '4* ALL INCLUSIVE', 't_trans': 'SAMOLOT PLL LOT',
    'hide_logo_cli': False,
    'k_hide': False, 'k_overline': 'OPIS KIERUNKU', 'k_main': 'CZARNOGÓRA', 'k_sub': 'BAŁKAŃSKI KLEJNOT', 'k_opis': 'Opisz tutaj <b>piękno</b> kierunku...',
    'l_hide': False, 'l_przesiadka': False, 'l_port': 'Monachium (MUC)', 'l_czas': '3h 20 min', 'l_overline': 'PRZELOT', 'l_main': 'JAK LECIMY?', 'l_sub': 'NASZA PROPOZYCJA PRZELOTU', 'l_desc': 'Komfortowy przelot liniami PLL LOT.', 'm_route': 'Warszawa (WAW) - Podgorica (TGD)', 'm_luggage': '23kg rejestrowany',
    'f1': 'LO 585, 17MAY, WAW-TGD, 14:25 - 16:25', 'f2': 'LO 586, 21MAY, TGD-WAW, 17:15 - 19:05', 'f3': '', 'f4': '',
    'map_hide': False, 'map_overline': 'TRASA WYJAZDU', 'map_title': 'ZARYS\nPODRÓŻY', 'map_subtitle': 'Kluczowe punkty programu', 'map_desc': 'Zapraszamy do zapoznania się z poglądową mapą naszego wyjazdu. Odkryjemy najpiękniejsze zakątki regionu.',
    'map_zoom': 6, 'num_map_points': 3, 'map_pt_name_0': 'Warszawa', 'map_conn_0': 'Przelot (Linia przerywana + Samolot)', 'map_pt_sym_0': True, 'map_pt_x_0': 15, 'map_pt_y_0': 15, 'map_pt_name_1': 'Podgorica', 'map_conn_1': 'Przejazd (Linia ciągła)', 'map_pt_sym_1': False, 'map_pt_name_2': 'Kotor', 'map_conn_2': 'Brak', 'map_pt_sym_2': False,
    'num_hotels': 1, 'h_hide_0': False, 'h_overline_0': 'ZAKWATEROWANIE', 'h_title_0': 'NAZWA HOTELU 5*', 'h_subtitle_0': 'Komfort i elegancja na najwyższym poziomie', 'h_url_0': 'www.przykładowy-hotel.com', 'h_booking_0': '8.9', 'h_amenities_0': ["Basen", "SPA", "Wi-Fi", "Restauracja", "Plaża"], 'h_text_0': 'Zapewniamy zakwaterowanie w starannie wyselekcjonowanym hotelu.', 'h_advantages_0': 'Położenie tuż przy prywatnej plaży',
    'prg_hide': False, 'num_days': 4, 'num_places': 0, 'num_attr': 1,
    'koszt_hide_1': False, 'koszt_hide_2': False, 'koszt_title': 'KOSZTORYS', 'koszt_pax': '25', 'koszt_price': '4.990 zł / os.', 'koszt_hotel': 'Iberostar Bellevue 4* all inclusive', 'koszt_dbl': '12', 'koszt_sgl': '1',
    'koszt_zawiera_1': 'Wybierz z listy auto-uzupełniania', 'koszt_zawiera_2': '', 'koszt_nie_zawiera': 'Napiwki\nWydatki osobiste\nAtrakcje wymienione jako opcje', 'koszt_opcje': '',
    'app_hide': False, 'app_overline': 'KOMUNIKACJA', 'app_title': 'APLIKACJA\nNA WYJAZD', 'app_subtitle': 'Dedykowana na wyjazd aplikacja dla uczestników', 'app_features': 'Intuicyjna obsługa\nWygoda i nowoczesność',
    'brand_hide': False, 'brand_overline': 'IDENTYFIKACJA', 'brand_title': 'MATERIAŁY\nBRANDINGOWE', 'brand_subtitle': 'Komunikacja przed, w trakcie i po wyjeździe', 
    'brand_features': 'Komunikacja SMS, e-mail, push w aplikacji przed i w trakcie wyjazdu\nAtrakcyjne zaproszenie elektroniczne\nProgram i materiały, w tym koperta na bilet z logo\nStrona www i aplikacja mobilna z formularzem uczestnika\nStanowisko na lotnisku z logo',
    'va_hide': False, 'va_overline': 'SPRAWNA ORGANIZACJA', 'va_title': 'WIRTUALNY\nASYSTENT', 'va_subtitle': 'Sprawna organizacja i wygoda', 'va_text': 'Nowatorski system do zarządzania grupami.',
    'pg_hide': False, 'pg_overline': 'PILLOW GIFTS', 'pg_title': 'PILLOW\nGIFTS', 'pg_subtitle': 'Aby wspólne chwile zatrzymać na dłużej', 'pg_text': 'Upominki pełnią ważną rolę w budowaniu relacji biznesowych.',
    'testim_hide': False, 'testim_overline': 'REKOMENDACJE', 'testim_title': 'CO O NAS\nMÓWIĄ?', 'testim_subtitle': '100% NASZYCH KLIENTÓW JEST CAŁKOWICIE ZADOWOLONYCH Z NASZYCH USŁUG.', 'testim_count': 3, 'testim_head_0': 'PROJEKT INCENTIVE W DUBAJU', 'testim_quote_0': 'Pełen profesjonalizm.', 'testim_author_0': 'Anna Kowalska', 'testim_role_0': 'Dyrektor Marketingu', 'testim_head_1': 'WYJAZD INTEGRACYJNY', 'testim_quote_1': 'Niezwykłe zaangażowanie.', 'testim_author_1': 'Piotr Nowak', 'testim_role_1': 'CEO', 'testim_head_2': 'NAGRODA DLA KLIENTÓW', 'testim_quote_2': 'Współpraca na najwyższym poziomie.', 'testim_author_2': 'Marta Wiśniewska', 'testim_role_2': 'Head of Sales',
    'about_hide': False, 'about_overline': 'NASZ ZESPÓŁ', 'about_title': 'POZNAJMY SIĘ', 'about_sub': 'ZESPÓŁ ACTIVEZONE', 'about_desc': 'Activezone to agencja incentive travel...', 'about_panel_title': 'NASZE WARTOŚCI', 'about_panel_text': 'Bezpieczeństwo\nProfesjonalizm', 'team_count': 2, 'p_start_dt': date(2026, 10, 1)
}

for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

@st.cache_data
def build_day_options(start_dt: date, num_days: int) -> list:
    options = ["Brak przypisania"]
    for d in range(num_days):
        curr_date = start_dt + timedelta(days=d)
        options.append(f"Dzień {d+1} ({curr_date.strftime('%d.%m.%Y')} - {pl_days_map[curr_date.weekday()]})")
    return options

def auto_generate_kosztorys():
    s = st.session_state
    part1, part2 = [], []
    route, luggage = s.get('m_route', ''), s.get('m_luggage', '')
    if route: part1.append(f"Przelot samolotem na trasie {route}, bagaż {luggage}")
    
    dbl, sgl = s.get('koszt_dbl', ''), s.get('koszt_sgl', '')
    part1.append(f"Zakwaterowanie w pokojach dwuosobowych ({dbl}) i jednoosobowych ({sgl})")
    part1.extend(["Wyżywienie wg programu", "Napoje wg programu", "Ubezpieczenie wersja MAX", "Transfery", "Woda podczas wycieczek i transferów", "Opieka profesjonalnego tour leadera Activezone"])
    for i in range(s.get('num_attr', 1)):
        if not s.get(f'ahide_{i}', False):
            name = str(s.get(f'amain_{i}', '')).strip()
            if name: part1.append(name)
            
    if not s.get('brand_hide', False):
        part2.append("Materiały brandingowe:")
        for bf in str(s.get('brand_features', '')).split('\n'):
            if bf.strip(): part2.append(f"-- {bf.strip()}")
            
    if not s.get('app_hide', False): part2.extend(["Aplikacja na wyjazd", "Strona www z formularzem uczestnika"])
    if not s.get('pg_hide', False): part2.append("Pillow gift dla każdego uczestnika na przywitanie")
    part2.extend(["Obowiązkowa opłata TFG i TFP", "VAT marża"])
    
    s['koszt_zawiera_1'] = "\n".join(part1)
    s['koszt_zawiera_2'] = "\n".join(part2)
    s['koszt_nie_zawiera'] = "Napiwki\nWydatki osobiste\nAtrakcje wymienione jako opcje"

# --- RENDEROWANIE GŁÓWNEGO OKNA ---
html_content = build_presentation(current_page=st.session_state.get('last_page', 'Strona Tytułowa'))
st.markdown(f'{get_local_css(True)}\n<div class="presentation-wrapper" id="main-wrapper">{html_content}</div>', unsafe_allow_html=True)

first_visible_place = next((i for i in range(int(st.session_state.get('num_places', 0))) if not st.session_state.get(f'phide_{i}')), None)
pid = f"place_{first_visible_place}" if first_visible_place is not None else "slide-title"
first_visible_attr = next((i for i in range(int(st.session_state.get('num_attr', 1))) if not st.session_state.get(f'ahide_{i}')), None)
fid = f"attr_{first_visible_attr}" if first_visible_attr is not None else "slide-title"

default_tid = {"Strona Tytułowa":"slide-title","Opis Kierunku":"slide-kierunek","Mapa Podróży":"slide-mapa","Jak lecimy?":"slide-loty","Zakwaterowanie":"slide-hotel-0","Program Wyjazdu":"slide-program","Opis miejsc":pid,"Opis atrakcji":fid,"Kosztorys":"slide-kosztorys-1","Aplikacja (Komunikacja)":"slide-app","Materiały Brandingowe":"slide-branding","Wirtualny Asystent":"slide-virtual-assistant","Pillow Gifts":"slide-pillow-gifts","Co o nas mówią":"slide-testimonials","O Nas (Zespół)":"slide-about"}.get(st.session_state.get('last_page', 'Strona Tytułowa'), "")
tid = st.session_state.get('scroll_target') or default_tid

if tid and not st.session_state.get('client_mode', False):
    components.html(f"<script>var t = window.parent.document.getElementById('{tid}'); if(t) {{ t.scrollIntoView({{behavior: 'smooth', block: 'center'}}); }}</script>", height=0)

if st.session_state.get('client_mode', False):
    accent_color = st.session_state.get('color_accent', '#FF6600')
    st.markdown(f"<style>div.stButton {{ position: fixed !important; top: 20px !important; left: 20px !important; z-index: 999999 !important; width: auto !important; }} div.stButton > button {{ background-color: {accent_color} !important; color: white !important; border: none !important; border-radius: 4px !important; padding: 15px 25px !important; font-size: 14px !important; font-weight: 700 !important; box-shadow: 0 4px 15px rgba(0,0,0,0.3) !important; display: flex !important; align-items: center !important; justify-content: center !important; width: auto !important; white-space: nowrap !important; text-transform: uppercase !important; }} div.stButton > button:hover {{ transform: scale(1.02); opacity: 0.9; }}</style>", unsafe_allow_html=True)
    if st.button("ZAKOŃCZ PODGLĄD"):
        st.session_state['client_mode'] = False
        st.rerun()
    st.stop()


# --- PANEL BOCZNY (INTERFEJS) ---
with st.sidebar:
    page = st.radio("WYBIERZ SEKCJĘ:", ["Strona Tytułowa", "Opis Kierunku", "Mapa Podróży", "Jak lecimy?", "Zakwaterowanie", "Program Wyjazdu", "Opis miejsc", "Opis atrakcji", "Aplikacja (Komunikacja)", "Materiały Brandingowe", "Wirtualny Asystent", "Pillow Gifts", "Kosztorys", "Co o nas mówią", "O Nas (Zespół)", "Wygląd i Kolory", "Zapisz / Wczytaj Projekt"])
    
    if st.session_state.get('last_page') != page:
        st.session_state['last_page'] = page
        st.session_state['scroll_target'] = ""
        
    st.divider()

    if page == "Wygląd i Kolory":
        st.markdown("<h2 style='color: #003366; margin-bottom: 0; font-size: 22px; font-weight: 700; font-family: Montserrat, sans-serif;'>KONFIGURACJA WYGLĄDU</h2>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 13px; color: #64748b; margin-bottom: 15px; font-family: Open Sans, sans-serif;'>Dostosuj kolory i typografię oferty</div>", unsafe_allow_html=True)
    elif page == "Zapisz / Wczytaj Projekt":
        st.markdown("<h2 style='color: #003366; margin-bottom: 0; font-size: 22px; font-weight: 700; font-family: Montserrat, sans-serif;'>ZARZĄDZANIE PROJEKTEM</h2>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 13px; color: #64748b; margin-bottom: 15px; font-family: Open Sans, sans-serif;'>Eksportuj lub importuj cały plik JSON</div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<h2 style='color: #003366; margin-bottom: 0; font-size: 22px; font-weight: 700; font-family: Montserrat, sans-serif; text-transform: uppercase;'>{page}</h2>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 13px; color: #64748b; margin-bottom: 15px; font-family: Open Sans, sans-serif;'>Wprowadź dane dla tej sekcji poniżej:</div>", unsafe_allow_html=True)

    if page == "Strona Tytułowa":
        tit_keys = ['t_date', 'country_name', 'country_code', 't_main', 't_sub', 't_klient', 't_kierunek', 't_pax', 't_hotel', 't_trans', 'img_hero_t', 'logo_az', 'logo_cli', 'hide_logo_cli']
        section_template_manager(tit_keys, "TYT", "strona-tytulowa", "tit")
        
        st.text_input("Termin:", key="t_date", on_change=parse_date_and_days)
        st.selectbox("Kraj docelowy:", list(COUNTRIES_DICT.keys()), key="country_name")
        st.session_state['country_code'] = COUNTRIES_DICT[st.session_state['country_name']]
        
        for k, l in [('t_main','Tytuł H1'), ('t_sub','Podtytuł'), ('t_klient','Klient'), ('t_kierunek','Kierunek'), ('t_pax','Liczba osób'), ('t_hotel','Hotel'), ('t_trans','Dojazd')]: 
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
        k_keys = ['k_hide', 'k_overline', 'k_main', 'k_sub', 'k_opis', 'img_hero_k', 'img_k_th1', 'img_k_th2', 'img_k_th3']
        section_template_manager(k_keys, "KIE", st.session_state.get('k_main', 'czarnogora'), "kie")
        
        st.checkbox("Ukryj ten slajd w PDF", key="k_hide")
        st.text_input("Mały nadtytuł:", key="k_overline")
        for k, l in [('k_main','Kierunek (Tytuł H2)'), ('k_sub','Podtytuł')]: 
            st.text_input(l, key=k)
        st.text_area("Opis (obsługuje HTML, np. <b>):", height=200, key="k_opis")
        
        u4 = st.file_uploader("Zdjęcie lewe", key="kie_hero")
        if u4: st.session_state['img_hero_k'] = optimize_img(u4.getvalue())
        c1, c2, c3 = st.columns(3)
        ut1 = c1.file_uploader("Fot. 1", key="kie_th1")
        if ut1: st.session_state['img_k_th1'] = optimize_img(ut1.getvalue())
        ut2 = c2.file_uploader("Fot. 2", key="kie_th2")
        if ut2: st.session_state['img_k_th2'] = optimize_img(ut2.getvalue())
        ut3 = c3.file_uploader("Fot. 3", key="kie_th3")
        if ut3: st.session_state['img_k_th3'] = optimize_img(ut3.getvalue())

    elif page == "Mapa Podróży":
        map_keys = ['map_hide', 'map_overline', 'map_title', 'map_subtitle', 'map_desc', 'img_map_bg', 'map_zoom', 'num_map_points', 'img_map_bg_auto', 'auto_map_points']
        for i in range(int(st.session_state.get('num_map_points', 3))): 
            map_keys.extend([f'map_pt_name_{i}', f'map_conn_{i}', f'map_pt_sym_{i}', f'map_pt_x_{i}', f'map_pt_y_{i}'])
        section_template_manager(map_keys, "MAP", "mapa-podrozy", "map")

        st.checkbox("Ukryj slajd", key="map_hide")
        st.text_input("Mały nadtytuł:", key="map_overline")
        st.text_area("Główny tytuł H1:", key="map_title")
        st.text_input("Podtytuł:", key="map_subtitle")
        st.text_area("Opis pod mapą:", height=100, key="map_desc")

        st.markdown("<div style='font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-top: 15px; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; letter-spacing: 1px;'>AUTOMATYCZNY KREATOR MAPY</div>", unsafe_allow_html=True)
        map_zoom = st.slider("Przybliżenie mapy docelowej (Zoom):", 4, 10, key="map_zoom")
        st.number_input("Liczba punktów na trasie:", 1, 10, step=1, key="num_map_points")
        
        points_data = []
        for i in range(int(st.session_state.get('num_map_points', 3))):
            with st.expander(f"Punkt {i+1}", expanded=True):
                if f'map_pt_name_{i}' not in st.session_state: st.session_state[f'map_pt_name_{i}'] = f'Punkt {i+1}'
                if f'map_conn_{i}' not in st.session_state: st.session_state[f'map_conn_{i}'] = 'Brak'
                if f'map_pt_sym_{i}' not in st.session_state: st.session_state[f'map_pt_sym_{i}'] = False
                if f'map_pt_x_{i}' not in st.session_state: st.session_state[f'map_pt_x_{i}'] = 15
                if f'map_pt_y_{i}' not in st.session_state: st.session_state[f'map_pt_y_{i}'] = 10
                
                st.text_input("Nazwa (np. Rzym, Hiszpania):", key=f"map_pt_name_{i}")
                conn_opts = ["Brak", "Przejazd (Linia ciągła)", "Przelot (Linia przerywana + Samolot)"]
                st.selectbox("Połączenie z NASTĘPNYM punktem:", conn_opts, key=f"map_conn_{i}")
                
                pt_sym = st.checkbox("Punkt oddalony (symboliczny - np. wylot z Polski)", key=f"map_pt_sym_{i}")
                if pt_sym:
                    c1, c2 = st.columns(2)
                    c1.slider("Ręczna pozycja X (lewo-prawo) %:", 0, 100, key=f"map_pt_x_{i}")
                    c2.slider("Ręczna pozycja Y (góra-dół) %:", 0, 100, key=f"map_pt_y_{i}")
                    
                points_data.append({
                    'name': st.session_state[f"map_pt_name_{i}"], 
                    'conn': st.session_state[f"map_conn_{i}"], 
                    'symbolic': st.session_state[f"map_pt_sym_{i}"], 
                    'x': st.session_state[f"map_pt_x_{i}"], 
                    'y': st.session_state[f"map_pt_y_{i}"]
                })

        if st.button("GENERUJ MAPĘ AUTOMATYCZNIE", type="primary", use_container_width=True):
            with st.spinner("Pobieranie i renderowanie danych..."):
                country = st.session_state.get('country_name', '')
                valid_pts = []
                for p in points_data:
                    nm = p['name'].strip()
                    if not nm: continue
                    if p['symbolic']: 
                        valid_pts.append({'name': nm, 'conn': p['conn'], 'symbolic': True, 'x': p['x'], 'y': p['y']})
                    else:
                        lat, lon = geocode_place(nm, country)
                        if lat is None: lat, lon = geocode_place(nm)
                        if lat is not None: 
                            valid_pts.append({'name': nm, 'conn': p['conn'], 'symbolic': False, 'lat': lat, 'lon': lon})
                
                if valid_pts:
                    try:
                        bg_b64, final_pts = generate_map_data(valid_pts, zoom=map_zoom)
                        if bg_b64 is not None or final_pts:
                            if bg_b64: st.session_state['img_map_bg_auto'] = bg_b64
                            st.session_state['auto_map_points'] = final_pts
                            st.success("Mapa wygenerowana pomyślnie.")
                            st.rerun()
                    except Exception: 
                        st.error("Błąd podczas generowania mapy.")

    elif page == "Jak lecimy?":
        l_keys = ['l_hide', 'l_przesiadka', 'l_port', 'l_czas', 'l_overline', 'l_main', 'l_sub', 'm_route', 'm_luggage', 'f1', 'f2', 'f3', 'f4', 'l_desc', 'l_extra', 'img_hero_l']
        section_template_manager(l_keys, "LOT", "jak-lecimy", "lot")

        st.checkbox("Ukryj ten slajd w PDF", key="l_hide")
        st.text_input("Mały nadtytuł:", key="l_overline")
        st.text_input("Tytuł (H1):", key="l_main")
        for k, l in [('l_sub','Podtytuł'), ('m_route','Trasa'), ('m_luggage','Bagaż'), ('f1','Lot 1'), ('f2','Lot 2')]: 
            st.text_input(l, key=k)
        
        if st.checkbox("Lot z przesiadką", key="l_przesiadka"):
            st.markdown("<div style='font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-top: 15px; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; letter-spacing: 1px;'>DANE PRZESIADKI I KOLEJNE ODCINKI LOTU</div>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            c1.text_input("Port przesiadkowy:", key="l_port")
            c2.text_input("Długość przesiadki:", key="l_czas")
            for k, l in [('f3','Lot 3'), ('f4','Lot 4')]: 
                st.text_input(l, key=k)

        for k, l in [('l_desc','Opis'), ('l_extra','Dodatkowe info')]: 
            st.text_area(l, key=k)
            
        u5 = st.file_uploader("Foto Samolotu", key="lot_hero")
        if u5: st.session_state['img_hero_l'] = optimize_img(u5.getvalue())

    elif page == "Zakwaterowanie":
        st.session_state['num_hotels'] = st.number_input("Liczba hoteli do wyboru:", 1, 3, value=int(st.session_state.get('num_hotels', 1)), step=1)
        for i in range(int(st.session_state.get('num_hotels', 1))):
            with st.expander(f"Hotel {i+1}"):
                st.button("POKAŻ PODGLĄD", key=f"btn_show_hot_{i}", on_click=set_focus, args=(f"slide-hotel-{i}",), use_container_width=True)
                
                if f'h_hide_{i}' not in st.session_state: st.session_state[f'h_hide_{i}'] = False
                if f'h_overline_{i}' not in st.session_state: st.session_state[f'h_overline_{i}'] = 'ZAKWATEROWANIE'
                if f'h_title_{i}' not in st.session_state: st.session_state[f'h_title_{i}'] = f'NAZWA HOTELU {i+1} 5*'
                if f'h_subtitle_{i}' not in st.session_state: st.session_state[f'h_subtitle_{i}'] = 'Komfort i elegancja na najwyższym poziomie'
                if f'h_url_{i}' not in st.session_state: st.session_state[f'h_url_{i}'] = 'www.przykładowy-hotel.com'
                if f'h_booking_{i}' not in st.session_state: st.session_state[f'h_booking_{i}'] = '8.9'
                if f'h_amenities_{i}' not in st.session_state: st.session_state[f'h_amenities_{i}'] = ["Basen", "SPA", "Wi-Fi", "Restauracja", "Plaża"]
                if f'h_text_{i}' not in st.session_state: st.session_state[f'h_text_{i}'] = 'Zapewniamy zakwaterowanie w starannie wyselekcjonowanym hotelu.'
                if f'h_advantages_{i}' not in st.session_state: st.session_state[f'h_advantages_{i}'] = 'Położenie tuż przy prywatnej plaży'
                
                h_keys = [f'h_hide_{i}', f'h_overline_{i}', f'h_title_{i}', f'h_subtitle_{i}', f'h_url_{i}', f'h_booking_{i}', f'h_amenities_{i}', f'h_text_{i}', f'h_advantages_{i}', f'img_hotel_1_{i}', f'img_hotel_1b_{i}', f'img_hotel_2_{i}', f'img_hotel_3_{i}']
                section_template_manager(h_keys, "HOT", st.session_state.get(f'h_title_{i}', f'hotel-{i+1}'), f"hot_{i}", index=i)

                st.checkbox("Ukryj ten slajd w PDF", key=f"h_hide_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.text_input("Mały nadtytuł:", key=f"h_overline_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.text_area("Nazwa hotelu (H1):", key=f"h_title_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.text_input("Podtytuł:", key=f"h_subtitle_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                c1, c2 = st.columns(2)
                c1.text_input("Strona www:", key=f"h_url_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                c2.text_input("Ocena Booking.com:", key=f"h_booking_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.multiselect("Udogodnienia (ikonki):", list(hotel_icons.keys()), key=f"h_amenities_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.text_area("Opis hotelu:", height=100, key=f"h_text_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                st.text_area("Atuty hotelu (nowa linia = nowy punkt):", height=100, key=f"h_advantages_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                
                c_left1, c_left2 = st.columns(2)
                u_h1 = c_left1.file_uploader("Zdj. Lewe Górne (poziome)", key=f"uh1_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                if u_h1: st.session_state[f'img_hotel_1_{i}'] = optimize_img(u_h1.getvalue())
                u_h1b = c_left2.file_uploader("Zdj. Lewe Dolne (poziome)", key=f"uh1b_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                if u_h1b: st.session_state[f'img_hotel_1b_{i}'] = optimize_img(u_h1b.getvalue())
                
                c3, c4 = st.columns(2)
                u_h2 = c3.file_uploader("Zdj. Dolne 1 (poziome)", key=f"uh2_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                if u_h2: st.session_state[f'img_hotel_2_{i}'] = optimize_img(u_h2.getvalue())
                u_h3 = c4.file_uploader("Zdj. Dolne 2 (poziome)", key=f"uh3_{i}", on_change=set_focus, args=(f"slide-hotel-{i}",))
                if u_h3: st.session_state[f'img_hotel_3_{i}'] = optimize_img(u_h3.getvalue())

    elif page == "Program Wyjazdu":
        st.checkbox("Ukryj CAŁĄ sekcję Programu w PDF", key="prg_hide")
        st.session_state['num_days'] = st.number_input("Ilość dni:", 1, 15, value=int(st.session_state.get('num_days', 5)), step=1)
        st.date_input("Data startu:", key="p_start_dt")
        for d in range(int(st.session_state.get('num_days', 5))):
            with st.expander(f"Dzień {d+1}"):
                if f"attr_{d}" not in st.session_state: st.session_state[f"attr_{d}"] = ""
                if f"desc_{d}" not in st.session_state: st.session_state[f"desc_{d}"] = ""
                
                d_keys = [f'img_d_{d}', f'attr_{d}', f'desc_{d}']
                section_template_manager(d_keys, "PRG", f"Dzien_{d+1}", f"prg_{d}", index=d)

                ud = st.file_uploader(f"Foto D{d+1} (16:9)", key=f"prg_img_{d}")
                if ud: st.session_state[f"img_d_{d}"] = optimize_img(ud.getvalue())
                st.text_input(f"Highlights D{d+1}", key=f"attr_{d}")
                st.text_area(f"Opis D{d+1}", key=f"desc_{d}")

    elif page == "Opis miejsc":
        day_options_global = build_day_options(
            st.session_state.get('p_start_dt', date.today()),
            int(st.session_state.get('num_days', 5))
        )
        st.session_state['num_places'] = st.number_input("Liczba miejsc:", 0, 20, value=int(st.session_state.get('num_places', 0)), step=1)
        for i in range(int(st.session_state.get('num_places', 0))):
            if f"pmain_{i}" not in st.session_state: st.session_state[f"pmain_{i}"] = ""
            if f"psub_{i}" not in st.session_state: st.session_state[f"psub_{i}"] = ""
            if f"pday_{i}" not in st.session_state: st.session_state[f"pday_{i}"] = "Brak przypisania"
            if f"popis_{i}" not in st.session_state: st.session_state[f"popis_{i}"] = ""
            if f"pfacts_{i}" not in st.session_state: st.session_state[f"pfacts_{i}"] = "Czas przelotu: 7 h\nRóżnica czasu: +4h 30min\nStolica: Nowe Delhi\nKlimat: zwrotnikowy\nWaluta: rupia indyjska"
            if f"phide_{i}" not in st.session_state: st.session_state[f"phide_{i}"] = False
            
            st.session_state[f"pmain_{i}"] = clean_str(st.session_state.get(f"pmain_{i}"))
            st.session_state[f"psub_{i}"] = clean_str(st.session_state.get(f"psub_{i}"))
            st.session_state[f"popis_{i}"] = clean_str(st.session_state.get(f"popis_{i}"))
            
            pmain_val = st.session_state[f"pmain_{i}"]
            
            with st.expander(f"Miejsce {i+1}"):
                st.button("POKAŻ PODGLĄD", key=f"btn_show_place_{i}", on_click=set_focus, args=(f"place_{i}",), use_container_width=True)
                
                p_keys = [f'phide_{i}', f'pover_{i}', f'pmain_{i}', f'psub_{i}', f'pday_{i}', f'pfacts_{i}', f'popis_{i}', f'pimg1_{i}', f'pimg2_{i}']
                section_template_manager(p_keys, "MIE", pmain_val if pmain_val else f"Miejsce_{i+1}", f"plc_{i}", index=i)

                st.checkbox("Ukryj ten slajd w PDF", key=f"phide_{i}", on_change=set_focus, args=(f"place_{i}",))
                st.text_input("Mały nadtytuł:", value=st.session_state.get(f"pover_{i}", "NASZ KIERUNEK"), key=f"pover_{i}", on_change=set_focus, args=(f"place_{i}",))
                st.text_input("Nazwa (H1):", key=f"pmain_{i}", on_change=set_focus, args=(f"place_{i}",))
                st.text_input("Podtytuł:", key=f"psub_{i}", on_change=set_focus, args=(f"place_{i}",))
                
                curr_day = st.session_state.get(f"pday_{i}", "")
                d_match = re.search(r'Dzień\s+(\d+)', curr_day)
                day_idx = 0
                if d_match:
                    d_val = int(d_match.group(1))
                    if 1 <= d_val < len(day_options_global):
                        day_idx = d_val
                
                widget_key = f"pday_{i}"
                if widget_key in st.session_state and st.session_state[widget_key] not in day_options_global:
                    st.session_state[widget_key] = day_options_global[0]
                
                st.selectbox("Przypisz do dnia:", day_options_global, index=day_idx, key=widget_key, on_change=set_focus, args=(f"place_{i}",))
                
                st.text_area("Fakty (niebieska ramka, Format: 'Etykieta: Wartość'):", height=120, key=f"pfacts_{i}", on_change=set_focus, args=(f"place_{i}",))
                st.text_area("Główny opis:", height=150, key=f"popis_{i}", on_change=set_focus, args=(f"place_{i}",))
                
                c1, c2 = st.columns(2)
                up1 = c1.file_uploader("Foto Pionowe (lewe)", key=f"plc_img1_{i}", on_change=set_focus, args=(f"place_{i}",))
                if up1: st.session_state[f"pimg1_{i}"] = optimize_img(up1.getvalue())
                up2 = c2.file_uploader("Foto Kwadrat (środek)", key=f"plc_img2_{i}", on_change=set_focus, args=(f"place_{i}",))
                if up2: st.session_state[f"pimg2_{i}"] = optimize_img(up2.getvalue())

    elif page == "Opis atrakcji":
        day_options_global = build_day_options(
            st.session_state.get('p_start_dt', date.today()),
            int(st.session_state.get('num_days', 5))
        )
        st.session_state['num_attr'] = st.number_input("Ilość atrakcji:", 1, 20, value=int(st.session_state.get('num_attr', 1)), step=1)
        for i in range(int(st.session_state.get('num_attr', 1))):
            if f"amain_{i}" not in st.session_state: st.session_state[f"amain_{i}"] = ""
            if f"asub_{i}" not in st.session_state: st.session_state[f"asub_{i}"] = ""
            if f"aday_{i}" not in st.session_state: st.session_state[f"aday_{i}"] = "Brak przypisania"
            if f"atype_{i}" not in st.session_state: st.session_state[f"atype_{i}"] = "Atrakcja"
            if f"aopis_{i}" not in st.session_state: st.session_state[f"aopis_{i}"] = ""
            if f"ahide_{i}" not in st.session_state: st.session_state[f"ahide_{i}"] = False
            
            st.session_state[f"amain_{i}"] = clean_str(st.session_state.get(f"amain_{i}"))
            st.session_state[f"asub_{i}"] = clean_str(st.session_state.get(f"asub_{i}"))
            st.session_state[f"aopis_{i}"] = clean_str(st.session_state.get(f"aopis_{i}"))
            
            amain_val = st.session_state[f"amain_{i}"]
            
            with st.expander(f"Atrakcja {i+1}"):
                st.button("POKAŻ PODGLĄD", key=f"btn_show_attr_{i}", on_click=set_focus, args=(f"attr_{i}",), use_container_width=True)
                
                a_keys = [f'ahide_{i}', f'amain_{i}', f'asub_{i}', f'aday_{i}', f'atype_{i}', f'aopis_{i}', f'ah_{i}', f'at1_{i}', f'at2_{i}', f'at3_{i}']
                section_template_manager(a_keys, "ATR", amain_val if amain_val else f"Atrakcja_{i+1}", f"atr_{i}", index=i)

                st.checkbox("Ukryj ten slajd w PDF", key=f"ahide_{i}", on_change=set_focus, args=(f"attr_{i}",))
                st.text_input("Nazwa:", key=f"amain_{i}", on_change=set_focus, args=(f"attr_{i}",))
                st.text_input("Podtytuł:", key=f"asub_{i}", on_change=set_focus, args=(f"attr_{i}",))
                
                curr_day = st.session_state.get(f"aday_{i}", "")
                d_match = re.search(r'Dzień\s+(\d+)', curr_day)
                day_idx = 0
                if d_match:
                    d_val = int(d_match.group(1))
                    if 1 <= d_val < len(day_options_global):
                        day_idx = d_val
                
                widget_key = f"aday_{i}"
                if widget_key in st.session_state and st.session_state[widget_key] not in day_options_global:
                    st.session_state[widget_key] = day_options_global[0]
                
                st.selectbox("Przypisz do dnia:", day_options_global, index=day_idx, key=widget_key, on_change=set_focus, args=(f"attr_{i}",))
                st.selectbox("Ikona:", list(icon_map.keys()), key=f"atype_{i}", on_change=set_focus, args=(f"attr_{i}",))
                st.text_area("Opis:", key=f"aopis_{i}", on_change=set_focus, args=(f"attr_{i}",))
                
                upa = st.file_uploader("Foto Główne", key=f"atr_hero_{i}", on_change=set_focus, args=(f"attr_{i}",))
                if upa: st.session_state[f"ah_{i}"] = optimize_img(upa.getvalue())
                c1, c2, c3 = st.columns(3)
                uat1 = c1.file_uploader("Fot. 1", key=f"atr_th1_{i}", on_change=set_focus, args=(f"attr_{i}",))
                if uat1: st.session_state[f"at1_{i}"] = optimize_img(uat1.getvalue())
                uat2 = c2.file_uploader("Fot. 2", key=f"atr_th2_{i}", on_change=set_focus, args=(f"attr_{i}",))
                if uat2: st.session_state[f"at2_{i}"] = optimize_img(uat2.getvalue())
                uat3 = c3.file_uploader("Fot. 3", key=f"atr_th3_{i}", on_change=set_focus, args=(f"attr_{i}",))
                if uat3: st.session_state[f"at3_{i}"] = optimize_img(uat3.getvalue())

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
        st.text_area("Punkty na liście (Enter = nowy punkt):", height=300, key="brand_features")
        
        c1, c2, c3 = st.columns(3)
        u1 = c1.file_uploader("Zdj 1 (Lewa góra)", key="bra_img_1")
        if u1: st.session_state['img_brand_1'] = optimize_img(u1.getvalue())
        u2 = c2.file_uploader("Zdj 2 (Prawa góra)", key="bra_img_2")
        if u2: st.session_state['img_brand_2'] = optimize_img(u2.getvalue())
        u3 = c3.file_uploader("Zdj 3 (Dół - podzielone)", key="bra_img_3")
        if u3: st.session_state['img_brand_3'] = optimize_img(u3.getvalue())

    elif page == "Wirtualny Asystent":
        va_keys = ['va_hide', 'va_overline', 'va_title', 'va_subtitle', 'va_text', 'img_va_1', 'img_va_2', 'img_va_3']
        section_template_manager(va_keys, "VA", "Asystent", "va")

        st.checkbox("Ukryj slajd", key="va_hide")
        st.text_input("Mały nadtytuł:", key="va_overline")
        st.text_area("Główny tytuł H1:", key="va_title")
        st.text_input("Podtytuł:", key="va_subtitle")
        st.text_area("Treść oferty:", height=300, key="va_text")
        
        c1, c2, c3 = st.columns(3)
        u1 = c1.file_uploader("Zdj 1 (Szerokie)", key="va_img_1")
        if u1: st.session_state['img_va_1'] = optimize_img(u1.getvalue())
        u2 = c2.file_uploader("Zdj 2 (Lewy dół)", key="va_img_2")
        if u2: st.session_state['img_va_2'] = optimize_img(u2.getvalue())
        u3 = c3.file_uploader("Zdj 3 (Prawy dół)", key="va_img_3")
        if u3: st.session_state['img_va_3'] = optimize_img(u3.getvalue())

    elif page == "Pillow Gifts":
        gif_keys = ['pg_hide', 'pg_overline', 'pg_title', 'pg_subtitle', 'pg_text', 'img_pg_1', 'img_pg_2', 'img_pg_3']
        section_template_manager(gif_keys, "GIF", "Gifts", "gif")

        st.checkbox("Ukryj slajd", key="pg_hide")
        st.text_input("Mały nadtytuł:", key="pg_overline")
        st.text_area("Główny tytuł H1:", key="pg_title")
        st.text_input("Podtytuł:", key="pg_subtitle")
        st.text_area("Treść oferty (obsługuje HTML):", height=300, key="pg_text")
        
        c1, c2, c3 = st.columns(3)
        u1 = c1.file_uploader("Zdjęcie 1", key="pg_img_1")
        if u1: st.session_state['img_pg_1'] = optimize_img(u1.getvalue())
        u2 = c2.file_uploader("Zdjęcie 2 (Pionowe)", key="pg_img_2")
        if u2: st.session_state['img_pg_2'] = optimize_img(u2.getvalue())
        u3 = c3.file_uploader("Zdjęcie 3", key="pg_img_3")
        if u3: st.session_state['img_pg_3'] = optimize_img(u3.getvalue())

    elif page == "Kosztorys":
        koszt_keys = ['koszt_hide_1', 'koszt_hide_2', 'koszt_title', 'koszt_pax', 'koszt_price', 'koszt_hotel', 'koszt_dbl', 'koszt_sgl', 'koszt_zawiera_1', 'koszt_zawiera_2', 'koszt_nie_zawiera', 'koszt_opcje', 'img_koszt_1', 'img_koszt_2']
        section_template_manager(koszt_keys, "KOS", "Kosztorys", "koszt")
        
        c1, c2 = st.columns(2)
        c1.checkbox("Ukryj CAŁY Kosztorys (Slajd 1 i 2)", key="koszt_hide_1")
        c2.checkbox("Ukryj TYLKO Slajd 2 (Ciąg dalszy)", key="koszt_hide_2")
        
        st.text_input("Tytuł slajdu:", key="koszt_title")
        
        st.markdown("<div style='font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-top: 15px; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; letter-spacing: 1px;'>GŁÓWNE DANE TABELI</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.text_input("Wielkość grupy (np. 25):", key="koszt_pax")
        c2.text_input("Cena (np. 4.990 zł / os.):", key="koszt_price")
        st.text_input("Wybrany Hotel / Standard:", key="koszt_hotel")
        
        c1, c2 = st.columns(2)
        c1.text_input("Ilość pokoi DBL (2-os.):", key="koszt_dbl")
        c2.text_input("Ilość pokoi SGL (1-os.):", key="koszt_sgl")

        st.markdown("<div style='font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-top: 15px; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; letter-spacing: 1px;'>AUTO-UZUPEŁNIANIE</div>", unsafe_allow_html=True)
        if st.button("GENERUJ LISTĘ KOSZTÓW Z OFERTY", type="primary", use_container_width=True):
            auto_generate_kosztorys()
            st.success("Lista kosztów wygenerowana pomyślnie.")
            st.rerun()

        st.markdown("<div style='font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-top: 15px; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; letter-spacing: 1px;'>TREŚĆ KOSZTORYSU</div>", unsafe_allow_html=True)
        st.text_area("Cena zawiera (Część 1 - Slajd 1):", height=200, key="koszt_zawiera_1")
        st.text_area("Cena zawiera (Część 2 - Slajd 2):", height=150, key="koszt_zawiera_2")
        st.text_area("Nie policzone w cenie:", height=100, key="koszt_nie_zawiera")
        st.text_area("Koszty opcjonalne (zostaw puste, by ukryć):", height=100, key="koszt_opcje")

        st.markdown("<div style='font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-top: 15px; margin-bottom: 10px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; letter-spacing: 1px;'>ZDJĘCIA</div>", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        u1 = c1.file_uploader("Zdjęcie (Slajd 1)", key="koszt_img_1")
        if u1: st.session_state['img_koszt_1'] = optimize_img(u1.getvalue())
        u2 = c2.file_uploader("Zdjęcie (Slajd 2)", key="koszt_img_2")
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
        
        u_main = st.file_uploader("Zdjęcie główne slajdu (z prawej strony)", key="opi_main")
        if u_main: st.session_state['img_testim_main'] = optimize_img(u_main.getvalue())
        
        st.session_state['testim_count'] = st.number_input("Liczba opinii:", 1, 4, value=int(st.session_state.get('testim_count', 3)), step=1)
        for i in range(int(st.session_state.get('testim_count', 3))):
            with st.expander(f"Opinia {i+1}"):
                if f"testim_head_{i}" not in st.session_state: st.session_state[f"testim_head_{i}"] = ""
                if f"testim_quote_{i}" not in st.session_state: st.session_state[f"testim_quote_{i}"] = ""
                if f"testim_author_{i}" not in st.session_state: st.session_state[f"testim_author_{i}"] = ""
                if f"testim_role_{i}" not in st.session_state: st.session_state[f"testim_role_{i}"] = ""
                
                u_testim = st.file_uploader("Zdjęcie / Logo", key=f"opi_img_{i}")
                if u_testim: st.session_state[f"testim_img_{i}"] = optimize_img(u_testim.getvalue())
                
                st.text_input("Nagłówek", key=f"testim_head_{i}")
                st.text_area("Treść rekomendacji", key=f"testim_quote_{i}")
                c1, c2 = st.columns(2)
                c1.text_input("Autor (Pogrubiony)", key=f"testim_author_{i}")
                c2.text_input("Stanowisko", key=f"testim_role_{i}")

    elif page == "O Nas (Zespół)":
        nas_keys = ['about_hide', 'about_overline', 'about_title', 'about_sub', 'about_desc', 'about_panel_title', 'about_panel_text', 'team_count', 'img_about_clients']
        for i in range(st.session_state.get('team_count', 2)):
            nas_keys.extend([f't_name_{i}', f't_role_{i}', f't_desc_{i}', f't_img_{i}'])
        section_template_manager(nas_keys, "NAS", "Zespol", "nas")

        st.checkbox("Ukryj ten slajd w PDF", key="about_hide")
        st.text_input("Mały nadtytuł:", key="about_overline")
        st.text_area("Główny tytuł H1:", key="about_title")
        st.text_input("Podtytuł:", key="about_sub")
        st.text_area("Opis główny:", height=150, key="about_desc")
        
        u_clients = st.file_uploader("Zdjęcie prawe (Klienci / Logotypy)", key="nas_clients")
        if u_clients: st.session_state['img_about_clients'] = optimize_img(u_clients.getvalue())
        
        st.session_state['team_count'] = st.number_input("Liczba osób w zespole:", 1, 4, value=int(st.session_state.get('team_count', 2)), step=1)
        for i in range(int(st.session_state.get('team_count', 2))):
            with st.expander(f"Osoba {i+1}"):
                if f"t_name_{i}" not in st.session_state: st.session_state[f"t_name_{i}"] = ""
                if f"t_role_{i}" not in st.session_state: st.session_state[f"t_role_{i}"] = ""
                if f"t_desc_{i}" not in st.session_state: st.session_state[f"t_desc_{i}"] = ""
                
                st.text_input("Imię i nazwisko", key=f"t_name_{i}")
                st.text_input("Stanowisko", key=f"t_role_{i}")
                st.text_area("Krótki opis", key=f"t_desc_{i}")
                u_team = st.file_uploader("Zdjęcie (okrągłe)", key=f"nas_img_{i}")
                if u_team: st.session_state[f"t_img_{i}"] = optimize_img(u_team.getvalue())

    elif page == "Wygląd i Kolory":
        c1, c2, c3 = st.columns([2, 1, 1])
        c1.selectbox("Czcionka H1", FONTS_LIST, key="font_h1")
        c2.color_picker("Kolor H1", key="color_h1")
        c3.number_input("Rozmiar (px)", key="font_size_h1")

        c1, c2, c3 = st.columns([2, 1, 1])
        c1.selectbox("Czcionka H2", FONTS_LIST, key="font_h2")
        c2.color_picker("Kolor H2", key="color_h2")
        c3.number_input("Rozmiar (px)", key="font_size_h2")

        c1, c2, c3 = st.columns([2, 1, 1])
        c1.selectbox("Czcionka Podt.", FONTS_LIST, key="font_sub")
        c2.color_picker("Kolor Podt.", key="color_sub")
        c3.number_input("Rozmiar (px)", key="font_size_sub")

        c1, c2, c3 = st.columns([2, 1, 1])
        c1.selectbox("Czcionka Tekstu", FONTS_LIST, key="font_text")
        c2.color_picker("Kolor Tekstu", key="color_text")
        c3.number_input("Rozmiar (px)", key="font_size_text")

        c1, c2, c3 = st.columns([2, 1, 1])
        c1.selectbox("Czcionka Wyr.", FONTS_LIST, key="font_metric")
        c2.color_picker("Kolor Wyr.", key="color_metric")
        c3.number_input("Rozmiar (px)", key="font_size_metric")

        st.color_picker("Akcent", key="color_accent")

    elif page == "Zapisz / Wczytaj Projekt":
        proj = {}
        for k, v in st.session_state.items():
            if k in ['client_mode', 'scroll_target', 'last_page', 'ready_export_html', 'show_link_info']: continue
            if k.startswith(('btn_', 'up_', 'uh', 'plc_img', 'atr_hero', 'atr_th', 'bra_img', 'va_img', 'pg_img', 'koszt_img', 'opi_main', 'opi_img', 'nas_clients', 'nas_img', 'kie_hero', 'kie_th', 'tyt_hero', 'tyt_logo', 'lot_hero', 'app_bg', 'app_sc', '_')): continue
            if "UploadedFile" in str(type(v)): continue
            
            if isinstance(v, bytes):
                proj[k] = base64.b64encode(v).decode('utf-8')
            elif isinstance(v, (date, datetime)):
                proj[k] = v.isoformat()
            elif isinstance(v, (str, int, float, bool, list, dict)):
                proj[k] = v

        st.download_button("POBIERZ PLIK PROJEKTU (JSON)", json.dumps(proj), get_project_filename(), use_container_width=True)
        
        st.markdown("---")
        st.markdown("**Wczytaj istniejący projekt z dysku (.json)**")
        upf = st.file_uploader("Wgraj projekt z dysku (.json)", type=['json'], key="up_export", label_visibility="collapsed")
        if upf and st.button("WCZYTAJ PROJEKT", use_container_width=True, type="primary"):
            data = json.load(upf)
            load_project_data(data)
            st.rerun()

    # --- SZYBKIE AKCJE (ZAWSZE WIDOCZNE NA DOLE PANELU) ---
    st.divider()
    st.markdown("<div style='font-size: 10px; font-weight: 700; color: #94a3b8; text-transform: uppercase; margin-bottom: 10px; letter-spacing: 1px;'>SZYBKIE AKCJE (CAŁA OFERTA)</div>", unsafe_allow_html=True)
    
    if st.button("PRZYGOTUJ OFERTĘ DO POBRANIA", type="secondary", use_container_width=True):
        with st.spinner("Generowanie ostatecznego pliku oferty..."):
            export_content = build_presentation(export_mode=True)
            client_html = f"""<!DOCTYPE html><html lang="pl"><head><meta charset="UTF-8"><title>{st.session_state.get('t_main')}</title><style>body{{background:#f4f5f7;margin:0;}} .presentation-wrapper{{height:100vh;overflow-y:auto;scroll-snap-type:y proximity;}} .client-export-btn{{position:fixed;top:20px;left:20px;z-index:9999;background:{st.session_state.get('color_accent')};color:white;border:none;padding:15px 25px;border-radius:4px;font-family:sans-serif;font-size:12px;font-weight:700;text-transform:uppercase;cursor:pointer;box-shadow:0 4px 15px rgba(0,0,0,0.3);}} @media print{{.client-export-btn{{display:none !important;}} .presentation-wrapper{{height:auto !important;overflow:visible !important;}}}}</style>{get_local_css(True)}</head><body><button class="client-export-btn" onclick="window.print()">POBIERZ JAKO PDF</button><div class="presentation-wrapper">{export_content}</div></body></html>"""
            st.session_state['ready_export_html'] = client_html
            st.rerun()
            
    if st.session_state.get('ready_export_html'):
        st.download_button(
            "POBIERZ GOTOWY PLIK HTML", 
            st.session_state['ready_export_html'], 
            get_project_filename().replace('.json', '.html'), 
            "text/html", 
            type="primary", 
            use_container_width=True
        )
    
    if st.button("GENERUJ LINK DO OFERTY ONLINE", use_container_width=True):
        st.session_state['show_link_info'] = not st.session_state.get('show_link_info', False)
        
    if st.session_state.get('show_link_info', False):
        st.info("Wyeksportuj plik HTML za pomocą przycisku wyżej i umieść go na serwerze swojej agencji. Plik jest w pełni autonomiczną stroną WWW – gotowym, bezpiecznym linkiem dla klienta.")
    
    if st.button("PODGLĄD PEŁNOEKRANOWY", use_container_width=True): 
        st.session_state['client_mode'] = True
        st.rerun()
