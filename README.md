# DataAgents AI 7.0
Subir los archivos de este ZIP a la raíz del repositorio, incluida .streamlit/config.toml. Mantener los secretos de Streamlit existentes. Ejecutar con `streamlit run app.py`.

Motor local: ausencias condicionadas, comparaciones descriptivas, Pearson y Spearman, anomalías IQR/MAD/Z, normalización opcional de categorías por capitalización. Los umbrales son heurísticos, no pruebas de significancia. Se examinan hasta 20 variables numéricas y 20 categóricas de cardinalidad 2–30; se conservan hasta 30 patrones por tabla. Los agentes reciben evidencia agregada, no filas completas, previa autorización. No usar información sensible. La interpretación generativa requiere revisión humana.

Pruebas locales: compilación, motor sobre Brújula y Solicitudes, generación DOCX/PDF sin IA. No se verificó despliegue ni llamadas reales a proveedores. Los cruces siguen siendo opcionales y requieren confirmación.
