from flask_login import UserMixin
from flask_bcrypt import check_password_hash

class User(UserMixin):
    def __init__(self, id_usuario, correo, nombre_completo, rol):
        self.id = id_usuario
        self.correo = correo
        self.nombre = nombre_completo
        self.rol = rol

def verificar_usuario(db_connection, correo, contrasena):
   # Nos regresa los datos como un diccionario
    cursor = db_connection.cursor(dictionary=True)
    
    # Ejecutamos la consulta
    query = "SELECT id_usuario, correo, nombre_completo, contrasena, rol FROM usuarios WHERE correo = %s AND estado = 'ACTIVO'"
    cursor.execute(query, (correo,))
    user_data = cursor.fetchone()
    cursor.close()
    
    # Compara la constraseña hasheada
    if user_data and check_password_hash(user_data['contrasena'], contrasena):
        # Si coincide, se returna un objeto User con los datos del usuario
        return User(
            id_usuario=user_data['id_usuario'],
            correo=user_data['correo'],
            nombre_completo=user_data['nombre_completo'],
            rol=user_data['rol']
        )
        # Si no, no retorna nada
    return None