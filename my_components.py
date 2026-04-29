import streamlit as st

def safe_text_input(label, key, **kwargs):
    """
    Text input z buforem — nie przeładowuje na każdy znak.
    Synchronizuje buffer z głównym kluczem przy każdym wywołaniu,
    żeby formularze zachowywały się spójnie po reloadach.
    """
    buffer_key = f"buffer_{key}"
    main_value = st.session_state.get(key, "")
    
    # Jeśli buffer nie istnieje — zainicjalizuj wartością z głównego klucza
    if buffer_key not in st.session_state:
        st.session_state[buffer_key] = main_value
    # Jeśli buffer i główny klucz się rozeszły — synchronizuj
    # Usunięto 'and main_value' na rzecz sprawdzenia, czy klucz główny istnieje
    elif st.session_state.get(buffer_key) != main_value and key in st.session_state:
        st.session_state[buffer_key] = main_value
    
    # Przechwytujemy dodatkowy on_change (np. ten z app.py z zapisem do bazy)
    user_on_change = kwargs.pop("on_change", None)
    
    def _handle_change():
        # Najpierw aktualizujemy stan główny z bufora
        st.session_state[key] = st.session_state[buffer_key]
        # Następnie odpalamy akcje zdefiniowane w app.py (jeśli są)
        if user_on_change:
            user_on_change()

    return st.text_input(
        label,
        key=buffer_key,
        on_change=_handle_change,
        **kwargs
    )


def safe_text_area(label, key, **kwargs):
    """
    Text area z buforem — nie przeładowuje na każdy znak.
    Synchronizuje buffer z głównym kluczem przy każdym wywołaniu,
    żeby formularze zachowywały się spójnie po reloadach.
    """
    buffer_key = f"buffer_{key}"
    main_value = st.session_state.get(key, "")
    
    if buffer_key not in st.session_state:
        st.session_state[buffer_key] = main_value
    elif st.session_state.get(buffer_key) != main_value and key in st.session_state:
        st.session_state[buffer_key] = main_value
        
    # Przechwytujemy dodatkowy on_change
    user_on_change = kwargs.pop("on_change", None)
    
    def _handle_change():
        st.session_state[key] = st.session_state[buffer_key]
        if user_on_change:
            user_on_change()
            
    return st.text_area(
        label,
        key=buffer_key,
        on_change=_handle_change,
        **kwargs
    )
