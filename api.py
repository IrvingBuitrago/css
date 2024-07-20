# Importaciones necesarias
from flask import Flask, request, render_template, url_for, redirect, session, jsonify
from conex import myconex
from passlib.hash import pbkdf2_sha256

# Crear una instancia de la aplicación Flask
app = Flask(__name__)

# Cargar la configuración desde el archivo 'config.py'
app.config.from_pyfile('config.py')

# Instanciar la conexión a la base de datos
instancia = myconex

# Ruta para el login
@app.route('/', methods=['POST'])
def logIn():
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return jsonify({'error': 'Faltan campos obligatorios'}), 400

        instancia.conectar()
        query = 'SELECT passwrd FROM users WHERE user_name = %s'
        result = instancia.consultar(query, (username,), fetchall=False)

        try:
            if result and pbkdf2_sha256.verify(password, result[0]):
                query = 'SELECT rol, id FROM users WHERE user_name = %s'
                result = instancia.consultar(query, (username,), fetchall=False)
                rol = result[0]

                session['user'] = {'username': username, 'rol': rol}

                instancia.cerrar_conex()

                if rol == 'paciente':
                    return jsonify({'message': 'Inicio de sesión exitoso', 'rol': 'paciente',
                                    'redirect': 'index_paciente'}), 200
                elif rol == 'medico':
                    return jsonify({'message': 'Inicio de sesión exitoso', 'rol': 'medico',
                                    'redirect': 'index_medico'}), 200
                else:
                    return jsonify({'message': 'Usuario no registrado', 'redirect': 'registro'}), 200
            else:
                return jsonify({'error': 'Datos no encontrados o incorrectos'}), 400
        except Exception as e:
            return jsonify({'error': f'Error del servidor: {str(e)}'}), 500

# Ruta para el registro
@app.route('/registro', methods=['POST'])
def registro():
    if request.method == 'GET':
        if 'user' in session:
            username = session['user']
            instancia.conectar()
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        date_birth = data.get('date_birth')
        idc = data.get('idc')
        email = data.get('email')
        rol = data.get('rol')

        if not all([username, password, first_name, last_name, date_birth, idc, email, rol]):
            return jsonify({'error': 'Faltan campos obligatorios'}), 400

        instancia.conectar()
        query = 'SELECT * FROM users WHERE user_name = %s'
        result = instancia.consultar(query, (username,))

        if result:
            instancia.cerrar_conex()
            return jsonify({'error': 'Este usuario ya existe'}), 400
        else:
            try:
                password_hash = pbkdf2_sha256.hash(password)
                query2 = 'INSERT INTO users (user_name, passwrd, first_name, last_name, date_birth, idc, email, rol) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)'
                values = (username, password_hash, first_name, last_name, date_birth, idc, email, rol)
                instancia.insertar(query2, values)
                instancia.cerrar_conex()
                return jsonify({'message': 'Usuario registrado exitosamente'}), 201
            except Exception as e:
                instancia.cerrar_conex()
                return jsonify({'error': f'Error en el registro: {str(e)}'}), 500

# Ruta para solicitar cita
@app.route('/cita_nueva', methods= ['GET', 'POST'])
def citas():
    if request.method == 'GET':
        if 'user' in session:
            username = session['user']
            instancia.conectar()
    if request.method == 'POST':
        data = request.get_json()
        patient_id = data.get('patient_id')
        doctor_id = data.get('doctor_id')
        day = data.get('day')
        time = data.get('time')
        reason = data.get('reason')

        if not all([patient_id, doctor_id, day, time, reason]):
            return jsonify({'error': 'Faltan campos obligatorios'}), 400

        # Convertir los strings de fecha y hora a objetos datetime
        try:
            day = datetime.strptime(day, '%Y-%m-%d').date()
            time = datetime.strptime(time, '%H:%M:%S').time()
        except ValueError:
            return jsonify({'error': 'Formato de fecha o hora inválido'}), 400

        instancia.conectar()

        # Verificar disponibilidad en la agenda del doctor
        query = 'SELECT available FROM schedules WHERE doctor_id = %s AND day = %s AND time = %s'
        result = instancia.consultar(query, (doctor_id, day, time), fetchall=False)

        if result and result[0]:
            try:
                # Insertar la cita en la base de datos
                query = ('INSERT INTO appointments (patient_id, doctor_id, day, time, reason) '
                         'VALUES (%s, %s, %s, %s, %s)')
                values = (patient_id, doctor_id, day, time, reason)
                instancia.insertar(query, values)

                # Actualizar la disponibilidad en la agenda del doctor
                query = 'UPDATE schedules SET available = FALSE WHERE doctor_id = %s AND day = %s AND time = %s'
                instancia.actualizar(query, (doctor_id, day, time))

                instancia.cerrar_conex()

                # Crear el JSON de la cita
                appointment_json = {
                    'patient_id': patient_id,
                    'doctor_id': doctor_id,
                    'day': str(day),
                    'time': str(time),
                    'reason': reason
                }

                return jsonify({'message': 'Cita programada exitosamente', 'appointment': appointment_json}), 201
            except Exception as e:
                instancia.cerrar_conex()
                return jsonify({'error': f'Error al programar la cita: {str(e)}'}), 500
        else:
            instancia.cerrar_conex()
            return jsonify({'error': 'El horario no está disponible. Por favor, elija otro.'}), 400

