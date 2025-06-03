#!/usr/bin/env python3
# extraccion_datos_encabezado.py

import os, sys, json, re, requests, time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup

# —————— CONFIG ——————
LINKS_FILE      = "resultados/links/repositorio_unico.json"
MASTER_REPO     = "resultados/repositorio_propiedades.json"
OUTPUT_DIR_ROOT = "resultados"
FB_STATE        = "fb_state.json"
BASE_URL        = "https://www.facebook.com"

def parse_price_location_from_og(desc: str):
    parts = [p.strip() for p in desc.split("·", 1)]
    return (parts[0] if parts else "", parts[1] if len(parts)>1 else "")

class ProgressBar:
    MAGENTA = "\033[35m"; RESET = "\033[0m"
    def __init__(self, total, desc=''):
        self.total=total; self.n=0; self.ok=0; self.err=0; self.last=0; self.desc=desc
    def update(self, **k):
        self.n=k.get('n',self.n+1); self.ok=k.get('ok',self.ok); self.err=k.get('err',self.err)
        self.last=k.get('last',self.last)
        pct=int(self.n/self.total*100)
        bar='█'*(pct//2)+'-'*(50-pct//2)
        print(f"\r{self.MAGENTA}{self.desc}:{self.RESET} {pct}%|{bar}| "
              f"{self.n}/{self.total} faltan {self.total-self.n} ok={self.ok} err={self.err} t={self.last:.1f}s",
              end='', flush=True)
    def close(self): print()

def main():
    # 1) Maestro
    repo = {}
    if os.path.exists(MASTER_REPO):
        with open(MASTER_REPO, encoding="utf-8") as f:
            repo = json.load(f)

    # 2) Links
    with open(LINKS_FILE, encoding="utf-8") as f:
        raw = json.load(f)
    pendientes = []
    for href in raw:
        url = BASE_URL+href if href.startswith("/") else href
        pid = url.rstrip("/").split("/")[-1]
        if pid not in repo:
            pendientes.append((pid, url))

    total = len(pendientes)
    if total == 0:
        print("No hay enlaces nuevos.")
        return

    # 3) Carpeta salida
    fecha = datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join(OUTPUT_DIR_ROOT, fecha)
    os.makedirs(out_dir, exist_ok=True)

    pbar = ProgressBar(total, desc="Extrayendo encabezados")
    start_all = time.time()

    # 4) Playwright con sesión
    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=False)
    context = browser.new_context(storage_state=FB_STATE)

    ok = err = 0
    for pid, url in pendientes:
        t0 = time.time()
        try:
            page = context.new_page()
            # esperamos solo al DOMContentLoaded
            page.goto(url, wait_until="domcontentloaded", timeout=15000)

            # -> extraemos el HTML completo
            html = page.content()
            soup = BeautifulSoup(html, "html.parser")

            # —— Open Graph meta tags ——
            meta_title = soup.find("meta", property="og:title")
            title_og   = meta_title["content"] if meta_title and meta_title.has_attr("content") else ""
            meta_desc  = soup.find("meta", property="og:description")
            desc_og    = meta_desc["content"] if meta_desc and meta_desc.has_attr("content") else ""
            precio, ubicacion = parse_price_location_from_og(desc_og)

            # —— Fallback si OG faltó ——
            if not title_og:
                h1 = soup.find("h1")
                title_og = h1.get_text(strip=True) if h1 else ""
            if not desc_og:
                sp = soup.find("span", string=lambda t: t and "$" in t)
                precio = sp.get_text(strip=True) if sp else ""
                loc = soup.find(string=re.compile(r"·|\s—|\s–"))
                ubicacion = loc.strip("·–— ") if loc else ""

            page.close()

            # —— Guardar JSON individual ——
            record = {
                "id": pid,
                "link": url,
                "titulo": title_og,
                "precio": precio,
                "ubicacion": ubicacion
            }
            with open(os.path.join(out_dir, f"{pid}.json"), "w", encoding="utf-8") as jf:
                json.dump(record, jf, ensure_ascii=False, indent=2)

            repo[pid] = record
            ok += 1

        except Exception as e:
            err += 1
            print(f"\n❌ Error en {pid}: {e}")

        finally:
            pbar.update(n=ok+err, ok=ok, err=err, last=time.time()-t0)

    pbar.close()
    browser.close(); pw.stop()

    # 5) Guardar maestro
    with open(MASTER_REPO, "w", encoding="utf-8") as mf:
        json.dump(repo, mf, ensure_ascii=False, indent=2)

    print(f"\n→ Extraídos {ok}, errores {err}, tiempo total {time.time()-start_all:.1f}s")

if __name__ == "__main__":
    main()