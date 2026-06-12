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


def safe_checkbox(label, key, default=False, **kwargs):
    """
    Checkbox z buforem - prawidlowo czyta session_state przy kazdym renderze.
    ROZWIAZANIE BUGa: Streamlit checkbox z `key=` przy pierwszym renderze
    po zniszczeniu widgetu nie respektuje session_state - wraca do False.
    """
    buffer_key = f"buffer_{key}"
    
    if key not in st.session_state:
        st.session_state[key] = bool(default)
    
    main_value = bool(st.session_state.get(key, default))
    
    if buffer_key not in st.session_state:
        st.session_state[buffer_key] = main_value
    elif st.session_state.get(buffer_key) != main_value:
        st.session_state[buffer_key] = main_value
    
    user_on_change = kwargs.pop("on_change", None)
    user_args = kwargs.pop("args", ())
    user_kwargs = kwargs.pop("kwargs", {})
    
    def _handle_change(*_args, **_kwargs):
        st.session_state[key] = st.session_state[buffer_key]
        if user_on_change:
            user_on_change(*user_args, **user_kwargs)
    
    return st.checkbox(
        label,
        value=main_value,
        key=buffer_key,
        on_change=_handle_change,
        **kwargs,
    )
def safe_selectbox(label, options, key, default_index=0, **kwargs):
    """
    Selectbox z buforem - prawidlowo czyta session_state przy kazdym renderze.
    ROZWIAZANIE BUGa: Streamlit selectbox z `key=` przy pierwszym renderze
    po zniszczeniu widgetu nie respektuje session_state - wraca do pierwszej opcji.
    Mechanizm identyczny jak w safe_checkbox: bufor + on_change synchronizacja.
    
    Args:
        label: Etykieta selectboxa
        options: Lista opcji do wyboru
        key: Klucz w session_state
        default_index: Indeks opcji domyslnej (default 0)
        **kwargs: Pozostale argumenty (help, on_change, args, kwargs itp.)
    """
    buffer_key = f"buffer_{key}"
    
    # Inicjalizacja glownego klucza jesli nie istnieje
    if key not in st.session_state:
        if 0 <= default_index < len(options):
            st.session_state[key] = options[default_index]
        elif options:
            st.session_state[key] = options[0]
        else:
            st.session_state[key] = None
    
    main_value = st.session_state.get(key)
    
    # Jesli aktualna wartosc nie jest w opcjach, ustaw default
    if main_value not in options:
        if 0 <= default_index < len(options):
            main_value = options[default_index]
        elif options:
            main_value = options[0]
        st.session_state[key] = main_value
    
    # Synchronizuj buffer z glownym kluczem
    if buffer_key not in st.session_state:
        st.session_state[buffer_key] = main_value
    elif st.session_state.get(buffer_key) != main_value:
        st.session_state[buffer_key] = main_value
    
    user_on_change = kwargs.pop("on_change", None)
    user_args = kwargs.pop("args", ())
    user_kwargs = kwargs.pop("kwargs", {})
    
    def _handle_change(*_args, **_kwargs):
        st.session_state[key] = st.session_state[buffer_key]
        if user_on_change:
            user_on_change(*user_args, **user_kwargs)
    
    # Obliczamy index dla widgetu na podstawie aktualnej wartosci w buforze
    try:
        _idx = options.index(st.session_state[buffer_key])
    except (ValueError, KeyError):
        _idx = default_index if 0 <= default_index < len(options) else 0
    
    return st.selectbox(
        label,
        options,
        index=_idx,
        key=buffer_key,
        on_change=_handle_change,
        **kwargs,
    )
def safe_number_input(label, key, default=0, min_value=None, max_value=None, step=1, **kwargs):
    """
    Number input z buforem - prawidlowo czyta session_state przy kazdym renderze.
    ROZWIAZANIE BUGa: Streamlit number_input z `key=` przy pierwszym renderze
    po zniszczeniu widgetu (np. po st.rerun() w callbacku) nie respektuje
    session_state - wraca do min_value lub default.
    Mechanizm identyczny jak w safe_checkbox/safe_selectbox: bufor + on_change.
    
    Args:
        label: Etykieta number_inputa
        key: Klucz w session_state
        default: Wartosc domyslna jesli klucza nie ma
        min_value: Minimum (przekazywane do st.number_input)
        max_value: Maximum (przekazywane do st.number_input)
        step: Krok (default 1)
        **kwargs: Pozostale argumenty
    """
    buffer_key = f"buffer_{key}"
    
    # Inicjalizacja glownego klucza jesli nie istnieje
    if key not in st.session_state:
        st.session_state[key] = default
    
    main_value = st.session_state.get(key, default)
    
    # Walidacja typu (int / float)
    try:
        if isinstance(step, int):
            main_value = int(main_value)
        else:
            main_value = float(main_value)
    except (ValueError, TypeError):
        main_value = default
    
    # Walidacja zakresu
    if min_value is not None and main_value < min_value:
        main_value = min_value
    if max_value is not None and main_value > max_value:
        main_value = max_value
    
    # Synchronizuj buffer z glownym kluczem
    if buffer_key not in st.session_state:
        st.session_state[buffer_key] = main_value
    elif st.session_state.get(buffer_key) != main_value:
        st.session_state[buffer_key] = main_value
    
    user_on_change = kwargs.pop("on_change", None)
    user_args = kwargs.pop("args", ())
    user_kwargs = kwargs.pop("kwargs", {})
    
    def _handle_change(*_args, **_kwargs):
        st.session_state[key] = st.session_state[buffer_key]
        if user_on_change:
            user_on_change(*user_args, **user_kwargs)
    
    # Buduj argumenty dla st.number_input
    _params = {
        'value': main_value,
        'key': buffer_key,
        'step': step,
        'on_change': _handle_change,
    }
    if min_value is not None:
        _params['min_value'] = min_value
    if max_value is not None:
        _params['max_value'] = max_value
    _params.update(kwargs)
    
    return st.number_input(label, **_params)
