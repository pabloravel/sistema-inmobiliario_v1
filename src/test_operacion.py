#!/usr/bin/env python3
# test_operacion.py
#
# Para cada URL de Marketplace que le pases:
#  • carga en visible con tu fb_state.json (no pide login)
#  • espera al contenedor React de descripción
#  • imprime la descripción RAW en consola
#  • y luego decide Venta/Renta basándose en unidad de tiempo o palabras clave.

import sys, re
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

FB_STATE = "fb_state.json"

# regexs
RE_UNIDADES = re.compile(r"\b(semana|mes|noche|día|días)\b", re.IGNORECASE)
RE_RENTA    = re.compile(r"\b(renta|alquiler)\b", re.IGNORECASE)
RE_VENTA    = re.compile(r"\b(vendo|venta|vender)\b", re.IGNORECASE)

def detectar_operacion(page) -> str:
    desc = ""

    # 1) expandir “Ver más” si existe
    try:
        btn = page.locator("text=Ver más").first
        if btn.is_visible():
            btn.click()
            page.wait_for_timeout(500)
    except:
        pass

    # 2) espera y lee la descripción React-rendered
    try:
        # Este es el selector que funciona tras React mount
        locator = page.wait_for_selector("div[data-testid='marketplace_post_description']",
                                         timeout=10000)
        desc = locator.inner_text(timeout=5000).strip()
    except PlaywrightTimeoutError:
        # no apareció: lo dejamos en ""
        pass
    except Exception:
        pass

    # 3) imprimir para debug
    print("\n--- DESCRIPCIÓN CAPTURADA ---\n" + (desc or "<VACÍA>") + "\n--- FIN DESCRIPCIÓN ---\n")

    txt = desc.lower()

    # 4) decide basándote en unidades de tiempo
    if RE_UNIDADES.search(txt):
        return "Renta"
    if RE_RENTA.search(txt):
        return "Renta"
    if RE_VENTA.search(txt):
        return "Venta"
    return "Desconocido"


def main():
    if len(sys.argv) < 2:
        print(f"Uso: {sys.argv[0]} <url1> [<url2> …]")
        sys.exit(1)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(storage_state=FB_STATE)

        for url in sys.argv[1:]:
            print(f"\n↪ Cargando {url}")
            page = context.new_page()
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
            except PlaywrightTimeoutError:
                print("⚠️ Timeout cargando página, intentando con lo que haya…")
            except Exception as e:
                print(f"❌ Error navegando: {e}")

            op = detectar_operacion(page)
            print(f"   → Operación detectada: {op}")
            page.close()

        browser.close()


if __name__ == "__main__":
    main()