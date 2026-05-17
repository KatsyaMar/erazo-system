import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from PYTHON.conection_db.db import get_db_connection


def _obtener_usuario(id_usuario):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id_usuario, nombre_completo, correo, estado
            FROM usuarios
            WHERE id_usuario = %s
        """, (id_usuario,))
        usuario = cursor.fetchone()
        return usuario
    finally:
        cursor.close()
        conn.close()


def registrar_notificacion_interna(id_usuario, mensaje, leida=False):
    """
    Guarda una notificación interna en la tabla notificaciones.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO notificaciones (id_usuario, mensaje, tipo, leida)
            VALUES (%s, %s, 'INTERNA', %s)
        """, (id_usuario, mensaje, 1 if leida else 0))
        conn.commit()
        return True
    except Exception:
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


def enviar_notificacion_correo(id_usuario, mensaje, guardar_interna=True):
    """
    Envía una notificación por correo al usuario.
    Si se envía correctamente, también la guarda en la tabla notificaciones.
    """
    usuario = _obtener_usuario(id_usuario)

    if not usuario:
        return False

    if not usuario["correo"]:
        return False

    remitente = os.getenv("MAIL_USER")
    password = os.getenv("MAIL_PASS")

    if not remitente or not password:
        return False

    asunto = "Notificación Erazo System"

    cuerpo = f"""
Hola {usuario['nombre_completo']},

{mensaje}

Erazo System
"""

    try:
        msg = MIMEMultipart()
        msg["From"] = remitente
        msg["To"] = usuario["correo"]
        msg["Subject"] = asunto
        msg.attach(MIMEText(cuerpo, "plain"))

        servidor = smtplib.SMTP("smtp.gmail.com", 587)
        servidor.starttls()
        servidor.login(remitente, password)
        servidor.send_message(msg)
        servidor.quit()

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO notificaciones (id_usuario, mensaje, tipo, leida)
                VALUES (%s, %s, 'CORREO', 0)
            """, (id_usuario, mensaje))
            conn.commit()
        except Exception:
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()

        if guardar_interna:
            registrar_notificacion_interna(id_usuario, mensaje, leida=False)

        return True

    except Exception:
        return False