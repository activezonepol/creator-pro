import streamlit as st
from datetime import date, timedelta
import json
import base64
import re

# ====================== IMPORTY Z RENDERERA ======================
from renderer import (
    build_presentation,
    get_local_css,
    get_project_filename,
    optimize_img,
    optimize_logo,
    geocode_place,
    generate_map_data,
    section_template_manager,
    parse_date_and_days,
    set_focus,
    clean_str,
    build_day_options,
    auto_generate_kosztorys,
    load_project_data,
)

# ====================== INICJALIZACJA ======================
if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.last_page = "Strona Tytułowa"
    st.session_state.client_mode = False
    st.session_state.scroll_target = ""

# ====================== GŁÓWNA APLIKACJA ======================
def main():
    # Renderowanie prezentacji
    html_content = build_presentation(
        current_page=st.session_state.get('last_page', 'Strona Tytułowa')
    )

    css_str = get_local_css(return_str=True)

    st.markdown(
        css_str + f'\n<div class="presentation-wrapper" id="main-wrapper">{html_content}</div>',
        unsafe_allow_html=True
    )

    # Scroll do aktywnej sekcji
    tid = st.session_state.get('scroll_target')
    if tid and not st.session_state.get('client_mode', False):
        st.components.v1.html(
            f"<script>var t = window.parent.document.getElementById('{tid}'); if(t) t.scrollIntoView({{behavior: 'smooth', block: 'center'}});</script>",
            height=0
        )

    # Tryb klienta (pełny ekran bez sidebaru)
    if st.session_state.get('client_mode', False):
        accent = st.session_state.get('color_accent', '#FF6600')
        st.markdown(f"""
        <style>
        div.stButton {{ position: fixed !important; top: 20px !important; left: 20px !important; z-index: 999999 !important; }}
        div.stButton > button {{ background-color: {accent} !important; color: white !important; }}
        </style>
        """, unsafe_allow_html=True)

        if st.button("ZAKOŃCZ PODGLĄD"):
            st.session_state.client_mode = False
            st.rerun()
        st.stop()

    # ====================== PANEL BOCZNY ======================
    with st.sidebar:
        page = st.radio("WYBIERZ SEKCJE DO EDYCJI:", 
                        ["Strona Tytułowa", "Opis Kierunku", "Mapa Podróży", "Jak lecimy?", 
                         "Zakwaterowanie", "Program Wyjazdu", "Opis miejsc", "Opis atrakcji", 
                         "Aplikacja (Komunikacja)", "Materiały Brandingowe", "Wirtualny Asystent", 
                         "Pillow Gifts", "Kosztorys", "Co o nas mówią", "O Nas (Zespół)", 
                         "Wygląd i Kolory", "Zapisz / Wczytaj Projekt"])

        if st.session_state.get('last_page') != page:
            st.session_state.last_page = page
            st.session_state.scroll_target = ""

        st.divider()

        # === TWÓJ PEŁNY KOD SIDEBARU ===
 if page == "Wygląd i Kolory":
        st.markdown(f"<h2 style='color: #003366; margin-bottom: 0; font-size: 22px; font-weight: 700; font-family: Montserrat, sans-serif;'>KONFIGURACJA WYGLĄDU</h2>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 13px; color: #64748b; margin-bottom: 15px; font-family: Open Sans, sans-serif;'>Dostosuj kolory i typografię oferty</div>", unsafe_allow_html=True)
    elif page == "Zapisz / Wczytaj Projekt":
        st.markdown(f"<h2 style='color: #003366; margin-bottom: 0; font-size: 22px; font-weight: 700; font-family: Montserrat, sans-serif;'>ZARZĄDZANIE PROJEKTEM</h2>", unsafe_allow_html=True)
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
        for i in range(st.session_state.get('num_map_points', 3)): 
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
        for i in range(st.session_state['num_map_points']):
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
                else:
                    st.warning("Nie udało się zgeokodować żadnego punktu. Sprawdź połączenie z internetem lub poprawność nazw.")

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
        st.number_input("Liczba hoteli do wyboru:", 1, 3, step=1, key="num_hotels")
        for i in range(st.session_state['num_hotels']):
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
        st.number_input("Ilość dni:", 1, 15, step=1, key="num_days")
        st.date_input("Data startu:", key="p_start_dt")
        for d in range(st.session_state['num_days']):
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
        st.number_input("Liczba miejsc:", 0, 20, step=1, key="num_places")
        for i in range(st.session_state['num_places']):
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
                
                # POPRAWKA #5: bezpieczna walidacja wartości przed renderem widgetu
                widget_key = f"pday_{i}"
                curr_val = st.session_state.get(widget_key, day_options_global[0])
                if curr_val not in day_options_global:
                    st.session_state[widget_key] = day_options_global[0]
                
                st.selectbox("Przypisz do dnia:", day_options_global, key=widget_key, on_change=set_focus, args=(f"place_{i}",))
                
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
        # POPRAWKA #6: bez dubla klucza
        st.number_input("Ilość atrakcji:", 1, 20, step=1, key="num_attr")
        for i in range(st.session_state['num_attr']):
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
                
                # POPRAWKA #5: bezpieczna walidacja wartości przed renderem widgetu
                widget_key = f"aday_{i}"
                curr_val = st.session_state.get(widget_key, day_options_global[0])
                if curr_val not in day_options_global:
                    st.session_state[widget_key] = day_options_global[0]
                
                st.selectbox("Przypisz do dnia:", day_options_global, key=widget_key, on_change=set_focus, args=(f"attr_{i}",))
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
        
        st.number_input("Liczba opinii:", 1, 4, step=1, key="testim_count")
        for i in range(st.session_state['testim_count']):
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
        
        st.number_input("Liczba osób w zespole:", 1, 4, step=1, key="team_count")
        for i in range(st.session_state['team_count']):
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
        # POPRAWKA #8: jawna lista wyłączeń zamiast fragile startswith("u")
        proj = {}
        for k, v in st.session_state.items():
            if k in EXCLUDE_EXPORT_KEYS:
                continue
            # Pomijamy klucze technicznych widgetów (uploaderów itp.) oraz pól formularzy
            if k.startswith('FormSubmitter') or k.startswith('$$'):
                continue
            if k.startswith('up_') or k.startswith('fn_') or k.startswith('dl_') or k.startswith('btn_'):
                continue
            if k in ('tyt_hero', 'tyt_logo_az', 'tyt_logo_cli', 'kie_hero', 'kie_th1', 'kie_th2', 'kie_th3', 'lot_hero', 'app_bg', 'app_sc', 'bra_img_1', 'bra_img_2', 'bra_img_3', 'va_img_1', 'va_img_2', 'va_img_3', 'pg_img_1', 'pg_img_2', 'pg_img_3', 'koszt_img_1', 'koszt_img_2', 'opi_main', 'nas_clients'):
                continue
            # Pomijamy uploadery dynamiczne (np. uh1_0, uh1b_0, uh2_0, atr_hero_0, ...)
            if re.match(r'^(uh1|uh1b|uh2|uh3|prg_img|plc_img1|plc_img2|atr_hero|atr_th1|atr_th2|atr_th3|opi_img|nas_img)_\d+$', k):
                continue
            try:
                if isinstance(v, bytes):
                    proj[k] = base64.b64encode(v).decode()
                elif isinstance(v, (date, datetime)):
                    proj[k] = v.isoformat()
                elif isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                    proj[k] = v
                # inne typy (np. UploadedFile) pomijamy
            except Exception:
                pass
        
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
            client_html = f"""<!DOCTYPE html><html lang="pl"><head><meta charset="UTF-8"><title>{st.session_state.get('t_main')}</title><link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='50' fill='%23FF6600'/></svg>">{get_local_css(True)}
            <style>body{{background:#f4f5f7;margin:0;}} .presentation-wrapper{{height:100vh;overflow-y:auto;scroll-snap-type:y proximity;}}
            .client-export-btn{{position:fixed;top:20px;left:20px;z-index:9999;background:{st.session_state.get('color_accent')};color:white;border:none;padding:15px 25px;border-radius:4px;font-family:sans-serif;font-size:12px;font-weight:700;text-transform:uppercase;cursor:pointer;box-shadow:0 4px 15px rgba(0,0,0,0.3);}}
            @media print{{.client-export-btn{{display:none !important;}} .presentation-wrapper{{height:auto !important;overflow:visible !important;}}}}</style>
            </head><body><button class="client-export-btn" onclick="window.print()">POBIERZ JAKO PDF</button>
            <div class="presentation-wrapper">{export_content}</div></body></html>"""
            st.session_state['ready_export_html'] = client_html
            st.rerun()
            
  # ====================== URUCHOMIENIE ======================
if __name__ == "__main__":
    main()
