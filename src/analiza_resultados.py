def normalizar_precio(texto: str) -> float:
    """Normaliza un precio en formato string a float."""
    if not texto:
        return 0.0
    
    # Limpiar el texto
    texto = texto.lower().strip()
    texto = texto.replace('$', '').replace('mxn', '').replace('mnx', '').replace('mx', '')
    texto = texto.replace(' ', '')
    
    # Convertir millones
    if 'mill' in texto:
        texto = texto.replace('millones', '').replace('millon', '').replace('mill', '')
        try:
            # Reemplazar puntos por nada (son separadores de miles)
            numero = float(texto.replace('.', '').replace(',', '.'))
            return numero * 1_000_000
        except:
            return 0.0
    
    # Convertir miles
    if 'mil' in texto:
        texto = texto.replace('mil', '')
        try:
            numero = float(texto.replace('.', '').replace(',', '.'))
            return numero * 1_000
        except:
            return 0.0
    
    # Convertir número normal
    try:
        # Reemplazar puntos por nada (son separadores de miles)
        return float(texto.replace('.', '').replace(',', '.'))
    except:
        return 0.0

# ... existing code ...