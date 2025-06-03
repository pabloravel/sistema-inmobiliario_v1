from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

# Cambia a tu modelo y pipeline local
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.3"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, device_map="auto")

generator = pipeline("text-generation", model=model, tokenizer=tokenizer, device_map="auto")

prompt = """
Eres un experto en bienes raíces en México. Extrae y devuelve solo un JSON con los siguientes campos a partir de este texto descriptivo de una propiedad (los campos que no estén presentes déjalos en null):

Ubicación:
- colonia
- estado
- ciudad
- tipo_propiedad
- precio
- tipo_operacion
- moneda

Descripción de Propiedad:
- recamaras
- banos
- niveles
- superficie_m2
- construccion_m2
- cisterna
- apto_discapacitados
- tipo_de_condominio
- fraccionamiento
- edad

Amenidades:
- seguridad
- alberca
- patio
- bodega
- terraza
- jardin
- estudio
- roof_garden

Legal:
- escrituras
- cesion_derechos
- formas_de_pago

Texto de ejemplo:
Casa de 3 recámaras y 2.5 baños en el fraccionamiento Lomas de Cortés, Cuernavaca, Morelos. Cuenta con alberca, seguridad, terraza, cisterna y jardín. Precio $3,200,000 MXN. Escriturada. 200 m2 de terreno, 150 m2 de construcción. 
"""

output = generator(prompt, max_new_tokens=500)[0]['generated_text']
print(output)