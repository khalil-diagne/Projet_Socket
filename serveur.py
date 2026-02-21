import socket, ssl, os, subprocess, json

# -------------------- Configuration --------------------
HOST = '127.0.0.1'
PORT = 5000
CERT = 'cert.pem'
KEY = 'key.pem'
USERS_FILE = 'users.json'

client_connected = False  # Limiter à un seul client

# -------------------- Génération certificat si manquant --------------------
if not (os.path.exists(CERT) and os.path.exists(KEY)):
    print("❗ Certificat ou clé manquant. Génération automatique...")
    subprocess.run([
        "openssl", "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", KEY, "-out", CERT, "-days", "365", "-nodes",
        "-subj", "/C=FR/ST=Paris/L=Paris/O=MonServeur/CN=localhost"
    ])
    print("✅ Certificat et clé générés.")

# -------------------- Gestion des utilisateurs --------------------
if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, 'w') as f:
        json.dump({"admin":"admin"}, f)

with open(USERS_FILE, 'r') as f:
    USERS = json.load(f)

# -------------------- Exécution commande --------------------
def execute_command(cmd, current_dir=None):
    """
    Exécute une commande shell dans le répertoire courant (ou celui par défaut)
    et renvoie stdout + stderr
    """
    try:
        # shell=True pour exécuter les commandes système
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=current_dir)
        return result.stdout + result.stderr
    except Exception as e:
        return f"❌ Erreur: {e}"

# -------------------- Gestion client --------------------
def handle_client(conn, addr):
    global client_connected
    print(f"Client connecté: {addr}")
    try:
        # -------------------- Authentification --------------------
        conn.send(b"LOGIN\n")
        username = conn.recv(1024).decode().strip()
        conn.send(b"PASSWORD\n")
        password = conn.recv(1024).decode().strip()

        if USERS.get(username) != password:
            conn.send(b"AUTH_FAILED\n")
            conn.close()
            print(f"❌ Auth échouée pour {addr}")
            client_connected = False
            return

        conn.send(b"AUTH_SUCCESS\n")
        print(f"✅ Auth réussie pour {username} ({addr})")

        # -------------------- Commandes dans tous les répertoires --------------------
        current_dir = os.getcwd()  # On peut changer de répertoire avec cd
        while True:
            data = conn.recv(4096).decode().strip()
            if not data:
                break

            # Gestion changement répertoire
            if data.startswith("cd "):
                path = data[3:].strip()
                try:
                    os.chdir(path)
                    current_dir = os.getcwd()
                    conn.send(f"✅ Répertoire changé: {current_dir}\n".encode())
                except Exception as e:
                    conn.send(f"❌ Erreur cd: {e}\n".encode())
                continue

            # Gestion transfert fichier
            if data.startswith("FILE:"):
                filename = data[5:]
                conn.send(b"READY\n")
                filesize = int(conn.recv(16).decode())
                with open("server_" + filename, "wb") as f:
                    remaining = filesize
                    while remaining > 0:
                        chunk = conn.recv(min(4096, remaining))
                        if not chunk:
                            break
                        f.write(chunk)
                        remaining -= len(chunk)
                conn.send(f"FILE_RECEIVED:{filename}".encode())
                print(f"✅ Fichier reçu: {filename} ({addr})")
            # Exécution commande shell
            else:
                result = execute_command(data, current_dir=current_dir)
                conn.send(result.encode())

    except Exception as e:
        print(f"Erreur client {addr}: {e}")
    finally:
        conn.close()
        print(f"Client déconnecté: {addr}")
        client_connected = False

# -------------------- Serveur SSL --------------------
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certfile=CERT, keyfile=KEY)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.bind((HOST, PORT))
    sock.listen(1)
    print(f"Serveur lancé sur {HOST}:{PORT} (1 client à la fois)")

    with context.wrap_socket(sock, server_side=True) as ssock:
        while True:
            client_conn, client_addr = ssock.accept()

            if client_connected:
                client_conn.send(b"SERVER_BUSY\n")
                client_conn.close()
                print(f"Connexion refusée: {client_addr} (serveur occupé)")
                continue

            client_connected = True
            handle_client(client_conn, client_addr)
