"""
Skrypt "budzący" aplikację Streamlit Cloud, żeby nie usypiała po 12h
bezczynności. Uruchamiany automatycznie przez GitHub Actions co kilka
godzin - odwiedza aplikację prawdziwą, headless przeglądarką (samo
zapytanie HTTP nie wystarcza, bo Streamlit Cloud zwraca statyczną
"powłokę" HTML bez uruchamiania właściwej aplikacji Python).
"""
import os
from playwright.sync_api import sync_playwright

APP_URL = os.environ.get("STREAMLIT_APP_URL", "https://TWOJA-APLIKACJA.streamlit.app/")

def wake_up_app():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print(f"Odwiedzam: {APP_URL}")
        page.goto(APP_URL, timeout=60000)
        page.wait_for_timeout(5000)  # czekaj 5 sekund na załadowanie

        # Jeśli aplikacja śpi, pojawi się przycisk "Yes, get this app back up!"
        try:
            wake_button = page.get_by_text("get this app back up", exact=False)
            if wake_button.is_visible(timeout=3000):
                print("Aplikacja spała - klikam przycisk budzenia...")
                wake_button.click()
                page.wait_for_timeout(15000)  # czekaj na uruchomienie
        except Exception:
            print("Przycisk budzenia nie znaleziony - aplikacja prawdopodobnie już aktywna.")

        print("Gotowe.")
        browser.close()

if __name__ == "__main__":
    wake_up_app()
