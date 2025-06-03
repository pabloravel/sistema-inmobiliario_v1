#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_descriptions.py

Script de extracción prioritaria de campos desde description_raw:
1. precio      (desde JSON 'price')
2. ciudad      (regex en description_raw)
3. tipo_operacion (regex en description_raw)
4. tipo_propiedad (regex en description_raw)
5. un_nivel    (niveles == 1 desde description_raw)
6. recamara_en_pb (regex en description_raw, planta baja)
7. amenidades  (lista de amenities desde description_raw)

Se mantienen extras (dimensiones, features booleanos) y fallback GPT-3.5
SOLO para recamaras/banos/niveles si falla regex.

Carga automática de clave OpenAI desde entorno o api_key.txt.
"""
import os
import time
import json
import re
import hashlib
import logging
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import openai

# ——————————————————————————————————————————————————————————————————————————
# Configuración de rutas
BASE_DIR     = Path(__file__).resolve().parent
RESULTS_DIR  = BASE_DIR / "resultados"
CACHE35_DIR  = BASE_DIR / "cache_ia35"
METRICS_FILE = RESULTS_DIR / "metrics.csv"
INPUT_DEFAULT= RESULTS_DIR / "repositorio_propiedades.json"
API_KEY_FILE = BASE_DIR / "api_key.txt"
# ——————————————————————————————————————————————————————————————————————————

# Logger global
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ——— Utilidades genéricas ———
def record_metric(pid: str, dur: float, toks: int, ok: bool, metrics_file: Path):
    metrics_file.parent.mkdir(exist_ok=True)
    header = not metrics_file.exists()
    with metrics_file.open("a", encoding="utf-8") as f:
        if header:
            f.write("id,time_s,tokens,valido\n")
        f.write(f"{pid},{dur:.2f},{toks},{int(ok)}\n")

def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def load_json(path: Path):
    if path.exists() and path.stat().st_size > 0:
        return json.loads(path.read_text(encoding="utf-8"))
    return []

def save_json(path: Path, data):
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# ——— LLM fallback GPT-3.5 ———
def make_cache_key(model: str, fields: list, text: str) -> str:
    return f"{model}_{hash_text(text)}_{'_'.join(fields)}"

def call_llm(model: str, fields: list, text: str, pid: str,
             cache35_dir: Path, metrics_file: Path):
    cache35_dir.mkdir(exist_ok=True)
    key = make_cache_key(model, fields, text)
    cache_path = cache35_dir / f"{key}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    start = time.time()
    result = {}
    try:
        resp = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "Extrae solo JSON."},
                {"role": "user",   "content": text}
            ],
            temperature=0, max_tokens=150
        )
        content = resp.choices[0].message.content
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            result = {}
        toks = getattr(resp.usage, "total_tokens", 0)
        record_metric(pid, time.time() - start, toks, bool(result), metrics_file)
    except Exception as e:
        logger.warning(f"LLM {model} fallo ID {pid}: {e}")
        record_metric(pid, 0, 0, False, metrics_file)

    cache_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result

# ——— Extracción por regex desde description_raw ———
def extract_numeric(txt: str):
    out = {}
    patterns = {"recamaras": [r"(\d+)\s*rec(?:á|a)maras?"],
                "banos":     [r"(\d+)\s*baños?"],
                "niveles":   [r"(\d+)\s*niveles?"]}
    for key, pats in patterns.items():
        val = None
        for pat in pats:
            m = re.search(pat, txt, re.IGNORECASE)
            if m:
                try: val = int(m.group(1))
                except: val = None
                break
        out[key] = val
    return out

def extract_dimensions(txt: str):
    out = {}
    dims = {"superficie_m2":   r"Superficie[:\s]*([0-9]+(?:[.,][0-9]+)?)",
            "construccion_m2": r"Construcci[oó]n[:\s]*([0-9]+(?:[.,][0-9]+)?)"}
    for key, pat in dims.items():
        m = re.search(pat, txt, re.IGNORECASE)
        if m:
            val = m.group(1).replace(",", ".")
            try: out[key] = float(val)
            except: out[key] = None
        else:
            out[key] = None
    return out

def extract_features(txt: str):
    feats = ["alberca","piscina","patio","bodega","terraza","cisterna"]
    return {f: bool(re.search(rf"\b{f}\b", txt, re.IGNORECASE)) for f in feats}

def extract_recamara_pb(txt: str):
    m = re.search(r"PLANTA BAJA[\s\S]*?(\d+)\s*rec(?:á|a)maras?", txt, re.IGNORECASE)
    return int(m.group(1)) if m else None

def extract_city(txt: str):
    m = re.search(r"ciudad[:\s]*([A-Za-zÁÉÍÓÚáéíóúñÑ ]+)", txt, re.IGNORECASE)
    return m.group(1).strip() if m else None

def extract_operation(txt: str):
    m = re.search(r"\b(Venta|Renta)\b", txt, re.IGNORECASE)
    return m.group(1).capitalize() if m else None

def extract_propiedad(txt: str):
    m = re.search(r"\b(Casa|Departamento|Townhouse|PH|Oficina|Local)\b", txt, re.IGNORECASE)
    return m.group(1) if m else None

# ——— Procesar un ítem ———
def process_item(item: dict):
    pid = item.get("id")
    txt = item.get("descripcion_raw","") or item.get("description","")
    if not pid: return None, False
    out = {}
    # 1. precio directo del JSON
    out["precio"] = item.get("price")
    out["moneda"] = "MXN"
    # 2. ciudad
    out["ciudad"] = extract_city(txt)
    # 3. tipo_operacion
    out["tipo_operacion"] = extract_operation(txt)
    # 4. tipo_propiedad
    out["tipo_propiedad"] = extract_propiedad(txt)
    # 5. un_nivel
    nums = extract_numeric(txt)
    out.update(nums)
    out["un_nivel"] = (out.get("niveles")==1)
    # 6. recamara_en_pb
    out["recamara_en_pb"] = extract_recamara_pb(txt)
    # 7. amenidades
    feats = extract_features(txt)
    out["amenidades"] = [f for f, ok in feats.items() if ok]
    # extras
    out.update(extract_dimensions(txt))
    # fallback GPT-3.5 numéricos
    missing = [k for k in ["recamaras","banos","niveles"] if out.get(k) is None]
    if missing:
        prompt = f"{txt}\nkeys: {','.join(missing)}"
        res = call_llm("gpt-3.5-turbo", missing, prompt, pid, CACHE35_DIR, METRICS_FILE)
        for k in missing:
            if res.get(k) is not None: out[k] = res[k]
        out["un_nivel"] = (out.get("niveles")==1)
    return out, True

# ——— MAIN CLI ———
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse descripciones priorizando campos clave")
    parser.add_argument("--input", default=str(INPUT_DEFAULT))
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--cache35-dir", default=str(CACHE35_DIR))
    parser.add_argument("--metrics", default=str(METRICS_FILE))
    args = parser.parse_args()
    # Carga de API key
    key = os.getenv("OPENAI_API_KEY")
    if not key and API_KEY_FILE.exists():
        key = API_KEY_FILE.read_text().strip()
    openai.api_key = key
    if not openai.api_key:
        logger.error("Define OPENAI_API_KEY en entorno o en api_key.txt")
        exit(1)
    RESULTS_DIR.mkdir(exist_ok=True)
    raw = load_json(Path(args.input))
    items = list(raw.values()) if isinstance(raw, dict) else raw
    items = items[:args.batch_size]
    logger.info(f"A procesar: {len(items)} propiedades")
    validos, invalidos = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process_item, i): i for i in items}
        for fut in as_completed(futures):
            res, ok = fut.result()
            (validos if ok else invalidos).append(res if ok else futures[fut])
    save_json(RESULTS_DIR / "repositorio_validos.json", validos)
    save_json(RESULTS_DIR / "repositorio_invalidos.json", invalidos)
    logger.info(f"Procesados: válidos={len(validos)}, inválidos={len(invalidos)}")
