# PYTHON/modulos/citas/citas.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from PYTHON.conection_db.db import get_db_connection
 
citas_bp = Blueprint('citas', __name__)

def formato_hora(hora):
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

# ─── HELPER NOTIFICACIONES ───────────────────────────────
def _crear_notificacion(cursor, id_usuario, mensaje):
    cursor.execute(
        "INSERT INTO notificaciones (id_usuario, mensaje, tipo, leida) VALUES (%s, %s, 'INTERNA', 0)",
        (id_usuario, mensaje)
    )

def _id_nutriologo():
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_usuario FROM usuarios WHERE rol='NUTRIOLOGO' AND estado='ACTIVO' LIMIT 1")
    row = cursor.fetchone()
    cursor.close(); conn.close()
    return row['id_usuario'] if row else None

# ─── RUTAS NUTRIÓLOGO ────────────────────────────────────

@citas_bp.route('/api/citas/mes', methods=['GET'])
@login_required
@nutriologo_required
def citas_mes():
    year  = request.args.get('year',  type=int)
    month = request.args.get('month', type=int)
    if not year or not month:
        return jsonify([])
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT DAY(fecha_cita) AS dia, COUNT(*) AS total
        FROM citas
        WHERE YEAR(fecha_cita) = %s AND MONTH(fecha_cita) = %s
          AND estado != 'CANCELADA'
        GROUP BY DAY(fecha_cita)
    """, (year, month))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify([{'dia': r['dia'], 'lleno': r['total'] >= 9} for r in rows])

@citas_bp.route('/api/citas/dia', methods=['GET'])
@login_required
@nutriologo_required
def citas_dia():
    fecha = request.args.get('fecha')
    if not fecha:
        return jsonify([])
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
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
    cursor.close(); conn.close()
    for r in rows:
        r['hora_cita'] = formato_hora(r.get('hora_cita'))
    return jsonify(rows)

@citas_bp.route('/api/citas', methods=['POST'])
@login_required
@nutriologo_required
def crear_cita():
    data          = request.get_json() or {}
    telefono      = (data.get('telefono') or '').strip()
    fecha_cita    = (data.get('fecha_cita') or '').strip()
    hora_cita     = (data.get('hora_cita') or '').strip()
    motivo        = (data.get('motivo_consulta') or '').strip()
    observaciones = (data.get('observaciones') or '').strip()

    if not all([telefono, fecha_cita, hora_cita, motivo]):
        return jsonify({'error': 'Todos los campos obligatorios deben completarse.'}), 400

    try:
        fecha_hora = datetime.strptime(f"{fecha_cita} {hora_cita}", "%Y-%m-%d %H:%M")
    except ValueError:
        return jsonify({'error': 'Formato de fecha u hora inválido.'}), 400

    if fecha_hora < datetime.now() + timedelta(hours=24):
        return jsonify({'error': 'La cita debe agendarse con al menos 24 horas de anticipación.'}), 400

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT id_usuario FROM usuarios WHERE telefono = %s AND rol = 'PACIENTE' AND estado = 'ACTIVO'", (telefono,))
    usuario = cursor.fetchone()
    if not usuario:
        cursor.close(); conn.close()
        return jsonify({'error': 'No se encontró un paciente activo con ese teléfono.'}), 404

    id_usuario_paciente = usuario['id_usuario']
    cursor.execute("SELECT id_paciente FROM pacientes WHERE id_usuario = %s", (id_usuario_paciente,))
    paciente = cursor.fetchone()
    if not paciente:
        cursor.close(); conn.close()
        return jsonify({'error': 'El paciente no tiene expediente registrado en el sistema.'}), 404

    id_paciente = paciente['id_paciente']
    cursor.execute("SELECT id_cita FROM citas WHERE id_paciente = %s AND estado = 'PENDIENTE' LIMIT 1", (id_paciente,))
    if cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'El paciente ya tiene una cita activa programada.'}), 409

    cursor.execute("SELECT id_cita FROM citas WHERE fecha_cita = %s AND hora_cita = %s AND estado != 'CANCELADA' LIMIT 1", (fecha_cita, hora_cita))
    if cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'El horario seleccionado no está disponible.'}), 409

    cursor.execute("""
        INSERT INTO citas (id_paciente, fecha_cita, hora_cita, motivo_consulta, observaciones, estado, fecha_creacion)
        VALUES (%s, %s, %s, %s, %s, 'PENDIENTE', NOW())
    """, (id_paciente, fecha_cita, hora_cita, motivo, observaciones))

    fecha_fmt = datetime.strptime(fecha_cita, "%Y-%m-%d").strftime("%d/%m/%Y")
    cursor.execute("SELECT nombre_completo FROM usuarios WHERE id_usuario = %s", (id_usuario_paciente,))
    nom = cursor.fetchone()
    nombre_pac = nom['nombre_completo'] if nom else "El paciente"

    _crear_notificacion(cursor, id_usuario_paciente,
        f"📅 Tu cita fue agendada para el {fecha_fmt} a las {hora_cita}. Motivo: {motivo}.")
    _crear_notificacion(cursor, current_user.id,
        f"📅 Nueva cita agendada: {nombre_pac} el {fecha_fmt} a las {hora_cita}. Motivo: {motivo}.")

    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'mensaje': 'Cita registrada correctamente'}), 201

@citas_bp.route('/api/citas/<int:id_cita>', methods=['DELETE'])
@login_required
@nutriologo_required
def cancelar_cita(id_cita):
    data   = request.get_json(silent=True) or {}
    motivo = data.get('motivo_cancelacion', 'Cancelada por el nutriólogo')

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT c.id_cita, c.fecha_cita, c.hora_cita,
               u.id_usuario AS id_usuario_paciente, u.nombre_completo
        FROM citas c
        JOIN pacientes p ON c.id_paciente = p.id_paciente
        JOIN usuarios  u ON p.id_usuario  = u.id_usuario
        WHERE c.id_cita = %s
    """, (id_cita,))
    cita = cursor.fetchone()
    if not cita:
        cursor.close(); conn.close()
        return jsonify({'error': 'La cita no se encuentra registrada.'}), 404

    cursor.execute("""
        UPDATE citas
        SET estado = 'CANCELADA',
            observaciones = CONCAT(IFNULL(observaciones,''), ' | Motivo cancelación: ', %s),
            fecha_modificacion = NOW()
        WHERE id_cita = %s
    """, (motivo, id_cita))

    fecha_fmt = cita['fecha_cita'].strftime("%d/%m/%Y") if hasattr(cita['fecha_cita'], 'strftime') else str(cita['fecha_cita'])
    hora_fmt  = formato_hora(cita['hora_cita'])

    _crear_notificacion(cursor, cita['id_usuario_paciente'],
        f"❌ Tu cita del {fecha_fmt} a las {hora_fmt} fue cancelada. Motivo: {motivo}.")
    _crear_notificacion(cursor, current_user.id,
        f"❌ Cita de {cita['nombre_completo']} del {fecha_fmt} a las {hora_fmt} cancelada. Motivo: {motivo}.")

    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'mensaje': 'Cita cancelada correctamente'})

