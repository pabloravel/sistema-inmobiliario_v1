import pytest
from parse_descriptions import process_item

example = {
    'id': '123',
    'price': '$1,200,000',
    'tipo_operacion': 'Venta',
    'title': 'Casa en Venta en XYZ',
    'descripcion_raw': '3 recámaras, 2 baños, 1 nivel, Superficie: 250.00, Construcción: 200.00, alberca'
}

@pytest.mark.parametrize('item,expected', [
    (
        example,
        {
            'id': '123',
            'precio': 1200000.0,
            'moneda': 'MXN',
            'recamaras': 3,
            'banos': 2,
            'niveles': 1,
            'superficie_m2': 250.0,
            'construccion_m2': 200.0,
            'alberca': True,
            'es_un_nivel': True
        }
    )
])
def test_process_item(item, expected):
    out, ok = process_item(item)
    assert ok
    for key, val in expected.items():
        assert out[key] == val
