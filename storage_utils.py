"""
storage_utils.py
================
Moduł do zarządzania zdjęciami w Supabase Storage.

Architektura:
- Zdjęcia są przechowywane w Supabase Storage (bucket: nexa-images)
- W session_state trzymamy URL zdjęcia (string), nie bytes
- W tabeli projects.data trzymamy tylko teksty i URL-e (mały JSON)
- get_image_for_html() zwraca tag <img> działający z URL lub bytes (wsteczna kompatybilność)

Ścieżki w Storage:
  default_user/img_hero_t.jpg
  default_user/logo_az.png
  default_user/img_hotel_1_0.jpg
  itd.
"""

import io
import base64
import streamlit as st
from PIL import Image, ImageOps


STORAGE_BUCKET = "nexa-images"
STORAGE_USER = "default_user"


def _get_storage_path(key: str) -> str:
    """Zwraca ścieżkę w Storage dla danego klucza."""
    ext = "png" if key.startswith("logo") else "jpg"
    return f"{STORAGE_USER}/{key}.{ext}"


def upload_image(supabase_client, key: str, raw_bytes: bytes,
                 max_dim: int = 1000, is_logo: bool = False) -> str | None:
    """
    Optymalizuje zdjęcie i uploaduje do Supabase Storage.
    Zwraca publiczny URL zdjęcia lub None przy błędzie.

    Args:
        supabase_client: Klient Supabase
        key: Klucz zdjęcia (np. 'img_hero_t', 'logo_az')
        raw_bytes: Surowe bajty zdjęcia
        max_dim: Maksymalny wymiar (px)
        is_logo: True → PNG z przezroczystością, False → JPEG

    Returns:
        str: Publiczny URL zdjęcia
        None: Przy błędzie
    """
    if not raw_bytes:
        return None

    try:
        # 1. Optymalizacja zdjęcia
        with Image.open(io.BytesIO(raw_bytes)) as img:
            try:
                img = ImageOps.exif_transpose(img)
            except Exception:
                pass

            if is_logo:
                # Logo: zachowaj przezroczystość, PNG
                resample = getattr(Image, 'Resampling', Image).LANCZOS
                img.thumbnail((max_dim, max_dim), resample)
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                content_type = "image/png"
                file_ext = "png"
            else:
                # Zdjęcie: konwertuj do RGB, JPEG
                if img.mode in ("RGBA", "P"):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "RGBA":
                        bg.paste(img, mask=img.split()[3])
                    else:
                        bg.paste(img)
                    img = bg
                elif img.mode != "RGB":
                    img = img.convert("RGB")
                resample = getattr(Image, 'Resampling', Image).LANCZOS
                img.thumbnail((max_dim, max_dim), resample)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=80, optimize=True)
                content_type = "image/jpeg"
                file_ext = "jpg"

        optimized_bytes = buf.getvalue()

        # 2. Upload do Supabase Storage
        storage_path = f"{STORAGE_USER}/{key}.{file_ext}"

        # Usuń stary plik jeśli istnieje (upsert)
        try:
            supabase_client.storage.from_(STORAGE_BUCKET).remove([storage_path])
        except Exception:
            pass  # Plik może nie istnieć - OK

        # Upload nowego pliku
        supabase_client.storage.from_(STORAGE_BUCKET).upload(
            path=storage_path,
            file=optimized_bytes,
            file_options={"content-type": content_type, "upsert": "true"}
        )

        # 3. Pobierz publiczny URL
        url_response = supabase_client.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)
        public_url = url_response if isinstance(url_response, str) else url_response.get('publicUrl', '')

        if public_url:
            return public_url
        return None

    except Exception as e:
        st.error(f"Błąd uploadu zdjęcia ({key}): {str(e)[:100]}")
        return None


def delete_image(supabase_client, key: str) -> bool:
    """Usuwa zdjęcie z Storage."""
    try:
        for ext in ['jpg', 'png']:
            storage_path = f"{STORAGE_USER}/{key}.{ext}"
            try:
                supabase_client.storage.from_(STORAGE_BUCKET).remove([storage_path])
            except Exception:
                pass
        return True
    except Exception:
        return False


