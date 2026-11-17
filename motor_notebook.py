"""Motor OCR + clasificador supervisado cargado desde joblib y funciones del notebook."""
import ast
import json
import os
import io
import re
import unicodedata
import tempfile

from pathlib import Path

import cv2
import fitz
import joblib
import numpy as np
import pandas as pd
import pytesseract

from PIL import Image, ImageOps, ImageEnhance, ImageFilter
from pytesseract import Output

BASE = Path(__file__).resolve().parent
NOTEBOOK = BASE / "ID_documentos_11.ipynb"
if not NOTEBOOK.exists():
    encontrados = sorted(BASE.glob("ID_documentos_11*.ipynb"))
    if encontrados:
        NOTEBOOK = encontrados[0]
MODELO_RUTA = BASE / "modelo_documentos.joblib"
EXTENSIONES = {".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
MAX_PAGINAS_PDF = 200
MIN_CARACTERES_TEXTO = 35
DPI_PDF = 220
UMBRAL_REVISION = 0.0

if os.name == "nt":
    exe = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if exe.exists():
        pytesseract.pytesseract.tesseract_cmd = str(exe)
try:
    IDIOMAS_DISPONIBLES = set(pytesseract.get_languages(config=""))
except Exception:
    IDIOMAS_DISPONIBLES = set()
OCR_OK = bool(IDIOMAS_DISPONIBLES)
if {"spa", "eng"}.issubset(IDIOMAS_DISPONIBLES):
    IDIOMA_OCR = "spa+eng"
elif "spa" in IDIOMAS_DISPONIBLES:
    IDIOMA_OCR = "spa"
elif "eng" in IDIOMAS_DISPONIBLES:
    IDIOMA_OCR = "eng"
else:
    IDIOMA_OCR = ""

def cargar_funciones_notebook():
    if not NOTEBOOK.is_file():
        raise FileNotFoundError(f"No se encontró el notebook: {NOTEBOOK}")
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    funciones = {"limpiar_texto", "normalizar", "estrategias_imagen",
                 "ocr_imagen", "leer_documento", "extraer_campos",
                 "buscar", "clasificar", "limpiar_para_modelo",
                 "puntuacion_palabras", "identificar_documento"}
    constantes = {"CATEGORIAS", "PISTAS"}
    nodos, encontradas = [], set()
    for celda in notebook.get("cells", []):
        if celda.get("cell_type") != "code":
            continue
        codigo = "".join(celda.get("source", []))
        if not codigo.strip():
            continue
        try:
            arbol = ast.parse(codigo)
        except SyntaxError:
            continue
        for nodo in arbol.body:
            if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)) and nodo.name in funciones:
                nodos.append(nodo)
                encontradas.add(nodo.name)
            elif isinstance(nodo, (ast.Assign, ast.AnnAssign)):
                destinos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
                nombres = {d.id for d in destinos if isinstance(d, ast.Name)}
                if nombres & constantes:
                    nodos.append(nodo)
    faltantes = {"leer_documento", "ocr_imagen", "estrategias_imagen"} - encontradas
    if faltantes:
        raise RuntimeError("Faltan funciones del notebook: " + ", ".join(sorted(faltantes)))
    modulo = ast.Module(body=nodos, type_ignores=[])
    ast.fix_missing_locations(modulo)
    exec(compile(modulo, str(NOTEBOOK), "exec"), globals())
    print("Funciones cargadas:", ", ".join(sorted(encontradas)))

cargar_funciones_notebook()

def cargar_modelo():
    if not MODELO_RUTA.is_file():
        raise FileNotFoundError(f"No se encontró el modelo: {MODELO_RUTA}")
    modelo = joblib.load(MODELO_RUTA)
    for atributo in ("predict", "predict_proba", "classes_"):
        if not hasattr(modelo, atributo):
            raise TypeError(f"El modelo no contiene {atributo}.")
    print("Modelo cargado. Categorías:", modelo.classes_)
    return modelo

modelo_cargado = cargar_modelo()

def predecir_texto(texto):
    texto = (texto or "").strip()
    if len(texto) < MIN_CARACTERES_TEXTO:
        return "Revision_necesaria", 0.0
    probabilidades = modelo_cargado.predict_proba([texto])[0]
    indice = int(np.argmax(probabilidades))
    confianza = float(probabilidades[indice])
    categoria = str(modelo_cargado.classes_[indice])
    if confianza < UMBRAL_REVISION:
        categoria = "Revision_necesaria"
    return categoria, confianza

def _extraer_texto(nombre, contenido):
    extension = Path(nombre).suffix.lower()
    if extension not in EXTENSIONES:
        raise ValueError(f"Formato no admitido: {extension}")
    if not contenido:
        raise ValueError("El archivo está vacío.")
    with tempfile.TemporaryDirectory(prefix="organizador_documentos_") as carpeta:
        ruta = Path(carpeta) / ("entrada" + extension)
        ruta.write_bytes(contenido)
        paginas, avisos = leer_documento(ruta)
    paginas = paginas or []
    texto = "\n".join(p.get("texto", "") for p in paginas).strip()
    return texto, len(paginas), list(avisos or [])

def procesar_documento(nombre, contenido):
    texto, paginas, avisos = _extraer_texto(nombre, contenido)
    categoria, confianza = predecir_texto(texto)
    resultado = {
        "categoria": categoria,
        "coincidencia": round(confianza * 100, 2),
        "estado": "Clasificado" if categoria != "Revision_necesaria" else "Revisión necesaria",
        "plantilla_similar": "",
        "texto_extraido": texto[:5000],
        "caracteres_extraidos": len(texto),
    }
    if not texto:
        avisos.append("No se pudo extraer texto del documento.")
    return resultado, paginas, avisos

def diagnosticar_documento(nombre, contenido):
    texto, paginas, avisos = _extraer_texto(nombre, contenido)
    if len(texto) < MIN_CARACTERES_TEXTO:
        return {"texto_extraido": texto, "caracteres": len(texto),
                "paginas": paginas, "categoria": "Revision_necesaria",
                "probabilidades": {}, "avisos": avisos}
    probs = modelo_cargado.predict_proba([texto])[0]
    return {
        "texto_extraido": texto, "caracteres": len(texto), "paginas": paginas,
        "categoria": str(modelo_cargado.predict([texto])[0]),
        "probabilidades": {str(c): round(float(p), 4)
                           for c, p in zip(modelo_cargado.classes_, probs)},
        "avisos": avisos,
    }

print("OCR:", OCR_OK, "| Idioma:", IDIOMA_OCR or "No disponible")
print("Motor preparado:", BASE)
