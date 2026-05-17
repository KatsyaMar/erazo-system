from flask import Blueprint, jsonify
from flask_login import login_required, current_user

from PYTHON.conection_db.db import get_db_connection

notificaciones_bp = Blueprint(
    'notificaciones',
    __name__,
    url_prefix='/api/notificaciones'
)

# ============================================
# OBTENER NOTIFICACIONES DEL USUARIO LOGUEADO
# ============================================

@notificaciones_bp.route('', methods=['GET'])
@login_required
def obtener_notificaciones():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            id_notificacion,
            mensaje,
            tipo,
            fecha_envio,
            leida
        FROM notificaciones
        WHERE id_usuario = %s
        ORDER BY fecha_envio DESC
    """, (current_user.id,))

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    for r in rows:
        r['fecha_envio'] = str(r['fecha_envio'])

    return jsonify(rows)


# ============================================
# MARCAR COMO LEIDA
# ============================================

@notificaciones_bp.route('/<int:id_notificacion>/leer', methods=['PUT'])
@login_required
def marcar_leida(id_notificacion):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE notificaciones
        SET leida = 1
        WHERE id_notificacion = %s
        AND id_usuario = %s
    """, (id_notificacion, current_user.id))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        'mensaje': 'Notificación marcada como leída'
    })