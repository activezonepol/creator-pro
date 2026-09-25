import io
import re
import uuid
import streamlit as st
from PIL import Image, ImageOps

from renderer import IMAGE_KEYS
from db_utils import save_to_supabase

# Zmienne globalne
STORAGE_BUCKET = "nexa-images"
STORAGE_USER = "default_user"

# Klucze zdjęć atrakcji (foto główne + 3 miniatury). Dla tych pól NIE
# nadpisujemy pliku po nazwie klucza - każdy upload dostaje unikalną nazwę
# (attr_{uuid}), żeby zdjęcia gromadziły się w galerii kraju do ponownego
# użycia w innych ofertach, zamiast znikać przy kolejnym uploadzie.
_ATTR_GALLERY_KEY_PATTERN = re.compile(r'^(ah|at1|at2|at3)_\d+$')

def _is_attraction_image_key(key: str) -> bool:
    return bool(_ATTR_GALLERY_KEY_PATTERN.match(key))
# Klucze zdjęć atrakcji (foto główne + 3 miniatury). Dla tych pól NIE
# nadpisujemy pliku po nazwie klucza - każdy upload dostaje unikalną nazwę
# (attr_{uuid}), żeby zdjęcia gromadziły się w galerii kraju do ponownego
# użycia w innych ofertach, zamiast znikać przy kolejnym uploadzie.
_ATTR_GALLERY_KEY_PATTERN = re.compile(r'^(ah|at1|at2|at3)_\d+$')

def _is_attraction_image_key(key: str) -> bool:
    return bool(_ATTR_GALLERY_KEY_PATTERN.match(key))

def upload_image(supabase_client, key: str, raw_bytes: bytes, max_dim: int = 1400, is_logo: bool = False) -> str | None:
    """Optymalizuje zdjęcie i uploaduje do Supabase Storage. Zwraca publiczny URL."""
    if not raw_bytes:
        return None
    
    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            img = ImageOps.exif_transpose(img)
            if is_logo:
                resample = getattr(Image, 'Resampling', Image).LANCZOS
                img.thumbnail((max_dim, max_dim), resample)
                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                content_type, file_ext = "image/png", "png"
            else:
                if img.mode in ("RGBA", "P"):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                    img = bg
                elif img.mode != "RGB":
                    img = img.convert("RGB")
                resample = getattr(Image, 'Resampling', Image).LANCZOS
                img.thumbnail((max_dim, max_dim), resample)
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=80, optimize=True)
                content_type, file_ext = "image/jpeg", "jpg"
            optimized_bytes = buf.getvalue()
            
        _country_prefix = str(st.session_state.get('country_code', '') or '').strip().upper()
        if not _country_prefix or len(_country_prefix) != 3:
            _country_prefix = "XXX"

        if key == 'logo_cli':
            # Logo klienta gromadzi się w osobnym folderze (galeria logotypów) -
            # każdy upload dostaje unikalną nazwę, nic nie nadpisujemy.
            _unique_name = f"logo_{uuid.uuid4().hex[:12]}"
            storage_path = f"{STORAGE_USER}/loga_klientow/{_unique_name}.{file_ext}"
        elif key.startswith('img_pg_'):
            # Pillow gifts gromadzą się w osobnym folderze (galeria prezentów) -
            # te same prezenty w różnych ofertach, bez wgrywania od nowa.
            _unique_name = f"pg_{uuid.uuid4().hex[:12]}"
            storage_path = f"{STORAGE_USER}/prezenty/{_unique_name}.{file_ext}"
        elif key.startswith('img_brand_') or key.startswith('img_va_') or key == 'img_app_screen':
            # Wspólna galeria: branding + wirtualny asystent + ekran aplikacji.
            _unique_name = f"brand_{uuid.uuid4().hex[:12]}"
            storage_path = f"{STORAGE_USER}/BRANDING/{_unique_name}.{file_ext}"
        elif key in ('img_hero_l', 'img_hero_j'):
            # Wspólna galeria TRANSPORT (samolot / autokar itp.).
            _unique_name = f"trans_{uuid.uuid4().hex[:12]}"
            storage_path = f"{STORAGE_USER}/TRANSPORT/{_unique_name}.{file_ext}"
        elif _is_attraction_image_key(key) or key in ('img_hero_t', 'img_hero_k', 'img_k_th1', 'img_k_th2', 'img_app_bg') or key.startswith('img_koszt_') or (key.startswith('sek_') and key.endswith('_img')):
            # Nazwa unikalna - nic nie nadpisujemy. Wszystkie zdjecia zwiazane z
            # danym krajem (atrakcje, strona tytulowa, kierunek, przerywniki)
            # laduja w jednym folderze kraju = wspolna galeria per kraj.
            _unique_name = f"attr_{uuid.uuid4().hex[:12]}"
            storage_path = f"{STORAGE_USER}/{_country_prefix}/{_unique_name}.{file_ext}"
        else:
            storage_path = f"{STORAGE_USER}/{_country_prefix}/{key}.{file_ext}"
            try:
                supabase_client.storage.from_(STORAGE_BUCKET).remove([storage_path])
            except Exception:
                pass

        supabase_client.storage.from_(STORAGE_BUCKET).upload(
            storage_path, optimized_bytes, file_options={"content-type": content_type}
        )
        # ?v=timestamp wymusza pobranie nowej wersji pliku
        # (URL jest stały, ale plik w Storage zmienił się — bez ?v= browser cache'uje)
        public_url = supabase_client.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)
        import time
        return f"{public_url}?v={int(time.time())}"
    except Exception as e:
        print(f"Błąd uploadu: {e}") 
        return None

