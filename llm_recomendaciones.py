
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

BASE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE, ".env"))

MODELO_LLM = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

_cliente = None


def _cliente_gemini():
    global _cliente

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("Falta GEMINI_API_KEY en .env")

    if _cliente is None:
        _cliente = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=60000)
        )

    return _cliente


def generar_recomendacion(
    categoria,
    puntuacion,
    nombre_archivo,
    texto_documento="",
    estrategia="detallada"
):
    estilos = {
        "breve": "Sé conciso, pero supera 200 caracteres.",
        "detallada": "Explica detalladamente el resultado.",
        "pasos": "Organiza las recomendaciones en pasos numerados."
    }

    fragmento = (texto_documento or "")[:3500]

    if not fragmento.strip():
        fragmento = "[No se pudo extraer texto.]"

    prompt = f"""
Eres un asistente especializado en organización documental.

Archivo: {nombre_archivo}
Categoría predicha: {categoria}
Puntuación: {puntuacion}%

Texto extraído:
{fragmento}

Genera una recomendación en español de más de 200 caracteres.
Explica la clasificación, recomienda una carpeta,
sugiere cómo organizar el archivo y qué debe verificar
el usuario.

No inventes información ni expongas datos personales.
Si la puntuación es baja, recomienda revisión manual.

Estilo: {estilos.get(estrategia, estilos["detallada"])}
"""

    cliente = _cliente_gemini()

    for intento in range(1, 4):

        try:
            print(
                f"Conectando con Gemini... Intento {intento}/3",
                flush=True
            )

            respuesta = cliente.models.generate_content(
                model=MODELO_LLM,
                contents=prompt
            )

            texto = (respuesta.text or "").strip()

            if len(texto) < 200:
                raise ValueError(
                    "Gemini generó menos de 200 caracteres."
                )

            print("Recomendación generada correctamente.", flush=True)

            return texto

        except Exception as error:

            mensaje = str(error)

            if "503" in mensaje or "UNAVAILABLE" in mensaje:
                if intento < 3:
                    print("Servidor saturado. Reintentando...", flush=True)
                    time.sleep(2 * intento)
                    continue

            raise

    raise RuntimeError("Gemini no respondió después de 3 intentos.")
