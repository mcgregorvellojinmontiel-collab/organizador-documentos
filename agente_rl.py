"""Agente educativo RL contextual de un paso con persistencia SQLite."""
import random
import sqlite3
from pathlib import Path

DB_RUTA = Path(__file__).resolve().parent / "feedback.db"
ACCIONES = ("breve", "detallada", "pasos")
ALPHA = 0.30
EPSILON = 0.15

def conectar():
    return sqlite3.connect(DB_RUTA)

def inicializar():
    categorias = ("Comprobante", "Contratos", "Facturas", "Formulario",
                  "Ordenes_compra", "Recibos", "Revision_necesaria", "Error")
    with conectar() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS valores_q (
            categoria TEXT NOT NULL, accion TEXT NOT NULL,
            valor REAL NOT NULL DEFAULT 0,
            PRIMARY KEY(categoria, accion))""")
        conn.execute("""CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria TEXT NOT NULL, accion TEXT NOT NULL,
            calificacion INTEGER NOT NULL, recompensa REAL NOT NULL,
            comentario TEXT, fecha DATETIME DEFAULT CURRENT_TIMESTAMP)""")
        for cat in categorias:
            for accion in ACCIONES:
                conn.execute("""INSERT OR IGNORE INTO valores_q
                    (categoria, accion, valor) VALUES (?, ?, 0)""", (cat, accion))

def seleccionar_estrategia(categoria):
    inicializar()
    if random.random() < EPSILON:
        return random.choice(ACCIONES)
    with conectar() as conn:
        filas = conn.execute(
            "SELECT accion, valor FROM valores_q WHERE categoria=?",
            (categoria,)).fetchall()
    if not filas:
        return "detallada"
    maximo = max(v for _, v in filas)
    return random.choice([a for a, v in filas if v == maximo])

def registrar_feedback(categoria, accion, calificacion, comentario=""):
    if not isinstance(calificacion, int) or not 1 <= calificacion <= 5:
        raise ValueError("La calificación debe estar entre 1 y 5.")
    if accion not in ACCIONES:
        raise ValueError("Estrategia desconocida.")
    inicializar()
    recompensa = (calificacion - 3) / 2
    with conectar() as conn:
        fila = conn.execute(
            "SELECT valor FROM valores_q WHERE categoria=? AND accion=?",
            (categoria, accion)).fetchone()
        anterior = float(fila[0]) if fila else 0.0
        # Actualización de Q para una interacción de un solo paso.
        nuevo = anterior + ALPHA * (recompensa - anterior)
        conn.execute("""INSERT INTO valores_q(categoria, accion, valor)
            VALUES (?, ?, ?) ON CONFLICT(categoria, accion)
            DO UPDATE SET valor=excluded.valor""", (categoria, accion, nuevo))
        conn.execute("""INSERT INTO feedback
            (categoria, accion, calificacion, recompensa, comentario)
            VALUES (?, ?, ?, ?, ?)""",
            (categoria, accion, calificacion, recompensa, comentario))
    return {"recompensa": recompensa, "valor_anterior": anterior, "nuevo_valor": nuevo}

def consultar_aprendizaje(categoria):
    inicializar()
    with conectar() as conn:
        return conn.execute(
            "SELECT accion, valor FROM valores_q WHERE categoria=? ORDER BY valor DESC",
            (categoria,)).fetchall()

inicializar()
