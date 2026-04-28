import streamlit as st

def safe_text_input(label, key, **kwargs):
    """Text input z buforem — nie przeładowuje na każdy znak."""
    buffer_key = f"buffer_{key}"
    
    if buffer_key not in st.session_state:
        st.session_state[buffer_key] = st.session_state.get(key, "")

    st.text_input(
        label,
        key=buffer_key,
        on_change=lambda: st.session_state.update({key: st.session_state[buffer_key]}),
        **kwargs
    )


def safe_text_area(label, key, **kwargs):
    """Text area z buforem — nie przeładowuje na każdy znak."""
    buffer_key = f"buffer_{key}"
    
    if buffer_key not in st.session_state:
        st.session_state[buffer_key] = st.session_state.get(key, "")

    st.text_area(
        label,
        key=buffer_key,
        on_change=lambda: st.session_state.update({key: st.session_state[buffer_key]}),
        **kwargs
    )

W app.py — na POCZĄTKU dodaj import:
pythonfrom my_components import safe_text_input, safe_text_area

TERAZ — Find & Replace:
Find:
st.text_input(
Replace:
safe_text_input(
Replace All ✅

Find:
st.text_area(
Replace:
safe_text_area(
Replace All ✅

GOTOWE! 🚀
Zapisz, F5, testuj — powinno być płynnie bez zawieszania!
