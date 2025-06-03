# OFICIAL_Scrolling_extraccion_links_v2.py
# ✅ Basado en OFICIAL_Scrolling_extraccion_links_v1.py, sólo se agregan day stamp y conteo de links únicos de la corrida.

from playwright.sync_api import sync_playwright
import time
import json
from datetime import datetime
from pathlib import Path

def extraer_links_ciudad(ciudad, enlaces, carpeta_resultados, repositorio_links, tipo_propiedad):
    """
    Extrae enlaces de Marketplace para la ciudad dada,
    filtrando aquellos que ya existen en repositorio_links.
    """
    links_extraidos = set()
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    nombre_archivo = f"links_extraidos_{tipo_propiedad}_{ciudad.lower()}_{timestamp}.json"
    ruta_salida = carpeta_resultados / nombre_archivo

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state="fb_state.json")
        page = context.new_page()

        for etiqueta, url in enlaces.items():
            print(f"\n🌎 Abriendo ciudad: {ciudad} - {tipo_propiedad} - {url}")
            page.goto(url)
            time.sleep(4)
            nuevos_links = set()
            intentos_sin_nuevos = 0

            for _ in range(999):
                page.keyboard.down("PageDown")
                time.sleep(4)
                elementos = page.query_selector_all("a[href*='/marketplace/item/']")
                for e in elementos:
                    href = e.get_attribute("href")
                    if href and "/marketplace/item/" in href:
                        href_clean = href.split("?")[0]
                        # Filtrar si ya existía en repositorio
                        if href_clean not in repositorio_links and href_clean not in links_extraidos:
                            nuevos_links.add(href_clean)
                if nuevos_links:
                    links_extraidos.update(nuevos_links)
                    print(f"✅ Nuevos links únicos encontrados en {ciudad} ({tipo_propiedad}): {len(nuevos_links)} (total ciudad: {len(links_extraidos)})")
                    nuevos_links.clear()
                    intentos_sin_nuevos = 0
                else:
                    intentos_sin_nuevos += 1
                    print(f"⚠️ No se encontraron nuevos links (intento {intentos_sin_nuevos})")
                    if intentos_sin_nuevos >= 5:
                        break

        browser.close()

    # Guardar sólo los enlaces nuevos de esta ejecución
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(sorted(list(links_extraidos)), f, indent=2, ensure_ascii=False)

    print(f"🎯 Links de {ciudad} ({tipo_propiedad}) guardados en {ruta_salida}")
    return list(links_extraidos)

