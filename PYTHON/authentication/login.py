# PYTHON/authentication/login.py
from flask_login import UserMixin
from flask_bcrypt import check_password_hash


class User(UserMixin):
    def __init__(self, id_usuario, correo, nombre_completo, rol):
        self.id             = id_usuario
        self.correo         = correo
        self.nombre         = nombre_completo
        self.rol            = rol

    def get_id(self):
        return str(self.id)


def verificar_usuario(db_connection, correo, contrasena):
    """
    Verifica credenciales y retorna un objeto User si son correctas, None si no.
    """
    cursor = db_connection.cursor(dictionary=True)
    query  = """
        SELECT id_usuario, correo, nombre_completo, contrasena, rol
        FROM   usuarios
        WHERE  correo = %s AND estado = 'ACTIVO'
    """
    cursor.execute(query, (correo,))
    user_data = cursor.fetchone()
    cursor.close()

    if user_data and check_password_hash(user_data['contrasena'], contrasena):
        return User(
            id_usuario     = user_data['id_usuario'],
            correo         = user_data['correo'],
            nombre_completo= user_data['nombre_completo'],
            rol            = user_data['rol'],
        )
    return None
