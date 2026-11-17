
import hashlib
import io
import zipfile
from pathlib import Path

from PIL import Image

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

import streamlit as st
import motor_notebook as motor
import agente_rl as rl
from llm_recomendaciones import generar_recomendacion


# =========================================================
# 1. CONFIGURACIÓN
# =========================================================

# Icono de la pestaña del navegador: archivo dentro del proyecto.
# Mantén la carpeta assets junto a app.py.
LOGO_PATH = Path(__file__).resolve().parent / "assets" / "folder_logo.png"
if not LOGO_PATH.is_file():
    raise FileNotFoundError(f"No se encontró el icono: {LOGO_PATH}")
FAVICON = Image.open(LOGO_PATH)

st.set_page_config(
    page_title="docganizer",
    page_icon=FAVICON,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# 2. DISEÑO VISUAL
# =========================================================

st.markdown("""
<style>

/* ================================
   TEMA GENERAL
================================ */
:root {
    color-scheme: light !important;
}

.stApp,
[data-testid="stAppViewContainer"] {
    background: #f3f4f8 !important;
    color: #222222 !important;
}

html, body,
.stApp p,
.stApp span,
.stApp label,
.stApp li,
.stApp h1,
.stApp h2,
.stApp h3,
.stApp h4,
.stMarkdown,
[data-testid="stWidgetLabel"] {
    color: #222222 !important;
}

/* Ocultar barra superior de Streamlit */
header[data-testid="stHeader"] {
    display: none !important;
}

[data-testid="stToolbar"] {
    display: none !important;
}

[data-testid="stDecoration"] {
    display: none !important;
}

#MainMenu, footer {
    visibility: hidden !important;
}

/* Contenedor principal */
.block-container {
    max-width: 1250px;
    padding-top: 0.8rem !important;
    padding-bottom: 3rem;
}

/* ================================
   NAVBAR DOCGANIZER — grupo alineado a la izquierda
================================ */
.st-key-navbar {
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    width: 100% !important;
    height: 64px !important;
    min-height: 64px !important;
    box-sizing: border-box !important;
    z-index: 99999 !important;
    background: #ffffff !important;
    border-bottom: 1px solid #e8e8ee !important;
    margin: 0 !important;
    padding: 0 28px !important;
    border-radius: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
}

.st-key-navbar [data-testid="stVerticalBlock"] {
    width: 100% !important;
    height: 64px !important;
    min-height: 64px !important;
    display: flex !important;
    justify-content: center !important;
    gap: 0 !important;
}

/* La fila solo ocupa el ancho necesario: no reparte los botones por toda la pantalla. */
.st-key-navbar [data-testid="stHorizontalBlock"] {
    width: 720px !important;
    min-width: 720px !important;
    max-width: none !important;
    height: 64px !important;
    min-height: 64px !important;
    display: flex !important;
    flex-wrap: nowrap !important;
    overflow: visible !important;
    align-items: center !important;
    justify-content: flex-start !important;
    gap: 22px !important;
}

.st-key-navbar [data-testid="column"] {
    flex: 0 0 auto !important;
    flex-shrink: 0 !important;
    width: auto !important;
    min-height: 64px !important;
    height: 64px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    padding: 0 !important;
}

/* Anchos naturales de cada elemento para mantenerlos agrupados a la izquierda. */
.st-key-navbar [data-testid="column"]:nth-child(1) { width: 230px !important; }
.st-key-navbar [data-testid="column"]:nth-child(2) { width: 105px !important; }
.st-key-navbar [data-testid="column"]:nth-child(3) { width: 175px !important; }
.st-key-navbar [data-testid="column"]:nth-child(4) { width: 135px !important; }

.st-key-navbar [data-testid="column"] > div,
.st-key-navbar [data-testid="column"] [data-testid="stVerticalBlock"] {
    width: 100% !important;
    height: 64px !important;
    min-height: 64px !important;
    display: flex !important;
    flex-direction: column !important;
    justify-content: center !important;
    gap: 0 !important;
}

/* Streamlit agrega márgenes a los párrafos Markdown; se eliminan para centrar el logo. */
.st-key-navbar [data-testid="stMarkdown"],
.st-key-navbar [data-testid="stMarkdownContainer"] {
    width: 100% !important;
    height: 64px !important;
    min-height: 64px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    margin: 0 !important;
    padding: 0 !important;
}

.st-key-navbar [data-testid="stMarkdownContainer"] p {
    margin: 0 !important;
    padding: 0 !important;
    line-height: 1 !important;
}

.logo {
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    height: 64px !important;
    min-height: 64px !important;
    font-size: 36px !important;
    font-weight: 900 !important;
    color: #111111 !important;
    letter-spacing: -1.6px !important;
    line-height: 1 !important;
    white-space: nowrap !important;
    margin: 0 !important;
    padding: 0 !important;
}

.logo span { color: #e53935 !important; }

.st-key-navbar [data-testid="stButton"] {
    width: 100% !important;
    height: 64px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    margin: 0 !important;
    padding: 0 !important;
}

.st-key-navbar [data-testid="stButton"] button {
    width: auto !important;
    min-width: 0 !important;
    min-height: 64px !important;
    height: 64px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    background: transparent !important;
    color: #171717 !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    font-size: 16px !important;
    font-weight: 750 !important;
    line-height: 1 !important;
    padding: 0 4px !important;
    margin: 0 !important;
    white-space: nowrap !important;
}

.st-key-navbar [data-testid="stButton"] button p,
.st-key-navbar [data-testid="stButton"] button span {
    color: inherit !important;
    font-size: 16px !important;
    font-weight: 750 !important;
    line-height: 1 !important;
    margin: 0 !important;
    padding: 0 !important;
}

.st-key-navbar [data-testid="stButton"] button:hover { color: #e53935 !important; background: transparent !important; }
.st-key-navbar [data-testid="stButton"] button[kind="primary"],
.st-key-navbar [data-testid="stButton"] button[data-testid="stBaseButton-primary"] {
    background: transparent !important;
    color: #e53935 !important;
    border: none !important;
    box-shadow: none !important;
}
.st-key-navbar [data-testid="stButton"] button[kind="primary"] p,
.st-key-navbar [data-testid="stButton"] button[data-testid="stBaseButton-primary"] p { color: #e53935 !important; }

.navbar-spacer { height: 64px !important; min-height: 64px !important; width: 100% !important; }

/* ================================
   HERO
================================ */
.hero-title {
    text-align: center;
    font-size: clamp(34px, 4vw, 50px);
    font-weight: 850;
    color: #30303a !important;
    margin-top: 35px;
    margin-bottom: 10px;
}

.hero-subtitle {
    text-align: center;
    font-size: 20px;
    color: #666678 !important;
    margin-bottom: 35px;
}

/* ================================
   BOTONES
================================ */
.stApp .stButton:not(.st-key-navbar .stButton) button,
.stDownloadButton button,
.stFormSubmitButton button,
.stApp button[kind="primary"]:not(.st-key-navbar button),
.stApp [data-testid="stBaseButton-primary"]:not(.st-key-navbar [data-testid="stBaseButton-primary"]) {
    background-color: #e53935 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 700 !important;
}

.stApp .stButton:not(.st-key-navbar .stButton) button *,
.stDownloadButton button *,
.stFormSubmitButton button *,
.stApp button[kind="primary"]:not(.st-key-navbar button) *,
.stApp [data-testid="stBaseButton-primary"]:not(.st-key-navbar [data-testid="stBaseButton-primary"]) * {
    color: #ffffff !important;
}

.stApp .stButton:not(.st-key-navbar .stButton) button:hover,
.stDownloadButton button:hover,
.stFormSubmitButton button:hover,
.stApp button[kind="primary"]:not(.st-key-navbar button):hover,
.stApp [data-testid="stBaseButton-primary"]:not(.st-key-navbar [data-testid="stBaseButton-primary"]):hover {
    background-color: #cc2f2b !important;
    color: #ffffff !important;
}

/* ================================
   CARGA DE ARCHIVOS
================================ */
[data-testid="stFileUploader"] {
    background: #ffffff !important;
    border: 1px solid #e4e5ea !important;
    border-radius: 12px;
    padding: 14px;
}

[data-testid="stFileUploader"] section {
    background: #ffffff !important;
    border: 1px dashed #cfd2da !important;
    border-radius: 10px;
}

[data-testid="stFileUploader"] section * {
    color: #333333 !important;
}

[data-testid="stFileUploader"] button {
    background: #ffffff !important;
    color: #333333 !important;
    border: 1px solid #dddddd !important;
}

/* Icono nativo del archivo: fondo oscuro y pictograma blanco.
   Se estiliza el SVG real de Streamlit, sin depender de la estructura
   interna exacta del contenedor (que cambia entre versiones). */
[data-testid="stFileUploaderFile"] svg {
    width: 50px !important;
    height: 50px !important;
    min-width: 50px !important;
    min-height: 50px !important;
    box-sizing: border-box !important;
    padding: 11px !important;
    background: #292929 !important;
    color: #ffffff !important;
    stroke: #ffffff !important;
    border-radius: 10px !important;
    filter: none !important;
}

[data-testid="stFileUploaderFile"] svg path,
[data-testid="stFileUploaderFile"] svg rect,
[data-testid="stFileUploaderFile"] svg line,
[data-testid="stFileUploaderFile"] svg polyline,
[data-testid="stFileUploaderFile"] svg circle {
    stroke: #ffffff !important;
}

/* Los controles de quitar archivo conservan contraste y fondo blanco. */
[data-testid="stFileUploaderFile"] button {
    background: #ffffff !important;
    color: #444444 !important;
    border: 1px solid #d8dce5 !important;
}
[data-testid="stFileUploaderFile"] button svg {
    width: 16px !important;
    height: 16px !important;
    min-width: 16px !important;
    min-height: 16px !important;
    padding: 0 !important;
    background: transparent !important;
    stroke: #444444 !important;
    color: #444444 !important;
}

/* ================================
   COMPONENTES
================================ */
[data-testid="stExpander"] {
    background: #ffffff !important;
    border: 1px solid #e6e7ec !important;
    border-radius: 10px;
}

[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p {
    color: #222222 !important;
}

[data-testid="stMetric"] {
    background: #ffffff !important;
    border: 1px solid #e8e8ed;
    padding: 14px;
    border-radius: 10px;
}

[data-testid="stMetricLabel"],
[data-testid="stMetricValue"] {
    color: #222222 !important;
}

.stTextInput input,
.stTextArea textarea,
.stNumberInput input {
    background: #ffffff !important;
    color: #222222 !important;
    border: 1px solid #d9d9df !important;
}

.stSelectbox div[data-baseweb="select"] > div,
.stMultiSelect div[data-baseweb="select"] > div {
    background: #ffffff !important;
    color: #222222 !important;
}

.stRadio label {
    color: #222222 !important;
}

[data-testid="stDataFrame"],
[data-testid="stTable"] {
    background: #ffffff !important;
}

/* texto pequeño */
.soft-text {
    color: #666678 !important;
    font-size: 16px;
    text-align: center;
}

.section-note {
    color: #666678 !important;
    font-size: 15px;
}

.category-list {
    color: #444455 !important;
    font-size: 15px;
    margin-top: 6px;
    margin-bottom: 10px;
}

.footer {
    text-align: center;
    color: #8a8a96 !important;
    font-size: 12px;
    padding: 28px 0 10px 0;
}

hr {
    border-color: #e4e5ea !important;
}

.stTextArea textarea {
    background: #ffffff !important;
    color: #222222 !important;
    border: 1px solid #d9d9df !important;
}

.stTextArea textarea:focus {
    border-color: #e53935 !important;
    box-shadow: 0 0 0 1px #e53935 !important;
}

</style>
""", unsafe_allow_html=True)



# =========================================================
# 3. BARRA DE NAVEGACIÓN
# =========================================================

if "pagina_actual" not in st.session_state:
    st.session_state.pagina_actual = "Inicio"

with st.container(key="navbar"):
    nav_logo, nav_inicio, nav_como, nav_integrantes = st.columns(
        [1.35, 0.62, 1.05, 0.85],
        vertical_alignment="center"
    )

    with nav_logo:
        st.markdown(
            '<div class="logo">doc<span>ganizer</span></div>',
            unsafe_allow_html=True
        )

    with nav_inicio:
        if st.button(
            "Inicio",
            key="nav_inicio",
            type="primary" if st.session_state.pagina_actual == "Inicio" else "secondary"
        ):
            st.session_state.pagina_actual = "Inicio"
            st.rerun()

    with nav_como:
        if st.button(
            "Cómo funciona",
            key="nav_como",
            type="primary" if st.session_state.pagina_actual == "Cómo funciona" else "secondary"
        ):
            st.session_state.pagina_actual = "Cómo funciona"
            st.rerun()

    with nav_integrantes:
        if st.button(
            "Integrantes",
            key="nav_integrantes",
            type="primary" if st.session_state.pagina_actual == "Integrantes" else "secondary"
        ):
            st.session_state.pagina_actual = "Integrantes"
            st.rerun()

pagina = st.session_state.pagina_actual

# La navbar está fija arriba; este espacio evita que cubra el contenido.
st.markdown('<div class="navbar-spacer"></div>', unsafe_allow_html=True)


# =========================================================
# 4. PÁGINA PRINCIPAL
# =========================================================

if pagina == "Inicio":

    st.markdown(
        '<div class="hero-title">Organizar archivos</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="hero-subtitle">'
        'Organiza de forma rápida facturas, comprobantes de compra, etc.'
        '</div>',
        unsafe_allow_html=True
    )

    # Verificar modelo
    try:
        modelo = motor.modelo_cargado
    except Exception as error:
        st.error("No se pudo cargar el modelo.")
        st.exception(error)
        st.stop()

    st.markdown("---")

    st.subheader("Selecciona tus documentos")

    st.write(
        "Arrastra tus archivos o selecciónalos desde tu equipo."
    )

    st.markdown(
        """
        <div class="category-list">
        <strong>Categorías que clasifica:</strong>
        Comprobantes · Contratos · Facturas · Formularios · Órdenes de compra · Recibos
        </div>
        """,
        unsafe_allow_html=True
    )

    archivos = st.file_uploader(
        "Seleccionar documentos",
        type=[
            "pdf", "png", "jpg", "jpeg",
            "tif", "tiff", "bmp", "webp"
        ],
        accept_multiple_files=True,
        key="documentos_subidos"
    )

    MAX_ARCHIVOS = 40
    MAX_ARCHIVO = 15 * 1024 * 1024
    MAX_LOTE = 100 * 1024 * 1024

    if archivos:
        st.info(
            f"Documentos seleccionados: {len(archivos)}"
        )

    if st.button(
        "Clasificar y preparar ZIP",
        type="primary",
        use_container_width=True,
        disabled=not archivos
    ):

        if len(archivos) > MAX_ARCHIVOS:
            st.error(
                f"Máximo {MAX_ARCHIVOS} archivos por lote."
            )
            st.stop()

        contenidos = [a.getvalue() for a in archivos]
        tamanos = [len(c) for c in contenidos]

        if any(t > MAX_ARCHIVO for t in tamanos):
            st.error(
                "Cada archivo debe pesar 15 MB o menos."
            )
            st.stop()

        if sum(tamanos) > MAX_LOTE:
            st.error("El lote supera 100 MB.")
            st.stop()

        st.session_state.pop("zip_organizado", None)
        st.session_state.pop("resultados_organizacion", None)

        resultados = []
        buffer_zip = io.BytesIO()
        usados = set()

        progreso = st.progress(0)
        estado = st.empty()

        with zipfile.ZipFile(
            buffer_zip,
            "w",
            zipfile.ZIP_DEFLATED
        ) as zip_salida:

            for i, (archivo, contenido) in enumerate(
                zip(archivos, contenidos)
            ):

                nombre = Path(archivo.name).name

                categoria = "Error"
                puntuacion = 0.0
                paginas = 0
                avisos = []
                estado_pred = "Error"
                estrategia = ""
                recomendacion = ""
                pred = {}

                estado.info(
                    f"Procesando {i + 1}/{len(archivos)}: {nombre}"
                )

                # -----------------------------------------
                # CLASIFICACIÓN ML + OCR
                # -----------------------------------------

                try:
                    pred, paginas, avisos = (
                        motor.procesar_documento(
                            nombre,
                            contenido
                        )
                    )

                    categoria = str(pred["categoria"])

                    puntuacion = float(
                        pred.get("coincidencia", 0)
                    )

                    estado_pred = str(
                        pred.get("estado", "Procesado")
                    )

                except Exception as error:
                    avisos = [
                        f"Error de clasificación/OCR: {error}"
                    ]

                # -----------------------------------------
                # AGENTE RL + GEMINI
                # -----------------------------------------

                if categoria != "Error":

                    try:
                        estrategia = rl.seleccionar_estrategia(
                            categoria
                        )

                        recomendacion = generar_recomendacion(
                            categoria=categoria,
                            puntuacion=puntuacion,
                            nombre_archivo=nombre,
                            texto_documento=pred.get(
                                "texto_extraido", ""
                            ),
                            estrategia=estrategia
                        )

                    except Exception as error:
                        avisos.append(
                            f"Gemini no generó recomendación: {error}"
                        )

                # -----------------------------------------
                # ORGANIZAR ARCHIVO EN EL ZIP
                # -----------------------------------------

                identificador = hashlib.sha256(
                    contenido + str(i).encode("utf-8")
                ).hexdigest()[:8]

                nombre_zip = (
                    f"{Path(nombre).stem}_{identificador}"
                    f"{Path(nombre).suffix.lower()}"
                )

                destino = f"{categoria}/{nombre_zip}"

                while destino in usados:

                    identificador = hashlib.sha256(
                        (identificador + destino).encode()
                    ).hexdigest()[:8]

                    nombre_zip = (
                        f"{Path(nombre).stem}_{identificador}"
                        f"{Path(nombre).suffix.lower()}"
                    )

                    destino = f"{categoria}/{nombre_zip}"

                usados.add(destino)

                zip_salida.writestr(
                    destino,
                    contenido
                )

                resultados.append({
                    "Archivo": nombre,
                    "Categoría": categoria,
                    "Puntuación (%)": round(puntuacion, 2),
                    "Páginas": paginas,
                    "Destino ZIP": destino,
                    "Estado": estado_pred,
                    "Estrategia RL": estrategia,
                    "Recomendación": recomendacion,
                    "Avisos": "; ".join(avisos)
                })

                progreso.progress(
                    (i + 1) / len(archivos)
                )

        # ---------------------------------------------
        # GENERAR RESUMEN EXCEL PARA INCLUIR EN EL ZIP
        # ---------------------------------------------

        columnas = [
            "Archivo",
            "Categoría",
            "Puntuación (%)",
            "Páginas",
            "Destino ZIP",
            "Estado",
            "Estrategia RL",
            "Avisos"
        ]

        libro = Workbook()
        hoja = libro.active
        hoja.title = "Clasificación"
        hoja.append(columnas)

        for celda in hoja[1]:
            celda.font = Font(bold=True, color="FFFFFF")
            celda.fill = PatternFill(
                fill_type="solid", fgColor="E53935"
            )
            celda.alignment = Alignment(
                horizontal="center", vertical="center"
            )

        for fila in resultados:
            hoja.append([fila.get(columna, "") for columna in columnas])

        hoja.freeze_panes = "A2"
        hoja.auto_filter.ref = hoja.dimensions

        anchos = [30, 22, 17, 12, 48, 24, 24, 55]
        for indice, ancho in enumerate(anchos, start=1):
            hoja.column_dimensions[get_column_letter(indice)].width = ancho

        for fila_excel in hoja.iter_rows(min_row=2):
            for celda in fila_excel:
                celda.alignment = Alignment(
                    vertical="top", wrap_text=True
                )

        excel_buffer = io.BytesIO()
        libro.save(excel_buffer)
        excel_bytes = excel_buffer.getvalue()

        # El ZIP incluye un solo resumen Excel; no se duplica en CSV.
        with zipfile.ZipFile(
            buffer_zip,
            "a",
            zipfile.ZIP_DEFLATED
        ) as zip_salida:
            zip_salida.writestr(
                "resumen_clasificacion.xlsx",
                excel_bytes
            )

        st.session_state["zip_organizado"] = (
            buffer_zip.getvalue()
        )

        st.session_state["resultados_organizacion"] = (
            resultados
        )

        progreso.empty()
        estado.empty()

        st.success("¡Procesamiento terminado!")


    # =====================================================
    # 5. MOSTRAR RESULTADOS
    # =====================================================

    if "resultados_organizacion" in st.session_state:

        resultados = st.session_state[
            "resultados_organizacion"
        ]

        st.divider()

        st.header("Resultados de clasificación")

        st.dataframe(
            [{
                "Archivo": r["Archivo"],
                "Categoría": r["Categoría"],
                "Puntuación (%)": r["Puntuación (%)"],
                "Páginas": r["Páginas"],
                "Estado": r["Estado"],
                "Avisos": r["Avisos"]
            } for r in resultados],
            use_container_width=True,
            hide_index=True
        )

        total = len(resultados)

        clasificados = sum(
            r["Categoría"] not in (
                "Revision_necesaria",
                "Error"
            )
            for r in resultados
        )

        revisiones = sum(
            r["Categoría"] == "Revision_necesaria"
            for r in resultados
        )

        errores = sum(
            r["Categoría"] == "Error"
            for r in resultados
        )

        a, b, c, d = st.columns(4)

        a.metric("Total", total)
        b.metric("Clasificados", clasificados)
        c.metric("Por revisar", revisiones)
        d.metric("Errores", errores)

        # ---------------------------------------------
        # RECOMENDACIONES GEMINI
        # ---------------------------------------------

        st.divider()

        st.header("Recomendaciones generadas por Gemini")

        st.caption(
            "El agente RL selecciona el estilo de recomendación. "
            "Tu calificación actualiza sus valores Q."
        )

        for i, r in enumerate(resultados):

            with st.expander(
                f"📄 {r['Archivo']} — {r['Categoría']}",
                expanded=False
            ):

                if r["Recomendación"]:

                    st.write(r["Recomendación"])

                    st.caption(
                        f"Estrategia RL: {r['Estrategia RL']}"
                    )

                    guardada = f"feedback_guardado_{i}"

                    if st.session_state.get(guardada, False):

                        st.success(
                            "Calificación registrada."
                        )

                    else:

                        estrellas = st.radio(
                            "¿Qué tan útil fue esta recomendación?",
                            [1, 2, 3, 4, 5],
                            format_func=lambda x: "⭐" * x,
                            horizontal=True,
                            key=f"rating_{i}"
                        )

                        comentario = st.text_area(
                            "Comentario opcional",
                            key=f"comentario_{i}",
                            height=80,
                            placeholder="Escribe aquí una observación (opcional)..."
                        )

                        if st.button(
                            "Enviar calificación",
                            key=f"feedback_{i}"
                        ):

                            try:

                                datos = rl.registrar_feedback(
                                    r["Categoría"],
                                    r["Estrategia RL"],
                                    int(estrellas),
                                    comentario
                                )

                                st.session_state[guardada] = True

                                st.success(
                                    "Feedback guardado. "
                                    f"Recompensa: {datos['recompensa']:.2f}"
                                )

                                st.info(
                                    f"Q anterior: {datos['valor_anterior']:.3f} | "
                                    f"Q nuevo: {datos['nuevo_valor']:.3f}"
                                )

                            except Exception as error:

                                st.error(
                                    f"No se pudo guardar el feedback: {error}"
                                )

                else:

                    st.warning(
                        "No se generó recomendación. "
                        "Revisa la API Key y los avisos."
                    )

                if r["Avisos"]:
                    st.caption(
                        "Avisos: " + r["Avisos"]
                    )

        # ---------------------------------------------
        # DESCARGA ZIP
        # ---------------------------------------------

        st.divider()

        st.header("Descargar documentos organizados")

        st.download_button(
            "⬇️ Descargar ZIP organizado",
            data=st.session_state["zip_organizado"],
            file_name="documentos_organizados.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True
        )



    # =====================================================
    # 6. CONSULTAR APRENDIZAJE RL
    # =====================================================

    st.divider()

    with st.expander("Consultar aprendizaje del agente RL"):

        cat = st.selectbox(
            "Selecciona una categoría",
            [
                "Comprobante",
                "Contratos",
                "Facturas",
                "Formulario",
                "Ordenes_compra",
                "Recibos",
                "Revision_necesaria"
            ]
        )

        st.dataframe(
            [
                {
                    "Estrategia": accion,
                    "Valor Q": round(valor, 4)
                }
                for accion, valor in rl.consultar_aprendizaje(cat)
            ],
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# 7. PÁGINA: CÓMO FUNCIONA
# =========================================================


elif pagina == "Cómo funciona":

    st.markdown(
        '<div class="hero-title">Cómo funciona doc<span style="color:#e53935;">ganizer</span></div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="hero-subtitle">'
        'Tecnología e inteligencia artificial para transformar '
        'la manera de organizar documentos.'
        '</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    ## Del documento a la información organizada

    docganizer integra diferentes técnicas de inteligencia artificial
    para identificar, clasificar y organizar documentos de manera
    automática. Su funcionamiento se desarrolla en seis etapas.

    ---

    ### 01. Recepción de documentos

    El usuario carga documentos en formatos PDF e imágenes.
    El sistema recibe los archivos y los prepara para su análisis.

    ### 02. Extracción de información mediante OCR

    Utilizamos **Tesseract OCR** para reconocer y extraer
    el contenido textual de documentos digitales y escaneados.

    Se encuentra configurado para trabajar con español e inglés.

    ### 03. Clasificación mediante Machine Learning

    El texto extraído es procesado por un modelo de
    **TF-IDF y Regresión Logística**, entrenado con documentos
    previamente etiquetados.

    El modelo identifica seis categorías:

    - Comprobantes
    - Contratos
    - Facturas
    - Formularios
    - Órdenes de compra
    - Recibos

    Cuando la clasificación requiere revisión, el sistema
    identifica el documento como pendiente de verificación.

    ### 04. Recomendaciones mediante un LLM

    docganizer integra **Google Gemini**, un modelo de lenguaje
    grande (LLM).

    La predicción obtenida por el clasificador se utiliza como
    entrada para generar una explicación y recomendaciones
    relacionadas con el tipo de documento identificado.

    Las recomendaciones se generan en lenguaje natural
    y ayudan al usuario a interpretar el resultado.

    ### 05. Aprendizaje por refuerzo (RL)

    El usuario puede calificar las recomendaciones generadas
    mediante una escala de una a cinco estrellas.

    El agente utiliza esta valoración como recompensa y
    actualiza sus valores Q para aprender qué estrategias
    de recomendación ofrecen mejores resultados.

    ### 06. Organización y descarga

    Finalmente, los documentos se distribuyen en carpetas
    según su clasificación.

    El usuario puede descargar un archivo ZIP que contiene
    los documentos organizados y un archivo CSV con el
    resumen de los resultados.

    ---

    ## Tecnologías utilizadas

    """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **Desarrollo y procesamiento**

        - Python
        - Streamlit
        - OpenCV
        - Tesseract OCR
        - PyMuPDF
        """)

    with col2:
        st.markdown("""
        **Inteligencia artificial**

        - Scikit-learn
        - TF-IDF
        - Regresión Logística
        - Google Gemini API
        - Aprendizaje por refuerzo
        """)

    st.divider()

    st.markdown("""
    ### Arquitectura general

    ```text
    DOCUMENTOS
         |
         v
       OCR
         |
         v
    EXTRACCIÓN DE TEXTO
         |
         v
    MODELO TF-IDF + REGRESIÓN LOGÍSTICA
         |
         v
    PREDICCIÓN DE CATEGORÍA
         |
         v
    GOOGLE GEMINI (LLM)
         |
         v
    RECOMENDACIONES
         |
         v
    FEEDBACK DEL USUARIO
         |
         v
    AGENTE DE APRENDIZAJE POR REFUERZO
         |
         v
    ORGANIZACIÓN Y DESCARGA ZIP
    ```

    """)

    st.subheader("Configuración del reconocimiento OCR")

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Tesseract OCR",
            "Disponible" if motor.OCR_OK else "No disponible"
        )

    with col2:
        st.metric(
            "Idiomas",
            motor.IDIOMA_OCR or "No disponibles"
        )


# =========================================================
# 8. PÁGINA: INTEGRANTES
# =========================================================


elif pagina == "Integrantes":

    st.markdown(
        '<div class="hero-title">Integrantes</div>',
        unsafe_allow_html=True
    )

    st.markdown("""
    <div style="max-width:760px; margin:35px 0 0; text-align:left;">
        <p style="font-size:23px; font-weight:600; margin:22px 0;">Mcgregor Vellojin Montiel</p>
        <p style="font-size:23px; font-weight:600; margin:22px 0;">Andrea Carolina Nieto Gonzalez</p>
        <p style="font-size:23px; font-weight:600; margin:22px 0;">Samuel Elías Mendoza Cáceres</p>
    </div>
    """, unsafe_allow_html=True)


# =========================================================
# 9. PIE DE PÁGINA
# =========================================================

st.markdown("""
<div class="footer">
    docganizer · Organizador Inteligente de Documentos
</div>
""", unsafe_allow_html=True)
