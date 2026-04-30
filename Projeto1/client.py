import base64
import hashlib
import socket
from time import sleep
import zlib
from datetime import datetime
from pathlib import Path

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12000

RECV_TIMEOUT = 0.5
MAX_ROUNDS = 30
NACK_BATCH = 200


def parse_drop_once(raw):
    if not raw.strip():
        return set()
    return {int(s) for s in raw.split(",") if s.strip().isdigit()}


def recv_initial_response(sock):
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
    return transfer_id, int(total_chunks), int(file_size), int(chunk_size), expected_sha256


def save_file(path, chunks, total_chunks):
    with open(path, "wb") as f:
        for i in range(total_chunks):
            if i not in chunks:
                print(f"Faltou chunk {i}")
                raise SystemExit(1)
            f.write(chunks[i])


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(64 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def crc32_hex(data):
    return f"{zlib.crc32(data) & 0xFFFFFFFF:08x}"


def main():
    filename_input = input("Nome do arquivo: ").strip()
    filename = filename_input if filename_input else "arquivo.txt"

    seq_input = input("Seq para perder (ex: 1,3,7) ou vazio: ").strip()
    drop_once = parse_drop_once(seq_input)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(RECV_TIMEOUT)

    req = f"GET /{filename}"
    sleep(1)
    sock.sendto(req.encode(), (SERVER_IP, SERVER_PORT))

    transfer_id, total_chunks, file_size, chunk_size, expected_sha256 = recv_initial_response(sock)
    print(
        f"OK transfer_id={transfer_id} size={file_size} "
        f"chunk_size={chunk_size} chunks={total_chunks}"
    )

    chunks = {}
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

            parts = s.split("|", 5)
            if len(parts) != 6:
                continue

            _, tid, seq_txt, _, recv_crc32, payload_b64 = parts
            if tid != transfer_id or not seq_txt.isdigit():
                continue

            seq = int(seq_txt)

            if seq in drop_once:
                print(f"Descartado seq: {seq}")
                drop_once.remove(seq)
                continue

            try:
                chunk = base64.b64decode(payload_b64.encode(), validate=True)
            except Exception:
                print(f"Payload inválido no seq {seq}")
                continue

            calc_crc32 = crc32_hex(chunk)
            if calc_crc32 != recv_crc32.lower():
                print(
                    f"CRC inválido no seq {seq}: "
                    f"esperado={recv_crc32.lower()} calculado={calc_crc32}"
                )
                continue

            if seq not in chunks:
                chunks[seq] = chunk

        missing = [i for i in range(total_chunks) if i not in chunks]
        if not missing:
            break

        batch = missing[:NACK_BATCH]
        nack_msg = f"NACK|{transfer_id}|{','.join(map(str, batch))}"
        sock.sendto(nack_msg.encode(), (SERVER_IP, SERVER_PORT))
        print(f"NACK -> pedindo {len(batch)} chunks, 10 primeiros: {batch[:10]}")

        rounds += 1

    if len(chunks) < total_chunks:
        print(f"[!] Não conseguiu todos os chunks após {rounds} rodadas")
        raise SystemExit(1)

    output_dir = Path(__file__).parent / "downloads"
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    name, ext = Path(filename).stem, Path(filename).suffix
    output_path = output_dir / f"{name}_{timestamp}{ext}"


    save_file(output_path, chunks, total_chunks)

    actual_hash = sha256_file(output_path)
    if actual_hash == expected_sha256:
        print(f" Download concluído: {output_path}")
    else:
        print(f"    Hash inválido!")
        print(f"    Esperado:  {expected_sha256}")
        print(f"    Obtido:    {actual_hash}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
