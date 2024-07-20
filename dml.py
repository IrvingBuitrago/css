import pymysql

class DML:
    def __init__(self, host="localhost", user="root", password="Iiebc04299?", db="css", port=3305):
        self.__host = host
        self.__user = user
        self.__password = password
        self.__db = db
        self.__port = port
        self.db = None
        self.cursor = None

    def conectar(self):
        try:
            self.db = pymysql.connect(
                host=self.__host,
                user=self.__user,
                password=self.__password,
                db=self.__db,
                port=self.__port
            )
            self.cursor = self.db.cursor()
        except pymysql.MySQLError as e:
            print(f"Error al conectar con la base de datos: {e}")
            raise

    def consultar(self, query, parameters=None, fetchall=False):
        try:
            if parameters:
                self.cursor.execute(query, parameters)
            else:
                self.cursor.execute(query)

            if fetchall:
                return self.cursor.fetchall()
            else:
                return self.cursor.fetchone()
        except pymysql.MySQLError as e:
            print(f"Error en la consulta: {e}")
            raise

    def insertar(self, query, values):
        try:
            self.cursor.execute(query, values)
            self.db.commit()
        except pymysql.MySQLError as e:
            print(f"Error al insertar datos: {e}")
            self.db.rollback()
            raise

    def actualizar(self, query, updated_data):
        try:
            self.cursor.execute(query, updated_data)
            self.db.commit()
        except pymysql.MySQLError as e:
            print(f"Error al actualizar datos: {e}")
            self.db.rollback()
            raise

    def eliminar(self, query, delete_data):
        try:
            self.cursor.execute(query, delete_data)
            self.db.commit()
        except pymysql.MySQLError as e:
            print(f"Error al eliminar datos: {e}")
            self.db.rollback()
            raise

    def cerrar_conex(self):
        if self.cursor:
            self.cursor.close()
        if self.db:
            self.db.close()
