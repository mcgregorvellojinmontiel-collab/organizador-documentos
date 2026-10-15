import csv
import io
import hashlib
import zipfile
from pathlib import Path
import streamlit as st
import motor_notebook as motor

st.set_page_config(page_title='Organizador de documentos',
layout='centered')
st.title('Organizador de documentos')
st.write('Sube documentos desordenados y descarga un ZIP clasificado usando **el modelo TF-IDF de tu notebook**.')
st.caption('Usa directamente la clasificación de tu notebook. No es necesario cargar plantillas.')

@st.cache_resource(show_spinner='Preparando el clasificador del notebook...')
def iniciar_motor():
    return motor.preparar_clasificador_local()

modo, cantidad, avisos_plantillas = iniciar_motor()
st.caption(f'Método activo: {modo}' + (f' · {cantidad} referencias locales' if cantidad else ''))
if avisos_plantillas:
    with st.expander('Avisos del clasificador'):
        for aviso in avisos_plantillas: st.write(aviso)

st.subheader('1. Archivos por organizar')
archivos=st.file_uploader('Selecciona varios documentos',type=['pdf','png','jpg','jpeg','tif','tiff','bmp','webp'],accept_multiple_files=True,key='docs')
if not motor.OCR_OK:
    st.warning('Tesseract OCR no está disponible. Los PDFs con texto funcionarán, pero las imágenes y los escaneos pueden quedar sin clasificar.')

if st.button('Clasificar y preparar ZIP',type='primary',disabled=not archivos):
    if len(archivos)>40:
        st.error('Para esta demo, carga como máximo 40 archivos.'); st.stop()
    if any(len(a.getvalue())>15*1024*1024 for a in archivos):
        st.error('Cada archivo debe ser de 15 MB o menos.'); st.stop()
    if sum(len(a.getvalue()) for a in archivos)>100*1024*1024:
        st.error('El lote supera 100 MB.'); st.stop()
    progreso=st.progress(0)
    resultados=[]
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for indice,archivo in enumerate(archivos):
            nombre=Path(archivo.name).name
            contenido=archivo.getvalue()
            try:
                pred,paginas,avisos = motor.procesar_documento_listo(nombre,contenido,usar_tfidf=(cantidad>0))
                categoria=pred['categoria']
                aviso='; '.join(avisos)
            except Exception as e:
                pred={'coincidencia':0,'estado':'Error de procesamiento','plantilla_similar':''}
                paginas=0
                categoria='Revision_necesaria'
                aviso=f'Error: {e}'
            identificador=hashlib.sha256((str(indice)+nombre).encode()).hexdigest()[:8]
            destino=f'{categoria}/{Path(nombre).stem}_{identificador}{Path(nombre).suffix.lower()}'
            z.writestr(destino,contenido)
            resultados.append({'Archivo':nombre,'Categoría':categoria,'Puntuación (no es probabilidad)':pred['coincidencia'],'Estado':pred['estado'],'Plantilla similar':pred['plantilla_similar'],'Páginas':paginas,'Avisos':aviso})
            progreso.progress((indice+1)/len(archivos))
        csv_buffer=io.StringIO()
        columnas=list(resultados[0])
        escritor=csv.DictWriter(csv_buffer,fieldnames=columnas)
        escritor.writeheader(); escritor.writerows(resultados)
        z.writestr('resumen_clasificacion.csv',csv_buffer.getvalue().encode('utf-8-sig'))
    st.session_state['zip']=buffer.getvalue()
    st.session_state['resultados']=resultados

if 'resultados' in st.session_state:
    st.subheader('2. Resultados')
    st.dataframe(st.session_state['resultados'],use_container_width=True,hide_index=True)
    st.download_button('Descargar ZIP organizado',data=st.session_state['zip'],file_name='documentos_organizados.zip',mime='application/zip',type='primary')
    st.caption('Las puntuaciones no son probabilidades validadas. El ZIP contiene los archivos originales y un CSV resumen.')
