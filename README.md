# DataAgents AI 9.0
Subir los archivos de este ZIP a la raíz del repositorio, incluida .streamlit/config.toml. Mantener los secretos de Streamlit existentes. Ejecutar con `streamlit run app.py`.

Motor local: ausencias condicionadas, comparaciones descriptivas, Pearson y Spearman, anomalías IQR/MAD/Z, normalización opcional de categorías por capitalización. Los umbrales son heurísticos, no pruebas de significancia. Se examinan hasta 20 variables numéricas y 20 categóricas de cardinalidad 2–30; se conservan hasta 30 patrones por tabla. Los agentes reciben evidencia agregada, no filas completas, previa autorización. No usar información sensible. La interpretación generativa requiere revisión humana.

Pruebas locales: compilación, motor sobre Brújula y Solicitudes, generación DOCX/PDF sin IA. No se verificó despliegue ni llamadas reales a proveedores. Los cruces siguen siendo opcionales y requieren confirmación.

## Versión 9.0
Panel ejecutivo con brechas descriptivas, tendencias por mes observado y simulación aritmética. Consulta local mediante selectores; la consulta libre interpreta evidencia, no ejecuta código generado. Informe ejecutivo disponible sin IA. Agentes secuenciales, espera acotada ante 429 y continuación de agentes pendientes. Las cuotas externas pueden impedir completar el análisis. Reemplazar todos los archivos en GitHub, incluido strategy.py y .streamlit/config.toml.
