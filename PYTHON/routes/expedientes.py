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

            u.nombre_completo,

            p.peso,
            p.estatura,
            p.imc

        FROM expedientes e

        INNER JOIN pacientes p
            ON e.id_paciente = p.id_paciente

        INNER JOIN usuarios u
            ON p.id_usuario = u.id_usuario

        WHERE u.id_usuario = %s
    """

    cursor.execute(sql, (id_usuario,))

    expediente = cursor.fetchone()

    cursor.close()
    conn.close()

    if not expediente:

        return jsonify({
            'error': 'Expediente no encontrado'
        }), 404

    return jsonify(expediente)


    ## -----------------------RUTA PARA CREAR EXPEDIENTE
@expedientes_bp.route('/api/expedientes', methods=['POST'])
def crear_expediente():

    data = request.get_json()

    conn = get_db_connection()

    cursor = conn.cursor(dictionary=True)

    # Buscar paciente por teléfono
    telefono = data['telefono']

    buscar_sql = """SELECT p.id_paciente 
                    FROM pacientes p 
                    INNER JOIN usuarios u 
                        ON p.id_usuario = u.id_usuario 
                    WHERE u.telefono = %s 
                    AND u.rol = 'PACIENTE' 
                    """

    cursor.execute(buscar_sql, (telefono,))

    paciente = cursor.fetchone()

    if not paciente:

        cursor.close()
        conn.close()

        return jsonify({
            'error': 'Paciente no encontrado'
        }), 404

    id_paciente = paciente['id_paciente']

    # Verificar si ya existe expediente
    verificar_sql = """
        SELECT id_expediente
        FROM expedientes
        WHERE id_paciente = %s
    """

    cursor.execute(verificar_sql, (id_paciente,))

    expediente_existente = cursor.fetchone()

    if expediente_existente:

        cursor.close()
        conn.close()

        return jsonify({
            'error': 'El paciente ya tiene un expediente'
        }), 400

    # Insertar expediente
    insert_sql = """
        INSERT INTO expedientes (
            id_paciente,
            objetivo_nutricional,
            diagnostico_inicial,
            observaciones_medicas,
            historial_clinico,
            nuevas_observaciones
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """

    valores = (
        id_paciente,
        data['objetivo_nutricional'],
        data['diagnostico_inicial'],
        data['observaciones_medicas'],
        data['historial_clinico'],
        data.get('nuevas_observaciones')
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

    # Obtener id_paciente del usuario
    sql_paciente = """
        SELECT id_paciente
        FROM pacientes
        WHERE id_usuario = %s
    """

    cursor.execute(sql_paciente, (id_usuario,))
    paciente = cursor.fetchone()

    if not paciente:
        return jsonify({
            'error': 'Paciente no encontrado'
        }), 404

    id_paciente = paciente['id_paciente']

    # Actualizar expediente usando id_paciente
    sql_exp = """
        UPDATE expedientes
        SET
        nuevas_observaciones = COALESCE(%s, nuevas_observaciones),
        objetivo_nutricional = COALESCE(%s, objetivo_nutricional),
        fecha_modificacion = NOW()
    WHERE id_paciente = %s
    """

    valores_exp = (
        data.get('nuevas_observaciones'),
        data.get('objetivo_nutricional'),
        id_paciente
    )

    cursor.execute(sql_exp, valores_exp)

    # Actualizar paciente
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
##
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

#
    cursor.execute(sql_update_paciente, valores_paciente)

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        'success': True,
        'message': 'Expediente actualizado correctamente'
    })


### ----------------ELIMINAR EXPEDIENTE
@expedientes_bp.route('/api/expedientes/<int:id_expediente>', methods=['DELETE'])
def eliminar_expediente(id_expediente):

    conn = get_db_connection()

    cursor = conn.cursor()

    sql = """
        DELETE FROM expedientes
        WHERE id_expediente = %s
    """

    cursor.execute(sql, (id_expediente,))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({
        'success': True
    })

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
