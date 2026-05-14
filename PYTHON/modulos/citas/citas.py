# PYTHON/modulos/pacientes/citas/citas.py
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from PYTHON.conection_db.db import get_db_connection
 
citas_bp = Blueprint('citas', __name__)

def formato_hora(hora):
    """Convierte timedelta o string de hora a formato HH:MM"""
    if hora is None:
        return None
    from datetime import timedelta
    if isinstance(hora, timedelta):
        total = int(hora.total_seconds())
        h = total // 3600
        m = (total % 3600) // 60
        return f"{h:02d}:{m:02d}"
    return str(hora)[:5]  # toma HH:MM de HH:MM:SS

 
def nutriologo_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'NUTRIOLOGO':
            return jsonify({'error': 'Acceso no autorizado'}), 403
        return f(*args, **kwargs)
    return decorated
 
 
# ─────────────────────────────────────────────────────────
# RUTAS NUTRIÓLOGO
# ─────────────────────────────────────────────────────────
 
# GET /api/citas/mes?year=2026&month=4
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
 
 
# GET /api/citas/dia?fecha=2026-04-19
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
 
 
# POST /api/citas  — Nutriólogo agenda cita
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
 
    cursor.execute(
        "SELECT id_usuario FROM usuarios WHERE telefono = %s AND rol = 'PACIENTE' AND estado = 'ACTIVO'",
        (telefono,)
    )
    usuario = cursor.fetchone()
    if not usuario:
        cursor.close(); conn.close()
        return jsonify({'error': 'No se encontró un paciente activo con ese teléfono.'}), 404
 
    cursor.execute(
        "SELECT id_paciente FROM pacientes WHERE id_usuario = %s",
        (usuario['id_usuario'],)
    )
    paciente = cursor.fetchone()
    if not paciente:
        cursor.close(); conn.close()
        return jsonify({'error': 'El paciente no tiene expediente registrado en el sistema.'}), 404
 
    id_paciente = paciente['id_paciente']
 
    cursor.execute(
        "SELECT id_cita FROM citas WHERE id_paciente = %s AND estado = 'PENDIENTE' LIMIT 1",
        (id_paciente,)
    )
    if cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'El paciente ya tiene una cita activa programada.'}), 409
 
    cursor.execute(
        "SELECT id_cita FROM citas WHERE fecha_cita = %s AND hora_cita = %s AND estado != 'CANCELADA' LIMIT 1",
        (fecha_cita, hora_cita)
    )
    if cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'El horario seleccionado no está disponible.'}), 409
 
    cursor.execute("""
        INSERT INTO citas (id_paciente, fecha_cita, hora_cita, motivo_consulta, observaciones, estado, fecha_creacion)
        VALUES (%s, %s, %s, %s, %s, 'PENDIENTE', NOW())
    """, (id_paciente, fecha_cita, hora_cita, motivo, observaciones))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'mensaje': 'Cita registrada correctamente'}), 201
 
 
# DELETE /api/citas/<id>  — Nutriólogo cancela cita
@citas_bp.route('/api/citas/<int:id_cita>', methods=['DELETE'])
@login_required
@nutriologo_required
def cancelar_cita(id_cita):
    data   = request.get_json(silent=True) or {}
    motivo = data.get('motivo_cancelacion', 'Cancelada por el nutriólogo')
 
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id_cita FROM citas WHERE id_cita = %s", (id_cita,))
    if not cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'La cita no se encuentra registrada.'}), 404
 
    cursor.execute("""
        UPDATE citas
        SET estado = 'CANCELADA',
            observaciones = CONCAT(IFNULL(observaciones,''), ' | Motivo cancelación: ', %s),
            fecha_modificacion = NOW()
        WHERE id_cita = %s
    """, (motivo, id_cita))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'mensaje': 'Cita cancelada correctamente'})
 
 
# ─────────────────────────────────────────────────────────
# RUTAS PACIENTE
# ─────────────────────────────────────────────────────────

