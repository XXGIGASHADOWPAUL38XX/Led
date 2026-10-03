import socket
import time

ip = "192.168.1.11"  # ESP32 IP
led_count = 300
rgb = bytes([255, 0, 0]) * led_count

header = bytes([0x41, 0x00, 0x01, 0x01])
header += (0).to_bytes(4, "big")
header += len(rgb).to_bytes(2, "big")
packet = header + rgb

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
    sock.sendto(packet, (ip, 4048))
    time.sleep(0.05)