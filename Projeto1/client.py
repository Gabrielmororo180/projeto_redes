import socket
import sys

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12000
FILENAME = "arquivo.txt"

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