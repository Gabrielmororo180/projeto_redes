import socket

SERVER_IP = "127.0.0.1"
SERVER_PORT = 12000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

msg = "hello udp"
sock.sendto(msg.encode(), (SERVER_IP, SERVER_PORT))

data, _ = sock.recvfrom(1024)
print("Resposta do servidor:", data.decode(errors="ignore"))

sock.close()