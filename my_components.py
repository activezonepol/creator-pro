import streamlit as st

def safe_text_input(label, key, **kwargs):
    """Text input z buforem — nie przeładowuje na każdy znak."""
    buffer_key = f"buffer_{key}"
    
    if buffer_key not in st.session_state:
        st.session_state[buffer_key] = st.session_state.get(key, "")

    return st.text_input(  # ← DODAJ return!
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

    return st.text_area(  # ← DODAJ return!
        label,
        key=buffer_key,
        on_change=lambda: st.session_state.update({key: st.session_state[buffer_key]}),
        **kwargs
    )

