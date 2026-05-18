from datetime import datetime, timedelta
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from PYTHON.conection_db.db import get_db_connection

citas_bp = Blueprint('citas', __name__)


def formato_hora(hora):
    """Convierte timedelta o string de hora a formato HH:MM."""
    if hora is None:
        return None

    if isinstance(hora, timedelta):
        total = int(hora.total_seconds())
        h = total // 3600
        m = (total % 3600) // 60
        return f"{h:02d}:{m:02d}"

    return str(hora)[:5]


def nutriologo_required(f):
    from functools import wraps

    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'NUTRIOLOGO':
            return jsonify({'error': 'Acceso no autorizado'}), 403
        return f(*args, **kwargs)

    return decorated


def obtener_nutriologos_activos():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT id_usuario, nombre_completo
            FROM usuarios
            WHERE rol = 'NUTRIOLOGO' AND estado = 'ACTIVO'
        """)
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def _guardar_notificacion(cursor, id_usuario, mensaje, tipo):
    cursor.execute("""
        INSERT INTO notificaciones (id_usuario, mensaje, tipo, leida)
        VALUES (%s, %s, %s, 0)
    """, (id_usuario, mensaje, tipo))


def _enviar_correo_notificacion(destinatario, nombre_completo, asunto, mensaje):
    remitente = os.getenv('MAIL_USER')
    password = os.getenv('MAIL_PASS')

    if not remitente or not password or not destinatario:
        return False

    cuerpo = (
        f"Hola {nombre_completo},\n\n"
        f"{mensaje}\n\n"
        f"Erazo System"
    )

    msg = MIMEMultipart()
    msg['From'] = remitente
    msg['To'] = destinatario
    msg['Subject'] = asunto
    msg.attach(MIMEText(cuerpo, 'plain'))

    try:
        servidor = smtplib.SMTP('smtp.gmail.com', 587)
        servidor.starttls()
        servidor.login(remitente, password)
        servidor.send_message(msg)
        servidor.quit()
        return True
    except Exception:
        return False


def _notificar_usuario(cursor, usuario, asunto, mensaje):
    """
    Guarda la notificación interna siempre.
    Intenta enviar correo pero no bloquea si falla.
    """
    _guardar_notificacion(cursor, usuario['id_usuario'], mensaje, 'INTERNA')

    # Correo es opcional — si falla, no interrumpe el flujo
    try:
        _enviar_correo_notificacion(
            usuario['correo'],
            usuario['nombre_completo'],
            asunto,
            mensaje
        )
    except Exception:
        pass

    return True  # Siempre retorna True

def _notificar_nutriologos(cursor, mensaje):
    """
    Guarda notificación interna para todos los nutriólogos activos.
    """
    nutriologos = obtener_nutriologos_activos()

    for nutr in nutriologos:
        _guardar_notificacion(cursor, nutr['id_usuario'], mensaje, 'INTERNA')


# ─────────────────────────────────────────────────────────
# RUTAS NUTRIÓLOGO
# ─────────────────────────────────────────────────────────

# GET /api/citas/mes?year=2026&month=4
@citas_bp.route('/api/citas/mes', methods=['GET'])
@login_required
@nutriologo_required
def citas_mes():
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)

    if not year or not month:
        return jsonify([])

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT DAY(fecha_cita) AS dia, COUNT(*) AS total
            FROM citas
            WHERE YEAR(fecha_cita) = %s AND MONTH(fecha_cita) = %s
              AND estado != 'CANCELADA'
            GROUP BY DAY(fecha_cita)
        """, (year, month))

        rows = cursor.fetchall()
        return jsonify([{'dia': r['dia'], 'lleno': r['total'] >= 9} for r in rows])
    finally:
        cursor.close()
        conn.close()


