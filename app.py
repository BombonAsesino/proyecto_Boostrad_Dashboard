from flask import Flask, render_template, request, url_for, redirect, session, flash
from flask_mysqldb import MySQL

# ------------------------- Configuración -------------------------
app = Flask(__name__)
app.secret_key = 'appsecretkey'

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'ventas'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# ------------------------- Páginas públicas ----------------------
@app.route('/')
def inicio():
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/acercade')
def acercade():
    return render_template('acercade.html')

@app.route('/contacto', methods=['GET', 'POST'])
def contacto():
    user = {'nombre': '', 'email': '', 'mensaje': ''}
    if request.method == 'GET':
        user['nombre'] = request.args.get('nombre', '')
        user['email'] = request.args.get('email', '')
        user['mensaje'] = request.args.get('mensaje', '')
    return render_template('contacto.html', usuario=user)

@app.route('/contactopost', methods=['GET', 'POST'])
def contactopost():
    user = {'nombre': '', 'email': '', 'mensaje': ''}
    if request.method == 'POST':
        user['nombre'] = request.form.get('nombre', '')
        user['email'] = request.form.get('email', '')
        user['mensaje'] = request.form.get('mensaje', '')
    return render_template('contactopost.html', usuario=user)

# ------------------------- Registro / Login ----------------------
@app.route('/Registro', methods=['GET', 'POST'])
def Registro():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        id_rol = 2  # usuario por defecto

        if not email or not password:
            flash('Correo y contraseña son obligatorios', 'warning')
            return redirect(url_for('Registro'))

        cur = mysql.connection.cursor()
        cur.execute("SELECT 1 FROM usuario WHERE email=%s", (email,))
        if cur.fetchone():
            cur.close()
            flash('El correo ya existe', 'warning')
            return redirect(url_for('Registro'))

        cur.execute("INSERT INTO usuario (email, password, id_rol) VALUES (%s, %s, %s)",
                    (email, password, id_rol))
        mysql.connection.commit()
        cur.close()

        flash('Registro exitoso. Inicia sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('Registro.html')

@app.route('/accesologin', methods=['GET', 'POST'])
def accesologin():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not email or not password:
            flash('Correo y contraseña son obligatorios', 'warning')
            return redirect(url_for('login'))

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, email, password, id_rol FROM usuario WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if not user or user['password'] != password:
            flash('Usuario o contraseña incorrectos', 'danger')
            return redirect(url_for('login'))

        # Sesión
        session['logueado'] = True
        session['id'] = user['id']
        session['nombre'] = user['email']
        session['id_rol'] = user['id_rol']

        # Redirección por rol
        if user['id_rol'] == 1:
            flash('Bienvenido al panel de administración', 'success')
            return redirect(url_for('admin'))
        else:
            flash('Bienvenido', 'success')
            return redirect(url_for('usuario'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada', 'success')
    return redirect(url_for('login'))

# ------------------------- Panel protegido ----------------------
@app.route('/admin')
def admin():
    if session.get('id_rol') != 1:
        flash('Acceso restringido al administrador', 'warning')
        return redirect(url_for('login'))
    return render_template('admin.html')

@app.route('/usuario')
def usuario():
    if not session.get('logueado'):
        flash('Inicia sesión para continuar', 'warning')
        return redirect(url_for('login'))
    return render_template('usuario.html')

# -------- Perfil Admin fijo (métricas) --------
@app.route('/admin/perfil')
def perfil_admin():
    if session.get('id_rol') != 1:
        flash('Acceso restringido al administrador', 'warning')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM usuario")
    total_usuarios = cur.fetchone()['c']
    cur.execute("SELECT COUNT(*) AS c FROM producto")
    total_productos = cur.fetchone()['c']
    cur.close()

    return render_template('perfil_admin.html',
                           total_usuarios=total_usuarios,
                           total_productos=total_productos)

# Compatibilidad: /perfil → según rol
@app.route('/perfil')
def perfil_redirect():
    if session.get('id_rol') == 1:
        return redirect(url_for('perfil_admin'))
    return redirect(url_for('usuario'))

# ------------------------- Usuarios (lista/CRUD) ----------------
@app.route('/usuarios')
def listar():  # usado por “Perfil del Usuario”
    if session.get('id_rol') != 1:
        flash('Acceso restringido al administrador', 'warning')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, email, password, id_rol FROM usuario ORDER BY id ASC")
    usuarios = cur.fetchall()
    cur.close()

    return render_template('perfil_usuarios.html', usuarios=usuarios)

@app.route('/usuarios/agregar', methods=['POST'])
def usuarios_agregar():
    if session.get('id_rol') != 1:
        flash('Acceso restringido al administrador', 'warning')
        return redirect(url_for('login'))

    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    id_rol = request.form.get('id_rol', type=int) or 2

    if not email or not password:
        flash('Correo y contraseña son obligatorios', 'warning')
        return redirect(url_for('listar'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT 1 FROM usuario WHERE email=%s", (email,))
    if cur.fetchone():
        cur.close()
        flash('El correo ya existe', 'warning')
        return redirect(url_for('listar'))

    cur.execute("INSERT INTO usuario (email, password, id_rol) VALUES (%s, %s, %s)",
                (email, password, id_rol))
    mysql.connection.commit()
    cur.close()
    flash('Usuario agregado', 'success')
    return redirect(url_for('listar'))

# **Editar usuario con GET y POST**
@app.route('/usuarios/editar/<int:user_id>', methods=['GET', 'POST'])
def usuarios_editar(user_id):
    if session.get('id_rol') != 1:
        flash('Acceso restringido al administrador', 'warning')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        id_rol = request.form.get('id_rol', type=int) or 2

        if not email or not password:
            cur.close()
            flash('Correo y contraseña son obligatorios', 'warning')
            return redirect(url_for('usuarios_editar', user_id=user_id))

        cur.execute("""
            UPDATE usuario
               SET email=%s, password=%s, id_rol=%s
             WHERE id=%s
        """, (email, password, id_rol, user_id))
        mysql.connection.commit()
        cur.close()

        flash('Usuario actualizado', 'success')
        return redirect(url_for('listar'))

    # GET: cargar datos y mostrar formulario
    cur.execute("SELECT id, email, password, id_rol FROM usuario WHERE id=%s", (user_id,))
    u = cur.fetchone()
    cur.close()

    if not u:
        flash('Usuario no encontrado', 'warning')
        return redirect(url_for('listar'))

    return render_template('editar_usuario.html', u=u)

@app.route('/usuarios/eliminar/<int:user_id>')
def usuarios_eliminar(user_id):
    if session.get('id_rol') != 1:
        flash('Acceso restringido al administrador', 'warning')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM usuario WHERE id=%s", (user_id,))
    mysql.connection.commit()
    cur.close()
    flash('Usuario eliminado', 'success')
    return redirect(url_for('listar'))

# ------------------------- Productos ----------------------------
@app.route('/productos/agregar', methods=['GET', 'POST'])
def listar_productos_agregados():
    if session.get('id_rol') != 1:
        flash('Acceso restringido al administrador', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        precio = request.form.get('precio', type=float)
        descripcion = request.form.get('descripcion', '').strip()

        if not nombre:
            flash('El nombre es obligatorio', 'warning')
            return redirect(url_for('listar_productos_agregados'))

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO producto (nombre, precio, descripcion)
            VALUES (%s, %s, %s)
        """, (nombre, precio or 0, descripcion or None))
        mysql.connection.commit()
        cur.close()

        flash('Producto agregado', 'success')
        return redirect(url_for('listar_productos_agregados'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, nombre, precio, descripcion FROM producto ORDER BY id ASC")
    productos = cur.fetchall()
    cur.close()

    return render_template('agregar_producto.html', productos=productos)

@app.route('/productos')
def listar_productos():
    if session.get('id_rol') != 1:
        flash('Acceso restringido al administrador', 'warning')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, nombre, precio, descripcion FROM producto ORDER BY id ASC")
    productos = cur.fetchall()
    cur.close()

    return render_template('listar_productos.html', productos=productos)

@app.route('/productos/eliminar/<int:id>')
def eliminar_producto(id):
    if session.get('id_rol') != 1:
        flash('Acceso restringido al administrador', 'warning')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM producto WHERE id=%s", (id,))
    mysql.connection.commit()
    cur.close()

    flash('Producto eliminado', 'success')
    return redirect(url_for('listar_productos'))

@app.route('/productos/editar/<int:id>', methods=['GET', 'POST'])
def editar_producto(id):
    if session.get('id_rol') != 1:
        flash('Acceso restringido al administrador', 'warning')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        precio = request.form.get('precio', type=float)
        descripcion = request.form.get('descripcion', '').strip()

        cur.execute("""
            UPDATE producto
               SET nombre=%s, precio=%s, descripcion=%s
             WHERE id=%s
        """, (nombre, precio or 0, descripcion or None, id))
        mysql.connection.commit()
        cur.close()

        flash('Producto actualizado', 'success')
        return redirect(url_for('listar_productos'))

    cur.execute("SELECT id, nombre, precio, descripcion FROM producto WHERE id=%s", (id,))
    prod = cur.fetchone()
    cur.close()

    if not prod:
        flash('Producto no encontrado', 'warning')
        return redirect(url_for('listar_productos'))

    return render_template('agregar_producto.html', editar=True, prod=prod, productos=[])

# ------------------------- Arranque -----------------------------
if __name__ == '__main__':
    app.run(debug=True, port=8000)
