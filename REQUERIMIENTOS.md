# Requerimientos de extracción

- **precio**: campo `price` del JSON convertido a float.
- **moneda**: si `price` incluye `$`, usar `MXN`.
- **tipo_operacion**: solo valores `"Venta"` o `"Renta"`.
- **tipo_propiedad**: extraer con regex del título (`Casa`, `Departamento`, etc.).
- **colonia**, **ciudad**, **estado**: usar `location`, `ciudad` y `estado` del JSON.
- **recamaras**, **banos**, **niveles**: regex en `descripcion_raw`.
- **superficie_m2**, **construccion_m2**: regex en `descripcion_raw`.
- **amenidades** (alberca, patio, bodega, terraza, cisterna): booleanos por regex.
- **es_un_nivel**: `niveles == 1`.
