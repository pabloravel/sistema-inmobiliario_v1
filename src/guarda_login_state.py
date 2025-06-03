from playwright.sync_api import sync_playwright
import time
import json
from pathlib import Path

STATE_PATH = Path("fb_state.json")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)  # Mostrar navegador
    context = browser.new_context()
    page = context.new_page()

    print("🔐 Abriendo Facebook para iniciar sesión manualmente...")
    page.goto("https://www.facebook.com/login")

    # Esperar a que el usuario complete el login manualmente
    print("🕒 Esperando que completes el login...")
    input("Presiona ENTER cuando hayas iniciado sesión y la página principal esté completamente cargada.")

    # Guardar el estado de la sesión
    context.storage_state(path=STATE_PATH)
    print(f"✅ Estado guardado en {STATE_PATH.resolve()}")

    browser.close()
