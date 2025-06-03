
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
from pathlib import Path

# Cargar el dataset
df = pd.read_json("datos/train_banos_v150_final.json")

# Validar valores
df = df[df["valor"].apply(lambda x: isinstance(x, (int, float)))]
df["heuristica_cat"] = df["heuristica"].astype("category").cat.codes
df["score"] = pd.to_numeric(df["score"], errors="coerce").fillna(0)

X = df[["heuristica_cat", "score"]]
y = df["valor"].astype(int)

# Entrenar modelo
modelo = RandomForestClassifier(n_estimators=100, random_state=42)
modelo.fit(X, y)

# Guardar modelo en formato compatible localmente
Path("modelos").mkdir(parents=True, exist_ok=True)
joblib.dump(modelo, "modelos/modelo_banos_v150_py312_sklearn161.pkl")

print("✅ Modelo de Baños entrenado y guardado con éxito.")
