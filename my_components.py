"""
my_components.py
================
Custom widgety Streamlita z buforowaniem (zapobiegają reload przy każdym znaku).

ROZWIAZANIE BUG'a: Po wielokrotnym przelaczeniu slajdow widget tracil wartosc.
Naprawa: Wymuszamy `value=` w text_input zamiast polegac tylko na `key=`.

Python 3.14 / Streamlit nowsza wersja: Przekazujemy args/kwargs do user_on_change
zeby callbacki typu set_focus(target_id) mogly otrzymac argumenty.
"""
import streamlit as st


def safe_text_input(label, key, **kwargs):
    """
    Text input z buforem - nie przeladowuje na kazdy znak.
    Synchronizuje buffer z glownym kluczem przy kazdym wywolaniu.
    
    Wspiera on_change z args= i kwargs= (jak natywny st.text_input).
    """
    buffer_key = f"buffer_{key}"
    main_value = st.session_state.get(key, "")
    
    # Synchronizuj buffer z glownym kluczem
    if buffer_key not in st.session_state:
        st.session_state[buffer_key] = main_value
    elif st.session_state.get(buffer_key) != main_value and key in st.session_state:
        st.session_state[buffer_key] = main_value
    
    # Przejmujemy on_change uzytkownika oraz jego args/kwargs
    user_on_change = kwargs.pop("on_change", None)
    user_args = kwargs.pop("args", ())
    user_kwargs = kwargs.pop("kwargs", {})
    
    def _handle_change(*_args, **_kwargs):
        """Synchronizuje buffer -> main, potem odpala akcje uzytkownika z jej argumentami."""
        st.session_state[key] = st.session_state[buffer_key]
        if user_on_change:
            user_on_change(*user_args, **user_kwargs)
    
    return st.text_input(
        label,
        value=main_value,
        key=buffer_key,
        on_change=_handle_change,
        **kwargs,
    )


def safe_text_area(label, key, **kwargs):
    """
    Text area z buforem - nie przeladowuje na kazdy znak.
    Wspiera on_change z args= i kwargs=.
    """
    buffer_key = f"buffer_{key}"
    main_value = st.session_state.get(key, "")
    
    if buffer_key not in st.session_state:
        st.session_state[buffer_key] = main_value
    elif st.session_state.get(buffer_key) != main_value and key in st.session_state:
        st.session_state[buffer_key] = main_value
    
    user_on_change = kwargs.pop("on_change", None)
    user_args = kwargs.pop("args", ())
    user_kwargs = kwargs.pop("kwargs", {})
    
    def _handle_change(*_args, **_kwargs):
        st.session_state[key] = st.session_state[buffer_key]
        if user_on_change:
            user_on_change(*user_args, **user_kwargs)
    
    return st.text_area(
        label,
        value=main_value,
        key=buffer_key,
        on_change=_handle_change,
        **kwargs,
    )