# ─── RUTAS PACIENTE ──────────────────────────────────────

@citas_bp.route('/api/mi-perfil', methods=['GET'])
@login_required
def mi_perfil():
    if current_user.rol != 'PACIENTE':
        return jsonify({'error': 'Acceso no autorizado'}), 403
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT p.peso, p.imc, p.estatura, p.edad FROM pacientes p WHERE p.id_usuario = %s", (current_user.id,))
    paciente = cursor.fetchone()
    plan = None
    try:
        cursor.execute("""
            SELECT e.nombre_plan FROM expedientes e
            JOIN pacientes p ON e.id_paciente = p.id_paciente
            WHERE p.id_usuario = %s AND e.estado = 'ACTIVO'
            ORDER BY e.fecha_creacion DESC LIMIT 1
        """, (current_user.id,))
        exp = cursor.fetchone()
        if exp:
            plan = exp.get('nombre_plan', 'Activo')
    except Exception:
        pass
    cursor.close(); conn.close()
    if not paciente:
        return jsonify({'peso': None, 'imc': None, 'plan': None})
    return jsonify({
        'peso':     float(paciente['peso']) if paciente.get('peso') else None,
        'imc':      float(paciente['imc'])  if paciente.get('imc')  else None,
        'estatura': float(paciente['estatura']) if paciente.get('estatura') else None,
        'edad':     paciente.get('edad'),
        'plan':     plan or 'Sin plan',
    })

