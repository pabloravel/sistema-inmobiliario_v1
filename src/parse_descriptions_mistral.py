# parse_descriptions_mistral.py

import json
from transformers import AutoTokenizer, AutoModelForCausalLM
from tqdm import tqdm
import sys

# === CONFIGURACIÓN ===
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"
INPUT_JSON = "resultados/repositorio_propiedades.json"
OUTPUT_JSON = "resultados/repositorio_propiedades_mistral.json"
DEVICE = "cpu"

# Traducciones de campos para forzar español
traducciones = {
    "bedrooms": "recamaras",
    "bathrooms": "banos",
    "location": "colonia",
    "description": "descripcion",
    "price": "precio",
    "operation_type": "tipo_operacion",
    "property_type": "tipo_propiedad",
    "levels": "niveles",
    "surface_m2": "superficie_m2",
    "construction_m2": "construccion_m2",
    "cistern": "cisterna",
    "apto_discapacitados": "apto_discapacitados",
    "condo_type": "tipo_de_condominio",
    "fraccionamiento": "fraccionamiento",
    "age": "edad",
    "security": "seguridad",
    "pool": "alberca",
    "patio": "patio",
    "warehouse": "bodega",
    "terrace": "terraza",
    "garden": "jardin",
    "studio": "estudio",
    "roof_garden": "roof_garden",
    "deed": "escrituras",
    "cesion_derechos": "cesion_derechos",
    "payment_methods": "formas_de_pago",
    "currency": "moneda",
    "state": "estado",
    "city": "ciudad",
    "colony": "colonia",
    "tipo_operacion": "tipo_operacion"
}

# Lista final de campos
CAMPOS_ESPERADOS = [
    "colonia", "ciudad", "estado", "tipo_propiedad", "precio", "tipo_operacion", "moneda",
    "recamaras", "banos", "niveles", "superficie_m2", "construccion_m2", "cisterna",
    "apto_discapacitados", "tipo_de_condominio", "fraccionamiento", "edad", "seguridad",
    "alberca", "patio", "bodega", "terraza", "jardin", "estudio", "roof_garden",
    "escrituras", "cesion_derechos", "formas_de_pago"
]

# Prompt ultra detallado (ajústalo si quieres)
PROMPT_BASE = """
Eres una IA experta en extraer información inmobiliaria de descripciones de propiedades en México.
Extrae los siguientes campos SOLO de la descripción del inmueble, usando la lógica y la inferencia, y devuélvelos en formato JSON (campos en español, valor null si no existe):

{{
  "colonia": "",
  "ciudad": "",
  "estado": "",
  "tipo_propiedad": "",
  "precio": "",    // Usa el precio DIRECTO del repositorio, NO de la descripción
  "tipo_operacion": "",
  "moneda": "",
  "recamaras": "",
  "banos": "",
  "niveles": "",
  "superficie_m2": "",
  "construccion_m2": "",
  "cisterna": "",
  "apto_discapacitados": "",
  "tipo_de_condominio": "",
  "fraccionamiento": "",
  "edad": "",
  "seguridad": "",
  "alberca": "",
  "patio": "",
  "bodega": "",
  "terraza": "",
  "jardin": "",
  "estudio": "",
  "roof_garden": "",
  "escrituras": "",
  "cesion_derechos": "",
  "formas_de_pago": ""
}}

Ejemplo de entrada:
---
"Venta de casa en Colonia Centro, Cuernavaca, Morelos. $2,500,000. 3 recámaras, 2 baños completos, 2 niveles. Superficie: 150m2. Cuenta con jardín, alberca y cisterna. Escrituras en regla. Se aceptan créditos Infonavit."
---

Ejemplo de salida:
{{
  "colonia": "Centro",
  "ciudad": "Cuernavaca",
  "estado": "Morelos",
  "tipo_propiedad": "Casa",
  "precio": "",  // este valor será sustituido por el precio del repositorio
  "tipo_operacion": "Venta",
  "moneda": "MXN",
  "recamaras": 3,
  "banos": 2,
  "niveles": 2,
  "superficie_m2": 150,
  "construccion_m2": null,
  "cisterna": true,
  "apto_discapacitados": false,
  "tipo_de_condominio": null,
  "fraccionamiento": null,
  "edad": null,
  "seguridad": false,
  "alberca": true,
  "patio": true,
  "bodega": false,
  "terraza": true,
  "jardin": true,
  "estudio": false,
  "roof_garden": false,
  "escrituras": true,
  "cesion_derechos": false,
  "formas_de_pago": ["Infonavit"]
}}

Devuelve SOLO el JSON, sin explicaciones, y siempre usa los nombres de campos en español, nunca en inglés. Si no encuentras un dato, usa null.
"""

