from flask import Blueprint
from flask import render_template
from flask import jsonify
from flask import request
from PYTHON.conection_db.db import get_db_connection
from flask_login import login_required, current_user

expedientes_bp = Blueprint('expedientes', __name__)

@expedientes_bp.route('/expedientes')
def vista_expedientes():
    return render_template('expedientes.html')

@expedientes_bp.route('/api/pacientes')
def obtener_pacientes():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    estado = request.args.get('estado')
    busqueda = request.args.get('q', '')

    sql = """
        SELECT *
        FROM usuarios
        WHERE rol = 'PACIENTE'
    """

    valores = []

    if estado:
        sql += " AND estado = %s"
        valores.append(estado.upper())

    if busqueda:
        sql += " AND nombre_completo LIKE %s"
        valores.append(f"%{busqueda}%")

    cursor.execute(sql, valores)

    pacientes = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(pacientes)


## -----------------------RUTA PARA OBTENER EXPEDIENTE
@expedientes_bp.route('/api/expedientes/<int:id_usuario>')
def obtener_expediente(id_usuario):

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT
            e.id_expediente,
            e.objetivo_nutricional,
            e.diagnostico_inicial,
            e.observaciones_medicas,
            e.historial_clinico,
            e.nuevas_observaciones,
            e.fecha_creacion,
            e.fecha_modificacion,

            u.nombre_completo,
            u.correo,

            p.peso,
            p.estatura,
            p.imc

        FROM usuarios u

        INNER JOIN pacientes p
            ON u.id_usuario = p.id_usuario

        LEFT JOIN expedientes e
            ON p.id_paciente = e.id_paciente
            AND e.estado = 'ACTIVO'

        WHERE u.id_usuario = %s
    """

    cursor.execute(sql, (id_usuario,))
    expediente = cursor.fetchone()

    cursor.close()
    conn.close()

    if not expediente or not expediente['id_expediente']:
        return jsonify({
            'error': 'No existe un expediente para este paciente'
        }), 404

    return jsonify(expediente)

    ## -----------------------RUTA PARA CREAR EXPEDIENTE
@expedientes_bp.route('/api/expedientes', methods=['POST'])
def crear_expediente():

    data = request.get_json()

    nombre_usuario = data.get('nombre_usuario')
    correo = data.get('correo')

    objetivo = data.get('objetivo_nutricional')
    diagnostico = data.get('diagnostico_inicial')
    observaciones = data.get('observaciones_medicas')
    historial = data.get('historial_clinico')
    nuevas_observaciones = data.get('nuevas_observaciones')

    if not correo or not objetivo or not diagnostico or not observaciones or not historial:
        return jsonify({
            'error': 'Todos los datos son obligatorios, favor de rellenarlos'
        }), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    buscar_sql = """
        SELECT p.id_paciente
        FROM pacientes p
        INNER JOIN usuarios u
            ON p.id_usuario = u.id_usuario
        WHERE 
            (u.correo = %s OR u.nombre_completo = %s)
            AND u.rol = 'PACIENTE'
    """

    cursor.execute(buscar_sql, (correo, nombre_usuario))
    paciente = cursor.fetchone()

    if not paciente:
        cursor.close()
        conn.close()

        return jsonify({
            'error': 'Paciente no encontrado'
        }), 404

    id_paciente = paciente['id_paciente']

    verificar_sql = """
        SELECT id_expediente
        FROM expedientes
        WHERE id_paciente = %s
        AND estado = 'ACTIVO'
    """

    cursor.execute(verificar_sql, (id_paciente,))
    expediente_existente = cursor.fetchone()

    if expediente_existente:
        cursor.close()
        conn.close()

        return jsonify({
            'error': 'El paciente ya tiene un expediente'
        }), 400

    insert_sql = """
        INSERT INTO expedientes (
            id_paciente,
            objetivo_nutricional,
            diagnostico_inicial,
            observaciones_medicas,
            historial_clinico,
            nuevas_observaciones,
            fecha_creacion,
            fecha_modificacion
        )
        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NULL)
    """

    valores = (
        id_paciente,
        objetivo,
        diagnostico,
        observaciones,
        historial,
        nuevas_observaciones
    )

    cursor.execute(insert_sql, valores)
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        'success': True,
        'message': 'Expediente creado correctamente'
    })


## -----------actualizar expediente
@expedientes_bp.route('/api/expedientes/<int:id_usuario>', methods=['PUT'])
def actualizar_expediente(id_usuario):

    data = request.get_json()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    sql_paciente = """
        SELECT p.id_paciente, e.id_expediente
        FROM pacientes p
        LEFT JOIN expedientes e
            ON p.id_paciente = e.id_paciente
            AND e.estado = 'ACTIVO'
        WHERE p.id_usuario = %s
    """

    cursor.execute(sql_paciente, (id_usuario,))
    paciente = cursor.fetchone()

    if not paciente or not paciente['id_expediente']:
        cursor.close()
        conn.close()

        return jsonify({
            'error': 'No se puede actualizar porque el expediente no existe'
        }), 404

    id_paciente = paciente['id_paciente']

    sql_exp = """
        UPDATE expedientes
        SET
            nuevas_observaciones = COALESCE(%s, nuevas_observaciones),
            objetivo_nutricional = COALESCE(%s, objetivo_nutricional),
            fecha_modificacion = NOW()
        WHERE id_paciente = %s
        AND estado = 'ACTIVO'
    """

    valores_exp = (
        data.get('nuevas_observaciones') or None,
        data.get('objetivo_nutricional') or None,
        id_paciente
    )

    sql_update_paciente = """
        UPDATE pacientes
        SET
            peso = COALESCE(%s, peso),
            estatura = COALESCE(%s, estatura),
            fecha_modificacion = NOW()
        WHERE id_paciente = %s
    """

    valores_paciente = (
        data.get('peso'),
        data.get('estatura'),
        id_paciente
    )

    try:
        cursor.execute(sql_exp, valores_exp)
        cursor.execute(sql_update_paciente, valores_paciente)

        conn.commit()

        return jsonify({
            'success': True,
            'message': 'Expediente actualizado correctamente'
        })

    except Exception as e:
        conn.rollback()

        return jsonify({
            'error': str(e)
        }), 500

    finally:
        cursor.close()
        conn.close()

### ----------------ELIMINAR EXPEDIENTE
@expedientes_bp.route('/api/expedientes/<int:id_expediente>', methods=['DELETE'])
@login_required
def eliminar_expediente(id_expediente):

    data = request.get_json()
    dato_confirmacion = data.get('dato_confirmacion')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    buscar_sql = """
        SELECT
            e.id_expediente,
            p.id_paciente,
            u.id_usuario,
            u.nombre_completo,
            u.telefono,
            u.correo
        FROM expedientes e
        INNER JOIN pacientes p
            ON e.id_paciente = p.id_paciente
        INNER JOIN usuarios u
            ON p.id_usuario = u.id_usuario
        WHERE e.id_expediente = %s
    """

    cursor.execute(buscar_sql, (id_expediente,))
    expediente = cursor.fetchone()

    if not expediente:
        cursor.close()
        conn.close()
        return jsonify({
            'error': 'El expediente no se encuentra registrado'
        }), 404

    if dato_confirmacion != expediente['telefono'] and dato_confirmacion != expediente['correo']:
        cursor.close()
        conn.close()
        return jsonify({
            'error': 'El expediente no se encuentra registrado'
        }), 404

    citas_sql = """
        SELECT COUNT(*) AS total
        FROM citas
        WHERE id_paciente = %s
        AND estado IN ('PENDIENTE', 'CONFIRMADA')
    """

    cursor.execute(citas_sql, (expediente['id_paciente'],))
    citas = cursor.fetchone()

    if citas['total'] > 0:
        cursor.close()
        conn.close()
        return jsonify({
            'error': 'No se puede eliminar el expediente porque tiene citas pendientes o activas'
        }), 400

    try:
        historial_sql = """
            INSERT INTO historial (
                id_usuario,
                accion,
                descripcion
            )
            VALUES (%s, %s, %s)
        """

        cursor.execute(historial_sql, (
            expediente['id_usuario'],
            'ELIMINACION_EXPEDIENTE',
            'Se eliminó el expediente del paciente ' + expediente['nombre_completo']
        ))

        delete_sql = """
            DELETE FROM expedientes
            WHERE id_expediente = %s
        """

        cursor.execute(delete_sql, (id_expediente,))

        conn.commit()

        return jsonify({
            'success': True,
            'message': 'Expediente eliminado correctamente'
        })

    except Exception as e:
        conn.rollback()
        return jsonify({
            'error': str(e)
        }), 500

    finally:
        cursor.close()
        conn.close()


@expedientes_bp.route('/api/expedientes/eliminar-por-dato', methods=['DELETE'])
@login_required
def eliminar_expediente_por_dato():

    data = request.get_json()
    dato = data.get('dato')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    buscar_sql = """
        SELECT
            e.id_expediente,
            p.id_paciente,
            u.id_usuario,
            u.nombre_completo,
            u.telefono,
            u.correo
        FROM expedientes e
        INNER JOIN pacientes p
            ON e.id_paciente = p.id_paciente
        INNER JOIN usuarios u
            ON p.id_usuario = u.id_usuario
        WHERE (u.telefono = %s OR u.correo = %s)
        AND e.estado = 'ACTIVO'
    """

    cursor.execute(buscar_sql, (dato, dato))
    expediente = cursor.fetchone()

    if not expediente:
        cursor.close()
        conn.close()

        return jsonify({
            'error': 'El expediente no se encuentra registrado'
        }), 404

    citas_sql = """
        SELECT COUNT(*) AS total
        FROM citas
        WHERE id_paciente = %s
        AND estado IN ('PENDIENTE', 'CONFIRMADA')
    """

    cursor.execute(citas_sql, (expediente['id_paciente'],))
    citas = cursor.fetchone()

    if citas['total'] > 0:
        cursor.close()
        conn.close()

        return jsonify({
            'error': 'No se puede eliminar el expediente porque tiene citas pendientes o activas'
        }), 400

    try:
        historial_sql = """
            INSERT INTO historial (
                id_usuario,
                accion,
                descripcion
            )
            VALUES (%s, %s, %s)
        """

        cursor.execute(historial_sql, (
            expediente['id_usuario'],
            'ELIMINACION_EXPEDIENTE',
            'Se eliminó el expediente del paciente ' + expediente['nombre_completo']
        ))

        delete_sql = """
            DELETE FROM expedientes
            WHERE id_expediente = %s
        """

        cursor.execute(delete_sql, (expediente['id_expediente'],))

        conn.commit()

        return jsonify({
            'success': True,
            'message': 'Expediente eliminado correctamente'
        })

    except Exception as e:
        conn.rollback()

        return jsonify({
            'error': str(e)
        }), 500

    finally:
        cursor.close()
        conn.close()


@expedientes_bp.route('/api/expedientes/consultar-por-dato', methods=['GET'])
@login_required
def consultar_expediente_por_dato():

    dato = request.args.get('dato')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT
            e.id_expediente,
            e.objetivo_nutricional,
            e.diagnostico_inicial,
            e.observaciones_medicas,
            e.historial_clinico,
            e.nuevas_observaciones,
            e.fecha_creacion,
            e.fecha_modificacion,

            u.id_usuario,
            u.nombre_completo,
            u.correo,
            u.telefono,

            p.peso,
            p.estatura,
            p.imc

        FROM usuarios u
        INNER JOIN pacientes p
            ON u.id_usuario = p.id_usuario
        INNER JOIN expedientes e
            ON p.id_paciente = e.id_paciente

        WHERE (u.telefono = %s OR u.correo = %s)
        AND u.rol = 'PACIENTE'
    """

    cursor.execute(sql, (dato, dato))
    expediente = cursor.fetchone()

    cursor.close()
    conn.close()

    if not expediente:
        return jsonify({
            'error': 'No existe un expediente para este paciente'
        }), 404

    return jsonify(expediente)        


#-------------------------------Paciente consulta expediente
@expedientes_bp.route('/api/paciente/expediente', methods=['GET'])
@login_required
def obtener_mi_expediente():

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    sql = """
        SELECT
            e.id_expediente,
            e.objetivo_nutricional,
            e.diagnostico_inicial,
            e.observaciones_medicas,
            e.historial_clinico,
            e.nuevas_observaciones,
            p.peso,
            p.estatura,
            p.imc,
            u.nombre_completo,
            u.correo
        FROM usuarios u
        INNER JOIN pacientes p
            ON u.id_usuario = p.id_usuario
        INNER JOIN expedientes e
            ON p.id_paciente = e.id_paciente
        WHERE u.id_usuario = %s
    """

    cursor.execute(sql, (current_user.id,))
    expediente = cursor.fetchone()

    cursor.close()
    conn.close()

    if not expediente:
        return jsonify({
            'error': 'No existe expediente para este paciente'
        }), 404

    return jsonify(expediente)
