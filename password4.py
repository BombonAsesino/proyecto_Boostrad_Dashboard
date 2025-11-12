from cryptography.fernet import Fernet

texto = "x?1_p-M.4!eM"

# Generar una clave y crear un objeto Fernet

clave = Fernet.generate_key()
objeto = Fernet(clave)
# Encriptar el texto
texto_encriptado = objeto.encrypt(texto.encode())
print(f"Texto encriptado: {texto_encriptado}") 

# Dsencriptar el texto
texto_desencriptado = objeto.decrypt(texto_encriptado).decode()
print(f"Texto desencriptado: {texto_desencriptado}") 
