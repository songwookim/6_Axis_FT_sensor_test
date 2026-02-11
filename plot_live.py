#!/usr/bin/env python3
"""
Real-time plot of MMS-101 values for multiple sensors.
Plotted components: Fx, Fy, Fz, τx, τy, τz (6 subplots). Each subplot shows lines for selected sensors.

Usage examples:
    # plot all configured sensors (default)
    python3 plot_live.py

    # plot a single sensor (index 1)
    python3 plot_live.py --sensor 1

    # plot selected sensors (indices 0 and 2)
    python3 plot_live.py --sensors 0,2

Requirements:
    - matplotlib installed
    - config.yaml present with mms101.* fields
    - ensure src_port from config isn't in use by another process
"""

import argparse
import time
from collections import deque
from types import SimpleNamespace
import warnings
import yaml
import numpy as np

# Suppress Matplotlib 3D projection warning when mixed installs exist
warnings.filterwarnings(
    "ignore",
    message=r"Unable to import Axes3D.*",
    category=UserWarning,
    module=r"matplotlib\.projections.*",
)

import matplotlib.pyplot as plt

from mms101_controller import MMS101Controller


def load_config(path: str):
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    # Build a minimal object with attribute access: config.mms101.<field>
    cfg = SimpleNamespace()
    cfg.mms101 = SimpleNamespace(**data['mms101'])
    return cfg


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.yaml')
    parser.add_argument('--sensor', type=int, default=None, help='single sensor index to plot (0-based); ignored if --sensors is provided')
    parser.add_argument('--sensors', type=str, default='all', help="comma-separated sensor indices to plot (e.g., '0,1,2'); 'all' for all sensors")
    parser.add_argument('--window', type=int, default=500, help='number of recent samples to show')
    parser.add_argument('--interval', type=float, default=0.02, help='target loop interval seconds')
    parser.add_argument('--refresh-every', type=int, default=20, help='autoscale and axes update frequency (frames)')
    parser.add_argument('--no-blit', action='store_true', help='disable blitting (fallback full redraw)')
    parser.add_argument('--no-grid', action='store_true', help='disable grid for faster plotting')
    # Optional overrides to avoid editing config.yaml
    parser.add_argument('--src-port', type=int, default=None, help='override source UDP port (e.g., 2001)')
    parser.add_argument('--dest-ip', type=str, default=None, help='override destination IP')
    parser.add_argument('--dest-port', type=int, default=None, help='override destination UDP port')
    args = parser.parse_args()

    cfg = load_config(args.config)
    # Apply CLI overrides when provided
    if args.src_port is not None:
        cfg.mms101.src_port = args.src_port
    if args.dest_ip is not None:
        cfg.mms101.dest_ip = args.dest_ip
    if args.dest_port is not None:
        cfg.mms101.dest_port = args.dest_port
    # Determine sensors to plot
    total_sensors = int(getattr(cfg.mms101, 'n_sensors', 1))
    if args.sensors and args.sensors.lower() != 'all':
        sensors = []
        for tok in args.sensors.split(','):
            tok = tok.strip()
            if tok == '':
                continue
            try:
                si = int(tok)
                if 0 <= si < total_sensors:
                    sensors.append(si)
            except ValueError:
                pass
        if not sensors:
            sensors = [args.sensor] if args.sensor is not None else list(range(total_sensors))
    else:
        sensors = [args.sensor] if args.sensor is not None else list(range(total_sensors))

    # Deduplicate and sort
    sensors = sorted(set([s for s in sensors if 0 <= s < total_sensors]))
    if not sensors:
        sensors = [0]

    ctrl = MMS101Controller(cfg)

    # Prepare buffers
    buf_len = max(50, args.window)
    t0 = time.monotonic()
    ts = deque(maxlen=buf_len)
    # data_deques[comp_index][sensor_index] -> deque
    # comp_index: 0..5 => Fx,Fy,Fz,Tx,Ty,Tz
    data_deques = [[deque(maxlen=buf_len) for _ in sensors] for _ in range(6)]

    # Matplotlib setup
    plt.ion()
    fig, axs = plt.subplots(2, 3, figsize=(13, 6), sharex=True)
    axs = axs.ravel()
    comp_names = ['Fx [N]', 'Fy [N]', 'Fz [N]', r'$\tau_x$ [N·m]', r'$\tau_y$ [N·m]', r'$\tau_z$ [N·m]']
    # Distinct colors for up to 6 sensors
    colors = ['tab:red', 'tab:blue', 'tab:green', 'tab:orange', 'tab:purple', 'tab:brown']
    lines = []
    for ci, ax in enumerate(axs):
        ax.set_title(comp_names[ci])
        ax.grid(not args.no_grid)
        row = []
        for si, sidx in enumerate(sensors):
            color = colors[si % len(colors)]
            (ln,) = ax.plot([], [], '-', color=color, label=f'S{sidx}')
            row.append(ln)
        lines.append(row)
    axs[0].legend(loc='upper right', ncols=min(len(sensors), 3), fontsize=8)
    axs[3].set_xlabel('Time [s]')
    axs[4].set_xlabel('Time [s]')
    axs[5].set_xlabel('Time [s]')

    # Try to enable blitting for speed
    use_blit = not args.no_blit
    background = None
    if use_blit:
        try:
            for row in lines:
                for ln in row:
                    ln.set_animated(True)
            fig.canvas.draw()
            copy_from_bbox = getattr(fig.canvas, 'copy_from_bbox', None)
            if callable(copy_from_bbox):
                background = copy_from_bbox(fig.bbox)
            else:
                use_blit = False
        except Exception:
            use_blit = False

    try:
        i = 0
        frame = 0
        while True:
            d = ctrl.run(i)
            i += 1
            if d is None:
                # no data this tick
                time.sleep(args.interval)
                continue
            try:
                v = np.asarray(d)
                # Expect shape (n_sensors, 6)
                if v.ndim != 2 or v.shape[1] < 6:
                    time.sleep(args.interval)
                    continue
            except Exception:
                time.sleep(args.interval)
                continue

            now = time.monotonic() - t0
            ts.append(now)
            # Append values for selected sensors and all 6 components
            for si, sidx in enumerate(sensors):
                if sidx >= v.shape[0]:
                    continue
                for ci in range(6):
                    try:
                        data_deques[ci][si].append(float(v[sidx, ci]))
                    except Exception:
                        # keep lengths consistent
                        data_deques[ci][si].append(np.nan)

            # Update lines
            if len(ts) >= 2:
                # Set new data on lines
                for ci, ax in enumerate(axs):
                    for si, _ in enumerate(sensors):
                        lines[ci][si].set_data(ts, data_deques[ci][si])

                # Recompute axes limits at a lower frequency
                full_redraw = False
                if frame % max(1, args.refresh_every) == 0:
                    # Y-limits per component
                    for ci, ax in enumerate(axs):
                        y_vals = []
                        for si, _ in enumerate(sensors):
                            y_vals += [y for y in data_deques[ci][si] if y == y]
                        if y_vals:
                            y_min = min(y_vals)
                            y_max = max(y_vals)
                            if y_min == y_max:
                                y_min -= 1.0
                                y_max += 1.0
                            margin = 0.1 * (y_max - y_min)
                            ax.set_ylim(y_min - margin, y_max + margin)
                    # Shared X-limits
                    x0 = max(0, ts[0])
                    x1 = ts[-1] if ts[-1] > 5 else 5
                    for ax in axs:
                        ax.set_xlim(x0, x1)
                    fig.suptitle(f'MMS-101 Live (sensors {",".join(map(str, sensors))})', fontsize=12)
                    full_redraw = True

                if use_blit and background is not None and not full_redraw:
                    try:
                        # Fast path: restore background and draw only lines
                        restore_region = getattr(fig.canvas, 'restore_region', None)
                        if callable(restore_region):
                            restore_region(background)
                        for ci, ax in enumerate(axs):
                            for si, _ in enumerate(sensors):
                                ax.draw_artist(lines[ci][si])
                        blit = getattr(fig.canvas, 'blit', None)
                        if callable(blit):
                            blit(fig.bbox)
                        fig.canvas.flush_events()
                    except Exception:
                        # Fallback to full redraw
                        fig.canvas.draw()
                        fig.canvas.flush_events()
                        # Reset background for subsequent blits
                        try:
                            copy_from_bbox = getattr(fig.canvas, 'copy_from_bbox', None)
                            if callable(copy_from_bbox):
                                background = copy_from_bbox(fig.bbox)
                            else:
                                use_blit = False
                        except Exception:
                            use_blit = False
                else:
                    # Full redraw when limits change or blit disabled
                    fig.canvas.draw()
                    fig.canvas.flush_events()
                    if use_blit:
                        try:
                            copy_from_bbox = getattr(fig.canvas, 'copy_from_bbox', None)
                            if callable(copy_from_bbox):
                                background = copy_from_bbox(fig.bbox)
                            else:
                                use_blit = False
                        except Exception:
                            use_blit = False

                frame += 1

            # Pace the loop
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        plt.ioff()
        try:
            plt.show(block=False)
        except Exception:
            pass


if __name__ == '__main__':
    main()
