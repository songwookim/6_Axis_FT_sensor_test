import socket
import time
import sys
import array
import numpy as np
from omegaconf import DictConfig

# Sensor Constants
PROTOCOL_SPI = 0x01
SENSOR_MAP = {
    1: 0x01,
    2: 0x02,
    3: 0x04,
    4: 0x08,
    5: 0x10
}


class MMS101Controller:
    def __init__(self, config):
        cfg = config.mms101
        self.dest_ip = cfg.dest_ip
        self.dest_port = cfg.dest_port
        self.src_port = cfg.src_port
        self.measure_max = cfg.measure_max
        self.debug_mode = cfg.debug
        self.sensors = cfg.sensors
        self.n_sensors = cfg.n_sensors

        self.n_samples = 0
        self.sums = np.zeros([self.n_sensors, 6])
        self.contact_flag = 0
        self.offset = np.zeros([self.n_sensors, 6])

        self.destAddr = (self.dest_ip, self.dest_port)
        self.srcAddr = ("", self.src_port)
        self.sockOpenFlag = 0
        self.sensorNo = self._select_sensors(self.sensors)
        self.sockOpen()

        self._init_device()
    # ── Initialization ────────────────────────────────────────

    def _init_device(self):
        """Reset → Select → Boot → wait for READY state."""
        self.cmdReset()
        self.cmdSelect()
        self.cmdBoot()
        time.sleep(0.05)

        t0 = time.time()
        while time.time() - t0 < 5.0:
            status = self.cmdStatus()
            if not status or len(status) < 5:
                continue
            if status[4] == 0x03:       # READY
                return
            elif status[4] == 0x02:     # WAIT
                time.sleep(0.01)
            else:                       # ERROR → retry
                if self.debug_mode:
                    print("[init] error state, retrying reset/select/boot")
                self.cmdReset(); time.sleep(0.02)
                self.cmdSelect(); time.sleep(0.02)
                self.cmdBoot(); time.sleep(0.05)

        print("[init] timeout: device not READY")
        sys.exit(1)

    def __del__(self):
        self.sockClose()

    # ── Socket ────────────────────────────────────────────────

    def sockOpen(self):
        self.sockDsc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sockDsc.bind(self.srcAddr)
        # Avoid infinite blocking on recv
        self.sockDsc.settimeout(0.8)
        self.sockOpenFlag = 1

    def sockClose(self):
        if self.sockOpenFlag:
            self.cmdStop()
            self.sockDsc.close()
            self.sockOpenFlag = 0

    # ── Low-level I/O ─────────────────────────────────────────

    def recvData(self, rcvLen):
        try:
            data = self.sockDsc.recv(rcvLen)
            if self.debug_mode:
                print(data.hex())
            return data
        except socket.timeout:
            if self.debug_mode:
                print(f"[timeout] expecting {rcvLen} bytes")
            return b""

    # ── Commands ──────────────────────────────────────────────

    def cmdStart(self):
        self.send_cmd([0xF0])
        return self.recvData(2)

    def cmdData(self):
        self.send_cmd([0xE0])
        return self.recvData(100)

    def cmdRestart(self):
        self.send_cmd([0xC0])
        return self.recvData(2)

    def cmdBoot(self):
        self.send_cmd([0xB0])
        return self.recvData(100)

    def cmdStop(self):
        self.send_cmd([0xB2])
        return self.recvData(2)

    def cmdReset(self):
        self.send_cmd([0xB4])
        return self.recvData(2)

    def cmdStatus(self):
        self.send_cmd([0x80])
        return self.recvData(6)

    def cmdSelect(self):
        self.send_cmd([0xA0, PROTOCOL_SPI, self.sensorNo])
        return self.recvData(2)

    def cmdVersion(self):
        self.send_cmd([0xA2])
        return self.recvData(8)

    # ── Helpers ───────────────────────────────────────────────

    def send_cmd(self, cmd):
        sent = self.sockDsc.sendto(array.array('B', cmd), self.destAddr)
        if sent != len(cmd):
            print(f"[ERROR] send failed: {cmd}")

    @staticmethod
    def _select_sensors(sensor_list):
        selected = 0
        for sens in sensor_list:
            if sens in SENSOR_MAP:
                selected |= SENSOR_MAP[sens]
        return selected

    # ── Data acquisition ──────────────────────────────────────

    def _parse_data(self, raw):
        """Parse 100-byte DATA response → (n_sensors, 6) ndarray."""
        data = np.zeros([self.n_sensors, 6])
        for sens in range(self.n_sensors):
            for axis in range(6):
                idx = (sens * 18) + (axis * 3) + 10
                val = (raw[idx] << 16) | (raw[idx + 1] << 8) | raw[idx + 2]
                if val >= 0x00800000:
                    val -= 0x1000000
                data[sens][axis] = val / (1000 if axis < 3 else 100000)
        return data

    def _update_offset(self, raw_data, period):
        """Dynamically calibrate zero-offset."""
        sensed = raw_data - self.offset
        if np.abs(sensed.sum()) > 0.1 and period > 5000:
            self.contact_flag = 1
        else:
            self.contact_flag = 0

        if period < 5000 or self.contact_flag == 0:
            self.sums += raw_data
            self.n_samples += 1
            if self.n_samples > 300:
                self.offset = self.sums / self.n_samples
                self.n_samples = 0
                self.sums = np.zeros([self.n_sensors, 6])

    def run(self, period):
        """Single measurement cycle. Returns offset-corrected (n_sensors, 6) ndarray."""
        self.cmdStart()
        time.sleep(0.0001)

        rData = self.cmdData()
        if len(rData) != 100 or rData[0] != 0x00:
            return np.zeros([self.n_sensors, 6])

        mms101data = self._parse_data(rData)
        self._update_offset(mms101data, period)

        return mms101data - self.offset

