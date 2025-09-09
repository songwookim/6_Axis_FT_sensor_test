#******************************************************************************
#
#   @file       mms101_evaboard_ethernet_sample_code.py
#   @brief      MMS101 Evaboard Ethernet Sample Source File (Python)
#
#               copyright: MITSUMI Electric Co.,LTD
#   @attention  none
#   @warning    MITSUMI CONFIDENTIAL
#
#******************************************************************************
#******************************************************************************
# History : DD.MM.YYYY Version  Description
#         : 16.01.2023 1.0.0.0  First Release
#******************************************************************************

import socket
import time
import sys
import array

DEST_IP_ADDR = "192.168.0.200"
DEST_PORT = 1366
SRC_PORT = 2000

PROTOCOL_SPI = 0x01

SENSOR_NO1 = 0x01
# SENSOR_NO2 = 0x02
# SENSOR_NO3 = 0x04
# SENSOR_NO4 = 0x08
# SENSOR_NO5 = 0x10

#******************************************************************************
# MMS101 Class
#******************************************************************************
class mms101_evaboard_ethernet:
    debugMode = 1   # =1: debug print

    #**************************************************************************
    # Constractor
    #**************************************************************************
    def __init__(self):
        # Destination Address
        self.destAddr = (DEST_IP_ADDR, DEST_PORT)

        # Source Address (INADDR_ANY)
        self.srcAddr = ("", SRC_PORT)

        # socket open flag
        self.sockOpenFlag = 0

        # Open socket
        self.sockOpen()

        # Select Sensor
        self.sensorNo = SENSOR_NO1

    #**************************************************************************
    # Destractor
    #**************************************************************************
    def __del__(self):
        self.sockClose()


    #**************************************************************************
    # Method
    #**************************************************************************

    #====================
    # Open socket
    #====================
    def sockOpen(self):
        self.sockDsc = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sockDsc.bind(self.srcAddr)
        self.sockOpenFlag = 1

    #====================
    # Close socket
    #====================
    def sockClose(self):
        if self.sockOpenFlag == 1:
            self.cmdStop()      # for forced termination
            self.sockDsc.close()
            self.sockOpenFlag = 0

    #====================
    # Receive Data
    #====================
    def recvData(self, rcvLen):
        data = self.sockDsc.recv(rcvLen)
        if self.debugMode == 1:
            print(data.hex())
        return data

    #====================
    # START
    #====================
    def cmdStart(self):
        if self.debugMode == 1:
            print("START")
        sendSz = self.sockDsc.sendto(array.array('B', [0xF0]), self.destAddr)
        if sendSz != 1:
            print("Error: START send")

        data = self.recvData(2)

        #====================
        # Check whether the data is ready
        #====================
        if len(data) != 2 or data[0] != 0 or data[1] != 0:
            print("Error: START")
            exit()
        return data

    #====================
    # DATA
    #====================
    def cmdData(self):
        sendSz = self.sockDsc.sendto(array.array('B', [0xE0]), self.destAddr)
        if sendSz != 1:
            print("Error: DATA send")

        data = self.recvData(100)
        return data

    #====================
    # RESTART
    #====================
    def cmdRestart(self):
        if self.debugMode == 1:
            print("RESTART")
        sendSz = self.sockDsc.sendto(array.array('B', [0xC0]), self.destAddr)
        if sendSz != 1:
            print("Error: RESTART send")

        data = self.recvData(2)

        #====================
        # Check whether the data is ready
        #====================
        if len(data) != 2 or data[0] != 0 or data[1] != 0:
            print("Error: RESTART")
            #exit()
        return data

    #====================
    # BOOT
    #====================
    def cmdBoot(self):
        if self.debugMode == 1:
            print("BOOT")
        sendSz = self.sockDsc.sendto(array.array('B', [0xB0]), self.destAddr)
        if sendSz != 1:
            print("Error: BOOT send")

        data = self.recvData(100)

        #====================
        # Check whether the data is ready
        #====================
        if len(data) != 2 or data[0] != 0 or data[1] != 0:
            print("Error: BOOT")
            exit()
        return data

    #====================
    # STOP
    #====================
    def cmdStop(self):
        if self.debugMode == 1:
            print("STOP")
        sendSz = self.sockDsc.sendto(array.array('B', [0xB2]), self.destAddr)
        if sendSz != 1:
            print("Error: STOP send")

        data = self.recvData(2)

        #====================
        # Check whether the data is ready
        #====================
        #if len(data) != 2 or data[0] != 0 or data[1] != 0:
        #    print("Error: STOP")
        #    exit()

        #time.sleep(0.01)
        return data

    #====================
    # RESET
    #====================
    def cmdReset(self):
        if self.debugMode == 1:
            print("RESET")
        sendSz = self.sockDsc.sendto(array.array('B', [0xB4]), self.destAddr)
        if sendSz != 1:
            print("Error: RESET send")

        data = self.recvData(2)

        #====================
        # Check whether the data is ready
        #====================
        if len(data) != 2 or data[0] != 0 or data[1] != 0:
            print("Error: RESET")
            #exit()
        return data

    #====================
    # STATUS
    #====================
    def cmdStatus(self):
        if self.debugMode == 1:
            print("STATUS")
        sendSz = self.sockDsc.sendto(array.array('B', [0x80]), self.destAddr)
        if sendSz != 1:
            print("Error: STATUS send")

        data = self.recvData(6)

        #====================
        # Check whether the data is ready
        #====================
        if len(data) != 6 or data[0] != 0 or data[1] != 0:
            print("Error: STATUS")
            #exit()
        return data

    #====================
    # SELECT
    #====================
    def cmdSelect(self):
        if self.debugMode == 1:
            print("SELECT")
        sendSz = self.sockDsc.sendto(array.array('B', [0xA0, PROTOCOL_SPI, self.sensorNo]), self.destAddr)
        # sendSz = self.sockDsc.sendto(array.array('B', [0xA0, PROTOCOL_SPI, SENSOR_NO3]), self.destAddr)
        # sendSz = self.sockDsc.sendto(array.array('B', [0xA0, PROTOCOL_SPI, SENSOR_NO2]), self.destAddr)
        # sendSz = self.sockDsc.sendto(array.array('B', [0xA0, PROTOCOL_SPI, SENSOR_NO1]), self.destAddr)
        # sendSz = self.sockDsc.sendto(array.array('B', [0xA0, PROTOCOL_SPI, SENSOR_NO3]), self.destAddr)
        if sendSz != 3:
            print("Error: SELECT send")

        data = self.recvData(2)

        #====================
        # Check whether the data is ready
        #====================
        if len(data) != 2 or data[0] != 0 or data[1] != 0:
            print("Error: SELECT")
            exit()
        return data

    #====================
    # VERSION
    #====================
    def cmdVersion(self):
        if self.debugMode == 1:
            print("VERSION")
        sendSz = self.sockDsc.sendto(array.array('B', [0xA2]), self.destAddr)
        if sendSz != 1:
            print("Error: VERSION send")

        data = self.recvData(8)

        #====================
        # Check whether the data is ready
        #====================
        if len(data) != 8 or data[0] != 0 or data[1] != 0:
            print("Error: VERSION")
            exit()
        return data


