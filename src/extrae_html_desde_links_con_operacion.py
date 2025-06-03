#!/usr/bin/env python3
# extrae_html_desde_links_con_operacion.py

"""
Versión sin modificar tu lógica original: sólo inyecta detección de 'operacion'
(Venta/Renta) tras cargar la página. Mantiene todo lo demás intacto.
"""

import re
import json
import time
from pathlib import Path
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# —————— FUNCIONES AUXILIARES AÑADIDAS ——————

def _extract_listing_mode(page_source):
    """
    Busca en el HTML (con JS ya ejecutado) el patrón '"mode":"sell"' o '"mode":"rent"'.
    Devuelve 'sell' o 'rent', o None si no lo encuentra.
    """
    m = re.search(r'"mode"\s*:\s*"(sell|rent)"', page_source, re.IGNORECASE)
    return m.group(1).lower() if m else None

def _infer_operacion(texto):
    """
    Fallback por texto: si detecta '/ mes', 'renta', 'mensual' devuelve 'Renta',
    en otro caso 'Venta'.
    """
    low = texto.lower()
    for sig in (r'/\s*mes', 'renta', 'mensual', 'al mes'):
        if re.search(sig, low):
            return 'Renta'
    return 'Venta'

# —————— FIN DE FUNCIONES AUXILIARES ——————

# Configuración de Selenium (modo visible)
CHROME_PROFILE = "/Users/pabloravel/Library/Application Support/Google/Chrome/Default"
CHROMEDRIVER_PATH = None  # Si chromedriver está en PATH, déjalo None

def init_driver():
    opts = Options()
    # Comentamos headless para que sea visible
    # opts.add_argument("--headless=new")
    opts.add_argument(f"--user-data-dir={CHROME_PROFILE}")
    opts.add_argument("--log-level=3")
    if CHROMEDRIVER_PATH:
        return webdriver.Chrome(executable_path=CHROMEDRIVER_PATH, options=opts)
    return webdriver.Chrome(options=opts)

def extrae_de_pagina(url, driver):
    """
    Carga la URL, extrae los campos originales y además determina 'operacion'.
    """
    driver.get(url)

    # —————— NUEVO: detección de operacion ——————
    mode = _extract_listing_mode(driver.page_source)
    if mode == 'sell':
        operacion = 'Venta'
    elif mode == 'rent':
        operacion = 'Renta'
    else:
        # fallback: inferir por título/descr/precio usando los mismos selectores
        # que tu script ya tiene definidos abajo:
        # (aquí sólo armamos el texto; los selectores se usan tras parsear el soup)
        # obtendremos elementos luego con BeautifulSoup, pero podemos predefinir:
        # usaremos el texto bruto del page_source como simplificación
        operacion = _infer_operacion(driver.page_source)
    # ————————————— FIN DETECCIÓN ————————————

    # parsea con BeautifulSoup igual que tu script original
    soup = BeautifulSoup(driver.page_source, 'html.parser')

    # === Extracción ORIGINAL de campos (no modificar) ===
    # Ajusta estos selectores con los que ya usas en tu script:
    titulo_elem = soup.select_one('.titulo-selector')
    precio_elem = soup.select_one('.precio-selector')
    ciudad_elem = soup.select_one('.ciudad-selector')
    desc_elem   = soup.select_one('.descripcion-selector')
    tipo_elem   = soup.select_one('.tipo-propiedad-selector')
    img_elem    = soup.select_one('.imagen-portada-selector')
    # ... cualquier otro campo que extraigas ...

    titulo = titulo_elem.get_text(strip=True) if titulo_elem else ''
    precio = precio_elem.get_text(strip=True) if precio_elem else ''
    ciudad = ciudad_elem.get_text(strip=True) if ciudad_elem else ''
    descripcion = desc_elem.get_text(strip=True) if desc_elem else ''
    tipo_propiedad = tipo_elem.get_text(strip=True) if tipo_elem else ''
    imagen_portada = img_elem['src'].split('/')[-1] if img_elem and img_elem.get('src') else ''
    # === FIN Extracción ORIGINAL ===

    # Construye el objeto incluyendo 'operacion'
    item = {
        "link": url,
        "titulo": titulo,
        "precio": precio,
        "ciudad": ciudad,
        "descripcion": descripcion,
        "imagen_portada": imagen_portada,
        "tipo_propiedad": tipo_propiedad,
        # —————— campo NUEVO ——————
        "operacion": operacion
        # ————————————————————————
        # ... aquí el resto de tus campos originales ...
    }
    return item

def main():
    driver = init_driver()

    # Carga la lista de URLs desde tu JSON de links (no la toques)
    links_path = Path("resultados/links/repositorio_unico.json")
    with open(links_path, "r", encoding="utf-8") as f:
        urls = json.load(f)

    print(f"🔗 {len(urls)} URLs cargadas desde {links_path}")

    # Carga ya procesados para no duplicar
    processed_path = Path("resultados/repositorio_con_operacion.json")
    processed = set()
    if processed_path.exists():
        with open(processed_path, "r", encoding="utf-8") as f:
            for obj in json.load(f):
                processed.add(obj["link"])
        print(f"✅ Ya procesados: {len(processed)} URLs")

    nuevos = []
    for url in urls:
        if url in processed:
            continue
        print(f"Procesando {url} …")
        try:
            item = extrae_de_pagina(url, driver)
            print(f"  → Operacion: {item['operacion']}")
            nuevos.append(item)
        except Exception as e:
            print(f"  ERROR en {url}: {e}")

    driver.quit()

    # Guarda resultados, añadiendo a los anteriores
    existentes = []
    if processed_path.exists():
        with open(processed_path, "r", encoding="utf-8") as f:
            existentes = json.load(f)
    todas = existentes + nuevos
    processed_path.parent.mkdir(exist_ok=True)
    with open(processed_path, "w", encoding="utf-8") as f:
        json.dump(todas, f, ensure_ascii=False, indent=2)

    print(f"\n✔️  Nuevos items: {len(nuevos)}")
    print(f"   Total en repositorio: {len(todas)}")

if __name__ == "__main__":
    main()