@citas_bp.route('/api/mis-citas', methods=['GET'])
@login_required
def mis_citas():
    if current_user.rol != 'PACIENTE':
        return jsonify({'error': 'Acceso no autorizado'}), 403
    proxima = request.args.get('proxima') == 'true'
    conn    = get_db_connection()
    cursor  = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_paciente FROM pacientes WHERE id_usuario = %s", (current_user.id,))
    pac = cursor.fetchone()
    if not pac:
        cursor.close(); conn.close()
        return jsonify({'cita': None}) if proxima else jsonify([])
    id_paciente = pac['id_paciente']
    if proxima:
        cursor.execute("""
            SELECT id_cita, fecha_cita, hora_cita, motivo_consulta, estado
            FROM citas
            WHERE id_paciente = %s AND estado = 'PENDIENTE' AND fecha_cita >= CURDATE()
            ORDER BY fecha_cita ASC, hora_cita ASC LIMIT 1
        """, (id_paciente,))
        cita = cursor.fetchone()
        cursor.close(); conn.close()
        if cita:
            cita['fecha_cita'] = str(cita['fecha_cita'])
            cita['hora_cita']  = formato_hora(cita['hora_cita'])
            return jsonify({'cita': cita})
        return jsonify({'cita': None})
    cursor.execute("""
        SELECT id_cita, fecha_cita, hora_cita, motivo_consulta, observaciones, estado, fecha_creacion
        FROM citas WHERE id_paciente = %s
        ORDER BY fecha_cita DESC, hora_cita DESC
    """, (id_paciente,))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    for r in rows:
        r['fecha_cita']     = str(r['fecha_cita'])
        r['hora_cita']      = formato_hora(r['hora_cita'])
        r['fecha_creacion'] = str(r['fecha_creacion'])
    return jsonify(rows)

@citas_bp.route('/api/mis-citas', methods=['POST'])
@login_required
def agendar_mi_cita():
    if current_user.rol != 'PACIENTE':
        return jsonify({'error': 'Acceso no autorizado'}), 403
    data       = request.get_json() or {}
    fecha_cita = (data.get('fecha_cita') or '').strip()
    hora_cita  = (data.get('hora_cita') or '').strip()
    motivo     = (data.get('motivo_consulta') or '').strip()
    if not all([fecha_cita, hora_cita, motivo]):
        return jsonify({'error': 'Todos los campos son obligatorios.'}), 400
    try:
        fecha_hora = datetime.strptime(f"{fecha_cita} {hora_cita}", "%Y-%m-%d %H:%M")
    except ValueError:
        return jsonify({'error': 'Formato de fecha u hora inválido.'}), 400
    if fecha_hora < datetime.now() + timedelta(hours=24):
        return jsonify({'error': 'La cita debe agendarse con al menos 24 horas de anticipación.'}), 400
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_paciente FROM pacientes WHERE id_usuario = %s", (current_user.id,))
    pac = cursor.fetchone()
    if not pac:
        cursor.close(); conn.close()
        return jsonify({'error': 'No tienes un expediente registrado. Contacta a tu nutriólogo.'}), 404
    id_paciente = pac['id_paciente']
    cursor.execute("SELECT id_cita FROM citas WHERE id_paciente = %s AND estado = 'PENDIENTE' LIMIT 1", (id_paciente,))
    if cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'Ya tienes una cita activa programada.'}), 409
    cursor.execute("SELECT id_cita FROM citas WHERE fecha_cita = %s AND hora_cita = %s AND estado != 'CANCELADA' LIMIT 1", (fecha_cita, hora_cita))
    if cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'El horario seleccionado no está disponible.'}), 409
    cursor.execute("""
        INSERT INTO citas (id_paciente, fecha_cita, hora_cita, motivo_consulta, estado, fecha_creacion)
        VALUES (%s, %s, %s, %s, 'PENDIENTE', NOW())
    """, (id_paciente, fecha_cita, hora_cita, motivo))

    fecha_fmt = datetime.strptime(fecha_cita, "%Y-%m-%d").strftime("%d/%m/%Y")
    _crear_notificacion(cursor, current_user.id,
        f"📅 Tu cita fue agendada para el {fecha_fmt} a las {hora_cita}. Motivo: {motivo}.")
    id_nutri = _id_nutriologo()
    if id_nutri:
        _crear_notificacion(cursor, id_nutri,
            f"📅 Nueva cita de {current_user.nombre} para el {fecha_fmt} a las {hora_cita}. Motivo: {motivo}.")

    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'mensaje': 'Cita registrada correctamente'}), 201

