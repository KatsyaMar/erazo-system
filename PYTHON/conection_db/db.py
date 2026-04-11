import mysql.connector
from mysql.connector import Error

# establece coneccion 
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            user='root',        
            password= '', 
            database='erazo_system'
        )
        if connection.is_connected():
            return connection

    except Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

def close_db_connection(connection):
    if connection and connection.is_connected():
        connection.close()