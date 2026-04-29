import streamlit as st
from supabase import Client
from datetime import datetime, timedelta
import time

# Ten import jest tu kluczowy i musi zostać użyty w głównej funkcji
from data_utils import _build_proj_dict

# ---------------------------------------------------------------------------
# 1. GŁÓWNY ZAPIS SYSTEMOWY (Do obsługi auto-save w app.py)
# ---------------------------------------------------------------------------
def save_to_supabase():
    """Systemowy, bezpieczny zapis projektu. Nie wymaga argumentów w app.py!"""
    # Pobieramy klienta bazy z sesji
    supabase_client = st.session_state.get('supabase')
    if not supabase_client:
        print("Błąd: Brak klienta supabase w st.session_state!")
        return

    try:
        # Używamy zaimportowanej funkcji do zbudowania danych
        project_data = _build_proj_dict()
        project_name = st.session_state.get('t_main', 'Nowy projekt')
        
        # Szukamy istniejącego projektu
        existing = supabase_client.table('projects').select('id').eq('user_email', 'default_user').order('updated_at', desc=True).limit(1).execute()
        
        if existing.data:
            project_id = existing.data[0]['id']
            supabase_client.table('projects').update({
                'project_name': project_name,
                'data': project_data,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('id', project_id).execute()
        else:
            supabase_client.table('projects').insert({
                'user_email': 'default_user',
                'project_name': project_name,
                'data': project_data,
                'updated_at': datetime.utcnow().isoformat()
            }).execute()
            
        # KOREKTA CZASU: Pobieramy czas UTC i dodajemy 2 godziny (czas polski)
        now_pl = datetime.utcnow() + timedelta(hours=2)
        save_time = now_pl.strftime('%H:%M:%S')
        
        st.session_state['last_save_status'] = f"✅ Zapisano {save_time}"
        st.session_state['last_save_count'] = len(project_data)
        st.session_state['last_supabase_save'] = time.time()
        
    except Exception as e:
        st.session_state['last_save_status'] = "❌ Błąd bazy"
        print(f"Błąd Supabase: {e}")


# ---------------------------------------------------------------------------
# 2. DODATKOWE FUNKCJE DLA TABELI OFERT (Zgodnie z Twoim życzeniem)
# ---------------------------------------------------------------------------
TABLE_OFFERS = "offers"

def fetch_all_offers(supabase_client: Client):
    """Pobiera wszystkie oferty z tabeli."""
    try:
        response = supabase_client.table(TABLE_OFFERS).select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"Błąd pobierania danych: {e}")
        return []

def delete_offer(supabase_client: Client, offer_id: int):
    """Usuwa ofertę na podstawie jej ID."""
    try:
        supabase_client.table(TABLE_OFFERS).delete().eq("id", offer_id).execute()
        return True
    except Exception as e:
        st.error(f"Błąd usuwania oferty: {e}")
        return False
