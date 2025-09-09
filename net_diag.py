#!/usr/bin/env python3
import socket, time, array
import yaml

CFG = yaml.safe_load(open('config.yaml'))['mms101']
DEV_IP = CFG['dest_ip']
DEV_PORT = CFG['dest_port']
SRC_PORT = CFG['src_port']

def send(sock, addr, payload):
    sock.sendto(array.array('B', payload), addr)

def recv_try(sock, n=100, timeout=0.3):
    sock.settimeout(timeout)
    try:
        data, peer = sock.recvfrom(n)
        return data, peer
    except Exception as e:
        return None, None

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
    s.bind(("", SRC_PORT))
    addr = (DEV_IP, DEV_PORT)
    print(f"Target {addr} from src {SRC_PORT}")

    tests = [
        ("STATUS(0x80)", [0x80], 6),
        ("RESET(0xB4)", [0xB4], 2),
        ("SELECT(0xA0, SPI=0x01, sens=0x01)", [0xA0, 0x01, 0x01], 2),
        ("BOOT(0xB0)", [0xB0], 100),
        ("DATA(0xE0)", [0xE0], 100),
    ]

    for name, payload, expect in tests:
        print(f"\n-- {name}")
        send(s, addr, payload)
        time.sleep(0.05)
        for i in range(3):
            data, peer = recv_try(s, 512, timeout=0.5)
            if data:
                print(f"[{i}] from {peer}, {len(data)} bytes: {data.hex()}")
            else:
                print(f"[{i}] no response")
        time.sleep(0.2)

print("done")
