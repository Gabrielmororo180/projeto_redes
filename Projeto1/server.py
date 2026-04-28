import base64   
import socket
from pathlib import Path

SERVER_IP = "0.0.0.0"
SERVER_PORT = 12000
FILES_DIR = Path(__file__).parent / "files"


def main():
    FILES_DIR.mkdir(exist_ok=True)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, SERVER_PORT))
    print(f"Servidor UDP em {SERVER_IP}:{SERVER_PORT}")
    print(f"Diretório de arquivos: {FILES_DIR}")

    while True:
        data, client_addr = sock.recvfrom(65535)
        msg = data.decode(errors="ignore").strip()
        print(f"[REQ] {client_addr} -> {msg}")

        if not msg.startswith("GET /"):
            sock.sendto(b"ERR|requisicao_invalida", client_addr)
            continue

        


if __name__ == "__main__":
    main()