import base64   
import socket
from pathlib import Path
import hashlib
from uuid import uuid4
import time
SERVER_IP = "0.0.0.0"
SERVER_PORT = 12000
FILES_DIR = Path(__file__).parent / "files"
CHUNK_SIZE = 1000

RETRANS_TIMEOUT = 2.0
RETRANS_WINDOW = 10.0

def safe_resolve(filename: str) -> Path | None:
    
    candidate = (FILES_DIR / filename).resolve()
    if not str(candidate).startswith(str(FILES_DIR.resolve())):
        return None
    return candidate

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(64 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def send_file(sock: socket.socket, client_addr, file_path: Path):
    transfer_id = uuid4().hex[:8]
    file_size = file_path.stat().st_size
    total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE
    file_hash = sha256_file(file_path)

    ok_msg = f"OK|{transfer_id}|{file_size}|{CHUNK_SIZE}|{total_chunks}|{file_hash}"
    sock.sendto(ok_msg.encode(), client_addr)

    chunks = {}
    with open(file_path, "rb") as f:
        seq = 0
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            chunks[seq] = chunk
            payload_b64 = base64.b64encode(chunk).decode()
            data_msg = f"DATA|{transfer_id}|{seq}|{total_chunks}|{payload_b64}"
            sock.sendto(data_msg.encode(), client_addr)
            seq += 1

    sock.sendto(f"END|{transfer_id}".encode(), client_addr)
    print(f"[OK] Envio concluido: {file_path.name} -> {client_addr}")
    return transfer_id, total_chunks, chunks


def handle_nack(sock, client_addr, transfer_id, chunks):
    sock.settimeout(RETRANS_TIMEOUT)
    last_req = time.time()
    while True:
        if time.time() - last_req > RETRANS_WINDOW:
            break
        try:
            data, addr = sock.recvfrom(65535)
        except socket.timeout:
            continue

        if addr != client_addr:
            continue

        msg = data.decode(errors="ignore").strip()
        if not msg.startswith("NACK|"):
            continue

        parts = msg.split("|", 2)
        if len(parts) != 3:
            continue
        _, tid, seq_list = parts
        if tid != transfer_id:
            continue

        last_req = time.time()
        seqs = [s for s in seq_list.split(",") if s.isdigit()]
        for s in seqs:
            seq = int(s)
            if seq in chunks:
                payload_b64 = base64.b64encode(chunks[seq]).decode()
                data_msg = f"DATA|{transfer_id}|{seq}|0|{payload_b64}"
                sock.sendto(data_msg.encode(), client_addr)


def main():
    FILES_DIR.mkdir(exist_ok=True)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((SERVER_IP, SERVER_PORT))
    print(f"Servidor UDP em {SERVER_IP}:{SERVER_PORT}")
    print(f"Diretorio de arquivos: {FILES_DIR}")

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

        transfer_id, total_chunks, chunks = send_file(sock, client_addr, file_path)
        handle_nack(sock, client_addr, transfer_id, chunks)


        


if __name__ == "__main__":
    main()