"""
db_utils.py
===========
Funkcje do komunikacji z Supabase.

GŁÓWNE FUNKCJE:
- save_to_supabase: bezpieczny zapis projektu z walidacją kraju (Model C)
- fetch_all_offers: pobieranie listy ofert (Model C)
- fetch_offer_by_id: pobieranie konkretnej oferty
- delete_offer: usuwanie oferty
- clone_offer: klonowanie oferty
"""
import streamlit as st
from supabase import Client
from datetime import datetime, timedelta
import time

from data_utils import _build_proj_dict
from code_generator import (
    generate_project_code,
    is_country_selected,
    get_country_warning_message,
)


# ---------------------------------------------------------------------------
# 1. GŁÓWNY ZAPIS SYSTEMOWY (auto-save w app.py)
# ---------------------------------------------------------------------------
def save_to_supabase():
    """Systemowy zapis projektu z walidacją kraju.
    
    PROCES:
    1. Sprawdza czy kraj jest wybrany (KRYTYCZNE - Model C)
    2. Generuje kod oferty (np. 26-04-POL-KLIENT-NAZWA)
    3. Buduje słownik projektu (lekkie dane, bez bytes)
    4. Upsert do bazy (insert lub update istniejącego)
    5. Aktualizuje status w session_state
    
    BEZ KRAJU: NIE ZAPISUJE, ustawia komunikat ostrzegawczy.
    """
    supabase_client = st.session_state.get('supabase')
    if not supabase_client:
        st.session_state['last_save_status'] = "❌ Brak klienta bazy"
        print("Błąd: Brak klienta supabase w st.session_state!")
        return
    
    # ============================================================
    # KROK 1: WALIDACJA KRAJU (NOWE - Model C)
    # ============================================================
    if not is_country_selected():
        st.session_state['last_save_status'] = "⚠️ Wybierz kraj (nie zapisano)"
        st.session_state['last_save_count'] = 0
        st.session_state['last_supabase_save'] = time.time()
        return
    
    # ============================================================
    # KROK 2: GENEROWANIE KODU OFERTY
    # ============================================================
    code_data = generate_project_code()
    if not code_data:
        # Defensywne zabezpieczenie (is_country_selected już to sprawdziło)
        st.session_state['last_save_status'] = "❌ Nie udało się wygenerować kodu"
        return
    
    project_code = code_data['code']
    country_iso = code_data['country_iso']
    country_name = code_data['country_name']
    year = code_data['year']
    month = code_data['month']
    client_short = code_data['client_short']
    
    # ============================================================
    # KROK 3: BUDOWANIE DANYCH PROJEKTU
    # ============================================================
    try:
        project_data = _build_proj_dict()
        project_name = st.session_state.get('t_main', 'Nowy projekt')
        
        # Storage folder = project_code (raz ustalony, nie zmieniany przy update)
        storage_folder = st.session_state.get('storage_folder', project_code)
        
        # ============================================================
        # KROK 4: UPSERT DO BAZY
        # ============================================================
        # Szukamy istniejącego projektu (z storage_folder żeby zachować przy update)
        existing = supabase_client.table('projects').select('id, storage_folder').eq(
            'user_email', 'default_user'
        ).order('updated_at', desc=True).limit(1).execute()
        
        if existing.data:
            # UPDATE istniejący projekt
            project_id = existing.data[0]['id']
            
            # Zachowujemy oryginalny storage_folder z bazy (raz ustalony)
            existing_folder = existing.data[0].get('storage_folder')
            if existing_folder:
                storage_folder = existing_folder
                st.session_state['storage_folder'] = existing_folder
            
            update_data = {
                'project_name': project_name,
                'project_code': project_code,
                'country': country_iso,
                'country_name': country_name,
                'year': year,
                'month': month,
                'client_short': client_short,
                'storage_folder': storage_folder,
                'data': project_data,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            supabase_client.table('projects').update(update_data).eq('id', project_id).execute()
        else:
            # INSERT nowy projekt
            insert_data = {
                'user_email': 'default_user',
                'project_name': project_name,
                'project_code': project_code,
                'country': country_iso,
                'country_name': country_name,
                'year': year,
                'month': month,
                'client_short': client_short,
                'storage_folder': storage_folder,
                'data': project_data,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            supabase_client.table('projects').insert(insert_data).execute()
            st.session_state['storage_folder'] = storage_folder
        
        # ============================================================
        # KROK 5: AKTUALIZACJA STATUSU
        # ============================================================
        # KOREKTA CZASU: UTC → polski (UTC+2)
        now_pl = datetime.utcnow() + timedelta(hours=2)
        save_time = now_pl.strftime('%H:%M:%S')
        
        st.session_state['last_save_status'] = f"✅ Zapisano {save_time}"
        st.session_state['last_save_count'] = len(project_data)
        st.session_state['last_supabase_save'] = time.time()
        st.session_state['current_project_code'] = project_code
        
    except Exception as e:
        st.session_state['last_save_status'] = f"❌ Błąd: {str(e)[:50]}"
        print(f"Błąd Supabase: {e}")


# ---------------------------------------------------------------------------
# 2. FUNKCJE DLA TABELI OFERT (Model C - lista ofert)
# ---------------------------------------------------------------------------
# UWAGA: Wszystkie funkcje używają tabeli 'projects' (nie 'offers')
def fetch_all_offers(supabase_client: Client, user_email: str = 'default_user'):
    """Pobiera wszystkie oferty użytkownika z tabeli 'projects'.
    
    Sortowanie: kraj A-Z, potem rok malejąco, potem miesiąc malejąco.
    
    Returns:
        list of dict - każdy słownik to jedna oferta z polami:
            id, project_name, project_code, country, country_name,
            year, month, client_short, storage_folder, updated_at
    """
    try:
        response = supabase_client.table('projects').select(
            'id, project_name, project_code, country, country_name, '
            'year, month, client_short, storage_folder, updated_at'
        ).eq('user_email', user_email).order('country', desc=False).order(
            'year', desc=True
        ).order('month', desc=True).execute()
        
        return response.data or []
    except Exception as e:
        st.error(f"Błąd pobierania ofert: {e}")
        return []


def fetch_offer_by_id(supabase_client: Client, offer_id):
    """Pobiera pełne dane konkretnej oferty po ID."""
    try:
        response = supabase_client.table('projects').select('*').eq(
            'id', offer_id
        ).single().execute()
        return response.data
    except Exception as e:
        st.error(f"Błąd pobierania oferty: {e}")
        return None


def delete_offer(supabase_client: Client, offer_id):
    """Usuwa ofertę po ID z tabeli 'projects'."""
    try:
        supabase_client.table('projects').delete().eq("id", offer_id).execute()
        return True
    except Exception as e:
        st.error(f"Błąd usuwania oferty: {e}")
        return False


def clone_offer(supabase_client: Client, source_offer_id, user_email: str = 'default_user'):
    """Klonuje istniejącą ofertę (tworzy kopię z nowym ID).
    
    Returns:
        str - ID nowej oferty, lub None jeśli błąd
    """
    try:
        # 1. Pobierz źródłową ofertę
        source = fetch_offer_by_id(supabase_client, source_offer_id)
        if not source:
            return None
        
        # 2. Przygotuj dane kopii (bez ID, z nowym project_name)
        new_data = {
            'user_email': user_email,
            'project_name': f"Kopia: {source.get('project_name', 'Oferta')}",
            'project_code': source.get('project_code', '') + '-V2',
            'country': source.get('country'),
            'country_name': source.get('country_name'),
            'year': source.get('year'),
            'month': source.get('month'),
            'client_short': source.get('client_short'),
            'storage_folder': source.get('storage_folder'),
            'data': source.get('data', {}),
            'updated_at': datetime.utcnow().isoformat(),
        }
        
        # 3. Insert kopii
        result = supabase_client.table('projects').insert(new_data).execute()
        if result.data:
            return result.data[0].get('id')
        return None
    except Exception as e:
        st.error(f"Błąd klonowania oferty: {e}")
        return None