@citas_bp.route('/api/mis-citas/<int:id_cita>', methods=['DELETE'])
@login_required
def cancelar_mi_cita(id_cita):
    if current_user.rol != 'PACIENTE':
        return jsonify({'error': 'Acceso no autorizado'}), 403
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_paciente FROM pacientes WHERE id_usuario = %s", (current_user.id,))
    pac = cursor.fetchone()
    if not pac:
        cursor.close(); conn.close()
        return jsonify({'error': 'Paciente no encontrado.'}), 404
    cursor.execute("SELECT c.id_cita, c.fecha_cita, c.hora_cita FROM citas c WHERE c.id_cita = %s AND c.id_paciente = %s", (id_cita, pac['id_paciente']))
    cita = cursor.fetchone()
    if not cita:
        cursor.close(); conn.close()
        return jsonify({'error': 'La cita no se encuentra registrada.'}), 404
    cursor.execute("UPDATE citas SET estado = 'CANCELADA', fecha_modificacion = NOW() WHERE id_cita = %s", (id_cita,))

    fecha_fmt = cita['fecha_cita'].strftime("%d/%m/%Y") if hasattr(cita['fecha_cita'], 'strftime') else str(cita['fecha_cita'])
    hora_fmt  = formato_hora(cita['hora_cita'])
    _crear_notificacion(cursor, current_user.id,
        f"❌ Cancelaste tu cita del {fecha_fmt} a las {hora_fmt}. Contáctanos para reagendar.")
    id_nutri = _id_nutriologo()
    if id_nutri:
        _crear_notificacion(cursor, id_nutri,
            f"❌ {current_user.nombre} canceló su cita del {fecha_fmt} a las {hora_fmt}.")

    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'mensaje': 'Cita cancelada correctamente'})

@citas_bp.route('/api/citas/disponibilidad', methods=['GET'])
@login_required
def disponibilidad():
    fecha = request.args.get('fecha')
    if not fecha:
        return jsonify({'ocupadas': []})
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT TIME_FORMAT(hora_cita, '%H:%i') AS hora FROM citas WHERE fecha_cita = %s AND estado != 'CANCELADA'", (fecha,))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify({'ocupadas': [formato_hora(r['hora']) if r.get('hora') else r['hora'] for r in rows]})

# ─── RUTAS NOTIFICACIONES ────────────────────────────────

@citas_bp.route('/api/notificaciones', methods=['GET'])
@login_required
def get_notificaciones():
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id_notificacion, mensaje, leida, fecha_envio
        FROM notificaciones
        WHERE id_usuario = %s AND tipo = 'INTERNA'
        ORDER BY fecha_envio DESC LIMIT 30
    """, (current_user.id,))
    rows = cursor.fetchall()
    cursor.execute("SELECT COUNT(*) AS total FROM notificaciones WHERE id_usuario = %s AND tipo = 'INTERNA' AND leida = 0", (current_user.id,))
    no_leidas = cursor.fetchone()['total']
    cursor.close(); conn.close()
    for r in rows:
        r['fecha_envio'] = r['fecha_envio'].strftime("%d/%m/%Y %H:%M") if r.get('fecha_envio') else ''
    return jsonify({'notificaciones': rows, 'no_leidas': no_leidas})

@citas_bp.route('/api/notificaciones/leer', methods=['PUT'])
@login_required
def marcar_leidas():
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notificaciones SET leida = 1 WHERE id_usuario = %s AND tipo = 'INTERNA' AND leida = 0", (current_user.id,))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'mensaje': 'Notificaciones marcadas como leídas'})

@citas_bp.route('/api/notificaciones/<int:id_notif>/leer', methods=['PUT'])
@login_required
def marcar_una_leida(id_notif):
    conn   = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE notificaciones SET leida = 1 WHERE id_notificacion = %s AND id_usuario = %s", (id_notif, current_user.id))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'mensaje': 'Notificación marcada como leída'})