# PYTHON/modules/pacientes/pacientes.py
# ─────────────────────────────────────────────────────────────────────────────
# Módulo de Gestión de Pacientes — CRUD completo
# Rutas API consumidas por nutriologo.js vía fetch
# ─────────────────────────────────────────────────────────────────────────────
from datetime  import datetime, date
from flask     import Blueprint, jsonify, request
from flask_login import login_required, current_user
from flask_bcrypt import generate_password_hash

from PYTHON.conection_db.db import get_db_connection

pacientes_bp = Blueprint('pacientes', __name__, url_prefix='/api')


# ──────────────────────────────────────────────────
# DECORADOR: solo nutriólogo
# ──────────────────────────────────────────────────
def nutriologo_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.rol != 'NUTRIOLOGO':
            return jsonify({'error': 'Acceso no autorizado'}), 403
        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────────────────
# GET /api/pacientes — listar pacientes (con filtros)
# ──────────────────────────────────────────────────
@pacientes_bp.route('/pacientes', methods=['GET'])
@login_required
@nutriologo_required
def listar_pacientes():
    estado         = request.args.get('estado', 'activo').upper()
    q              = request.args.get('q', '').strip()
    con_expediente = request.args.get('con_expediente', 'false').lower() == 'true'

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if estado == 'TODOS':
        estado_cond = "1=1"
        params      = []
    else:
        estado_cond = "u.estado = %s"
        params      = [estado]

    busqueda_cond = ""
    if q:
        busqueda_cond = " AND (u.nombre_completo LIKE %s OR u.telefono LIKE %s OR u.correo LIKE %s)"
        like = f"%{q}%"
        params += [like, like, like]

    exp_join = ""
    exp_cond = ""
    if con_expediente:
        exp_join = "INNER JOIN expedientes e ON p.id_paciente = e.id_paciente AND e.estado = 'ACTIVO'"
        exp_cond = ""

    query = f"""
        SELECT u.id_usuario, u.nombre_completo, u.telefono, u.correo,
               u.estado, u.fecha_registro,
               p.id_paciente, p.edad, p.peso, p.estatura, p.imc
        FROM   usuarios u
        INNER  JOIN pacientes p ON u.id_usuario = p.id_usuario
        {exp_join}
        WHERE  u.rol = 'PACIENTE' AND {estado_cond}{busqueda_cond}
        ORDER  BY u.nombre_completo ASC
    """
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close(); conn.close()

    # Serializar decimales / fechas
    result = []
    for r in rows:
        result.append({
            'id_usuario':     r['id_usuario'],
            'nombre_completo':r['nombre_completo'],
            'telefono':       r['telefono'],
            'correo':         r['correo'],
            'estado':         r['estado'],
            'fecha_registro': str(r['fecha_registro']) if r['fecha_registro'] else None,
            'id_paciente':    r['id_paciente'],
            'edad':           r['edad'],
            'peso':           float(r['peso']),
            'estatura':       float(r['estatura']),
            'imc':            float(r['imc']) if r['imc'] else None,
        })
    return jsonify(result)


