import tkinter as tk
import ssl
import socket
import threading
import os
import tkinter.filedialog as fd

HOST = '127.0.0.1'
PORT = 5000
CERT = 'cert.pem'

conn = None
connected = False


# ==============================
# CONNEXION AU SERVEUR
# ==============================
def connect():
    global conn, connected

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn = context.wrap_socket(sock, server_hostname=HOST)

    try:
        conn.connect((HOST, PORT))
    except:
        log("❌ Impossible de se connecter au serveur")
        return

    # Phase LOGIN
    if conn.recv(1024).decode().strip() == "LOGIN":
        username = input_username.get()
        conn.send(username.encode())

        if conn.recv(1024).decode().strip() == "PASSWORD":
            password = input_password.get()
            conn.send(password.encode())

            status = conn.recv(1024).decode().strip()

            if status == "AUTH_SUCCESS":
                connected = True
                log("✅ Connecté au serveur")

                # cacher le login
                hide_login_ui()

                # activer commandes
                entry_command.config(state="normal")
                btn_send.config(state="normal")
                btn_disconnect.pack()

                threading.Thread(target=listen_server, daemon=True).start()

            else:
                log("❌ Authentification échouée")


# ==============================
# ENVOYER COMMANDE
# ==============================
def send_command():
    if not connected:
        log("⚠️ Connecte-toi d'abord")
        return

    cmd = entry_command.get()
    if cmd.strip() == "":
        return

    conn.send(cmd.encode())
    entry_command.delete(0, tk.END)


# ==============================
# ECOUTER SERVEUR
# ==============================
def listen_server():
    global connected

    while connected:
        try:
            data = conn.recv(4096).decode()
            if data:
                log(data)
        except:
            log("🔌 Déconnecté du serveur")
            disconnect()
            break


# ==============================
# DECONNEXION
# ==============================
def disconnect():
    global conn, connected

    connected = False

    try:
        if conn:
            conn.close()
    except:
        pass

    log("🛑 Déconnecté")

    # réafficher login
    show_login_ui()

    entry_command.config(state="disabled")
    btn_send.config(state="disabled")
    btn_disconnect.pack_forget()


# ==============================
# UI HELPERS
# ==============================
def hide_login_ui():
    input_username.pack_forget()
    input_password.pack_forget()
    btn_connect.pack_forget()


def show_login_ui():
    input_username.pack()
    input_password.pack()
    btn_connect.pack()


# ==============================
# LOG TERMINAL
# ==============================
def log(msg):
    text_log.insert(tk.END, msg + "\n")
    text_log.see(tk.END)


# ==============================
# INTERFACE TKINTER
# ==============================
root = tk.Tk()
root.title("Client Remote sécurisé")

# zone terminal
text_log = tk.Text(root, height=20)
text_log.pack()

# login
input_username = tk.Entry(root)
input_username.pack()
input_username.insert(0, "admin")

input_password = tk.Entry(root, show="*")
input_password.pack()
input_password.insert(0, "admin")

btn_connect = tk.Button(root, text="Connexion", command=connect)
btn_connect.pack()

# commandes
entry_command = tk.Entry(root, state="disabled")
entry_command.pack()

btn_send = tk.Button(root, text="Envoyer Commande", command=send_command, state="disabled")
btn_send.pack()

# bouton déconnexion (caché au début)
btn_disconnect = tk.Button(root, text="Déconnexion", command=disconnect)

root.mainloop()
