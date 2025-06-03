#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
guarda_login.py

Script para guardar el estado de login de Facebook
"""

from playwright.sync_api import sync_playwright
import time

def main():
    with sync_playwright() as p:
        # Iniciar navegador
        browser = p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )
        
        # Crear contexto
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        )
        
        # Crear página
        page = context.new_page()
        
        # Ir a Facebook
        print("\nNavegando a Facebook...")
        page.goto('https://www.facebook.com')
        
        print("\nPor favor, inicia sesión en Facebook.")
        print("Una vez que hayas iniciado sesión, presiona Enter para continuar...")
        input()
        
        # Guardar estado
        print("\nGuardando estado de la sesión...")
        context.storage_state(path="fb_state.json")
        print("✓ Estado guardado en fb_state.json")
        
        # Cerrar navegador
        browser.close()
        print("\n¡Listo! Ahora puedes ejecutar el script principal.")

if __name__ == "__main__":
    main() 