def cargar_modelo(device):
    print(f"🧠 Cargando modelo Mistral v0.3 en {device.upper()} (esto puede tardar unos minutos la primera vez)...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, device_map=device)
    return tokenizer, model

def construir_prompt(descripcion, precio_repositorio):
    prompt = PROMPT_BASE + "\nDESCRIPCIÓN:\n" + descripcion + "\n\nRecuerda: El campo 'precio' debe ser el del repositorio, no el de la descripción."
    return prompt

def llamar_mistral(tokenizer, model, prompt):
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2000)
    input_ids = inputs.input_ids.to(model.device)
    generated_ids = model.generate(input_ids, max_new_tokens=600, temperature=0.2, pad_token_id=tokenizer.eos_token_id)
    output = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
    # Tomar solo el bloque JSON
    try:
        inicio = output.index("{")
        fin = output.rindex("}") + 1
        json_str = output[inicio:fin]
        data = json.loads(json_str)
    except Exception as e:
        print(f"⚠️ Error al parsear salida de Mistral: {e}\nSalida:\n{output}")
        data = {}
    return data

def corregir_campos_ingles(resultado):
    for k_ing, k_esp in traducciones.items():
        if k_ing in resultado and k_esp not in resultado:
            resultado[k_esp] = resultado.pop(k_ing)
    return resultado

def main():
    # --- TEST MODE ---
    only_test = '--test' in sys.argv
    max_items = 20 if only_test else None

    print(f"📂 Cargando propiedades de: {INPUT_JSON}")
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        propiedades = json.load(f)

    # Manejo por diccionario (tu estructura)
    llaves = list(propiedades.keys())
    total = len(llaves)
    if max_items:
        print(f"📝 Procesando {max_items} propiedades (solo las primeras {max_items} para pruebas)...")
        llaves = llaves[:max_items]
    else:
        print(f"📝 Procesando {total} propiedades...")

    tokenizer, model = cargar_modelo(DEVICE)
    print("✅ Modelo cargado. Procesando propiedades...")

    resultados = {}

    for idx, key in enumerate(tqdm(llaves, desc="Procesando propiedades")):
        prop = propiedades[key]
        desc = prop.get("description") or prop.get("descripcion") or prop.get("descripcion_raw") or ""
        precio = prop.get("precio", None)

        print("\n" + "=" * 80)
        print(f"⏳ Procesando propiedad #{idx+1} de {len(llaves)} (ID: {key})")
        print("-" * 80)
        print("DESCRIPCIÓN DE ENTRADA PARA MISTRAL:")
        print(desc)
        print("-" * 80)

        prompt = construir_prompt(desc, precio)
        result_ia = llamar_mistral(tokenizer, model, prompt)
        result_ia = corregir_campos_ingles(result_ia)

        # Forzar campo precio y que estén TODOS los campos requeridos
        result_ia["precio"] = precio
        for campo in CAMPOS_ESPERADOS:
            if campo not in result_ia:
                result_ia[campo] = None

        print("RESULTADO IA:", result_ia)
        resultados[key] = result_ia

    print(f"✅ ¡Listo! Resultados guardados en {OUTPUT_JSON}")
    with open(OUTPUT_JSON, "w", encoding="utf-8") as fout:
        json.dump(resultados, fout, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()