import io
import streamlit as st
from PIL import Image, ImageOps
from renderer import IMAGE_KEYS

# Zmienne globalne - poprawne
STORAGE_BUCKET = "nexa-images"
STORAGE_USER = "default_user"

def upload_image(supabase_client, key: str, raw_bytes: bytes, max_dim: int = 1000, is_logo: bool = False) -> str | None:
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
        storage_path = f"{STORAGE_USER}/{key}.{file_ext}"
        try:
            supabase_client.storage.from_(STORAGE_BUCKET).remove([storage_path])
        except Exception:
            pass
        supabase_client.storage.from_(STORAGE_BUCKET).upload(
            storage_path, optimized_bytes, file_options={"content-type": content_type}
        )
        return supabase_client.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)
    except Exception:
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
    return migrated, failed # Tu kończy się ta funkcja

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
