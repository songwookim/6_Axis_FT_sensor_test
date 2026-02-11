#!/usr/bin/env python3
"""
Simple CSV logger for MMS-101.
Loops, reads data from MMS101Controller, and appends rows to a CSV file.

Columns: time_iso, t_elapsed_s, sample_index, sensor_index, Fx, Fy, Fz, Tx, Ty, Tz

Default output: outputs/YYYY-MM-DD/HH-MM-SS/mms101_log.csv
"""

import argparse
import csv
import os
from datetime import datetime
import time
from types import SimpleNamespace
import yaml
import numpy as np

from mms101_controller import MMS101Controller


def load_config(path: str):
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    cfg = SimpleNamespace()
    cfg.mms101 = SimpleNamespace(**data['mms101'])
    return cfg


def default_output_path() -> str:
    now = datetime.now()
    base = os.path.join('outputs', now.strftime('%Y-%m-%d'), now.strftime('%H-%M-%S'))
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, 'mms101_log.csv')


def parse_sensors(arg: str | None, single: int | None, total: int) -> list[int]:
    if arg and arg.lower() != 'all':
        sensors: list[int] = []
        for tok in arg.split(','):
            tok = tok.strip()
            if not tok:
                continue
            try:
                si = int(tok)
                if 0 <= si < total:
                    sensors.append(si)
            except ValueError:
                continue
        if sensors:
            return sorted(set(sensors))
    if single is not None and 0 <= single < total:
        return [single]
    return list(range(total))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', default='config.yaml')
    p.add_argument('--output', default=None, help='CSV file path (default under outputs/YYYY-MM-DD/HH-MM-SS)')
    p.add_argument('--interval', type=float, default=0.02, help='loop sleep seconds between reads')
    p.add_argument('--samples', type=int, default=0, help='stop after N samples (0 = infinite)')
    p.add_argument('--duration', type=float, default=0.0, help='stop after seconds (0 = infinite)')
    p.add_argument('--sensor', type=int, default=None, help='single sensor index to log')
    p.add_argument('--sensors', type=str, default='all', help="comma-separated indexes or 'all'")
    p.add_argument('--append', action='store_true', help='append to existing CSV (no header rewrite)')
    p.add_argument('--plot', action='store_true', help='plot the recorded CSV after logging completes')
    p.add_argument('--max-points', type=int, default=20000, help='max points per line when plotting (downsample if exceeded)')
    p.add_argument('--no-grid', action='store_true', help='disable grid in plot')
    # Optional overrides to avoid editing config.yaml
    p.add_argument('--src-port', type=int, default=None, help='override source UDP port')
    p.add_argument('--dest-ip', type=str, default=None, help='override destination IP')
    p.add_argument('--dest-port', type=int, default=None, help='override destination UDP port')
    args = p.parse_args()

    cfg = load_config(args.config)
    if args.src_port is not None:
        cfg.mms101.src_port = args.src_port
    if args.dest_ip is not None:
        cfg.mms101.dest_ip = args.dest_ip
    if args.dest_port is not None:
        cfg.mms101.dest_port = args.dest_port

    total = int(getattr(cfg.mms101, 'n_sensors', 1))
    sensors = parse_sensors(args.sensors, args.sensor, total)

    out_path = args.output or default_output_path()
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    ctrl = MMS101Controller(cfg)

    start = time.monotonic()
    written = 0
    i = 0
    end_time = start + args.duration if args.duration and args.duration > 0 else None

    mode = 'a' if args.append and os.path.exists(out_path) else 'w'
    with open(out_path, mode, newline='') as f:
        w = csv.writer(f)
        if mode == 'w':
            w.writerow(['time_iso', 't_elapsed_s', 'sample_idx', 'sensor_idx', 'Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz'])

        try:
            while True:
                if args.samples > 0 and written >= args.samples:
                    break
                if end_time is not None and time.monotonic() >= end_time:
                    break

                d = ctrl.run(i)
                i += 1
                if d is None:
                    time.sleep(args.interval)
                    continue

                try:
                    v = np.asarray(d)
                    if v.ndim != 2 or v.shape[1] < 6:
                        time.sleep(args.interval)
                        continue
                except Exception:
                    time.sleep(args.interval)
                    continue

                t_elapsed = time.monotonic() - start
                t_iso = datetime.now().isoformat(timespec='milliseconds')

                for sidx in sensors:
                    if sidx >= v.shape[0]:
                        continue
                    row = [t_iso, f"{t_elapsed:.6f}", i, sidx]
                    vals = [float(v[sidx, j]) for j in range(6)]
                    row.extend(vals)
                    w.writerow(row)
                    written += 1

                # Flush occasionally
                if written % 50 == 0:
                    f.flush()

                time.sleep(args.interval)
        except KeyboardInterrupt:
            pass

    print(f"CSV saved: {out_path} ({written} rows)")

    # Optional: plot the recorded CSV
    if args.plot:
        try:
            plot_recorded_csv(out_path, sensors, args.max_points, no_grid=args.no_grid)
        except Exception as e:
            print(f"Plot failed: {e}")