def cleanup_session_bytes_to_storage(supabase_client):
    """Przeszukuje sesję w poszukiwaniu bytes i migruje je do Storage."""
    migrated = 0
    failed = []
    for key in IMAGE_KEYS:
        val = st.session_state.get(key)
        if isinstance(val, bytes):
            url = upload_image(supabase_client, key, val, is_logo=key.startswith("logo"))
            if url:
                st.session_state[key] = url
                migrated += 1
            else:
                failed.append(key)
    return migrated, failed

def run_migration_flow(supabase_client):
    """Orkiestrator migracji: czyści, zapisuje i powiadamia."""
    migrated_count, failed = cleanup_session_bytes_to_storage(supabase_client)
    if migrated_count > 0:
        save_to_supabase() 
        st.success(f"✅ Zmigrowano {migrated_count} zdjęć i zaktualizowano bazę.")
    if failed:
        st.error(f"❌ Nie udało się zmigrować: {', '.join(failed)}")
    if migrated_count == 0 and not failed:
        st.info("ℹ️ Brak zdjęć w pamięci do migracji.")

# ---------------------------------------------------------------------------
# FUNKCJE POMOCNICZE (RENDEROWANIE HTML) ORAZ ALIAS
# ---------------------------------------------------------------------------
def get_image_html(url: str, max_width: str = "100%") -> str:
    """Zwraca tag HTML img dla zwykłego zdjęcia."""
    if not url:
        return ""
    return f'<img src="{url}" style="max-width: {max_width}; border-radius: 8px; object-fit: cover;">'

def get_logo_html(url: str, max_height: str = "80px") -> str:
    """Zwraca tag HTML img sformatowany specjalnie pod logo (bez zniekształceń)."""
    if not url:
        return ""
    return f'<img src="{url}" style="max-height: {max_height}; max-width: 100%; object-fit: contain;">'

def migrate_bytes_to_storage(supabase_client):
    """Alias dla nowej funkcji (dla kompatybilności wstecznej z app.py)."""
    return cleanup_session_bytes_to_storage(supabase_client)

