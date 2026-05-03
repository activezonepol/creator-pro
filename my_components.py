"""
my_components.py
================
Custom widgety Streamlita z buforowaniem (zapobiegają reload przy każdym znaku).

ROZWIAZANIE BUG'a: Po wielokrotnym przelaczeniu slajdow widget tracil wartosc.
Naprawa: Wymuszamy `value=` w text_input zamiast polegac tylko na `key=`.
"""
import streamlit as st


def safe_text_input(label, key, **kwargs):
    """
    Text input z buforem - nie przeladowuje na kazdy znak.
    Synchronizuje buffer z glownym kluczem przy kazdym wywolaniu.
    
    NAPRAWA: Wymuszamy `value=` zeby Streamlit nie tracil wartosci 
    po wielokrotnym odmontowaniu/zmontowaniu widgetu.
    """
    buffer_key = f"buffer_{key}"
    main_value = st.session_state.get(key, "")
    
    # Synchronizuj buffer z glownym kluczem
    if buffer_key not in st.session_state:
        st.session_state[buffer_key] = main_value
    elif st.session_state.get(buffer_key) != main_value and key in st.session_state:
        st.session_state[buffer_key] = main_value
    
    # Przechwytujemy on_change
    user_on_change = kwargs.pop("on_change", None)
    
    def _handle_change():
        # Aktualizujemy stan glowny z bufora
        st.session_state[key] = st.session_state[buffer_key]
        # Odpalamy akcje uzytkownika (jesli sa)
        if user_on_change:
            user_on_change()
    
    # KLUCZOWA NAPRAWA: Wymuszamy value= zeby zapewnic synchronizacje
    # nawet po wielokrotnym przelaczeniu slajdow
    return st.text_input(
        label,
        value=main_value,
        key=buffer_key,
        on_change=_handle_change,
        **kwargs
    )


def safe_text_area(label, key, **kwargs):
    """
    Text area z buforem - nie przeladowuje na kazdy znak.
    
    NAPRAWA: Wymuszamy `value=` zeby Streamlit nie tracil wartosci 
    po wielokrotnym odmontowaniu/zmontowaniu widgetu.
    """
    buffer_key = f"buffer_{key}"
    main_value = st.session_state.get(key, "")
    
    if buffer_key not in st.session_state:
        st.session_state[buffer_key] = main_value
    elif st.session_state.get(buffer_key) != main_value and key in st.session_state:
        st.session_state[buffer_key] = main_value
    
    user_on_change = kwargs.pop("on_change", None)
    
    def _handle_change():
        st.session_state[key] = st.session_state[buffer_key]
        if user_on_change:
            user_on_change()
    
    # KLUCZOWA NAPRAWA: Wymuszamy value= dla synchronizacji
    return st.text_area(
        label,
        value=main_value,
        key=buffer_key,
        on_change=_handle_change,
        **kwargs
    )
