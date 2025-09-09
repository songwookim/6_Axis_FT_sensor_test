import socket
import time
import array


def discover(timeout_s: float = 6.0, listen_port: int = 2000):
    """
    UDP 브로드캐스트(Status 0x80)를 전송하고, 포트 1366으로부터의 응답을 기다립니다.

    - 브로드캐스트 대상: 255.255.255.255, 192.168.1.255, 192.168.0.255
    - 송신 소스 포트: listen_port (기본 2000)
    - 수신 타임아웃: timeout_s
    """
    targets = [
        ("255.255.255.255", 1366),
        ("192.168.1.255", 1366),
        ("192.168.0.255", 1366),
    ]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.5)
        # 소스 포트를 고정하여 장치가 응답 시 동일 포트로 보내도록
        sock.bind(("", listen_port))

        payload = array.array('B', [0x80])  # STATUS
        t0 = time.time()
        seen = set()
        print("[DISCOVER] broadcasting STATUS (0x80) ...")
        while time.time() - t0 < timeout_s:
            # 주기적으로 브로드캐스트 송신
            for addr in targets:
                try:
                    sock.sendto(payload, addr)
                except OSError as e:
                    # 인터페이스/라우팅에 따라 일부 브로드캐스트는 실패할 수 있음
                    pass

            # 수신 폴링
            try:
                data, src = sock.recvfrom(2048)
                key = (src[0], src[1], data)
                if key not in seen:
                    seen.add(key)
                    print(f"[RECV] from {src[0]}:{src[1]} -> {data.hex()}")
            except socket.timeout:
                pass

        if not seen:
            print("[DISCOVER] no replies.")
        else:
            print(f"[DISCOVER] done. {len(seen)} unique replies.")
    finally:
        sock.close()


if __name__ == "__main__":
    discover()
