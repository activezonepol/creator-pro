"""
db_utils.py
===========
Funkcje do komunikacji z Supabase.

LOGIKA MODELU C (3 stany kraju):
- empty (-- Wybierz kraj --) -> zapisuje z OTH, status pomaranczowy
- other (Inny)               -> zapisuje z OTH, status niebieski
- concrete (Polska, ...)     -> zapisuje z konkretnym ISO, status zielony
"""
import streamlit as st
from supabase import Client
from datetime import datetime, timedelta
import time

from data_utils import _build_proj_dict
from code_generator import (
    generate_project_code,
    get_country_status,
)


# ---------------------------------------------------------------------------
# 1. GLOWNY ZAPIS SYSTEMOWY (auto-save w app.py)
# ---------------------------------------------------------------------------
def save_to_supabase():
    """Systemowy zapis projektu - zawsze zapisuje, status zalezny od stanu kraju.
    
    PROCES:
    1. Generuje kod oferty (zawsze, OTH dla pustego/Inny)
    2. Buduje slownik projektu
    3. Upsert do bazy
    4. Status zalezny od stanu kraju (3 mozliwe stany)
    """
    supabase_client = st.session_state.get('supabase')
    if not supabase_client:
        st.session_state['last_save_status'] = "Blad bazy"
        st.session_state['last_save_status_type'] = "error"
        return
    
    # ============================================================
    # KROK 1: GENEROWANIE KODU OFERTY (zawsze, OTH dla pustego/Inny)
    # ============================================================
    code_data = generate_project_code()
    if not code_data:
        st.session_state['last_save_status'] = "Blad generowania kodu"
        st.session_state['last_save_status_type'] = "error"
        return
    
    project_code = code_data['code']
    country_iso = code_data['country_iso']
    country_name = code_data['country_name']
    year = code_data['year']
    month = code_data['month']
    client_short = code_data['client_short']
    country_status = code_data['status']
    
    # ============================================================
    # KROK 2: BUDOWANIE DANYCH PROJEKTU
    # ============================================================
    try:
        project_data = _build_proj_dict()
        project_name = st.session_state.get('t_main', 'Nowy projekt')
        
        storage_folder = st.session_state.get('storage_folder', project_code)
        
        # ============================================================
        # KROK 3: UPSERT DO BAZY
        # ============================================================
        existing = supabase_client.table('projects').select('id, storage_folder').eq(
            'user_email', 'default_user'
        ).order('updated_at', desc=True).limit(1).execute()
        
        if existing.data:
            project_id = existing.data[0]['id']
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
        # KROK 4: STATUS ZALEZNY OD STANU KRAJU
        # ============================================================
        now_pl = datetime.utcnow() + timedelta(hours=2)
        save_time = now_pl.strftime('%H:%M:%S')
        
        # Status type definiuje kolor pola w sidebarze (app.py)
        if country_status == 'concrete':
            st.session_state['last_save_status_type'] = 'success'  # zielone
            st.session_state['last_save_extra'] = ''
        elif country_status == 'other':
            st.session_state['last_save_status_type'] = 'info'  # niebieskie
            st.session_state['last_save_extra'] = 'Kraj: Inny (kod OTH)'
        else:  # empty
            st.session_state['last_save_status_type'] = 'warning'  # pomaranczowe
            st.session_state['last_save_extra'] = 'Kraj do uzupelnienia'
        
        st.session_state['last_save_status'] = "Zapisano " + save_time
        st.session_state['last_save_count'] = len(project_data)
        st.session_state['last_supabase_save'] = time.time()
        st.session_state['current_project_code'] = project_code
        
    except Exception as e:
        st.session_state['last_save_status'] = "Blad: " + str(e)[:50]
        st.session_state['last_save_status_type'] = 'error'
        print("Blad Supabase: " + str(e))


# ---------------------------------------------------------------------------
# 2. FUNKCJE DLA TABELI OFERT (Model C - lista ofert)
# ---------------------------------------------------------------------------
def fetch_all_offers(supabase_client, user_email='default_user'):
    """Pobiera wszystkie oferty uzytkownika z tabeli projects.
    
    Sortowanie: kraj A-Z, potem rok malejaco, potem miesiac malejaco.
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
        st.error("Blad pobierania ofert: " + str(e))
        return []


def fetch_offer_by_id(supabase_client, offer_id):
    """Pobiera pelne dane konkretnej oferty po ID."""
    try:
        response = supabase_client.table('projects').select('*').eq(
            'id', offer_id
        ).single().execute()
        return response.data
    except Exception as e:
        st.error("Blad pobierania oferty: " + str(e))
        return None


def delete_offer(supabase_client, offer_id):
    """Usuwa oferte po ID z tabeli projects."""
    try:
        supabase_client.table('projects').delete().eq("id", offer_id).execute()
        return True
    except Exception as e:
        st.error("Blad usuwania oferty: " + str(e))
        return False


def clone_offer(supabase_client, source_offer_id, user_email='default_user'):
    """Klonuje istniejaca oferte (tworzy kopie z nowym ID)."""
    try:
        source = fetch_offer_by_id(supabase_client, source_offer_id)
        if not source:
            return None
        
        new_data = {
            'user_email': user_email,
            'project_name': "Kopia: " + str(source.get('project_name', 'Oferta')),
            'project_code': str(source.get('project_code', '')) + '-V2',
            'country': source.get('country'),
            'country_name': source.get('country_name'),
            'year': source.get('year'),
            'month': source.get('month'),
            'client_short': source.get('client_short'),
            'storage_folder': source.get('storage_folder'),
            'data': source.get('data', {}),
            'updated_at': datetime.utcnow().isoformat(),
        }
        
        result = supabase_client.table('projects').insert(new_data).execute()
        if result.data:
            return result.data[0].get('id')
        return None
    except Exception as e:
        st.error("Blad klonowania oferty: " + str(e))
        return None
