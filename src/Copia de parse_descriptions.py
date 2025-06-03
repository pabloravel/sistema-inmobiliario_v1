#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_descriptions.py

VERSIÓN FINAL AJUSTADA:
- Fallback completo: regex → GPT-3.5 → GPT-4.
- Filtrado inicial de publicaciones no inmobiliarias (solo Venta/Renta).
- Extracción local de recámaras, baños, niveles, dimensiones y amenidades.
- Extracción de precio desde `price` en JSON.
- Preservación total de campos originales en salida válida.
- Clasificación en `repositorio_validos.json` y `repositorio_invalidos.json`.
- Cache de LLM, manejo de errores de cuota y métricas.
"""
import os, time, json, re, hashlib, logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import openai

# -------- CLI y rutas --------
parser = argparse.ArgumentParser(description='Parsear descripciones con fallback regex → 3.5 → 4')
parser.add_argument('--input',       default='resultados/repositorio_limpio.json', help='JSON limpio de entrada')
parser.add_argument('--fallback',    default='resultados/repositorio_propiedades.json', help='JSON completo fallback')
parser.add_argument('--batch-size',  type=int, default=50,   help='Número de ítems por lote')
parser.add_argument('--workers',     type=int, default=5,    help='Número de hilos')
parser.add_argument('--cache35-dir', default='cache_ia35',  help='Directorio cache GPT-3.5')
parser.add_argument('--cache4-dir',  default='cache_ia',    help='Directorio cache GPT-4')
parser.add_argument('--metrics',     default='resultados/metrics.csv', help='Archivo métricas tokens/tiempo')
args = parser.parse_args()

input_path    = Path(args.input)
fallback_path = Path(args.fallback)
batch_size    = args.batch_size
workers       = args.workers
cache35_dir   = Path(args.cache35_dir)
cache4_dir    = Path(args.cache4_dir)
metrics_file  = Path(args.metrics)
result_dir    = Path('resultados')
output_valid   = result_dir / 'repositorio_validos.json'
output_invalid = result_dir / 'repositorio_invalidos.json'
result_dir.mkdir(exist_ok=True)

# -------- Logging --------
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger()

# -------- OpenAI Key --------
openai.api_key = os.getenv('OPENAI_API_KEY')
if not openai.api_key:
    logger.error('Define OPENAI_API_KEY en el entorno')

# -------- Métricas --------
def record_metric(pid, dur, toks, ok):
    header = not metrics_file.exists()
    with open(metrics_file, 'a', encoding='utf-8') as f:
        if header:
            f.write('id,time_s,tokens,valido\n')
        f.write(f"{pid},{dur:.2f},{toks},{int(ok)}\n")

# -------- Helpers --------
def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() and path.stat().st_size>0 else []

# -------- LLM Call con cache --------
def call_llm(model: str, fields: list, text: str, pid: str):
    cache_dir = cache35_dir if '3.5' in model else cache4_dir
    cache_dir.mkdir(exist_ok=True)
    key = f"{model}_{hash_text(text)}_{'_'.join(fields)}"
    cache_path = cache_dir / f"{key}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding='utf-8'))
    start = time.time()
    try:
        if 'gpt-4' in model:
            functions=[{
                'name':'extraer', 'description':'Extrae campos inmobiliarios',
                'parameters':{'type':'object','properties':{f:{'type':'string'} for f in fields}}
            }]
            resp = openai.ChatCompletion.create(
                model=model, messages=[{'role':'system','content':'Extrae sólo JSON.'},{'role':'user','content':text}],
                functions=functions, function_call='auto', temperature=0, max_tokens=200
            )
            msg = resp.choices[0].message
            args = msg.function_call.arguments if msg.get('function_call') else '{}'
            result = json.loads(args)
        else:
            resp = openai.ChatCompletion.create(
                model=model, messages=[{'role':'system','content':'Extrae sólo JSON.'},{'role':'user','content':text}],
                temperature=0, max_tokens=150
            )
            try:
                result = json.loads(resp.choices[0].message.content)
            except:
                result = {}
        toks = getattr(resp.usage,'total_tokens',0)
        record_metric(pid, time.time()-start, toks, bool(result))
    except Exception as e:
        logger.warning(f"LLM {model} falló ID {pid}: {e}")
        result = {}
        record_metric(pid, 0, 0, False)
    cache_path.write_text(json.dumps(result, ensure_ascii=False), encoding='utf-8')
    return result

# -------- Regex locales --------
def extract_numeric(txt: str):
    out={}
    m=re.search(r"(\d+)\s*rec(?:á|a)maras?",txt, re.I)
    out['recamaras']=int(m.group(1)) if m else None
    m=re.search(r"(\d+)\s*baños?",txt, re.I)
    out['banos']=int(m.group(1)) if m else None
    m=re.search(r"(\d+)\s*niveles?",txt, re.I)
    out['niveles']=int(m.group(1)) if m else None
    return out

def extract_dimensions(txt: str):
    out={}; areas={'superficie_m2':r'Superficie[:\s]*([\d\.,]+)','construccion_m2':r'Construcci[oó]n[:\s]*([\d\.,]+)'}
    for k,p in areas.items():
        m=re.search(p,txt, re.I)
        out[k]=float(m.group(1).replace(',','')) if m else None
    return out

def extract_features(txt: str):
    feats=['alberca','patio','bodega','terraza','cisterna']
    return {f:bool(re.search(rf"\b{f}\b",txt,re.I)) for f in feats}

# -------- Procesamiento de ítem --------
def process_item(item: dict):
    pid=item.get('id'); op=item.get('tipo_operacion')
    # Filtrar solo Venta/Renta
    if not pid or op not in ('Venta','Renta'):
        return None, False
    txt=item.get('descripcion_raw','')
    # Partimos del objeto original para preservarlo
    out = dict(item)
    # 1) regex local
    out.update(extract_numeric(txt))
    out.update(extract_dimensions(txt))
    out.update(extract_features(txt))
    # 2) fallback GPT-3.5
    missing=[k for k in ['colonia','ciudad','estado','tipo_propiedad','recamaras','banos','niveles'] if out.get(k) is None]
    base_text=f"{txt}\nkeys: {','.join(missing)}"
    if missing:
        res35=call_llm('gpt-3.5-turbo', missing, base_text, pid)
        for k in missing:
            if res35.get(k): out[k]=res35[k]
        missing=[k for k in missing if out.get(k) is None]
    # 3) fallback GPT-4
    if missing:
        res4=call_llm('gpt-4', missing, base_text, pid)
        for k in missing:
            if res4.get(k): out[k]=res4[k]
    # Precio directo del JSON
    price_raw=item.get('price')
    try: out['precio']=float(str(price_raw).replace('$','').replace(',',''))
    except: out['precio']=None
    out['moneda']='MXN'
    return out, True

# -------- MAIN --------
if __name__=='__main__':
    raw = load_json(input_path)
    if not raw:
        logger.warning(f"Input vacío; fallback {fallback_path}")
        raw = load_json(fallback_path)
    items = list(raw.values()) if isinstance(raw, dict) else raw
    validos, invalidos = [], []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(process_item, i): i for i in items}
        for fut in as_completed(futures):
            res, ok = fut.result()
            if ok: validos.append(res)
            else: invalidos.append(futures[fut])
    save_json(output_valid, validos)
    save_json(output_invalid, invalidos)
    logger.info(f"Procesados: válidos={len(validos)}, inválidos={len(invalidos)}")