# recordatorios.py
# ─────────────────────────────────────────────────────────
# Script para enviar recordatorios automáticos de citas.
# Ejecutar diariamente (ej. a las 8:00 AM con el Programador
# de tareas de Windows o cron en Linux).
#
# Uso:  python recordatorios.py
# ─────────────────────────────────────────────────────────

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Cargar .env usando ruta absoluta al directorio del script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Añadir el directorio raíz al path para importar módulos del proyecto
sys.path.insert(0, BASE_DIR)

from PYTHON.conection_db.db import get_db_connection


def formato_hora(hora):
    """Convierte timedelta o string de hora a HH:MM."""
    if hora is None:
        return '—'
    if isinstance(hora, timedelta):
        total = int(hora.total_seconds())
        h = total // 3600
        m = (total % 3600) // 60
        return f"{h:02d}:{m:02d}"
    return str(hora)[:5]


def enviar_recordatorios():
    manana = (datetime.now() + timedelta(days=1)).date()
    manana_fmt = manana.strftime("%d/%m/%Y")

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Buscando citas para el {manana_fmt}...")

    conn   = get_db_connection()
    if not conn:
        print("ERROR: No se pudo conectar a la base de datos.")
        return

    cursor = conn.cursor(dictionary=True)

    # Buscar citas pendientes para mañana
    cursor.execute("""
        SELECT c.id_cita, c.hora_cita, c.motivo_consulta,
               u.id_usuario, u.nombre_completo
        FROM citas c
        JOIN pacientes p ON c.id_paciente = p.id_paciente
        JOIN usuarios  u ON p.id_usuario  = u.id_usuario
        WHERE c.fecha_cita = %s
          AND c.estado = 'PENDIENTE'
    """, (manana,))
    citas = cursor.fetchall()

    if not citas:
        print(f"No hay citas pendientes para {manana_fmt}.")
        cursor.close(); conn.close()
        return

    recordatorios_enviados = 0

    for cita in citas:
        id_usuario = cita['id_usuario']
        nombre     = cita['nombre_completo']
        hora       = formato_hora(cita['hora_cita'])
        motivo     = cita['motivo_consulta']

        # Verificar que no se haya enviado ya un recordatorio hoy para esta cita
        cursor.execute("""
            SELECT id_notificacion FROM notificaciones
            WHERE id_usuario = %s
              AND mensaje LIKE %s
              AND DATE(fecha_envio) = CURDATE()
        """, (id_usuario, f"%recordatorio%{manana_fmt}%"))
        ya_enviado = cursor.fetchone()

        if ya_enviado:
            print(f"  ⚠ Recordatorio ya enviado hoy a {nombre} para el {manana_fmt}.")
            continue

        # Insertar notificación interna
        mensaje = (
            f"⏰ Recordatorio: Tienes una cita mañana {manana_fmt} "
            f"a las {hora}. Motivo: {motivo}. "
            f"Si necesitas cancelar, hazlo con anticipación."
        )
        cursor.execute(
            "INSERT INTO notificaciones (id_usuario, mensaje, tipo) VALUES (%s, %s, 'INTERNA')",
            (id_usuario, mensaje)
        )
        recordatorios_enviados += 1
        print(f"  ✓ Recordatorio enviado a {nombre} — {manana_fmt} {hora}")

    conn.commit()
    cursor.close(); conn.close()

    print(f"\nListo. {recordatorios_enviados} recordatorio(s) enviado(s).")


if __name__ == '__main__':
    enviar_recordatorios()