# GET /api/mi-perfil  — datos del paciente para el hero
@citas_bp.route('/api/mi-perfil', methods=['GET'])
@login_required
def mi_perfil():
    if current_user.rol != 'PACIENTE':
        return jsonify({'error': 'Acceso no autorizado'}), 403

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT p.peso, p.imc, p.estatura, p.edad
        FROM pacientes p
        WHERE p.id_usuario = %s
    """, (current_user.id,))
    paciente = cursor.fetchone()

    # Buscar si tiene plan activo
    plan = None
    try:
        cursor.execute("""
            SELECT e.nombre_plan
            FROM expedientes e
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


# GET /api/mis-citas  |  GET /api/mis-citas?proxima=true
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
            ORDER BY fecha_cita ASC, hora_cita ASC
            LIMIT 1
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
        FROM citas
        WHERE id_paciente = %s
        ORDER BY fecha_cita DESC, hora_cita DESC
    """, (id_paciente,))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    for r in rows:
        r['fecha_cita']     = str(r['fecha_cita'])
        r['hora_cita']      = formato_hora(r['hora_cita'])
        r['fecha_creacion'] = str(r['fecha_creacion'])
    return jsonify(rows)
 
 
# POST /api/mis-citas  — Paciente agenda su cita
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
 
    cursor.execute(
        "SELECT id_cita FROM citas WHERE id_paciente = %s AND estado = 'PENDIENTE' LIMIT 1",
        (id_paciente,)
    )
    if cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'Ya tienes una cita activa programada.'}), 409
 
    cursor.execute(
        "SELECT id_cita FROM citas WHERE fecha_cita = %s AND hora_cita = %s AND estado != 'CANCELADA' LIMIT 1",
        (fecha_cita, hora_cita)
    )
    if cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'El horario seleccionado no está disponible.'}), 409
 
    cursor.execute("""
        INSERT INTO citas (id_paciente, fecha_cita, hora_cita, motivo_consulta, estado, fecha_creacion)
        VALUES (%s, %s, %s, %s, 'PENDIENTE', NOW())
    """, (id_paciente, fecha_cita, hora_cita, motivo))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'mensaje': 'Cita registrada correctamente'}), 201
 
 
# DELETE /api/mis-citas/<id>  — Paciente cancela su cita
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
 
    cursor.execute(
        "SELECT id_cita FROM citas WHERE id_cita = %s AND id_paciente = %s",
        (id_cita, pac['id_paciente'])
    )
    if not cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'La cita no se encuentra registrada.'}), 404
 
    cursor.execute("""
        UPDATE citas SET estado = 'CANCELADA', fecha_modificacion = NOW()
        WHERE id_cita = %s
    """, (id_cita,))
    conn.commit()
    cursor.close(); conn.close()
    return jsonify({'mensaje': 'Cita cancelada correctamente'})
 
 
# GET /api/citas/disponibilidad?fecha=2026-04-20
@citas_bp.route('/api/citas/disponibilidad', methods=['GET'])
@login_required
def disponibilidad():
    fecha = request.args.get('fecha')
    if not fecha:
        return jsonify({'ocupadas': []})
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT TIME_FORMAT(hora_cita, '%H:%i') AS hora
        FROM citas
        WHERE fecha_cita = %s AND estado != 'CANCELADA'
    """, (fecha,))
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify({'ocupadas': [formato_hora(r['hora']) if r.get('hora') else r['hora'] for r in rows]})


# GET /api/mi-plan  — plan alimenticio del paciente
@citas_bp.route('/api/mi-plan', methods=['GET'])
@login_required
def mi_plan():
    if current_user.rol != 'PACIENTE':
        return jsonify({'error': 'Acceso no autorizado'}), 403

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT e.nombre_plan, e.pdf_url
            FROM expedientes e
            JOIN pacientes p ON e.id_paciente = p.id_paciente
            WHERE p.id_usuario = %s AND e.estado = 'ACTIVO'
            ORDER BY e.fecha_creacion DESC LIMIT 1
        """, (current_user.id,))
        exp = cursor.fetchone()
        cursor.close(); conn.close()

        if exp and exp.get('pdf_url'):
            return jsonify({'tiene_plan': True, 'nombre_plan': exp.get('nombre_plan', 'Plan alimenticio'), 'pdf_url': exp['pdf_url']})
        return jsonify({'tiene_plan': False})
    except Exception:
        cursor.close(); conn.close()
        return jsonify({'tiene_plan': False})