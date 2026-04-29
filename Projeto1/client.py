import base64
import hashlib
import socket
from pathlib import Path

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12000

RECV_TIMEOUT = 0.5
MAX_ROUNDS = 30
NACK_BATCH = 200


def parse_drop_once(raw: str) -> set[int]:
    if not raw.strip():
        return set()
    return {int(s) for s in raw.split(",") if s.strip().isdigit()}


def recv_initial_response(sock: socket.socket) -> tuple[str, int, int, str]:
    try:
        msg, _ = sock.recvfrom(65535)
    except socket.timeout:
        print("Servidor não respondeu.")
        raise SystemExit(1)

    txt = msg.decode(errors="ignore").strip()

    if txt.startswith("ERR|"):
        print("Erro do servidor:", txt)
        raise SystemExit(1)

    if not txt.startswith("OK|"):
        print("Resposta inesperada:", txt)
        raise SystemExit(1)

    parts = txt.split("|", 5)
    if len(parts) != 6:
        print("Resposta OK inválida:", txt)
        raise SystemExit(1)

    _, transfer_id, file_size, chunk_size, total_chunks, expected_sha256 = parts
    return transfer_id, int(total_chunks), int(file_size), expected_sha256


def save_file(path: Path, chunks: dict[int, bytes], total_chunks: int) -> None:
    with open(path, "wb") as f:
        for i in range(total_chunks):
            if i not in chunks:
                print(f"Faltou chunk {i}")
                raise SystemExit(1)
            f.write(chunks[i])


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(64 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    filename_input = input("Nome do arquivo: ").strip()
    filename = filename_input if filename_input else "arquivo.txt"

    seq_input = input("Seq para perder (ex: 1,3,7) ou vazio: ").strip()
    drop_once = parse_drop_once(seq_input)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(RECV_TIMEOUT)

    req = f"GET /{filename}"
    sock.sendto(req.encode(), (SERVER_IP, SERVER_PORT))

    transfer_id, total_chunks, file_size, expected_sha256 = recv_initial_response(sock)
    print(f"OK transfer_id={transfer_id} size={file_size} chunks={total_chunks}")

    chunks: dict[int, bytes] = {}
    rounds = 0

    while rounds < MAX_ROUNDS and len(chunks) < total_chunks:
        saw_end = False

        while True:
            try:
                pkt, _ = sock.recvfrom(65535)
            except socket.timeout:
                break

            s = pkt.decode(errors="ignore").strip()

            if s.startswith("END|"):
                _, end_id = s.split("|", 1)
                if end_id == transfer_id:
                    saw_end = True
                    break
                continue

            if not s.startswith("DATA|"):
                continue

            parts = s.split("|", 4)
            if len(parts) != 5:
                continue

            _, tid, seq_txt, _, payload_b64 = parts
            if tid != transfer_id or not seq_txt.isdigit():
                continue

            seq = int(seq_txt)

            if seq in drop_once:
                print("Descartado seq:", seq)
                drop_once.remove(seq)
                continue

            try:
                chunk = base64.b64decode(payload_b64.encode(), validate=True)
            except Exception:
                continue

            if seq not in chunks:
                chunks[seq] = chunk

        missing = [i for i in range(total_chunks) if i not in chunks]
        if not missing:
            break

        batch = missing[:NACK_BATCH]
        print(f"NACK -> pedindo {len(batch)} chunks, exemplo: {batch[:10]}")
        nack = f"NACK|{transfer_id}|{','.join(str(x) for x in batch)}"
        sock.sendto(nack.encode(), (SERVER_IP, SERVER_PORT))
        rounds += 1

        if not saw_end and rounds >= MAX_ROUNDS:
            break

    sock.close()

    missing = [i for i in range(total_chunks) if i not in chunks]
    if missing:
        print("Transferência incompleta.")
        print("Chunks faltando:", missing[:20], "..." if len(missing) > 20 else "")
        raise SystemExit(1)

    out_dir = Path(__file__).parent / "downloads"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / filename

    save_file(out_path, chunks, total_chunks)

    got = sha256_file(out_path)
    print("Arquivo salvo em:", out_path)
    print("SHA256 esperado :", expected_sha256)
    print("SHA256 recebido :", got)
    print("Integridade:", got == expected_sha256)


if __name__ == "__main__":
    main()