@st.cache_data(ttl=20, show_spinner=False)
def list_country_gallery(_supabase_client, country_code: str, name_prefix: str = ""):
    """
    Zwraca listę publicznych URL-i WSZYSTKICH zdjęć w folderze danego kraju
    (atrakcje, strona tytułowa, kierunek, przerywniki) - jedna wspólna galeria
    per kraj. name_prefix opcjonalny (domyślnie pusty = wszystko).
    """
    _country_prefix = str(country_code or '').strip().upper()
    if not _country_prefix or len(_country_prefix) != 3:
        _country_prefix = "XXX"
    folder_path = f"{STORAGE_USER}/{_country_prefix}"
    try:
        files = _supabase_client.storage.from_(STORAGE_BUCKET).list(
            folder_path,
            {"limit": 1000, "sortBy": {"column": "created_at", "order": "desc"}},
        )
    except Exception:
        return []
    if not files:
        return []
    urls = []
    for f in files:
        _name = f.get('name', '')
        if not _name or _name.startswith('.'):
            continue
        if name_prefix and not _name.startswith(name_prefix):
            continue
        _full_path = f"{folder_path}/{_name}"
        try:
            _url = _supabase_client.storage.from_(STORAGE_BUCKET).get_public_url(_full_path)
            urls.append(_url)
        except Exception:
            continue
    return urls

def list_logo_gallery(_supabase_client):
    """Zwraca listę publicznych URL-i logotypów klientów zebranych w folderze
    loga_klientow/ (każde wgrane logo klienta ląduje tu z unikalną nazwą)."""
    folder_path = f"{STORAGE_USER}/loga_klientow"
    try:
        files = _supabase_client.storage.from_(STORAGE_BUCKET).list(
            folder_path,
            {"limit": 1000, "sortBy": {"column": "created_at", "order": "desc"}},
        )
    except Exception:
        return []
    if not files:
        return []
    urls = []
    for f in files:
        _name = f.get('name', '')
        if not _name or _name.startswith('.'):
            continue
        try:
            urls.append(_supabase_client.storage.from_(STORAGE_BUCKET).get_public_url(f"{folder_path}/{_name}"))
        except Exception:
            continue
    return urls

def list_pillow_gallery(_supabase_client):
    """Zwraca listę publicznych URL-i zdjęć pillow gifts zebranych w folderze
    prezenty/ (każde wgrane zdjęcie prezentu ląduje tu z unikalną nazwą)."""
    folder_path = f"{STORAGE_USER}/prezenty"
    try:
        files = _supabase_client.storage.from_(STORAGE_BUCKET).list(
            folder_path,
            {"limit": 1000, "sortBy": {"column": "created_at", "order": "desc"}},
        )
    except Exception:
        return []
    if not files:
        return []
    urls = []
    for f in files:
        _name = f.get('name', '')
        if not _name or _name.startswith('.'):
            continue
        try:
            urls.append(_supabase_client.storage.from_(STORAGE_BUCKET).get_public_url(f"{folder_path}/{_name}"))
        except Exception:
            continue
    return urls

def list_brand_gallery(_supabase_client):
    """Zwraca listę publicznych URL-i zdjęć brandingowych zebranych w folderze
    branding/ (wspólna galeria dla wszystkich ofert)."""
    folder_path = f"{STORAGE_USER}/BRANDING"
    try:
        files = _supabase_client.storage.from_(STORAGE_BUCKET).list(
            folder_path,
            {"limit": 1000, "sortBy": {"column": "created_at", "order": "desc"}},
        )
    except Exception:
        return []
    if not files:
        return []
    urls = []
    for f in files:
        _name = f.get('name', '')
        if not _name or _name.startswith('.'):
            continue
        try:
            urls.append(_supabase_client.storage.from_(STORAGE_BUCKET).get_public_url(f"{folder_path}/{_name}"))
        except Exception:
            continue
    return urls