# Ruta para solicitar cita
@app.route('/citas', methods=['GET'])
def ver_citas_pendientes():
    # Obtener el ID del usuario de la solicitud
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({'error': 'Faltan campos obligatorios'}), 400

    instancia.conectar()

    try:
        # Consultar las citas pendientes del usuario utilizando la vista
        query = 'SELECT id, day, time, reason, doctor_name FROM appo_pending WHERE patient_id = %s ORDER BY day, time'
        result = instancia.consultar(query, (user_id,), fetchall=True)

        instancia.cerrar_conex()

        if result:
            citas = []
            for row in result:
                citas.append({
                    'id': row[0],
                    'day': str(row[1]),
                    'time': str(row[2]),
                    'reason': row[3],
                    'doctor_name': row[4]
                })

            return jsonify({'citas': citas}), 200
        else:
            return jsonify({'message': 'No tienes citas pendientes'}), 200
    except Exception as e:
        instancia.cerrar_conex()
        return jsonify({'error': f'Error al obtener las citas: {str(e)}'}), 500

# Ruta para reagendar cita
@app.route('/citas/reagendar/<int:appointment_id>', methods=['PUT'])
def reagendar_cita(appointment_id):
    data = request.get_json()
    user_id = data.get('user_id')
    new_day = data.get('day')
    new_time = data.get('time')

    if not all([user_id, new_day, new_time]):
        return jsonify({'error': 'Faltan campos obligatorios'}), 400

    # Convertir los strings de fecha y hora a objetos datetime
    try:
        new_day = datetime.strptime(new_day, '%Y-%m-%d').date()
        new_time = datetime.strptime(new_time, '%H:%M:%S').time()
    except ValueError:
        return jsonify({'error': 'Formato de fecha o hora inválido'}), 400

    instancia.conectar()

    try:
        # Verificar si la cita pertenece al usuario
        query = 'SELECT doctor_id, day, time FROM appointments WHERE id = %s AND patient_id = %s'
        result = instancia.consultar(query, (appointment_id, user_id), fetchall=False)

        if result:
            doctor_id, old_day, old_time = result

            # Verificar disponibilidad del nuevo horario
            query = 'SELECT available FROM schedules WHERE doctor_id = %s AND day = %s AND time = %s'
            result = instancia.consultar(query, (doctor_id, new_day, new_time), fetchall=False)

            if result and result[0]:
                # Actualizar la cita con el nuevo horario
                query = 'UPDATE appointments SET day = %s, time = %s WHERE id = %s'
                instancia.actualizar(query, (new_day, new_time, appointment_id))

                # Actualizar la disponibilidad en la agenda del doctor
                query = 'UPDATE schedules SET available = TRUE WHERE doctor_id = %s AND day = %s AND time = %s'
                instancia.actualizar(query, (doctor_id, old_day, old_time))

                query = 'UPDATE schedules SET available = FALSE WHERE doctor_id = %s AND day = %s AND time = %s'
                instancia.actualizar(query, (doctor_id, new_day, new_time))

                instancia.cerrar_conex()
                return jsonify({'message': 'Cita reagendada exitosamente'}), 200
            else:
                instancia.cerrar_conex()
                return jsonify({'error': 'El nuevo horario no está disponible'}), 400
        else:
            instancia.cerrar_conex()
            return jsonify({'error': 'Cita no encontrada o no pertenece al usuario'}), 404
    except Exception as e:
        instancia.cerrar_conex()
        return jsonify({'error': f'Error al reagendar la cita: {str(e)}'}), 500

# Ruta para cancelar cita
@app.route('/citas/<int:appointment_id>', methods=['DELETE'])
def cancelar_cita(appointment_id):
    user_id = request.args.get('user_id')

    if not user_id:
        return jsonify({'error': 'Faltan campos obligatorios'}), 400

    instancia.conectar()

    try:
        # Verificar si la cita pertenece al usuario
        query = 'SELECT doctor_id, day, time FROM appointments WHERE id = %s AND patient_id = %s'
        result = instancia.consultar(query, (appointment_id, user_id), fetchall=False)

        if result:
            doctor_id, day, time = result
            # Borrar la cita
            query = 'DELETE FROM appointments WHERE id = %s'
            instancia.eliminar(query, (appointment_id,))

            # Actualizar la disponibilidad en la agenda del doctor
            query = 'UPDATE schedules SET available = TRUE WHERE doctor_id = %s AND day = %s AND time = %s'
            instancia.actualizar(query, (doctor_id, day, time))

            instancia.cerrar_conex()
            return jsonify({'message': 'Cita borrada exitosamente'}), 200
        else:
            instancia.cerrar_conex()
            return jsonify({'error': 'Cita no encontrada o no pertenece al usuario'}), 404
    except Exception as e:
        instancia.cerrar_conex()
        return jsonify({'error': f'Error al borrar la cita: {str(e)}'}), 500

# Ruta para el logout
@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        if 'user' in session:
            # Eliminar la clave 'user' de la sesión para cerrar la sesión del usuario
            session.pop('user')
            # Redirigir al usuario a la página de inicio de sesión
            return redirect(url_for('logIn'))

if __name__ == '__main__':
    app.run(debug=True)