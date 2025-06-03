# run_mistral_instruct.py
import argparse
from llama_cpp import Llama

def main():
    parser = argparse.ArgumentParser(description="Interfaz simple para Mistral-7B-Instruct con llama.cpp en Apple Silicon")
    parser.add_argument("--model", type=str, default="mistral-7b-instruct-ggml.bin",
                        help="Ruta al archivo GGML del modelo Mistral-7B-Instruct")
    parser.add_argument("--prompt", type=str, required=True,
                        help="Texto o prompt a procesar")
    parser.add_argument("--max_tokens", type=int, default=200,
                        help="Cantidad máxima de tokens a generar")
    parser.add_argument("--threads", type=int, default=4,
                        help="Número de hilos para inferencia (ajusta según tu CPU)")
    args = parser.parse_args()

    llama = Llama(
        model_path=args.model,
        n_threads=args.threads,
        use_metal=True  # Usa aceleración Metal en el M3 Max
    )

    response = llama(
        args.prompt,
        max_tokens=args.max_tokens,
        temperature=0.0
    )
    print(response["choices"][0]["text"])

if __name__ == "__main__":
    main()