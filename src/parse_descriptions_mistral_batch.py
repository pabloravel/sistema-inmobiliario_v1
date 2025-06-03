import os
import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from tqdm import tqdm

# ======== OPTIMIZA USO DE CPU ==========
num_cores = os.cpu_count()
torch.set_num_threads(num_cores)
torch.set_num_interop_threads(num_cores)
os.environ["OMP_NUM_THREADS"] = str(num_cores)
os.environ["MKL_NUM_THREADS"] = str(num_cores)
print(f"Usando {num_cores} núcleos de CPU para procesamiento.")

# ======== CONFIGURACIÓN DE ARCHIVOS Y MODELO ==========
REPO_PATH = "/Users/pabloravel/Proyectos/facebook_scraper/resultados/repositorio_propiedades.json"
OUTPUT_PATH = "resultados_propiedades_ia_batch.json"
MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.3"
DEVICE = "cpu"  # SOLO CPU

BATCH_SIZE = 3  # Cambia este número para procesar lotes más grandes

# ======== PROMPT BASE ==========
BASE_PROMPT = """
Estructura la siguiente propiedad en formato JSON siguiendo el prompt estricto:

id: {id}
descripcion: {descripcion}

Devuelve solo el JSON estructurado, sin explicaciones ni texto extra.
"""

def cargar_propiedades(path):
    with open(path, "r", encoding="utf-8") as f:
        props = json.load(f)
    if isinstance(props, dict):
        props = list(props.values())
    return props

def call_ia_batch(model, tokenizer, batch, base_prompt, device="cpu", max_new_tokens=512):
    prompts = []
    for prop in batch:
        prompts.append(
            base_prompt.format(
                id=prop.get("id", ""),
                descripcion=prop.get("descripcion", "")
            )
        )
    inputs = tokenizer(prompts, return_tensors="pt", padding=True, truncation=True).to(device)
    outputs = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=True, temperature=0.2)
    decoded_outputs = tokenizer.batch_decode(outputs, skip_special_tokens=True)
    return decoded_outputs

def main():
    print("\n--- INICIANDO PROCESO ---")
    print(f"Verificando archivo de entrada: {REPO_PATH}")
    if not os.path.exists(REPO_PATH):
        print(f"❌ Archivo no encontrado: {REPO_PATH}")
        return

    propiedades = cargar_propiedades(REPO_PATH)
    print(f"Propiedades encontradas: {len(propiedades)}")

    print("Cargando modelo...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, torch_dtype=torch.float32, device_map={"": "cpu"})
    print("Modelo cargado en CPU.\n")

    print(f"Procesando propiedades en lotes de {BATCH_SIZE}...\n")
    resultados = []

    for i in tqdm(range(0, len(propiedades), BATCH_SIZE), desc="Procesando propiedades"):
        batch = propiedades[i:i+BATCH_SIZE]
        print(f"\nProcesando batch {i//BATCH_SIZE + 1} (propiedades {i+1}-{min(i+BATCH_SIZE, len(propiedades))})...")

        try:
            outs = call_ia_batch(model, tokenizer, batch, BASE_PROMPT, device=DEVICE)
            for out in outs:
                # Intentar extraer el JSON (simple y robusto)
                json_start = out.find('{')
                json_end = out.rfind('}')
                if json_start != -1 and json_end != -1 and json_end > json_start:
                    try:
                        j = json.loads(out[json_start:json_end+1])
                        resultados.append(j)
                    except Exception as e:
                        print(f"⚠️  No se pudo parsear JSON: {e}\n--- Respuesta cruda ---\n{out}\n---")
                else:
                    print(f"⚠️  No se encontró bloque JSON en la respuesta:\n{out}\n---")
        except Exception as e:
            print(f"❌ Error al procesar el batch: {e}")

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"\nResultados guardados en {OUTPUT_PATH}")

if __name__ == "__main__":
    main()