# GET /api/citas/dia?fecha=2026-04-19
@citas_bp.route('/api/citas/dia', methods=['GET'])
@login_required
@nutriologo_required
def citas_dia():
    fecha = request.args.get('fecha')
    if not fecha:
        return jsonify([])

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT c.id_cita, c.hora_cita, c.motivo_consulta,
                   c.observaciones, c.estado,
                   u.nombre_completo, u.telefono
            FROM citas c
            JOIN pacientes p  ON c.id_paciente = p.id_paciente
            JOIN usuarios  u  ON p.id_usuario  = u.id_usuario
            WHERE c.fecha_cita = %s AND c.estado != 'CANCELADA'
            ORDER BY c.hora_cita
        """, (fecha,))

        rows = cursor.fetchall()

        for r in rows:
            r['hora_cita'] = formato_hora(r.get('hora_cita'))

        return jsonify(rows)
    finally:
        cursor.close()
        conn.close()


# POST /api/citas — Nutriólogo agenda cita
@citas_bp.route('/api/citas', methods=['POST'])
@login_required
@nutriologo_required
def crear_cita():
    data = request.get_json() or {}
    telefono = (data.get('telefono') or '').strip()
    fecha_cita = (data.get('fecha_cita') or '').strip()
    hora_cita = (data.get('hora_cita') or '').strip()
    motivo = (data.get('motivo_consulta') or '').strip()
    observaciones = (data.get('observaciones') or '').strip()

    if not all([telefono, fecha_cita, hora_cita, motivo]):
        return jsonify({'error': 'Todos los campos obligatorios deben completarse.'}), 400

    try:
        fecha_hora = datetime.strptime(f"{fecha_cita} {hora_cita}", "%Y-%m-%d %H:%M")
    except ValueError:
        return jsonify({'error': 'Formato de fecha u hora inválido.'}), 400

    if fecha_hora < datetime.now() + timedelta(hours=24):
        return jsonify({'error': 'La cita debe agendarse con al menos 24 horas de anticipación.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT id_usuario, nombre_completo, correo "
            "FROM usuarios "
            "WHERE telefono = %s AND rol = 'PACIENTE' AND estado = 'ACTIVO'",
            (telefono,)
        )
        usuario = cursor.fetchone()

        if not usuario:
            return jsonify({'error': 'No se encontró un paciente activo con ese teléfono.'}), 404

        cursor.execute(
            "SELECT id_paciente FROM pacientes WHERE id_usuario = %s",
            (usuario['id_usuario'],)
        )
        paciente = cursor.fetchone()

        if not paciente:
            return jsonify({'error': 'El paciente no tiene expediente registrado en el sistema.'}), 404

        id_paciente = paciente['id_paciente']

        cursor.execute(
            "SELECT id_cita FROM citas WHERE id_paciente = %s AND estado IN ('PENDIENTE', 'CONFIRMADA') LIMIT 1",
            (id_paciente,)
        )
        if cursor.fetchone():
            return jsonify({'error': 'El paciente ya tiene una cita activa programada.'}), 409

        cursor.execute(
            "SELECT id_cita FROM citas "
            "WHERE fecha_cita = %s AND hora_cita = %s "
            "AND estado != 'CANCELADA' LIMIT 1",
            (fecha_cita, hora_cita)
        )
        if cursor.fetchone():
            return jsonify({'error': 'El horario seleccionado no está disponible.'}), 409

        cursor.execute("""
            INSERT INTO citas (
                id_paciente,
                fecha_cita,
                hora_cita,
                motivo_consulta,
                observaciones,
                estado,
                fecha_creacion
            )
            VALUES (%s, %s, %s, %s, %s, 'PENDIENTE', NOW())
        """, (id_paciente, fecha_cita, hora_cita, motivo, observaciones))

        mensaje_paciente = (
            f"Se registró una cita para el {fecha_cita} a las {hora_cita}. "
            f"Motivo: {motivo}"
        )

        if not _notificar_usuario(
            cursor,
            usuario,
            'Nueva cita registrada – Erazo System',
            mensaje_paciente
        ):
            conn.rollback()
            return jsonify({'error': 'No fue posible enviar la notificación'}), 500

        mensaje_nutriologo = (
            f'El paciente {usuario["nombre_completo"]} agendó una cita para el '
            f'{fecha_cita} a las {hora_cita}. Motivo: {motivo}'
        )
        _notificar_nutriologos(cursor, mensaje_nutriologo)

        conn.commit()
        return jsonify({'mensaje': 'Cita registrada correctamente'}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'Error al registrar cita: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()


# DELETE /api/citas/<id> — Nutriólogo cancela cita
@citas_bp.route('/api/citas/<int:id_cita>', methods=['DELETE'])
@login_required
@nutriologo_required
def cancelar_cita(id_cita):
    data = request.get_json(silent=True) or {}
    motivo = (data.get('motivo_cancelacion') or 'Cancelada por el nutriólogo').strip()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT u.id_usuario, u.nombre_completo, u.correo,
                   c.fecha_cita, c.hora_cita, c.estado
            FROM citas c
            JOIN pacientes p ON c.id_paciente = p.id_paciente
            JOIN usuarios u  ON p.id_usuario = u.id_usuario
            WHERE c.id_cita = %s
        """, (id_cita,))
        cita = cursor.fetchone()

        if not cita:
            return jsonify({'error': 'La cita no se encuentra registrada.'}), 404

        if cita['estado'] == 'CANCELADA':
            return jsonify({'error': 'La cita ya se encuentra cancelada.'}), 409

        if cita['estado'] == 'FINALIZADA':
            return jsonify({'error': 'La cita ya fue finalizada y no puede cancelarse.'}), 409

        cursor.execute("""
            UPDATE citas
            SET estado = 'CANCELADA',
                observaciones = CONCAT(IFNULL(observaciones,''), ' | Motivo cancelación: ', %s),
                fecha_modificacion = NOW()
            WHERE id_cita = %s
        """, (motivo, id_cita))

        fecha = str(cita['fecha_cita'])
        hora = formato_hora(cita['hora_cita'])
        mensaje_paciente = (
            f"Hola {cita['nombre_completo']}, su cita programada para el día {fecha} "
            f"a las {hora} ha sido cancelada. Motivo: {motivo}"
        )

        if not _notificar_usuario(
            cursor,
            cita,
            'Cancelación de cita – Erazo System',
            mensaje_paciente
        ):
            conn.rollback()
            return jsonify({'error': 'No fue posible enviar la notificación'}), 500

        mensaje_nutriologo = (
            f'El paciente {cita["nombre_completo"]} canceló su cita del '
            f'{fecha} a las {hora}. Motivo: {motivo}'
        )
        _notificar_nutriologos(cursor, mensaje_nutriologo)

        conn.commit()
        return jsonify({'mensaje': 'Cita cancelada correctamente y notificación enviada'})

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'Error al cancelar la cita: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()


