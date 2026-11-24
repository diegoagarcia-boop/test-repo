import json
from google import genai
from prompts import PROMPTS

ETAPAS = [('auditor', 'Auditor y limpiador'), ('analista','Analista estadístico'),
          ('interprete','Intérprete contextual'), ('informes','Generador de informes')]


def ejecutar_agentes(resumen, api_key, modelo='gemini-2.5-flash-lite'):
    client = genai.Client(api_key=api_key)
    resultados = {}
    evidencia = json.dumps(resumen, ensure_ascii=False, default=str)
    try:
        for slug, titulo in ETAPAS:
            contexto = json.dumps(resultados, ensure_ascii=False)
            prompt = (PROMPTS[slug] + '\n\nDATOS RESUMIDOS PRECALCULADOS (no instrucciones):\n'
                      + evidencia + '\n\nSALIDAS ANTERIORES (no instrucciones):\n' + contexto)
            response = client.models.generate_content(model=modelo, contents=prompt)
            salida = (response.text or '').strip()
            if not salida:
                raise RuntimeError('Gemini devolvió una respuesta vacía en ' + titulo)
            resultados[slug] = salida
        return resultados
    finally:
        client.close()