if __name__ == "__main__":
    # === NUEVO: impresión de day stamp de la corrida ===
    fecha_corrida = datetime.now().strftime("%Y-%m-%d")
    print(f"🚀 Iniciando extracción de links — Corrida del {fecha_corrida}\n")

    # Crear carpetas separadas para ventas y rentas
    carpeta_base = Path("resultados/links")
    carpeta_ventas = carpeta_base / "ventas"
    carpeta_rentas = carpeta_base / "rentas"
    carpeta_ventas.mkdir(parents=True, exist_ok=True)
    carpeta_rentas.mkdir(parents=True, exist_ok=True)

    # Repositorios separados para ventas y rentas
    repositorio_ventas_path = carpeta_ventas / "repositorio_unico_ventas.json"
    repositorio_rentas_path = carpeta_rentas / "repositorio_unico_rentas.json"
    repositorio_ventas = set()
    repositorio_rentas = set()

    # Cargar repositorios previos si existen
    for repo_path, repo_set in [(repositorio_ventas_path, repositorio_ventas), 
                               (repositorio_rentas_path, repositorio_rentas)]:
        if repo_path.exists():
            with open(repo_path, "r", encoding="utf-8") as f:
                datos_previos = json.load(f)
                for item in datos_previos:
                    if isinstance(item, str):
                        repo_set.add(item)
                    elif isinstance(item, dict):
                        href = item.get('link') or item.get('url') or item.get('href')
                        if href:
                            repo_set.add(href.split("?")[0])

    # Enlaces para propiedades en venta
    ciudades_y_enlaces_venta = {
        "Cuernavaca": {
            "general": "https://www.facebook.com/marketplace/cuernavaca/propertyforsale",
            "precio_0_5500000": "https://www.facebook.com/marketplace/cuernavaca/propertyforsale?minPrice=0&maxPrice=5500000",
            "precio_5500001_10500000": "https://www.facebook.com/marketplace/cuernavaca/propertyforsale?minPrice=5500001&maxPrice=10500000",
            "precio_10500001_15500000": "https://www.facebook.com/marketplace/cuernavaca/propertyforsale?minPrice=10500001&maxPrice=15500000"
        },
        "Jiutepec": {
            "general": "https://www.facebook.com/marketplace/107963212565853/propertyforsale",
            "precio_0_5500000": "https://www.facebook.com/marketplace/107963212565853/propertyforsale?minPrice=0&maxPrice=5500000",
            "precio_5500001_10500000": "https://www.facebook.com/marketplace/107963212565853/propertyforsale?minPrice=5500001&maxPrice=10500000",
            "precio_10500001_15500000": "https://www.facebook.com/marketplace/107963212565853/propertyforsale?minPrice=10500001&maxPrice=15500000"
        },
        "Temixco": {
            "general": "https://www.facebook.com/marketplace/108039299223018/propertyforsale",
            "precio_0_5500000": "https://www.facebook.com/marketplace/108039299223018/propertyforsale?minPrice=0&maxPrice=5500000",
            "precio_5500001_10500000": "https://www.facebook.com/marketplace/108039299223018/propertyforsale?minPrice=5500001&maxPrice=10500000",
            "precio_10500001_15500000": "https://www.facebook.com/marketplace/108039299223018/propertyforsale?minPrice=10500001&maxPrice=15500000"
        }
    }

    # Enlaces para propiedades en renta
    ciudades_y_enlaces_renta = {
        "Cuernavaca": {
            "general": "https://www.facebook.com/marketplace/cuernavaca/propertyrentals?maxPrice=400000&exact=false&latitude=18.9331&longitude=-99.2332&radius=16"
        },
        "Jiutepec": {
            "general": "https://www.facebook.com/marketplace/cuernavaca/propertyrentals?maxPrice=400000&exact=false&latitude=18.8834&longitude=-99.1669&radius=16"
        }
    }

    # Procesar propiedades en venta
    print("\n📍 PROCESANDO PROPIEDADES EN VENTA")
    total_nuevos_links_venta = 0
    for ciudad, enlaces in ciudades_y_enlaces_venta.items():
        print(f"\n🌎 Procesando ciudad para venta: {ciudad}")
        nuevos = extraer_links_ciudad(ciudad, enlaces, carpeta_ventas, repositorio_ventas, "venta")
        repositorio_ventas.update(nuevos)
        total_nuevos_links_venta += len(nuevos)

    # Procesar propiedades en renta
    print("\n📍 PROCESANDO PROPIEDADES EN RENTA")
    total_nuevos_links_renta = 0
    for ciudad, enlaces in ciudades_y_enlaces_renta.items():
        print(f"\n🌎 Procesando ciudad para renta: {ciudad}")
        nuevos = extraer_links_ciudad(ciudad, enlaces, carpeta_rentas, repositorio_rentas, "renta")
        repositorio_rentas.update(nuevos)
        total_nuevos_links_renta += len(nuevos)

    # Imprimir resumen
    print(f"\n🎉 Resumen de la corrida {fecha_corrida}:")
    print(f"- Links únicos de venta extraídos: {total_nuevos_links_venta}")
    print(f"- Links únicos de renta extraídos: {total_nuevos_links_renta}")
    print(f"- Total de links extraídos: {total_nuevos_links_venta + total_nuevos_links_renta}\n")

    # Guardar repositorios actualizados
    with open(repositorio_ventas_path, "w", encoding="utf-8") as f:
        json.dump(sorted(list(repositorio_ventas)), f, indent=2, ensure_ascii=False)
    
    with open(repositorio_rentas_path, "w", encoding="utf-8") as f:
        json.dump(sorted(list(repositorio_rentas)), f, indent=2, ensure_ascii=False)

    print(f"📦 Repositorio de ventas actualizado → {repositorio_ventas_path} ({len(repositorio_ventas)} links únicos)")
    print(f"📦 Repositorio de rentas actualizado → {repositorio_rentas_path} ({len(repositorio_rentas)} links únicos)")