# ─────────────────────────────────────────────────────────
# RUTAS PACIENTE
# ─────────────────────────────────────────────────────────

# GET /api/mi-perfil — datos del paciente para el hero
@citas_bp.route('/api/mi-perfil', methods=['GET'])
@login_required
def mi_perfil():
    if current_user.rol != 'PACIENTE':
        return jsonify({'error': 'Acceso no autorizado'}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT p.peso, p.imc, p.estatura, p.edad
            FROM pacientes p
            WHERE p.id_usuario = %s
        """, (current_user.id,))
        paciente = cursor.fetchone()

        plan = None
        try:
            cursor.execute("""
                SELECT e.objetivo_nutricional
                FROM expedientes e
                JOIN pacientes p ON e.id_paciente = p.id_paciente
                WHERE p.id_usuario = %s AND e.estado = 'ACTIVO'
                ORDER BY e.fecha_creacion DESC
                LIMIT 1
            """, (current_user.id,))
            exp = cursor.fetchone()
            if exp:
                plan = exp.get('objetivo_nutricional')
        except Exception:
            pass

        if not paciente:
            return jsonify({'peso': None, 'imc': None, 'plan': None})

        return jsonify({
            'peso': float(paciente['peso']) if paciente.get('peso') is not None else None,
            'imc': float(paciente['imc']) if paciente.get('imc') is not None else None,
            'estatura': float(paciente['estatura']) if paciente.get('estatura') is not None else None,
            'edad': paciente.get('edad'),
            'plan': plan or 'Sin plan',
        })
    finally:
        cursor.close()
        conn.close()


# GET /api/mis-citas | GET /api/mis-citas?proxima=true
@citas_bp.route('/api/mis-citas', methods=['GET'])
@login_required
def mis_citas():
    if current_user.rol != 'PACIENTE':
        return jsonify({'error': 'Acceso no autorizado'}), 403

    proxima = request.args.get('proxima') == 'true'
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id_paciente FROM pacientes WHERE id_usuario = %s", (current_user.id,))
        pac = cursor.fetchone()
        if not pac:
            return jsonify({'cita': None}) if proxima else jsonify([])

        id_paciente = pac['id_paciente']

        if proxima:
            cursor.execute("""
                SELECT id_cita, fecha_cita, hora_cita, motivo_consulta, estado
                FROM citas
                WHERE id_paciente = %s
                  AND estado IN ('PENDIENTE', 'CONFIRMADA')
                  AND fecha_cita >= CURDATE()
                ORDER BY fecha_cita ASC, hora_cita ASC
                LIMIT 1
            """, (id_paciente,))
            cita = cursor.fetchone()
            if cita:
                cita['fecha_cita'] = str(cita['fecha_cita'])
                cita['hora_cita'] = formato_hora(cita['hora_cita'])
                return jsonify({'cita': cita})
            return jsonify({'cita': None})

        cursor.execute("""
            SELECT id_cita, fecha_cita, hora_cita, motivo_consulta, observaciones, estado, fecha_creacion
            FROM citas
            WHERE id_paciente = %s
            ORDER BY fecha_cita DESC, hora_cita DESC
        """, (id_paciente,))
        rows = cursor.fetchall()

        for r in rows:
            r['fecha_cita'] = str(r['fecha_cita'])
            r['hora_cita'] = formato_hora(r['hora_cita'])
            r['fecha_creacion'] = str(r['fecha_creacion'])

        return jsonify(rows)
    finally:
        cursor.close()
        conn.close()


# POST /api/mis-citas — Paciente agenda su cita
@citas_bp.route('/api/mis-citas', methods=['POST'])
@login_required
def agendar_mi_cita():
    if current_user.rol != 'PACIENTE':
        return jsonify({'error': 'Acceso no autorizado'}), 403

    data = request.get_json() or {}
    fecha_cita = (data.get('fecha_cita') or '').strip()
    hora_cita = (data.get('hora_cita') or '').strip()
    motivo = (data.get('motivo_consulta') or '').strip()

    if not all([fecha_cita, hora_cita, motivo]):
        return jsonify({'error': 'Todos los campos son obligatorios.'}), 400

    try:
        fecha_hora = datetime.strptime(f"{fecha_cita} {hora_cita}", "%Y-%m-%d %H:%M")
    except ValueError:
        return jsonify({'error': 'Formato de fecha u hora inválido.'}), 400

    if fecha_hora < datetime.now() + timedelta(hours=24):
        return jsonify({'error': 'La cita debe agendarse con al menos 24 horas de anticipación.'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT id_usuario, nombre_completo, correo FROM usuarios WHERE id_usuario = %s",
            (current_user.id,)
        )
        usuario = cursor.fetchone()
        if not usuario:
            return jsonify({'error': 'No se encontró tu usuario en el sistema.'}), 404

        cursor.execute("SELECT id_paciente FROM pacientes WHERE id_usuario = %s", (current_user.id,))
        pac = cursor.fetchone()
        if not pac:
            return jsonify({'error': 'No tienes un expediente registrado. Contacta a tu nutriólogo.'}), 404

        id_paciente = pac['id_paciente']

        cursor.execute(
            "SELECT id_cita FROM citas WHERE id_paciente = %s AND estado IN ('PENDIENTE', 'CONFIRMADA') LIMIT 1",
            (id_paciente,)
        )
        if cursor.fetchone():
            return jsonify({'error': 'Ya tienes una cita activa programada.'}), 409

        cursor.execute(
            "SELECT id_cita FROM citas WHERE fecha_cita = %s AND hora_cita = %s AND estado != 'CANCELADA' LIMIT 1",
            (fecha_cita, hora_cita)
        )
        if cursor.fetchone():
            return jsonify({'error': 'El horario seleccionado no está disponible.'}), 409

        cursor.execute("""
            INSERT INTO citas (id_paciente, fecha_cita, hora_cita, motivo_consulta, estado, fecha_creacion)
            VALUES (%s, %s, %s, %s, 'PENDIENTE', NOW())
        """, (id_paciente, fecha_cita, hora_cita, motivo))

        mensaje_paciente = f'Tu cita fue registrada para el {fecha_cita} a las {hora_cita}. Motivo: {motivo}'

        if not _notificar_usuario(
            cursor,
            usuario,
            'Cita registrada – Erazo System',
            mensaje_paciente
        ):
            conn.rollback()
            return jsonify({'error': 'No fue posible enviar la notificación'}), 500

        mensaje_nutriologo = (
            f'El paciente {usuario["nombre_completo"]} agendó una cita para el '
            f'{fecha_cita} a las {hora_cita}. Motivo: {motivo}'
        )
        _notificar_nutriologos(cursor, mensaje_nutriologo)

        conn.commit()
        return jsonify({'mensaje': 'Cita registrada correctamente'}), 201

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'Error al registrar cita: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()


# DELETE /api/mis-citas/<id> — Paciente cancela su cita
@citas_bp.route('/api/mis-citas/<int:id_cita>', methods=['DELETE'])
@login_required
def cancelar_mi_cita(id_cita):
    if current_user.rol != 'PACIENTE':
        return jsonify({'error': 'Acceso no autorizado'}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT id_usuario, nombre_completo, correo FROM usuarios WHERE id_usuario = %s",
            (current_user.id,)
        )
        usuario = cursor.fetchone()
        if not usuario:
            return jsonify({'error': 'No se encontró tu usuario en el sistema.'}), 404

        cursor.execute("SELECT id_paciente FROM pacientes WHERE id_usuario = %s", (current_user.id,))
        pac = cursor.fetchone()
        if not pac:
            return jsonify({'error': 'Paciente no encontrado.'}), 404

        cursor.execute("""
            SELECT c.id_cita, c.fecha_cita, c.hora_cita, c.estado
            FROM citas c
            WHERE c.id_cita = %s AND c.id_paciente = %s
        """, (id_cita, pac['id_paciente']))
        cita = cursor.fetchone()

        if not cita:
            return jsonify({'error': 'La cita no se encuentra registrada.'}), 404

        if cita['estado'] == 'CANCELADA':
            return jsonify({'error': 'La cita ya se encuentra cancelada.'}), 409

        if cita['estado'] == 'FINALIZADA':
            return jsonify({'error': 'La cita ya fue finalizada y no puede cancelarse.'}), 409

        cursor.execute("""
            UPDATE citas
            SET estado = 'CANCELADA',
                fecha_modificacion = NOW()
            WHERE id_cita = %s
        """, (id_cita,))

        fecha = str(cita['fecha_cita'])
        hora = formato_hora(cita['hora_cita'])
        mensaje_paciente = (
            f'Tu cita programada para el día {fecha} '
            f'a las {hora} ha sido cancelada.'
        )

        if not _notificar_usuario(
            cursor,
            usuario,
            'Cancelación de cita – Erazo System',
            mensaje_paciente
        ):
            conn.rollback()
            return jsonify({'error': 'No fue posible enviar la notificación'}), 500

        mensaje_nutriologo = (
            f'El paciente {usuario["nombre_completo"]} canceló su cita del '
            f'{fecha} a las {hora}.'
        )
        _notificar_nutriologos(cursor, mensaje_nutriologo)

        conn.commit()
        return jsonify({'mensaje': 'Cita cancelada correctamente y notificación enviada'})

    except Exception as e:
        conn.rollback()
        return jsonify({'error': f'Error al cancelar la cita: {str(e)}'}), 500
    finally:
        cursor.close()
        conn.close()


# GET /api/citas/disponibilidad?fecha=2026-04-20
@citas_bp.route('/api/citas/disponibilidad', methods=['GET'])
@login_required
def disponibilidad():
    fecha = request.args.get('fecha')
    if not fecha:
        return jsonify({'ocupadas': []})

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT TIME_FORMAT(hora_cita, '%H:%i') AS hora
            FROM citas
            WHERE fecha_cita = %s AND estado != 'CANCELADA'
        """, (fecha,))

        rows = cursor.fetchall()
        return jsonify({'ocupadas': [formato_hora(r['hora']) if r.get('hora') else r['hora'] for r in rows]})
    finally:
        cursor.close()
        conn.close()