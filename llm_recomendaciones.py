
"""Generación de recomendaciones con Gemini."""

import os
import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()

MODELO_LLM = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
_cliente = None


def obtener_configuracion():
    """Lee las credenciales localmente o desde Streamlit Cloud."""

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        try:
            api_key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            api_key = None

    try:
        modelo = st.secrets.get("GEMINI_MODEL", MODELO_LLM)
    except Exception:
        modelo = MODELO_LLM

    if not api_key:
        raise RuntimeError(
            "Falta GEMINI_API_KEY. Configúrala en "
            "Streamlit Cloud > Settings > Secrets "
            "o en tu archivo .env local."
        )

    return api_key, modelo


def _cliente_gemini():
    global _cliente

    api_key, modelo = obtener_configuracion()

    if _cliente is None:
        _cliente = genai.Client(api_key=api_key)

    return _cliente, modelo


def generar_recomendacion(
    categoria,
    puntuacion,
    nombre_archivo,
    texto_documento="",
    estrategia="detallada"
):

    estilos = {
        "breve": "Sé conciso, pero supera 200 caracteres.",
        "detallada": "Explica detalladamente el resultado y la organización.",
        "pasos": "Organiza las recomendaciones en pasos numerados."
    }

    fragmento = (texto_documento or "")[:3500]

    if not fragmento.strip():
        fragmento = "[No se pudo extraer texto del documento.]"

    prompt = f"""
Eres un asistente de organización documental.
Explica una predicción ya realizada;
no cambies la categoría ni inventes información.

Archivo: {nombre_archivo}
Categoría predicha: {categoria}
Puntuación del clasificador: {puntuacion}%

Fragmento extraído:
{fragmento}

Escribe en español una recomendación de más de 200 caracteres
que explique la categoría, cite señales presentes en el fragmento,
sugiera carpeta y criterio de nombre/orden, e indique qué debe
verificar el usuario.

Si la puntuación es baja o no hay texto, advierte que requiere
revisión manual.

No expongas ni repitas innecesariamente datos personales,
bancarios o identificaciones.

Estilo: {estilos.get(estrategia, estilos["detallada"])}
"""

    cliente, modelo = _cliente_gemini()

    respuesta = cliente.models.generate_content(
        model=modelo,
        contents=prompt
    )

    texto = (respuesta.text or "").strip()

    if len(texto) < 200:
        raise ValueError(
            "Gemini devolvió menos de 200 caracteres."
        )

    return texto
