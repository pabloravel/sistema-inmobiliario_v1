import os
import json
import requests
from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from tqdm import tqdm  # Para la barra de progreso

# Rutas y constantes
CARPETA_LINKS = "resultados/links/repositorio_unico.json"
CARPETA_RESULTADOS = "resultados"
ESTADO_FB = "fb_state.json"
BASE_URL = "https://www.facebook.com"

# Cargar y normalizar enlaces
with open(CARPETA_LINKS, "r", encoding="utf-8") as f:
    raw_links = json.load(f)

links = []
for item in raw_links:
    if isinstance(item, str):
        href = item
        if href.startswith("/"):
            href = BASE_URL + href
        if href.startswith(BASE_URL):
            id_pub = href.rstrip("/").split("/")[-1]
            links.append({"link": href, "id": id_pub})
    elif isinstance(item, dict):
        href = item.get("link", "")
        if href.startswith("/"):
            href = BASE_URL + href
        if href.startswith(BASE_URL):
            item["link"] = href
            links.append(item)

# Preparar carpeta destino
date_str = datetime.now().strftime("%Y-%m-%d")
carpeta_destino = os.path.join(CARPETA_RESULTADOS, date_str)
os.makedirs(carpeta_destino, exist_ok=True)

# Funciones de extracción

def extraer_descripcion_estable(soup):
    for div in soup.find_all("div"):
        if div.get_text(strip=True) in ["Descripción", "Detalles"]:
            siguiente = div.find_next_sibling("div")
            if siguiente:
                return siguiente.get_text(separator="\n", strip=True).replace("Ver menos", "").strip()
    return ""


def extraer_precio(soup):
    for span in soup.find_all("span"):
        texto = span.get_text(strip=True)
        if texto.startswith("$") and len(texto) < 30:
            return texto
    return ""


def extraer_vendedor(soup):
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "facebook.com/profile.php?id=" in href:
            link_vendedor = href.split("?")[0]
            strong = a.find("strong")
            if strong:
                vendedor = strong.get_text(strip=True)
            else:
                span = a.find("span")
                vendedor = span.get_text(strip=True) if span else ""
            return vendedor, link_vendedor
    return "", ""


def descargar_imagen_portada(soup, ciudad, id_publicacion):
    """
    Busca el primer <img> válido y descarga su contenido
    guardándolo en carpeta_destino. Devuelve el nombre de archivo o "".
    """
    img = soup.find("img")
    if not img:
        return ""
    src = img.get("src") or img.get("data-src")
    if not src or not src.startswith("http"):
        return ""
    filename = f"{ciudad}-{date_str}-{id_publicacion}.jpg"
    path_img = os.path.join(carpeta_destino, filename)
    try:
        resp = requests.get(src, timeout=10)
        if resp.status_code == 200:
            with open(path_img, "wb") as f:
                f.write(resp.content)
            return filename
    except Exception as e:
        print(f"⚠️ No se pudo descargar portada: {e}")
    return ""


def guardar_html_y_json(html, datos, ciudad, id_publicacion):
    base = f"{ciudad}-{date_str}-{id_publicacion}"
    ruta_html = os.path.join(carpeta_destino, base + ".html")
    ruta_json = os.path.join(carpeta_destino, base + ".json")

    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(html)
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def main():
    # Contadores para el progreso
    total_links = len(links)
    success_count = 0
    error_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=ESTADO_FB)
        page = context.new_page()

        # Barra de progreso con tqdm
        pbar = tqdm(total=total_links, desc="Extrayendo propiedades", unit="propiedad")

        for link_data in links:
            full_url = link_data["link"]
            ciudad = link_data.get("ciudad", "cuernavaca").lower()
            id_publicacion = link_data["id"]

            try:
                page.goto(full_url, timeout=60000)
                page.wait_for_timeout(3000)

                # Expandir descripción si existe
                try:
                    vm = page.locator("text=Ver más")
                    if vm.is_visible():
                        vm.click()
                        page.wait_for_timeout(1000)
                except:
                    pass

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # Extracciones básicas
                titulo_tag = soup.find("h1")
                titulo = titulo_tag.get_text(strip=True) if titulo_tag else ""
                descripcion = extraer_descripcion_estable(soup)
                precio = extraer_precio(soup)
                vendedor, link_vendedor = extraer_vendedor(soup)

                # Descargar imagen de portada
                nombre_imagen = descargar_imagen_portada(soup, ciudad, id_publicacion)

                # Preparar datos
                datos = {
                    "id": id_publicacion,
                    "link": full_url,
                    "titulo": titulo,
                    "precio": precio,
                    "ciudad": ciudad,
                    "vendedor": vendedor,
                    "link_vendedor": link_vendedor,
                    "description": descripcion,
                    "imagen_portada": nombre_imagen
                }

                # Guardar HTML, JSON e imagen
                guardar_html_y_json(html, datos, ciudad, id_publicacion)
                success_count += 1
            except Exception as e:
                error_count += 1
                print(f"❌ Error en {id_publicacion}: {e}")
                with open("errores_extraccion_html.log", "a", encoding="utf-8") as log:
                    log.write(f"{id_publicacion} - {e}\n")
            finally:
                # Actualizar barra de progreso
                pbar.set_postfix({"procesadas": pbar.n + 1, "ok": success_count, "err": error_count})
                pbar.update(1)

        pbar.close()
        browser.close()

if __name__ == "__main__":
    main()