def plot_recorded_csv(csv_path: str, sensors: list[int], max_points: int = 20000, no_grid: bool = False) -> None:
    import matplotlib.pyplot as plt

    # Prepare containers per sensor
    data: dict[int, dict[str, list[float]]] = {}
    for s in sensors:
        data[s] = {
            't': [], 'Fx': [], 'Fy': [], 'Fz': [], 'Tx': [], 'Ty': [], 'Tz': []
        }

    # Read CSV
    with open(csv_path, 'r', newline='') as f:
        r = csv.reader(f)
        header = next(r, None)
        for row in r:
            if len(row) < 10:
                continue
            try:
                t_elapsed = float(row[1])
                sidx = int(row[3])
                if sidx not in data:
                    continue
                vals = [float(row[j]) for j in range(4, 10)]
            except Exception:
                continue
            d = data[sidx]
            d['t'].append(t_elapsed)
            d['Fx'].append(vals[0])
            d['Fy'].append(vals[1])
            d['Fz'].append(vals[2])
            d['Tx'].append(vals[3])
            d['Ty'].append(vals[4])
            d['Tz'].append(vals[5])

    # Downsample helper
    def ds(x: list[float], stride: int) -> list[float]:
        return x[::stride] if stride > 1 else x

    # Build figure
    fig, axs = plt.subplots(2, 3, figsize=(13, 6), sharex=True)
    axs = axs.ravel()
    comp_keys = ['Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz']
    comp_titles = ['Fx [N]', 'Fy [N]', 'Fz [N]', r'$\\tau_x$ [N·m]', r'$\\tau_y$ [N·m]', r'$\\tau_z$ [N·m]']
    colors = ['tab:red', 'tab:blue', 'tab:green', 'tab:orange', 'tab:purple', 'tab:brown']

    for ci, ax in enumerate(axs):
        ax.set_title(comp_titles[ci])
        ax.grid(not no_grid)
        key = comp_keys[ci]
        for si, sidx in enumerate(sensors):
            d = data.get(sidx)
            if not d or not d['t']:
                continue
            n = len(d['t'])
            stride = max(1, (n // max_points))
            ax.plot(ds(d['t'], stride), ds(d[key], stride), '-', color=colors[si % len(colors)], label=f'S{sidx}')

    axs[0].legend(loc='upper right', ncols=min(len(sensors), 3), fontsize=8)
    axs[3].set_xlabel('Time [s]')
    axs[4].set_xlabel('Time [s]')
    axs[5].set_xlabel('Time [s]')
    fig.suptitle(f'CSV Plot: {os.path.basename(csv_path)} (sensors {",".join(map(str, sensors))})', fontsize=12)
    plt.tight_layout()
    plt.show()


if __name__ == '__main__':
    main()
