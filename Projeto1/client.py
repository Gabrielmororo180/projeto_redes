import socket
import sys

SERVER_IP = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
SERVER_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 12000
FILENAME = sys.argv[3] if len(sys.argv) > 3 else "arquivo.txt"

req = f"GET /{FILENAME}"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(3)

try:
    sock.sendto(req.encode(), (SERVER_IP, SERVER_PORT))
    print(f"Enviado: {req} -> {SERVER_IP}:{SERVER_PORT}")

    data, addr = sock.recvfrom(65535)
    resp = data.decode(errors="ignore")
    print(f"Resposta de {addr}: {resp}")

    if resp.startswith("OK|"):
        print("Servidor ACEITOU GET (OK).")
    elif resp.startswith("ERR|"):
        print("Servidor recebeu GET, mas retornou erro.")
    else:
        print("Resposta inesperada (mas servidor respondeu).")
except socket.timeout:
    print("Sem resposta (timeout). Verifique se o servidor está rodando.")
finally:
    sock.close()