import base64   
import socket
from pathlib import Path

SERVER_IP = "0.0.0.0"
SERVER_PORT = 12000
FILES_DIR = Path(__file__).parent / "files"


def safe_resolve(filename: str) -> Path | None:
    
    candidate = (FILES_DIR / filename).resolve()
    if not str(candidate).startswith(str(FILES_DIR.resolve())):
        return None
    return candidate


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

        filename = msg[5:].strip()
        if not filename:
            sock.sendto(b"ERR|arquivo_invalido", client_addr)
            continue

        file_path = safe_resolve(filename)
        if file_path is None or not file_path.exists() or not file_path.is_file():
            sock.sendto(b"ERR|arquivo_nao_encontrado", client_addr)
            continue

        file_size = file_path.stat().st_size
        sock.sendto(f"OK|{filename}|{file_size}".encode(), client_addr)
        print(f"[OK] GET aceito para {filename} ({file_size} bytes)")

        


if __name__ == "__main__":
    main()