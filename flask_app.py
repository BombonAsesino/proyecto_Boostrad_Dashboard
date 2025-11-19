from flask import Flask, render_template, request, url_for, redirect, session, flash, Response
from flask_mysqldb import MySQL
from passlib.hash import pbkdf2_sha256
import csv, io
from datetime import datetime, date   # importamos datetime y date

# ------------------------- Configuración -------------------------
app = Flask(__name__)
app.secret_key = 'appsecretkey'

app.config['MYSQL_HOST'] = 'bruxpe34vx2zksdfrrcu-mysql.services.clever-cloud.com'
app.config['MYSQL_PORT'] = 3306
app.config['MYSQL_USER'] = 'urygszsxdwe6jzya'
app.config['MYSQL_PASSWORD'] = 'vVAaW2FDucDA5lSkhADz'
app.config['MYSQL_DB'] = 'bruxpe34vx2zksdfrrcu'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

# ===== Ajuste de zona horaria para cada request (UTC-6, Nicaragua) =====
@app.before_request
def set_mysql_timezone():
    try:
        cur = mysql.connection.cursor()
        cur.execute("SET time_zone = '-06:00';")
        cur.close()
    except Exception:
        # Si por alguna razón falla, no rompemos la app
        pass
# =======================================================================

# ------------------------- Exportaciones CSV ----------------------------
def _csv_response(buffer_str: str, filename: str) -> Response:
    """Devuelve un Response con CSV descargable (UTF-8 + BOM para Excel)."""
    return Response(
        buffer_str,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'}
    )

@app.route('/export/usuarios.csv')
def export_usuarios_csv():
    if session.get('id_rol') != 1:
        flash('Acceso restringido al administrador', 'warning')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, nombre, email, id_rol FROM usuario ORDER BY id ASC")
    rows = cur.fetchall()
    cur.close()

    sio = io.StringIO(newline='')
    sio.write('\ufeff')  # BOM UTF-8
    writer = csv.writer(sio)
    writer.writerow(["ID", "Nombre", "Correo", "Rol"])

    for r in rows:
        rid    = r.get('id') if isinstance(r, dict) else r[0]
        rnom   = r.get('nombre') if isinstance(r, dict) else r[1]
        remail = r.get('email') if isinstance(r, dict) else r[2]
        ridrol = r.get('id_rol') if isinstance(r, dict) else r[3]
        writer.writerow([rid, rnom or '', remail or '', ('Admin' if ridrol == 1 else 'Usuario')])

    fname = f"usuarios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return _csv_response(sio.getvalue(), fname)

@app.route('/export/productos.csv')
def export_productos_csv():
    if session.get('id_rol') != 1:
        flash('Acceso restringido al administrador', 'warning')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, nombre, precio, descripcion, fecha FROM producto ORDER BY id ASC")
    rows = cur.fetchall()
    cur.close()

    sio = io.StringIO(newline='')
    sio.write('\ufeff')  # BOM UTF-8
    writer = csv.writer(sio)
    writer.writerow(["ID", "Nombre", "Precio", "Descripción", "Fecha"])

    for r in rows:
        rid    = r.get('id') if isinstance(r, dict) else r[0]
        rnom   = r.get('nombre') if isinstance(r, dict) else r[1]
        rprec  = r.get('precio') if isinstance(r, dict) else r[2]
        rdesc  = r.get('descripcion') if isinstance(r, dict) else r[3]
        rfecha = r.get('fecha') if isinstance(r, dict) else (r[4] if len(r) > 4 else None)
        if hasattr(rfecha, 'strftime'):
            rfecha = rfecha.strftime('%Y-%m-%d')
        elif isinstance(rfecha, str):
            rfecha = rfecha[:10]
        writer.writerow([rid, rnom or '', rprec if rprec is not None else '', rdesc or '', rfecha or ''])

    fname = f"productos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return _csv_response(sio.getvalue(), fname)

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
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip()
        password_raw = request.form.get('password', '').strip()

        id_rol = request.form.get('id_rol', type=int)
        if id_rol not in (1, 2):
            id_rol = 2

        if not email or not password_raw:
            flash('Correo y contraseña son obligatorios', 'warning')
            return redirect(url_for('Registro'))

        password_hash = pbkdf2_sha256.hash(password_raw)

        cur = mysql.connection.cursor()
        cur.execute("SELECT 1 FROM usuario WHERE email=%s", (email,))
        if cur.fetchone():
            cur.close()
            flash('El correo ya existe', 'warning')
            return redirect(url_for('Registro'))

        cur.execute(
            "INSERT INTO usuario (nombre, email, password, id_rol) VALUES (%s, %s, %s, %s)",
            (nombre or None, email, password_hash, id_rol)
        )
        mysql.connection.commit()
        cur.close()

        flash('Registro exitoso. Inicia sesión.', 'success')
        return redirect(url_for('login'))

    return render_template('Registro.html')

