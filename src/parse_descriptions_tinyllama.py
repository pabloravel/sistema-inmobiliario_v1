import json
import os
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from tqdm import tqdm

# === CONFIGURACIÓN ===
# Ruta al archivo de propiedades a procesar
INPUT_PATH = '/Users/pabloravel/Proyectos/facebook_scraper/resultados/repositorio_propiedades.json'
OUTPUT_PATH = 'resultados_propiedades_ia.json'
MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.3"
BATCH_SIZE = 3   # Cambia aquí el tamaño del lote

# Prompt base (puedes ajustarlo más si necesitas)
BASE_PROMPT = """
Extrae la información de la siguiente descripción de propiedad y devuélvela en un JSON estructurado usando **solo** estos campos (usa null si no hay información literal y nunca inventes datos):

{
  "id": (usa el id que te proporciono),
  "descripcion": (toda la descripción original, sin cambios),
  "colonia": (solo si se menciona explícitamente colonia, fraccionamiento o zona, sin inventar),
  "ubicacion": (solo si es una ubicación concreta como calle, avenida, referencia, etc.),
  "estado": (ej: "Morelos", si está explícito),
  "ciudad": (ej: "Cuernavaca", si está explícito),
  "tipo_propiedad": (ej: "casa sola", "departamento", "terreno", "local", extraído textual),
  "precio": (extrae el precio más relevante. Si hay varios precios, toma el de la venta/renta, sin comas ni puntos decimales. Ej: $1,800,000 → 1800000. Si hay "precio por m2", ignora y toma solo el total. Si es cesión de derechos, extrae ese precio. Si solo hay renta mensual, extrae ese precio. Si no hay, pon null),
  "tipo_operacion": ("Venta", "Renta", "Cesión de derechos" o "Desconocido", según corresponda y textual),
  "moneda": ("MXN" si es México y no se menciona otra, o extrae si dice "USD", "Dólares", etc.),
  "recamaras": (número de recámaras, si lo menciona explícito),
  "baños": (número de baños completos, si lo menciona explícito; medios baños no los cuentes),
  "niveles": (número de pisos o plantas, si lo menciona explícito),
  "superficie_m2": (m2 de terreno, si viene textual, solo el número, sin texto extra),
  "construccion_m2": (m2 de construcción, si viene textual, solo el número, sin texto extra),
  "cisterna": (true si menciona cisterna/tinaco; false si dice que no tiene; null si no se menciona),
  "alberca": (true si tiene alberca; false si no; null si no se menciona),
  "jardin": (true si tiene jardín; false si no; null si no se menciona),
  "terraza": (true si tiene terraza; false si no; null si no se menciona),
  "escrituras": (true si dice que está escriturada/libre de gravamen; false si dice que no; null si no se menciona),
  "cesion_derechos": (true si la operación es "cesión de derechos"; false si no; null si no se menciona),
  "formas_de_pago": (si menciona créditos, Infonavit, Fovissste, lista las opciones como array de string; null si no se menciona)
}

**Notas para IA**:
- No repitas la descripción en otros campos.
- No incluyas información no textual.
- Si un campo tiene varias opciones, elige la más relevante para la venta/renta total.
- Si el precio es confuso o está en un rango, elige el más bajo.
- No inventes valores si no están claros.
- Devuelve solo el JSON y nada más.

Descripción de la propiedad:
ID: {id}
{descripcion}
"""

def load_props(path, max_count=None):
    with open(path, 'r', encoding='utf-8') as f:
        props = json.load(f)
    if max_count is not None:
        return props[:max_count]
    return props

def call_mistral(model, tokenizer, prompt):
    pipe = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        device="cpu",  # Cambia a "cuda" si tienes GPU disponible
        max_new_tokens=800,
        do_sample=True,
        temperature=0.1,
        pad_token_id=tokenizer.eos_token_id,
    )
    res = pipe(prompt, num_return_sequences=1)[0]['generated_text']
    # Buscar JSON en la respuesta
    start = res.find('{')
    end = res.rfind('}') + 1
    if start >= 0 and end > start:
        raw_json = res[start:end]
        try:
            data = json.loads(raw_json)
            return data
        except Exception as e:
            print("⚠️  No se pudo parsear JSON:", e)
            print("=== Salida LLM ===\n", res, "\n==================\n")
            return None
    else:
        print("⚠️  No se encontró JSON en respuesta")
        print("=== Salida LLM ===\n", res, "\n==================\n")
        return None

def main():
    print("Cargando modelo...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(MODEL_ID, trust_remote_code=True)
    print(f"Procesando propiedades en lotes de {BATCH_SIZE}...")

    propiedades = load_props(INPUT_PATH)  # Quita max_count para todas, ponlo si quieres pocas

    resultados = []
    for i in tqdm(range(0, len(propiedades), BATCH_SIZE), desc="Procesando propiedades"):
        batch = propiedades[i:i+BATCH_SIZE]
        for prop in batch:
            prompt = BASE_PROMPT.format(id=prop.get("id", ""), descripcion=prop.get("descripcion", ""))
            res = call_mistral(model, tokenizer, prompt)
            if res:
                resultados.append(res)
            else:
                print(f"❌ Falló la propiedad {prop.get('id', '')}")

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    print(f"Resultados guardados en {OUTPUT_PATH}")

if __name__ == "__main__":
    main()