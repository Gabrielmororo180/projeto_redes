import base64
import hashlib
import socket
from pathlib import Path

SERVER_IP = "127.0.0.1"
SERVER_PORT= 12000
FILENAME = "arquivo.txt"

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(5)

req = f"GET /{FILENAME}"
sock.sendto(req.encode(), (SERVER_IP, SERVER_PORT))

# Primeira resposta (OK ou ERR)
msg, _ = sock.recvfrom(65535)
txt = msg.decode(errors="ignore")

if txt.startswith("ERR|"):
    print("Erro do servidor:", txt)
    sock.close()
    raise SystemExit(1)

if not txt.startswith("OK|"):
    print("Resposta inesperada:", txt)
    sock.close()
    raise SystemExit(1)

_, transfer_id, file_size, chunk_size, total_chunks, expected_sha256 = txt.split("|", 5)
file_size = int(file_size)
total_chunks = int(total_chunks)

print(f"OK transfer_id={transfer_id} size={file_size} chunks={total_chunks}")

# Recebe DATA até END
chunks = {}
while True:
    pkt, _ = sock.recvfrom(65535)
    s = pkt.decode(errors="ignore")

    if s.startswith("END|"):
        _, end_id = s.split("|", 1)
        if end_id == transfer_id:
            break
        continue

    if not s.startswith("DATA|"):
        continue

    parts = s.split("|", 4)
    if len(parts) != 5:
        continue

    _, tid, seq, total, payload_b64 = parts
    if tid != transfer_id:
        continue

    seq = int(seq)
    chunk = base64.b64decode(payload_b64.encode())
    chunks[seq] = chunk

sock.close()

# Monta arquivo
out_dir = Path(__file__).parent / "downloads"
out_dir.mkdir(exist_ok=True)
out_path = out_dir / FILENAME

with open(out_path, "wb") as f:
    for i in range(total_chunks):
        if i not in chunks:
            print(f"Faltou chunk {i}")
            raise SystemExit(1)
        f.write(chunks[i])

# Verifica hash
h = hashlib.sha256()
with open(out_path, "rb") as f:
    while True:
        b = f.read(64 * 1024)
        if not b:
            break
        h.update(b)

got = h.hexdigest()
print("Arquivo salvo em:", out_path)
print("SHA256 esperado :", expected_sha256)
print("SHA256 recebido :", got)
print("Integridade:" , got == expected_sha256)