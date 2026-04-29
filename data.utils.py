# data_utils.py

import streamlit as st
from datetime import date, datetime
from renderer import EXCLUDE_EXPORT_KEYS

def _build_proj_dict():
    """
    BUDOWA DOCELOWA: Pobiera tylko klucze zdefiniowane jako dane projektowe.
    Całkowicie izoluje projekt od stanu widgetów Streamlita.
    """
    proj = {}
    
    # Definiujemy prefiksy, które zawierają czyste dane (teksty, wybrane opcje)
    # t_ = tytuły, k_ = kierunek, l_ = loty, h_ = hotel, p_ = program, a_ = atrakcje
    valid_prefixes = ('t_', 'k_', 'l_', 'h_', 'p_', 'a_', 'font_', 'color_', 'font_size_', 'num_', 'sek_')
    
    # Definiujemy klucze zdjęć, ale TYLKO te, które przechowują linki URL (stringi)
    from renderer import IMAGE_KEYS

    for k, v in st.session_state.items():
        # A. Bierzemy tylko klucze z dozwolonymi prefiksami LUB jawne klucze zdjęć
        if k.startswith(valid_prefixes) or k in IMAGE_KEYS:
            
            # B. KRYTYCZNA WALIDACJA: 
            # Nawet jeśli klucz jest poprawny, sprawdzamy czy wartość nie jest "śmieciem" binarnym
            if v is None:
                proj[k] = None
                continue

            # Jeśli to jest URL ze Storage lub krótki tekst - zapisujemy
            if isinstance(v, (str, int, float, bool, list, dict)):
                # Blokada bezpieczeństwa: jeśli string jest podejrzanie długi (> 1MB), to nie jest tekst
                if isinstance(v, str) and len(v) > 100000: 
                    continue
                proj[k] = v
            
            # Daty zamieniamy na tekst ISO
            elif isinstance(v, (date, datetime)):
                proj[k] = v.isoformat()

    return proj
