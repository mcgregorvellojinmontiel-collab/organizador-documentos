"""Adaptador: usa funciones y parámetros reales de ID_documentos_11.ipynb."""
import ast
import io
import json
import os
import re
import unicodedata
from pathlib import Path
import numpy as np
import cv2
import fitz
import pytesseract
from pytesseract import Output
from PIL import Image, ImageOps
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

NOTEBOOK = Path(__file__).with_name('ID_documentos_11.ipynb')
EXTENSIONES = {'.pdf','.jpg','.jpeg','.png','.bmp','.tif','.tiff','.webp'}
MAX_PAGINAS_PDF = 200
MIN_CARACTERES_TEXTO = 35
DPI_PDF = 220
if os.name == 'nt':
    exe = Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe')
    if exe.exists():
        pytesseract.pytesseract.tesseract_cmd = str(exe)
try:
    langs = set(pytesseract.get_languages(config=''))
except Exception:
    langs = set()
OCR_OK = bool(langs)
IDIOMA_OCR = 'spa+eng' if {'spa','eng'} <= langs else 'spa' if 'spa' in langs else 'eng' if 'eng' in langs else ''

# Se extraen del notebook las funciones, no se ejecutan sus celdas de
# entrenamiento de TensorFlow ni sus bucles sobre carpetas locales.
def _cargar_funciones_del_notebook():
    notebook = json.loads(NOTEBOOK.read_text(encoding='utf-8'))
    entorno = globals()
    seleccion = {
        2: {'limpiar_texto','normalizar','estrategias_imagen','ocr_imagen','leer_documento'},
        3: {'extraer_campos','buscar','clasificar'},
        7: {'limpiar_para_modelo','puntuacion_palabras','identificar_documento'},
    }
    for indice, nombres in seleccion.items():
        codigo = ''.join(notebook['cells'][indice]['source'])
        arbol = ast.parse(codigo)
        nodos = [n for n in arbol.body if isinstance(n, (ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in nombres]
        if indice == 3:
            nodos = [n for n in arbol.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='CATEGORIAS' for t in n.targets)] + nodos
        if indice == 7:
            nodos = [n for n in arbol.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PISTAS' for t in n.targets)] + nodos
        exec(compile(ast.fix_missing_locations(ast.Module(body=nodos, type_ignores=[])), str(NOTEBOOK), 'exec'), entorno)

_cargar_funciones_del_notebook()


def entrenar_con_plantillas(plantillas):
    """plantillas: iterable (nombre, categoria, bytes); misma config TF-IDF notebook."""
    global plantillas_textos,plantillas_etiquetas,plantillas_archivos,vectorizador,matriz_plantillas,categorias
    textos,etiquetas,nombres,errores = [],[],[],[]
    from tempfile import TemporaryDirectory
    with TemporaryDirectory(prefix='docsort_ref_') as carpeta:
        for i,(nombre,categoria,contenido) in enumerate(plantillas):
            extension = Path(nombre).suffix.lower()
            if extension not in EXTENSIONES:
                errores.append(f'{nombre}: formato no compatible'); continue
            ruta = Path(carpeta) / f'ref_{i}{extension}'
            try:
                ruta.write_bytes(contenido)
                paginas,_ = leer_documento(ruta)
                texto = limpiar_para_modelo('\n'.join(p['texto'] for p in paginas))
                if len(texto)<20:
                    errores.append(f'{nombre}: texto insuficiente (revisa OCR)'); continue
                textos.append(texto); etiquetas.append(categoria); nombres.append(nombre)
            except Exception as e:
                errores.append(f'{nombre}: {e}')
    if not textos:
        raise ValueError('No se pudieron leer plantillas con texto suficiente. Revisa los PDFs o instala Tesseract para imágenes.')
    plantillas_textos,plantillas_etiquetas,plantillas_archivos = textos,etiquetas,nombres
    vectorizador = TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),sublinear_tf=True,max_features=20000)
    matriz_plantillas = vectorizador.fit_transform(textos)
    categorias = sorted(set(etiquetas))
    return len(textos), errores


def procesar_documento(nombre,contenido):
    from tempfile import TemporaryDirectory
    extension = Path(nombre).suffix.lower()
    if extension not in EXTENSIONES:
        raise ValueError('Formato no admitido')
    with TemporaryDirectory(prefix='docsort_doc_') as carpeta:
        ruta=Path(carpeta)/('entrada'+extension)
        ruta.write_bytes(contenido)
        paginas, avisos=leer_documento(ruta)
    texto='\n'.join(p['texto'] for p in paginas)
    resultado=identificar_documento(texto)  # Función original del notebook
    return resultado, len(paginas), avisos


# Modo listo para usar: busca referencias guardadas por el desarrollador.
# Si no hay referencias, usa la clasificación por reglas del MISMO notebook.
def preparar_clasificador_local():
    raiz = Path(__file__).with_name('plantillas')
    items = []
    if raiz.is_dir():
        for categoria in ['Facturas','Recibos','Contratos','Ordenes_compra']:
            carpeta = raiz / categoria
            if not carpeta.is_dir():
                continue
            for archivo in sorted(carpeta.iterdir()):
                if archivo.is_file() and archivo.suffix.lower() in EXTENSIONES:
                    items.append((archivo.name, categoria, archivo.read_bytes()))
    if items:
        try:
            cantidad, errores = entrenar_con_plantillas(items)
            return 'TF-IDF + palabras clave (notebook)', cantidad, errores
        except Exception as exc:
            return 'Reglas originales del notebook', 0, [f'No se pudieron leer las referencias locales: {exc}']
    return 'Reglas originales del notebook', 0, []


def procesar_documento_listo(nombre, contenido, usar_tfidf=False):
    if usar_tfidf:
        return procesar_documento(nombre, contenido)
    from tempfile import TemporaryDirectory
    extension = Path(nombre).suffix.lower()
    if extension not in EXTENSIONES:
        raise ValueError('Formato no admitido')
    with TemporaryDirectory(prefix='docsort_doc_') as carpeta:
        ruta = Path(carpeta) / ('entrada'+extension)
        ruta.write_bytes(contenido)
        paginas, avisos = leer_documento(ruta)
    texto = '\n'.join(p['texto'] for p in paginas)
    categoria, puntajes = clasificar(texto)  # Reglas originales, celda 3
    equivalencias = {
        'Factura':'Facturas', 'Recibo':'Recibos', 'Contrato':'Contratos',
        'Orden de compra':'Ordenes_compra', 'Formulario':'Formularios',
        'Comprobante':'Comprobantes', 'Revisión necesaria':'Revision_necesaria'
    }
    categoria_final = equivalencias.get(categoria, 'Revision_necesaria')
    return {
        'categoria':categoria_final,
        'coincidencia':max(puntajes.values(), default=0),
        'estado':'Clasificado por reglas' if categoria_final!='Revision_necesaria' else 'Revisar manualmente',
        'plantilla_similar':'(sin plantillas; reglas del notebook)'
    }, len(paginas), avisos
