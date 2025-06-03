from extractor_propiedades_v4 import extraer_superficie

def test_superficie():
    # Casos de prueba
    casos = [
        {
            "descripcion": "Terreno en venta, en colonia Unidad deportiva, Cuernavaca. A 3 minutos de la Autopista Cuernavaca- CDMX, a 2 minutos de Camino viejo A Tepoztlán. Superficie: 400 m² 20 metros de frente y 20 de fondo. Servicios: - Electricidad - Internet Otros características: - Totalmente bardeado. - Cisterna para agua. - Marquesina y portón - Pase de transporte público: ruta 10 a 100 metros del terreno. Precio por lote de 200 m2: $375,000",
            "esperado": {"superficie_m2": 400, "construccion_m2": 0}
        },
        {
            "descripcion": "SE VENDE CASA SOLA EN COLONIA PLAN DE AYALA JUNTO A LOMAS DE DE ATZINGO 210 MTS DE TERRENO 103 DE CONSTRUCCION 3 RECAMARAS SALA COCINA COMEDOR 2 BAÑOS GARAJE 2 AUTOS CISTERNA APTA PARA CREDITOS ESCRITURADA $1,800,000",
            "esperado": {"superficie_m2": 210, "construccion_m2": 103}
        },
        # Casos adicionales para probar diferentes formatos
        {
            "descripcion": "Terreno de 10x20 metros cuadrados en excelente ubicación",
            "esperado": {"superficie_m2": 200, "construccion_m2": 0}
        },
        {
            "descripcion": "Casa con 150m² de terreno y 120m² de construcción",
            "esperado": {"superficie_m2": 150, "construccion_m2": 120}
        },
        {
            "descripcion": "Propiedad en venta, superficie del terreno: 300 metros cuadrados, área construida: 180 m2",
            "esperado": {"superficie_m2": 300, "construccion_m2": 180}
        }
    ]

    for i, caso in enumerate(casos, 1):
        resultado = extraer_superficie(caso["descripcion"])
        esperado = caso["esperado"]
        
        print(f"\nPrueba #{i}:")
        print(f"Descripción: {caso['descripcion'][:100]}...")
        print(f"Resultado: {resultado}")
        print(f"Esperado: {esperado}")
        
        if resultado == esperado:
            print("✅ CORRECTO")
        else:
            print("❌ INCORRECTO")
            if resultado["superficie_m2"] != esperado["superficie_m2"]:
                print(f"  - Superficie no coincide: {resultado['superficie_m2']} != {esperado['superficie_m2']}")
            if resultado["construccion_m2"] != esperado["construccion_m2"]:
                print(f"  - Construcción no coincide: {resultado['construccion_m2']} != {esperado['construccion_m2']}")

if __name__ == "__main__":
    print("Probando extracción de superficie y construcción...")
    test_superficie() 