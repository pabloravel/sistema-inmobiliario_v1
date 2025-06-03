import pickle
import os
import re

# Carga del modelo
MODELO_PATH = "modelos/modelo_banos_v150_py312_sklearn161.pkl"

try:
    with open(MODELO_PATH, "rb") as f:
        modelo_banos = pickle.load(f)
    print("✅ Modelo de 'Baños' cargado correctamente desde modelo_banos.py")
except Exception as e:
    print(f"❌ Error al cargar el modelo de baños: {e}")
    modelo_banos = None

# Función de predicción
def predecir_banos_desde_modelo(texto):
    if not texto or not modelo_banos:
        return None
    try:
        features = [texto.lower()]
        pred = modelo_banos.predict(features)
        return int(pred[0])
    except Exception as e:
        print(f"❌ Error al predecir baños: {e}")
        return None
