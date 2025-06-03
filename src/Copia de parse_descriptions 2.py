#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_descriptions.py

Script con canalizacion de extraccion:
1) regex
2) GPT-3.5
3) GPT-4

Funciona importando process_item sin ejecutar parse_args.
"""

import os
import time
import json
import re
import hashlib
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import openai

# Configurar logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ---------- Métricas y cache ----------

def record_metric(pid: str, dur: float, toks: int, ok: bool, metrics_file: Path):
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
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------- LLM call con cache y fallback ----------

def make_cache_key(model: str, fields: list, text: str) -> str:
    return f"{model}_{hash_text(text)}_{'_'.join(fields)}"

def call_llm(model: str, fields: list, text: str, pid: str,
             cache35_dir: Path, cache4_dir: Path, metrics_file: Path):
    cache_dir = cache35_dir if "3.5" in model else cache4_dir
    cache_dir.mkdir(exist_ok=True)
    key = make_cache_key(model, fields, text)
    cache_path = cache_dir / f"{key}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))

    start = time.time()
    result = {}
    try:
        if "4" in model:
            functions = [{
                "name": "extraer",
                "description": "Extrae campos inmobiliarios",
                "parameters": {
                    "type": "object",
                    "properties": {f: {"type": "string"} for f in fields}
                }
            }]
            resp = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Extrae solo JSON."},
                    {"role": "user",   "content": text}
                ],
                functions=functions,
                function_call="auto",
                temperature=0,
                max_tokens=200
            )
            msg = resp.choices[0].message
            args = msg.function_call.arguments if msg.get("function_call") else "{}"
            result = json.loads(args)
        else:
            resp = openai.ChatCompletion.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Extrae solo JSON."},
                    {"role": "user",   "content": text}
                ],
                temperature=0,
                max_tokens=150
            )
            try:
                result = json.loads(resp.choices[0].message.content)
            except json.JSONDecodeError:
                result = {}
        toks = getattr(resp.usage, "total_tokens", 0)
        record_metric(pid, time.time() - start, toks, bool(result), metrics_file)
    except Exception as e:
        logger.warning(f"LLM {model} fallo ID {pid}: {e}")
        record_metric(pid, 0, 0, False, metrics_file)

    cache_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return result

# ---------- Regex de extracción ----------

def extract_numeric(txt: str):
    out = {}
    patterns = {
        "recamaras": [r"(\d+)\s*rec(?:á|a)maras?", r"rec(?:á|a)maras?[:\s]*(\d+)"],
        "banos":     [r"(\d+)\s*baños?",             r"baños?[:\s]*(\d+)"],
        "niveles":   [r"(\d+)\s*niveles?",           r"niveles?[:\s]*(\d+)"]
    }
    for key, pats in patterns.items():
        val = None
        for pat in pats:
            m = re.search(pat, txt, re.IGNORECASE)
            if m:
                try:
                    val = int(m.group(1))
                except ValueError:
                    val = None
                break
        out[key] = val
    return out

def extract_dimensions(txt: str):
    out = {}
    dims = {
        "superficie_m2":   r"Superficie[:\s]*([0-9]+(?:[.,][0-9]+)?)",
        "construccion_m2": r"Construcci[oó]n[:\s]*([0-9]+(?:[.,][0-9]+)?)"
    }
    for key, pat in dims.items():
        m = re.search(pat, txt, re.IGNORECASE)
        if m:
            val = m.group(1).replace(",", ".")
            try:
                out[key] = float(val)
            except ValueError:
                out[key] = None
        else:
            out[key] = None
    return out

def extract_features(txt: str):
    feats = ["alberca", "piscina", "patio", "bodega", "terraza", "cisterna"]
    return {f: bool(re.search(rf"\b{f}\b", txt, re.IGNORECASE)) for f in feats}

def extract_extra_booleans(txt: str):
    out = {}
    out["apto_discapacitados"] = bool(re.search(r"silla de ruedas|discapacit", txt, re.IGNORECASE))
    out["escrituras"]          = bool(re.search(r"escritura", txt, re.IGNORECASE))
    out["cesion_derechos"]     = bool(re.search(r"cesi.n de derechos", txt, re.IGNORECASE))
    m = re.search(r"seguridad[:\s]*([^.\n]+)", txt, re.IGNORECASE)
    out["seguridad"]           = m.group(1).strip() if m else None
    m = re.search(r"(efectivo|transferencia|cr[eé]dito bancario|tarjeta)", txt, re.IGNORECASE)
    out["formas_de_pago"]      = m.group(1) if m else None
    m = re.search(r"\b(priv\.|fracc(?:\.|ionamiento)|condominio)\b", txt, re.IGNORECASE)
    out["tipo_de_condominio"]  = m.group(0) if m else None
    devs = re.findall(r"Fracc(?:\.|ionamiento)?\s+([A-Za-zÁÉÍÓÚáéíóúñÑ ]+)", txt)
    out["fraccionamiento"]     = devs[0].strip() if devs else None
    return out

# ---------- Extracción local de ubicación y tipo de propiedad ----------

def extract_location_fields(item: dict):
    loc = item.get("location") or item.get("ubicacion") or ""
    parts = [p.strip() for p in loc.split(",")]
    return {
        "colonia": parts[0] if len(parts) > 0 else None,
        "ciudad":  parts[1] if len(parts) > 1 else None,
        "estado":  parts[2] if len(parts) > 2 else None
    }

def extract_tipo_propiedad(title: str):
    m = re.search(r"\b(Casa|Departamento|Townhouse|PH|Oficina|Local)\b", title, re.IGNORECASE)
    return m.group(1) if m else None

# ---------- Procesar un ítem ----------

def process_item(item: dict):
    pid = item.get("id")
    op  = item.get("tipo_operacion")
    if not pid or op not in ("Venta", "Renta"):
        return None, False

    txt = item.get("descripcion_raw", "") or item.get("description", "")
    out = dict(item)

    out.update(extract_numeric(txt))
    out.update(extract_dimensions(txt))
    out.update(extract_features(txt))
    out.update(extract_extra_booleans(txt))
    out.update(extract_location_fields(item))

    tp = extract_tipo_propiedad(item.get("title", "") or item.get("titulo", ""))
    if tp:
        out["tipo_propiedad"] = tp

    # Sólo fallback para lo que regex NO extraiga: recamaras, banos, niveles
    keys = ["recamaras", "banos", "niveles"]
    missing = [k for k in keys if out.get(k) is None]
    cache_args = (Path("cache_ia35"), Path("cache_ia"), Path("resultados/metrics.csv"))

    for model in ("gpt-3.5-turbo", "gpt-4"):
        if not missing:
            break
        prompt = f"{txt}\nkeys: {','.join(missing)}"
        res = call_llm(model, missing, prompt, pid, *cache_args)
        for k in missing:
            if res.get(k):
                out[k] = res[k]
        missing = [k for k in missing if out.get(k) is None]

    # Precio desde el JSON
    try:
        rawp = item.get("price") or item.get("precio","")
        out["precio"] = float(str(rawp).replace("$","").replace(",",""))
    except:
        out["precio"] = None
    out["moneda"] = "MXN"

    return out, True

# ---------- MAIN CLI ----------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Parse descriptions with fallback regex->3.5->4")
    parser.add_argument("--input",      default="resultados/repositorio_limpio.json")
    parser.add_argument("--fallback",   default="resultados/repositorio_propiedades.json")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--workers",    type=int, default=5)
    parser.add_argument("--cache35-dir", default="cache_ia35")
    parser.add_argument("--cache4-dir",  default="cache_ia")
    parser.add_argument("--metrics",     default="resultados/metrics.csv")

    args = parser.parse_args()

    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        logger.error("Define OPENAI_API_KEY en entorno")
        exit(1)

    Path("resultados").mkdir(exist_ok=True)
    raw = load_json(Path(args.input)) or load_json(Path(args.fallback))
    items = list(raw.values()) if isinstance(raw, dict) else raw

    validos, invalidos = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process_item, i): i for i in items}
        for fut in as_completed(futures):
            res, ok = fut.result()
            (validos if ok else invalidos).append(res if ok else futures[fut])

    save_json(Path("resultados/repositorio_validos.json"),   validos)
    save_json(Path("resultados/repositorio_invalidos.json"), invalidos)
    logger.info(f"Procesados: válidos={len(validos)}, inválidos={len(invalidos)}")