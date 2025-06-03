from extractor_propiedades_estable import es_propiedad

# Casos de prueba
casos = [
    {
        "titulo": "Vendo juguetes para niños",
        "descripcion": "Juguetes en buen estado, varios modelos disponibles, precio negociable",
        "precio": "$500",
        "location": "Cuernavaca"
    },
    {
        "titulo": "Moto Honda 2020",
        "descripcion": "Excelente estado, 10,000 km, todo pagado",
        "precio": "$45,000",
        "location": "Jiutepec"
    },
    {
        "titulo": "Casa en venta",
        "descripcion": "Hermosa casa con 3 recámaras, 2 baños, 200m2 de terreno",
        "precio": "$2,500,000",
        "location": "Lomas de Cortés, Cuernavaca"
    },
    {
        "titulo": "Cosméticos Mary Kay",
        "descripcion": "Productos originales, precios de mayoreo",
        "precio": "$300",
        "location": "Centro"
    },
    {
        "titulo": "Rento departamento",
        "descripcion": "2 recámaras, amueblado, servicios incluidos",
        "precio": "$8,000 mensuales",
        "location": "Vista Hermosa"
    }
]

print("Probando detección de propiedades:")
print("-" * 50)

for caso in casos:
    es_prop = es_propiedad(
        texto=caso["descripcion"],
        titulo=caso["titulo"],
        precio=caso["precio"],
        location=caso["location"]
    )
    print(f"\nTítulo: {caso['titulo']}")
    print(f"¿Es propiedad?: {'✓ SÍ' if es_prop else '✗ NO'}") 