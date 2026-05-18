import os
from flask import Blueprint, request, jsonify, session
from werkzeug.utils import secure_filename
from PYTHON.conection_db.db import get_db_connection  # Ajusta esta ruta si es necesario
from flask_login import current_user

planes_bp = Blueprint('planes', __name__)

# -------------------------------------------------------------------
# 1. RUTA PARA EL NUTRIÓLOGO: Ver el plan de un paciente específico
# -------------------------------------------------------------------
@planes_bp.route('/api/planes/<int:id_usuario>', methods=['GET'])
def verificar_plan_api(id_usuario):
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)
        
        # Traducimos id_usuario a id_paciente
        cursor.execute("SELECT id_paciente FROM pacientes WHERE id_usuario = %s", (id_usuario,))
        paciente = cursor.fetchone()
        
        if not paciente:
            return jsonify({"tiene_plan": False})

        id_real = paciente['id_paciente']
        
        # Buscamos el plan usando el ID real
        cursor.execute("SELECT ruta_pdf FROM planes_alimenticios WHERE id_paciente = %s", (id_real,))
        plan = cursor.fetchone()
        
        if plan and plan['ruta_pdf']:
            return jsonify({"tiene_plan": True, "pdf_url": plan['ruta_pdf']})
        return jsonify({"tiene_plan": False})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conexion' in locals() and conexion.is_connected():
            cursor.close()
            conexion.close()

# -------------------------------------------------------------------
# 2. RUTA PARA EL NUTRIÓLOGO: Subir y asignar el plan
# -------------------------------------------------------------------
@planes_bp.route('/api/planes/upload', methods=['POST'])
def subir_plan_api():
    id_usuario_recibido = request.form.get('id_usuario')
    archivo = request.files.get('pdf')

    if not id_usuario_recibido or not archivo:
        return jsonify({"error": "Faltan datos o archivo."}), 400

    if archivo and archivo.filename.endswith('.pdf'):
        nombre_seguro = secure_filename(archivo.filename)
        ruta_fisica = os.path.join('static', 'pdf_planes', nombre_seguro)
        
        # Asegurarnos de que la carpeta exista
        os.makedirs(os.path.dirname(ruta_fisica), exist_ok=True)
        
        try:
            conexion = get_db_connection()
            cursor = conexion.cursor(dictionary=True)

            # Traducimos el ID de nuevo para guardar correctamente en la BD
            cursor.execute("SELECT id_paciente FROM pacientes WHERE id_usuario = %s", (id_usuario_recibido,))
            resultado = cursor.fetchone()

            if not resultado:
                return jsonify({"error": "No existe un expediente para este usuario."}), 400
            
            id_real_paciente = resultado['id_paciente']

            # Guardamos archivo y generamos ruta web
            archivo.save(ruta_fisica)
            ruta_web = f"/static/pdf_planes/{nombre_seguro}"
            
            # Insertamos o actualizamos en la base de datos
            cursor.execute("SELECT id_plan FROM planes_alimenticios WHERE id_paciente = %s", (id_real_paciente,))
            existe_plan = cursor.fetchone()

            if existe_plan:
                cursor.execute("""
                    UPDATE planes_alimenticios 
                    SET nombre_pdf = %s, ruta_pdf = %s WHERE id_paciente = %s
                """, (nombre_seguro, ruta_web, id_real_paciente))
            else:
                cursor.execute("""
                    INSERT INTO planes_alimenticios (id_paciente, nombre_pdf, ruta_pdf) 
                    VALUES (%s, %s, %s)
                """, (id_real_paciente, nombre_seguro, ruta_web))
                               
            conexion.commit()
            return jsonify({"success": True})
            
        except Exception as e:
            return jsonify({"error": f"Error en BD: {e}"}), 500
        finally:
            if 'conexion' in locals() and conexion.is_connected():
                cursor.close()
                conexion.close()
    else:
        return jsonify({"error": "Formato inválido. Solo PDF."}), 400

# -------------------------------------------------------------------
# 3. RUTA PARA EL PACIENTE: Consultar su propio plan
# -------------------------------------------------------------------
# -------------------------------------------------------------------
# 3. RUTA PARA EL PACIENTE: Consultar su propio plan
# -------------------------------------------------------------------
@planes_bp.route('/api/mi-plan', methods=['GET'])
def mi_plan_api():
    # Usamos flask_login para saber si hay alguien conectado
    if not current_user.is_authenticated:
        return jsonify({"error": "No autorizado"}), 401

    # Extraemos el ID mágicamente gracias a flask_login
    id_usuario_sesion = current_user.get_id()
    
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)
        
        # Buscamos a este usuario en la tabla de pacientes
        cursor.execute("SELECT id_paciente FROM pacientes WHERE id_usuario = %s", (id_usuario_sesion,))
        paciente = cursor.fetchone()
        
        if not paciente:
            return jsonify({"tiene_plan": False})

        # Si sí existe como paciente, buscamos su PDF
        cursor.execute("SELECT nombre_pdf, ruta_pdf FROM planes_alimenticios WHERE id_paciente = %s", (paciente['id_paciente'],))
        plan = cursor.fetchone()
        
        if plan and plan['ruta_pdf']:
            # ¡Bingo! Encontramos el plan, se lo mandamos a tu JS
            return jsonify({
                "tiene_plan": True, 
                "nombre_plan": plan['nombre_pdf'],
                "pdf_url": plan['ruta_pdf']
            })
            
        # Si no tiene plan asignado
        return jsonify({"tiene_plan": False})
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conexion' in locals() and conexion.is_connected():
            cursor.close()
            conexion.close()

# -------------------------------------------------------------------
# 4. RUTA PARA EL NUTRIÓLOGO: Eliminar el plan alimenticio
# -------------------------------------------------------------------
@planes_bp.route('/api/planes/<int:id_usuario>', methods=['DELETE'])
def eliminar_plan_api(id_usuario):
    try:
        conexion = get_db_connection()
        cursor = conexion.cursor(dictionary=True)
        
        # Traducir id_usuario a id_paciente
        cursor.execute("SELECT id_paciente FROM pacientes WHERE id_usuario = %s", (id_usuario,))
        paciente = cursor.fetchone()
        
        if not paciente:
            return jsonify({"error": "Paciente no encontrado"}), 404

        id_real = paciente['id_paciente']
        
        # Eliminar el registro de la base de datos
        cursor.execute("DELETE FROM planes_alimenticios WHERE id_paciente = %s", (id_real,))
        conexion.commit()
        
        # (Opcional) Si el registro se borró, respondemos éxito
        if cursor.rowcount > 0:
            return jsonify({"success": True, "message": "Plan alimenticio eliminado correctamente."})
        else:
            return jsonify({"error": "El plan alimenticio no se encuentra registrado."}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'conexion' in locals() and conexion.is_connected():
            cursor.close()
            conexion.close()