#******************************************************************************
# Main Routine
#******************************************************************************
args = sys.argv
if len(args) >= 2:
    measureMax = int(args[1])
else:
    measureMax = 10

dataCounter = 0
mms101data = [
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0]
]
elapsTime = 0.0

# Initialize MMS101
mms101eb = mms101_evaboard_ethernet()

# Firmware Version
if mms101eb.debugMode == 1:
    version = mms101eb.cmdVersion()
    print('Hardware Version: ', version[2:4].hex())
    print('Software Version: ', version[4:8].hex())

# Reset
mms101eb.cmdReset()

# Select
# mms101eb.sensorNo = SENSOR_NO1     # only sensor1
mms101eb.sensorNo = SENSOR_NO1 | SENSOR_NO2 | SENSOR_NO3 # | SENSOR_NO4 | SENSOR_NO5  # 모든 센서 선택
mms101eb.cmdSelect()

# Boot
mms101eb.cmdBoot()
while True:
    # Check State
    status = mms101eb.cmdStatus()
    if status[4] == 0x03:
        # READY State
        break;
    elif status[4] == 0x02:
        # Retry Wait
        time.sleep(0.01)
    else:
        print("BOOT Error")
        exit()

# Start
mms101eb.cmdStart()

time.sleep(0.01)
# 초기화
dataCounter = 0
measureMax = 3000  # 예시 값
elapsTime = 0
mms101data = [[0]*6 for _ in range(5)]  # 5개의 센서, 각 센서당 6개의 데이터

print("Count[times],Time[s],Interval[us],DataUpdate[count],S1Fx[N],S1Fy[N],S1Fz[N],S1Mx[N],S1My[N],S1Mz[N],S2Fx[N],S2Fy[N],S2Fz[N],S2Mx[N],S2My[N],S2Mz[N],S3Fx[N],S3Fy[N],S3Fz[N],S3Mx[N],S3My[N],S3Mz[N],S4Fx[N],S4Fy[N],S4Fz[N],S4Mx[N],S4My[N],S4Mz[N],S5Fx[N],S5Fy[N],S5Fz[N],S5Mx[N],S5My[N],S5Mz[N]")
# 데이터 처리 (센서별 데이터 분리)
while True:
    if dataCounter < measureMax:
        rData = mms101eb.cmdData()
        if len(rData) == 100 and rData[0] == 0x00 and rData[1] == 0x00:
            measStatus = (rData[2] << 8) + rData[3]
            measCount = (rData[4] << 8) + rData[5]
            intervalTime = (rData[6] << 24) + (rData[7] << 16) + (rData[8] << 8) + rData[9]
            elapsTime += (intervalTime / 1000000)
            
            # 센서별 데이터 파싱
            for sens in range(5):  # 5개의 센서
                for axis in range(6):  # Fx, Fy, Fz, Mx, My, Mz
                    base_index = (sens * 18) + (axis * 3) + 10  # 각 센서 데이터의 시작 위치 계산
                    mms101data[sens][axis] = (rData[base_index] << 16) + (rData[base_index + 1] << 8) + rData[base_index + 2]
                    if mms101data[sens][axis] >= 0x00800000:
                        mms101data[sens][axis] -= 0x1000000  # 음수 처리

                # 변환
                mms101data[sens][0] /= 1000  # Fx
                mms101data[sens][1] /= 1000  # Fy
                mms101data[sens][2] /= 1000  # Fz
                mms101data[sens][3] /= 100000  # Mx
                mms101data[sens][4] /= 100000  # My
                mms101data[sens][5] /= 100000  # Mz

            # 결과 출력
            print(f'{dataCounter},{elapsTime:.3f},{intervalTime},{measCount}', end="")
            for sens in range(5):  # 각 센서별 데이터 출력
                print(f',{mms101data[sens][0]:.3f},{mms101data[sens][1]:.3f},{mms101data[sens][2]:.3f},{mms101data[sens][3]:.5f},{mms101data[sens][4]:.5f},{mms101data[sens][5]:.5f}', end="")
            print()  # 줄바꿈
        else:
            print('Error: Result data', len(rData))

        dataCounter += 1
        time.sleep(0.001)
    else:
        break  # 측정이 완료되면 루프 종료