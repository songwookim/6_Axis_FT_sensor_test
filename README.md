# MMS-101 6-Axis Force/Torque Sensor Test

Minebea Mitsumi MMS-101 evaluation board — Python control & visualization

## Requirements

```bash
pip install hydra-core omegaconf numpy pyyaml matplotlib
```

## Hardware Setup

<img src="./images/back.jpg" width="200"> <img src="./images/front.jpg" width="200">

- Check whether **only pin 2** is raised on the evaluation board.

## Network Configuration

### Host PC

| Item    | Value           |
|---------|-----------------|
| Address | `192.168.0.100` |
| Netmask | `255.255.255.0` |
| Gateway | `192.168.0.1`   |

### Sensor (`config.yaml`)

```yaml
mms101:
  dest_ip: "192.168.0.200"
  dest_port: 1366
  src_port: 2000
```

접속 확인:

```bash
ping 192.168.0.200
```

## Usage

```bash
# 기본 실행
python main.py

# config 값 오버라이드
python main.py mms101.measure_max=500 mms101.debug=true

# CSV 로깅
python log_csv.py --samples 1000 --interval 0.02

# 실시간 플롯
python plot_live.py --window 500

# 저장된 CSV 플롯
python plot_csv.py --csv sensor_data.csv
```

## File Structure

| File | Description |
|------|-------------|
| `main.py` | 진입점 (Hydra config 로딩) |
| `mms101_controller.py` | MMS-101 UDP 통신 및 데이터 파싱 |
| `config.yaml` | 센서 IP, 포트, 센서 수 등 설정 |
| `log_csv.py` | 센서 데이터 CSV 기록 |
| `plot_csv.py` | 저장된 CSV 데이터 플롯 |
| `plot_live.py` | 실시간 데이터 플롯 |
| `legacy.py` | 제조사 제공 샘플 코드 (참고용) |

## References

- [Product Info & Datasheet](https://pr.minebeamitsumi.com/6axisforce/)
- [Sample Codes & CAD Files](https://nmbtc.com/parts/mms101evalkit/)
