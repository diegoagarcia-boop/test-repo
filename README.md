# DataAgents AI — Universidad del Valle

Prototipo académico de sistema multiagente agnóstico a la estructura de datos. Analiza CSV, XLSX y JSON, calcula estadísticas con pandas y ejecuta cuatro roles secuenciales con Gemini.

## Inicio en Streamlit Community Cloud
1. Sube **los archivos de esta carpeta** a la raíz de tu repositorio GitHub (no la carpeta contenedora).
2. En https://share.streamlit.io/ selecciona **Create app**, repositorio y rama `main`, y archivo principal `app.py`.
3. En **Advanced settings → Secrets**, agrega `GEMINI_API_KEY = "TU_CLAVE_REAL"` y guarda. **Nunca subas el secreto a GitHub.**
4. Despliega la app y carga un CSV/XLSX/JSON de prueba.

## Ejecutar localmente (opcional)
`pip install -r requirements.txt`
`streamlit run app.py`

Para ejecutar Gemini localmente, exporta la variable de entorno `GEMINI_API_KEY`.

## Limitaciones de la versión inicial
- Sin limpieza automática destructiva: detecta nulos, duplicados y encabezados problemáticos, y normaliza encabezados.
- Análisis cualitativo avanzado y sentimiento aún pendientes.
- No está validado para uso institucional con datos personales.
- Gemini recibe resúmenes de datos y salidas previas; no recibe filas crudas.
- Se necesita documentación empírica de pruebas A (ventas), B (PQR) y ruido (30% nulos).
- Los límites del plan gratuito de Gemini pueden detener las solicitudes, sin recurrir automáticamente a facturación.
