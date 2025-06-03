import os
import json
import requests
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# Barra de progreso personalizada estilo tqdm en magenta, mostrando faltantes y tiempo por extracción
class ProgressBar:
    MAGENTA = "\033[35m"
    RESET = "\033[0m"

    def __init__(self, total, desc='', unit=''):
        self.total = total
        self.n = 0
        self.ok = 0
        self.err = 0
        self.last_time = 0.0
        self.desc = desc
        self.unit = unit
        self.length = 40
        self.start_time = time.time()
        self._print()

    def _print(self):
        filled = int(self.length * self.n / self.total) if self.total else self.length
        bar = '█' * filled + '-' * (self.length - filled)
        percent = (self.n / self.total * 100) if self.total else 100
        faltan = self.total - self.n
        print(
            f"\r{self.desc}: {percent:3.0f}%|"
            f"{self.MAGENTA}{bar}{self.RESET}| "
            f"{self.n}/{self.total}  Faltan: {faltan} de {self.total}  "
            f"[procesadas={self.n}, ok={self.ok}, err={self.err}, t={self.last_time:.2f}s]",
            end='', flush=True
        )

    def update(self, n=1, ok=None, err=None, last_time=None):
        self.n += n
        if ok is not None: self.ok = ok
        if err is not None: self.err = err
        if last_time is not None: self.last_time = last_time
        self._print()

    def close(self):
        print()

# Rutas de configuración
CARPETA_LINKS = "resultados/links/repositorio_unico.json"
CARPETA_RESULTADOS = "resultados"
CARPETA_REPO_MASTER = os.path.join(CARPETA_RESULTADOS, "repositorio_propiedades.json")
ESTADO_FB = "fb_state.json"
BASE_URL = "https://www.facebook.com"

# 1) Cargar repositorio maestro de propiedades
data_master = {}
if os.path.exists(CARPETA_REPO_MASTER):
    with open(CARPETA_REPO_MASTER, "r", encoding="utf-8") as f:
        data_master = json.load(f)
existing_ids = set(data_master.keys())

# 2) Cargar y normalizar enlaces desde repositorio_unico
with open(CARPETA_LINKS, "r", encoding="utf-8") as f:
    raw_links = json.load(f)
links = []
for item in raw_links:
    if isinstance(item, str):
        href = BASE_URL + item if item.startswith("/") else item
        city = "cuernavaca"
    elif isinstance(item, dict):
        href = item.get("link", "")
        href = BASE_URL + href if href.startswith("/") else href
        city = item.get("ciudad", "cuernavaca").lower()
    else:
        continue
    if not href.startswith(BASE_URL):
        continue
    pid = href.rstrip("/").split("/")[-1]
    links.append({"link": href, "id": pid, "ciudad": city})

# 3) Filtrar solo links pendientes
pending_links = [l for l in links if l["id"] not in existing_ids]

# 4) Preparar carpeta de resultados diaria
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

# 5) Descargar portada usando Playwright
def descargar_imagen_por_playwright(page, ciudad, pid):
    try:
        src = page.locator('img[alt^="Foto de"]').first.get_attribute('src')
    except:
        try:
            src = page.locator('img').first.get_attribute('src')
        except:
            return ""
    if not src or not src.startswith("http"):
        return ""
    filename = f"{ciudad}-{date_str}-{pid}.jpg"
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

# 6) Guardar HTML y JSON
def guardar_html_y_json(html, datos, ciudad, pid):
    base = f"{ciudad}-{date_str}-{pid}"
    ruta_html = os.path.join(carpeta_destino, base + ".html")
    ruta_json = os.path.join(carpeta_destino, base + ".json")
    with open(ruta_html, "w", encoding="utf-8") as f:
        f.write(html)
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)

# 7) Ejecución principal
def main():
    # Mostrar cantidad de HTMLs ya en repositorio maestro
    print(f"Propiedades ya procesadas: {len(existing_ids)}")
    total = len(pending_links)
    success_count = 0
    error_count = 0
    pbar = ProgressBar(total, desc="Extrayendo propiedades", unit="propiedad")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=ESTADO_FB)
        page = context.new_page()

        for item in pending_links:
            pid = item["id"]
            url = item["link"]
            ciudad = item["ciudad"]
            start_time = time.time()
            try:
                page.goto(url, timeout=60000)
                page.wait_for_timeout(3000)

                # Expandir descripción "Ver más" si existe
                try:
                    vm = page.locator("text=Ver más").first
                    if vm.is_visible():
                        vm.click()
                        page.wait_for_timeout(1000)
                except:
                    pass

                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # Extracciones
                titulo = soup.find("h1").get_text(strip=True) if soup.find("h1") else ""
                descripcion = extraer_descripcion_estable(soup)
                precio = extraer_precio(soup)
                vendedor, link_vendedor = extraer_vendedor(soup)
                imagen_portada = descargar_imagen_por_playwright(page, ciudad, pid)

                datos = {
                    "id": pid,
                    "link": url,
                    "titulo": titulo,
                    "precio": precio,
                    "ciudad": ciudad,
                    "vendedor": vendedor,
                    "link_vendedor": link_vendedor,
                    "descripcion": descripcion,
                    "imagen_portada": imagen_portada
                }

                guardar_html_y_json(html, datos, ciudad, pid)

                # Actualizar repositorio maestro
                data_master[pid] = datos
                with open(CARPETA_REPO_MASTER, "w", encoding="utf-8") as mf:
                    json.dump(data_master, mf, ensure_ascii=False, indent=2)

                success_time = time.time() - start_time
                success_count += 1
            except Exception as e:
                success_time = time.time() - start_time
                error_count += 1
                print(f"❌ Error en {pid}: {e}")
                with open("errores_extraccion_html.log", "a", encoding="utf-8") as log:
                    log.write(f"{pid} - {e}\n")
            finally:
                pbar.update(1, ok=success_count, err=error_count, last_time=success_time)

        pbar.close()
        browser.close()
        # Imprimir total de propiedades en el repositorio maestro
        print(f"\nTotal de propiedades en el repositorio maestro: {len(data_master)}")

if __name__ == "__main__":
    main()
