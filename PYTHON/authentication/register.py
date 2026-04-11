from flask import Blueprint, request, redirect, url_for, flash
from db import get_connection
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

register_bp = Blueprint('register', __name__)

@register_bp.route('/register', methods=['POST'])
def register():

    telefono = request.form['telefono']
    nombre = request.form['nombre_completo']
    correo = request.form['correo']
    contrasena = request.form['contrasena']
    rol = request.form['rol']

    # Encriptar contraseña
    password_hash = bcrypt.generate_password_hash(contrasena).decode('utf-8')

    conexion = get_connection()
    cursor = conexion.cursor()

    try:
        cursor.execute("""
            INSERT INTO usuarios 
            (telefono, nombre_completo, correo, contrasena, rol)
            VALUES (%s, %s, %s, %s, %s)
        """, (telefono, nombre, correo, password_hash, rol))

        conexion.commit()
        flash("Usuario registrado correctamente")

    except Exception as e:
        flash("Error: usuario ya existe o datos inválidos")

    finally:
        cursor.close()
        conexion.close()

    return redirect('/login')