def get_image_html(key: str, style: str = "width:100%;height:100%;object-fit:cover;",
                   placeholder_text: str = "BRAK ZDJĘCIA") -> str:
    """
    Zwraca tag <img> dla zdjęcia z danego klucza session_state.
    Obsługuje zarówno URL (nowy format) jak i bytes (stary format - wsteczna kompatybilność).

    Args:
        key: Klucz w session_state
        style: CSS style dla <img>
        placeholder_text: Tekst gdy brak zdjęcia

    Returns:
        str: Tag <img src="..."> lub div z placeholder
    """
    value = st.session_state.get(key)

    if not value:
        return f"<div style='width:100%;height:100%;background:#fcfcfc;display:flex;align-items:center;justify-content:center;color:#aaa;font-weight:bold;font-size:11px;text-align:center;text-transform:uppercase;'>{placeholder_text}</div>"

    # Nowy format: URL string
    if isinstance(value, str) and value.startswith('http'):
        return f"<img src='{value}' style='{style}'>"

    # Stary format: bytes (wsteczna kompatybilność)
    if isinstance(value, bytes):
        b64 = base64.b64encode(value).decode()
        # Wykryj format
        if value[:8] == b'\x89PNG\r\n\x1a\n':
            mime = "image/png"
        else:
            mime = "image/jpeg"
        return f"<img src='data:{mime};base64,{b64}' style='{style}'>"

    return f"<div style='width:100%;height:100%;background:#fcfcfc;display:flex;align-items:center;justify-content:center;color:#aaa;font-weight:bold;font-size:11px;text-align:center;text-transform:uppercase;'>{placeholder_text}</div>"


def get_logo_html(key: str, css_style: str = "max-height:100%;max-width:150px;object-fit:contain;") -> str:
    """
    Zwraca tag <img> dla logo.
    Obsługuje URL i bytes.
    """
    value = st.session_state.get(key)

    if not value:
        return ""

    if isinstance(value, str) and value.startswith('http'):
        return f"<img src='{value}' style='{css_style}'>"

    if isinstance(value, bytes):
        b64 = base64.b64encode(value).decode()
        return f"<img src='data:image/png;base64,{b64}' style='{css_style}'>"

    return ""


def get_image_b64_for_crop(key: str, ratio: tuple = (4, 5)):
    """
    Zwraca base64 string zdjęcia po przycięciu do podanego ratio.
    Potrzebne dla slajdów które kadrują zdjęcia (renderer.py get_b64).
    Obsługuje URL (pobiera i kadruje) i bytes (kadruje bezpośrednio).
    Wyniki są cache'owane przez Streamlit.
    """
    value = st.session_state.get(key)
    if not value:
        return None

    # Stary format: bytes - używamy istniejącej logiki
    if isinstance(value, bytes):
        from renderer import get_b64_cached
        return get_b64_cached(value, ratio)

    # Nowy format: URL - zwróć URL bezpośrednio (bez kadrowania po stronie serwera)
    # Kadrowanie przez CSS object-fit: cover na frontendzie
    if isinstance(value, str) and value.startswith('http'):
        return value  # URL - HTML użyje go jako src bezpośrednio

    return None


def migrate_bytes_to_storage(supabase_client) -> dict:
    """
    Jednorazowa migracja: konwertuje bytes ze session_state do Storage.
    Zwraca słownik {key: url} dla zmigrowanych zdjęć.
    Wywoływana raz przy starcie sesji jeśli są stare dane w bytes.
    """
    from renderer import IMAGE_KEYS

    migrated = {}
    keys_with_bytes = [
        k for k in IMAGE_KEYS
        if k in st.session_state and isinstance(st.session_state.get(k), bytes)
    ]

    if not keys_with_bytes:
        return migrated

    with st.spinner(f"Migracja {len(keys_with_bytes)} zdjęć do Storage..."):
        for key in keys_with_bytes:
            raw_bytes = st.session_state[key]
            is_logo = key.startswith('logo')
            url = upload_image(supabase_client, key, raw_bytes, is_logo=is_logo)
            if url:
                st.session_state[key] = url  # Zastąp bytes URL-em
                migrated[key] = url

    return migrated