# ──────────────────────────────────────────────────
# GET /api/pacientes/<id> — detalle de un paciente
# ──────────────────────────────────────────────────
@pacientes_bp.route('/pacientes/<int:id_usuario>', methods=['GET'])
@login_required
@nutriologo_required
def detalle_paciente(id_usuario):
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT u.id_usuario, u.nombre_completo, u.telefono, u.correo,
               u.estado, u.fecha_registro,
               p.edad, p.peso, p.estatura, p.imc, p.fecha_modificacion
        FROM   usuarios u
        INNER  JOIN pacientes p ON u.id_usuario = p.id_usuario
        WHERE  u.id_usuario = %s AND u.rol = 'PACIENTE'
    """, (id_usuario,))
    row = cursor.fetchone()
    cursor.close(); conn.close()

    if not row:
        return jsonify({'error': 'Paciente no encontrado'}), 404

    return jsonify({
        'id_usuario':      row['id_usuario'],
        'nombre_completo': row['nombre_completo'],
        'telefono':        row['telefono'],
        'correo':          row['correo'],
        'estado':          row['estado'],
        'fecha_registro':  str(row['fecha_registro']) if row['fecha_registro'] else None,
        'edad':            row['edad'],
        'peso':            float(row['peso']),
        'estatura':        float(row['estatura']),
        'imc':             float(row['imc']) if row['imc'] else None,
    })


# ──────────────────────────────────────────────────
# POST /api/pacientes — registrar nuevo paciente
# ──────────────────────────────────────────────────
@pacientes_bp.route('/pacientes', methods=['POST'])
@login_required
@nutriologo_required
def crear_paciente():
    data = request.get_json(silent=True) or {}

    nombre    = data.get('nombre_completo', '').strip()
    telefono  = data.get('telefono', '').strip()
    correo    = data.get('correo', '').strip()
    contrasena= data.get('contrasena', '')
    edad      = data.get('edad')
    peso      = data.get('peso')
    estatura  = data.get('estatura')

    if not all([nombre, telefono, correo, contrasena, edad, peso, estatura]):
        return jsonify({'error': 'Datos incompletos, favor de llenar todos los campos.'}), 400

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Verificar duplicado
    cursor.execute(
        "SELECT id_usuario FROM usuarios WHERE telefono = %s OR correo = %s",
        (telefono, correo)
    )
    if cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'El paciente ya se encuentra registrado.'}), 409

    try:
        hashed = generate_password_hash(contrasena).decode('utf-8')

        # Insertar en usuarios
        cursor.execute("""
            INSERT INTO usuarios (telefono, nombre_completo, correo, contrasena, rol, estado, fecha_registro)
            VALUES (%s, %s, %s, %s, 'PACIENTE', 'ACTIVO', %s)
        """, (telefono, nombre, correo, hashed, datetime.now()))
        id_usuario = cursor.lastrowid

        # Insertar en pacientes
        cursor.execute("""
            INSERT INTO pacientes (id_usuario, edad, peso, estatura)
            VALUES (%s, %s, %s, %s)
        """, (id_usuario, int(edad), float(peso), float(estatura)))

        # Registrar en historial
        cursor.execute("""
            INSERT INTO historial (id_usuario, accion, descripcion, fecha_accion)
            VALUES (%s, 'REGISTRO_PACIENTE', %s, %s)
        """, (current_user.id, f'Se registró al paciente {nombre}', datetime.now()))

        conn.commit()
        cursor.close(); conn.close()
        return jsonify({'message': 'Paciente registrado correctamente', 'id_usuario': id_usuario}), 201

    except Exception as e:
        conn.rollback(); cursor.close(); conn.close()
        return jsonify({'error': f'Error al registrar paciente: {str(e)}'}), 500


# ──────────────────────────────────────────────────
# PUT /api/pacientes/<id> — modificar paciente
# ──────────────────────────────────────────────────
@pacientes_bp.route('/pacientes/<int:id_usuario>', methods=['PUT'])
@login_required
@nutriologo_required
def modificar_paciente(id_usuario):
    data = request.get_json(silent=True) or {}

    nombre   = data.get('nombre_completo', '').strip()
    correo   = data.get('correo', '').strip()
    edad     = data.get('edad')
    peso     = data.get('peso')
    estatura = data.get('estatura')

    if not nombre or not correo:
        return jsonify({'error': 'El nombre y correo son obligatorios.'}), 400

    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Verificar que existe
    cursor.execute(
        "SELECT id_usuario FROM usuarios WHERE id_usuario = %s AND rol = 'PACIENTE'",
        (id_usuario,)
    )
    if not cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'No se puede actualizar porque el paciente no existe.'}), 404

    # Verificar correo duplicado (excluyendo al mismo usuario)
    cursor.execute(
        "SELECT id_usuario FROM usuarios WHERE correo = %s AND id_usuario != %s",
        (correo, id_usuario)
    )
    if cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'El correo electrónico ya está registrado por otro usuario.'}), 409

    try:
        cursor.execute("""
            UPDATE usuarios SET nombre_completo = %s, correo = %s WHERE id_usuario = %s
        """, (nombre, correo, id_usuario))

        if edad or peso or estatura:
            campos = []
            vals   = []
            if edad:     campos.append('edad = %s');     vals.append(int(edad))
            if peso:     campos.append('peso = %s');     vals.append(float(peso))
            if estatura: campos.append('estatura = %s'); vals.append(float(estatura))
            campos.append('fecha_modificacion = %s'); vals.append(datetime.now())
            vals.append(id_usuario)
            cursor.execute(
                f"UPDATE pacientes SET {', '.join(campos)} WHERE id_usuario = %s", vals
            )

        # Historial
        cursor.execute("""
            INSERT INTO historial (id_usuario, accion, descripcion, fecha_accion)
            VALUES (%s, 'MODIFICACION_PACIENTE', %s, %s)
        """, (current_user.id, f'Modificación del paciente id={id_usuario}', datetime.now()))

        conn.commit(); cursor.close(); conn.close()
        return jsonify({'message': 'Paciente actualizado correctamente'})

    except Exception as e:
        conn.rollback(); cursor.close(); conn.close()
        return jsonify({'error': f'Error al modificar: {str(e)}'}), 500


# ──────────────────────────────────────────────────
# POST /api/pacientes/<id>/baja — dar de baja (lógica)
# ──────────────────────────────────────────────────
@pacientes_bp.route('/pacientes/<int:id_usuario>/baja', methods=['POST'])
@login_required
@nutriologo_required
def dar_baja(id_usuario):
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Verificar existencia
    cursor.execute(
        "SELECT id_usuario FROM usuarios WHERE id_usuario = %s AND rol = 'PACIENTE' AND estado = 'ACTIVO'",
        (id_usuario,)
    )
    if not cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'El paciente no se encuentra registrado o ya está inactivo.'}), 404

    # Verificar citas activas
    cursor.execute("""
        SELECT COUNT(*) AS total FROM citas c
        INNER JOIN pacientes p ON c.id_paciente = p.id_paciente
        WHERE p.id_usuario = %s AND c.estado IN ('PENDIENTE', 'CONFIRMADA')
    """, (id_usuario,))
    row = cursor.fetchone()
    if row and row['total'] > 0:
        cursor.close(); conn.close()
        return jsonify({'error': 'No se puede dar de baja: el paciente tiene citas activas.'}), 409

    # Verificar expedientes activos
    cursor.execute("""
        SELECT COUNT(*) AS total FROM expedientes e
        INNER JOIN pacientes p ON e.id_paciente = p.id_paciente
        WHERE p.id_usuario = %s AND e.estado = 'ACTIVO'
    """, (id_usuario,))
    row = cursor.fetchone()
    if row and row['total'] > 0:
        cursor.close(); conn.close()
        return jsonify({'error': 'No se puede dar de baja: el paciente tiene expedientes activos.'}), 409

    try:
        cursor.execute(
            "UPDATE usuarios SET estado = 'INACTIVO' WHERE id_usuario = %s", (id_usuario,)
        )
        cursor.execute("""
            INSERT INTO historial (id_usuario, accion, descripcion, fecha_accion)
            VALUES (%s, 'BAJA_PACIENTE', %s, %s)
        """, (current_user.id, f'Baja lógica del paciente id={id_usuario}', datetime.now()))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({'message': 'Paciente eliminado correctamente'})

    except Exception as e:
        conn.rollback(); cursor.close(); conn.close()
        return jsonify({'error': f'Error al dar de baja: {str(e)}'}), 500


# ──────────────────────────────────────────────────
# POST /api/pacientes/<id>/alta — reactivar paciente
# ──────────────────────────────────────────────────
@pacientes_bp.route('/pacientes/<int:id_usuario>/alta', methods=['POST'])
@login_required
@nutriologo_required
def dar_alta(id_usuario):
    conn   = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT id_usuario FROM usuarios WHERE id_usuario = %s AND rol = 'PACIENTE' AND estado = 'INACTIVO'",
        (id_usuario,)
    )
    if not cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify({'error': 'El paciente no se encuentra inactivo.'}), 404

    try:
        cursor.execute(
            "UPDATE usuarios SET estado = 'ACTIVO' WHERE id_usuario = %s", (id_usuario,)
        )
        cursor.execute("""
            INSERT INTO historial (id_usuario, accion, descripcion, fecha_accion)
            VALUES (%s, 'ALTA_PACIENTE', %s, %s)
        """, (current_user.id, f'Alta del paciente id={id_usuario}', datetime.now()))
        conn.commit(); cursor.close(); conn.close()
        return jsonify({'message': 'Paciente dado de alta correctamente'})

    except Exception as e:
        conn.rollback(); cursor.close(); conn.close()
        return jsonify({'error': f'Error al dar de alta: {str(e)}'}), 500
