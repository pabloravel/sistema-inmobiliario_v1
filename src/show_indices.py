#!/usr/bin/env python3
"""
show_indices.py

Dado un texto, imprime bloques de 100 caracteres con índices para facilitar anotaciones.
Uso:
    python show_indices.py "Texto a analizar"
"""
import sys

def show_indices(text):
    for i in range(0, len(text), 100):
        segment = text[i:i+100]
        idxs = ''.join(str((i+j)%10) for j in range(len(segment)))
        print(f"Index {i:>4}..{i+len(segment)-1:>4}:")
        print(idxs)
        print(segment)
        print("-"*100)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Uso: python show_indices.py "Texto a analizar"')
        sys.exit(1)
    text = sys.argv[1]
    show_indices(text)
