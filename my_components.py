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
    # (np. po reloadzie strony, gdy widget się resetuje)
    elif st.session_state.get(buffer_key) != main_value and main_value:
        st.session_state[buffer_key] = main_value
    
    return st.text_input(
        label,
        key=buffer_key,
        on_change=lambda: st.session_state.update({key: st.session_state[buffer_key]}),
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
    
    # Jeśli buffer nie istnieje — zainicjalizuj wartością z głównego klucza
    if buffer_key not in st.session_state:
        st.session_state[buffer_key] = main_value
    # Jeśli buffer i główny klucz się rozeszły — synchronizuj
    elif st.session_state.get(buffer_key) != main_value and main_value:
        st.session_state[buffer_key] = main_value
    
    return st.text_area(
        label,
        key=buffer_key,
        on_change=lambda: st.session_state.update({key: st.session_state[buffer_key]}),
        **kwargs
    )