@app.route('/accesologin', methods=['GET', 'POST'])
def accesologin():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password_raw = request.form.get('password', '').strip()

        if not email or not password_raw:
            flash('Correo y contraseña son obligatorios', 'warning')
            return redirect(url_for('login'))

        cur = mysql.connection.cursor()
        cur.execute("SELECT id, nombre, email, password, id_rol FROM usuario WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()

        if not user or not pbkdf2_sha256.verify(password_raw, user['password']):
            flash('Usuario o contraseña incorrectos', 'danger')
            return redirect(url_for('login'))

        session['logueado'] = True
        session['id'] = user['id']
        session['nombre'] = user['email']
        session['id_rol'] = user['id_rol']

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
@app.route('/admin', methods=['GET', 'POST'])
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
@app.route("/admin/perfil")
def perfil_admin():
    cur = mysql.connection.cursor()

    cur.execute("SELECT COUNT(*) FROM usuario")
    r1 = cur.fetchone()
    total_usuarios = r1[0] if isinstance(r1, (list, tuple)) else list(r1.values())[0]

    cur.execute("SELECT COUNT(*) FROM producto")
    r2 = cur.fetchone()
    total_productos = r2[0] if isinstance(r2, (list, tuple)) else list(r2.values())[0]

    cur.close()

    return render_template(
        "perfil_admin.html",
        total_usuarios=total_usuarios,
        total_productos=total_productos
    )

@app.route('/perfil')
def perfil_redirect():
    if session.get('id_rol') == 1:
        return redirect(url_for('perfil_admin'))
    return redirect(url_for('usuario'))

# ------------------------- Usuarios (lista/CRUD) ----------------
@app.route('/usuarios')
def listar():
    if session.get('id_rol') != 1:
        flash('Acceso restringido al administrador', 'warning')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, nombre, email, password, id_rol FROM usuario ORDER BY id ASC")
    usuarios = cur.fetchall()
    cur.close()

    return render_template('perfil_usuarios.html', usuarios=usuarios)

@app.route('/usuarios/agregar', methods=['GET', 'POST'])
def usuarios_agregar():
    if session.get('id_rol') != 1:
        flash('Acceso restringido al administrador', 'warning')
        return redirect(url_for('login'))

    if request.method == 'GET':
        return redirect(url_for('listar'))

    nombre   = request.form.get('nombre', '').strip()
    email    = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    id_rol_s = request.form.get('id_rol', '').strip()

    if not email or not password:
        flash('Correo y contraseña son obligatorios', 'warning')
        return redirect(url_for('listar'))

    try:
        id_rol = int(id_rol_s)
        if id_rol not in (1, 2):
            id_rol = 2
    except ValueError:
        id_rol = 2

    password_hash = pbkdf2_sha256.hash(password)

    cur = mysql.connection.cursor()
    cur.execute("SELECT 1 FROM usuario WHERE email=%s", (email,))
    if cur.fetchone():
        cur.close()
        flash('El correo ya existe', 'warning')
        return redirect(url_for('listar'))

    cur.execute(
        "INSERT INTO usuario (nombre, email, password, id_rol) VALUES (%s, %s, %s, %s)",
        (nombre or None, email, password_hash, id_rol)
    )
    mysql.connection.commit()
    cur.close()
    flash('Usuario agregado', 'success')
    return redirect(url_for('listar'))

@app.route('/usuarios/editar/<int:user_id>', methods=['GET', 'POST'])
def usuarios_editar(user_id):
    if session.get('id_rol') != 1:
        flash('Acceso restringido al administrador', 'warning')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nombre   = request.form.get('nombre', '').strip()
        email    = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        id_rol   = request.form.get('id_rol', type=int)

        if id_rol not in (1, 2):
            id_rol = 2

        if not email or not password:
            cur.close()
            flash('Correo y contraseña son obligatorios', 'warning')
            return redirect(url_for('usuarios_editar', user_id=user_id))

        cur.execute("""
            UPDATE usuario
               SET nombre=%s, email=%s, password=%s, id_rol=%s
             WHERE id=%s
        """, (nombre or None, email, password, id_rol, user_id))
        mysql.connection.commit()
        cur.close()

        flash('Usuario actualizado', 'success')
        return redirect(url_for('listar'))

    cur.execute("SELECT id, nombre, email, password, id_rol FROM usuario WHERE id=%s", (user_id,))
    user = cur.fetchone()
    cur.close()

    if not user:
        flash('Usuario no encontrado', 'warning')
        return redirect(url_for('listar'))

    return render_template('editar_usuario.html', user=user)

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
        nombre      = request.form.get('nombre', '').strip()
        precio      = request.form.get('precio', type=float)
        descripcion = request.form.get('descripcion', '').strip()
        fecha_str   = request.form.get('fecha', '').strip()   # NUEVO

        if not nombre:
            flash('El nombre es obligatorio', 'warning')
            return redirect(url_for('listar_productos_agregados'))

        fecha_dt = None
        if fecha_str:
            try:
                fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d')
            except ValueError:
                fecha_dt = None

        cur = mysql.connection.cursor()
        if fecha_dt is None:
            cur.execute("""
                INSERT INTO producto (nombre, precio, descripcion)
                VALUES (%s, %s, %s)
            """, (nombre, precio or 0, descripcion or None))
        else:
            cur.execute("""
                INSERT INTO producto (nombre, precio, descripcion, fecha)
                VALUES (%s, %s, %s, %s)
            """, (nombre, precio or 0, descripcion or None, fecha_dt))
        mysql.connection.commit()
        cur.close()

        flash('Producto agregado', 'success')
        return redirect(url_for('listar_productos_agregados'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, nombre, precio, descripcion, fecha FROM producto ORDER BY id ASC")
    productos = cur.fetchall()
    cur.close()

    return render_template('agregar_producto.html', productos=productos)

@app.route('/productos')
def listar_productos():
    if session.get('id_rol') != 1:
        flash('Acceso restringido al administrador', 'warning')
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    cur.execute("SELECT id, nombre, precio, descripcion, fecha FROM producto ORDER BY id ASC")
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

    if request.method == 'POST':
        nombre      = request.form.get('nombre', '').strip()
        precio      = request.form.get('precio', type=float)
        descripcion = request.form.get('descripcion', '').strip()
        fecha_str   = request.form.get('fecha', '').strip()   # NUEVO

        fecha_dt = None
        if fecha_str:
            try:
                fecha_dt = datetime.strptime(fecha_str, '%Y-%m-%d')
            except ValueError:
                fecha_dt = None

        # 🔒 VALIDACIÓN: NO PERMITIR FECHAS FUTURAS
        if fecha_dt is not None and fecha_dt.date() > date.today():
            flash('La fecha no puede ser mayor a la fecha actual.', 'warning')
            return redirect(url_for('editar_producto', id=id))

        cur = mysql.connection.cursor()

        if fecha_dt is None:
            cur.execute("""
                UPDATE producto
                   SET nombre=%s, precio=%s, descripcion=%s
                 WHERE id=%s
            """, (nombre, precio or 0, descripcion or None, id))
        else:
            cur.execute("""
                UPDATE producto
                   SET nombre=%s, precio=%s, descripcion=%s, fecha=%s
                 WHERE id=%s
            """, (nombre, precio or 0, descripcion or None, fecha_dt, id))

        mysql.connection.commit()
        cur.close()

        flash('Producto actualizado', 'success')
        return redirect(url_for('listar_productos'))

    # GET: mostrar formulario de edición
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, nombre, precio, descripcion, fecha FROM producto WHERE id=%s", (id,))
    prod = cur.fetchone()
    cur.close()

    if not prod:
        flash('Producto no encontrado', 'warning')
        return redirect(url_for('listar_productos'))

    return render_template('agregar_producto.html', editar=True, prod=prod, productos=[])

# === Totales globales para las vistas (usuarios y productos) ===
@app.context_processor
def inject_totals():
    total_usuarios = 0
    total_productos = 0
    cur = None
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT COUNT(*) FROM usuario")
        r1 = cur.fetchone()
        total_usuarios = r1[0] if isinstance(r1, (list, tuple)) else list(r1.values())[0]

        cur.execute("SELECT COUNT(*) FROM producto")
        r2 = cur.fetchone()
        total_productos = r2[0] if isinstance(r2, (list, tuple)) else list(r2.values())[0]
    except Exception as e:
        print("inject_totals error:", e)
    finally:
        if cur:
            cur.close()

    # también inyectamos la fecha actual (para usarla como max en inputs date)
    return dict(
        total_usuarios=total_usuarios,
        total_productos=total_productos,
        fecha_hoy=date.today().strftime('%Y-%m-%d')
    )

# ------------------------- Arranque -----------------------------
if __name__ == '__main__':
    app.run(debug=True, port=8000)
