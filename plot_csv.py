#!/usr/bin/env python3
"""
Plot MMS-101 CSV logs (Fx, Fy, Fz, Tx, Ty, Tz) per sensor.

Expected CSV columns (header names are matched case-sensitively):
  - time_iso, t_elapsed_s, sample_idx, sensor_idx, Fx, Fy, Fz, Tx, Ty, Tz

If some names are missing, the script falls back to standard index positions
assuming the same order as above.
"""

import argparse
import csv
import os
from typing import Dict, List, Optional, Tuple
import re

import matplotlib.pyplot as plt


def parse_sensors(arg: Optional[str], total_present: List[int]) -> List[int]:
    if arg and arg.lower() != 'all':
        sensors = []
        for tok in arg.split(','):
            tok = tok.strip()
            if not tok:
                continue
            try:
                sensors.append(int(tok))
            except ValueError:
                pass
        sensors = sorted(set([s for s in sensors if s in total_present]))
        return sensors if sensors else total_present
    return sorted(total_present)


def load_csv(csv_path: str) -> Tuple[Dict[int, Dict[str, List[float]]], List[int]]:
    """
    Load CSV supporting two layouts:

    1) Long format (one sensor per row) with columns like:
       time_iso, t_elapsed_s, sample_idx, sensor_idx, Fx, Fy, Fz, Tx, Ty, Tz

    2) Wide format (all sensors per row) with columns like:
       t_sec, iter, Fx_1, Fy_1, Fz_1, Mx_1, My_1, Mz_1, Fx_2, ...
       (Torque columns may be Mx/My/Mz or Tx/Ty/Tz; suffix _<sensorId> optional for single sensor.)
    """
    with open(csv_path, 'r', newline='') as f:
        r = csv.reader(f)
        header = next(r, None)
        if not header:
            return {}, []

        # Detect layout
        long_layout = 'sensor_idx' in header or ('Fx' in header and 'Tx' in header and 'sensor_idx' in header)

        data: Dict[int, Dict[str, List[float]]] = {}
        present_set = set()

        if long_layout:
            # Original parser path
            def idx(name: str, default: Optional[int] = None) -> Optional[int]:
                if name in header:
                    return header.index(name)
                return default

            i_t = idx('t_elapsed_s', None)
            if i_t is None:
                # fallback possible names
                for cand in ['t_sec', 'time', 't']:
                    if cand in header:
                        i_t = header.index(cand)
                        break
            i_sidx = idx('sensor_idx', None)
            named_axes = ['Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz']
            axes_idx = [idx(n, None) for n in named_axes]
            # Fallback positional if any missing
            if any(a is None for a in axes_idx):
                # Attempt torque synonyms Mx/My/Mz
                torque_syn = {'Tx': ('Tx', 'Mx'), 'Ty': ('Ty', 'My'), 'Tz': ('Tz', 'Mz')}
                for i, name in enumerate(named_axes):
                    if axes_idx[i] is None:
                        for alt in torque_syn.get(name, (name,)):
                            if alt in header:
                                axes_idx[i] = header.index(alt)
                                break
            if any(a is None for a in axes_idx):
                # Last resort: assume indices
                # Find starting index by locating first force-like column
                start_guess = None
                for candidate in ['Fx', 'Fx_1']:
                    if candidate in header:
                        start_guess = header.index(candidate)
                        break
                if start_guess is None:
                    start_guess = 4
                axes_idx = list(range(start_guess, start_guess + 6))

            row_index = 0
            for row in r:
                row_index += 1
                if not row:
                    continue
                try:
                    # time fallback: use specified column or row count
                    if i_t is not None and i_t < len(row):
                        t = float(row[i_t])
                    else:
                        t = float(row_index)
                    sidx = int(row[i_sidx]) if (i_sidx is not None and i_sidx < len(row)) else 0
                    vals: List[float] = []
                    ok = True
                    for j in axes_idx:
                        if j is None or j >= len(row):
                            ok = False
                            break
                        try:
                            vals.append(float(row[j]))
                        except ValueError:
                            ok = False
                            break
                    if not ok or len(vals) != 6:
                        continue
                except Exception:
                    continue

                present_set.add(sidx)
                if sidx not in data:
                    data[sidx] = {k: [] for k in ['t', 'Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz']}
                d = data[sidx]
                d['t'].append(t)
                d['Fx'].append(vals[0])
                d['Fy'].append(vals[1])
                d['Fz'].append(vals[2])
                d['Tx'].append(vals[3])
                d['Ty'].append(vals[4])
                d['Tz'].append(vals[5])
            return data, sorted(present_set)

        # Wide layout parsing
        # Identify time column
        time_col = None
        for cand in ['t_elapsed_s', 't_sec', 'time', 't', 'timestamp']:
            if cand in header:
                time_col = header.index(cand)
                break
        if time_col is None:
            # fallback: first column
            time_col = 0

        # Build sensor axis map: sensor_id -> axis -> column index
        # Accept patterns: Fx, Fy, Fz, Tx, Ty, Tz, Mx, My, Mz with optional _<id>
        axis_pattern = re.compile(r'^(F[xyz]|T[xyz]|M[xyz])(?:_(\d+))?$', re.IGNORECASE)
        sensor_axes: Dict[int, Dict[str, int]] = {}
        for ci, name in enumerate(header):
            m = axis_pattern.match(name)
            if not m:
                continue
            axis_raw, sid_raw = m.group(1), m.group(2)
            axis_norm = axis_raw.upper()
            if axis_norm.startswith('M'):
                # Map Mx/My/Mz -> Tx/Ty/Tz
                axis_norm = 'T' + axis_norm[1]
            # Force F? keep as is (Fx/Fy/Fz)
            if axis_norm[0] not in ['F', 'T']:
                continue
            sid = int(sid_raw) if sid_raw is not None else 0
            if sid not in sensor_axes:
                sensor_axes[sid] = {}
            sensor_axes[sid][axis_norm] = ci

        if not sensor_axes:
            return {}, []

        # Prepare data containers
        for sid in sensor_axes.keys():
            data[sid] = {k: [] for k in ['t', 'Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz']}

        for row in r:
            if not row:
                continue
            try:
                t = float(row[time_col]) if time_col < len(row) else float(len(data.get(0, {}).get('t', [])))
            except Exception:
                continue
            for sid, axes_map in sensor_axes.items():
                # Ensure all 6 axes exist; if any missing skip this sensor for this row
                needed = {
                    'Fx': axes_map.get('FX'), 'Fy': axes_map.get('FY'), 'Fz': axes_map.get('FZ'),
                    'Tx': axes_map.get('TX'), 'Ty': axes_map.get('TY'), 'Tz': axes_map.get('TZ')
                }
                # Case-insensitive map attempt if uppercase keys not present
                if any(v is None for v in needed.values()):
                    # Rebuild with case-insensitive by scanning names again (rare)
                    pass
                try:
                    vals_ok = True
                    extracted = {}
                    for k, col in needed.items():
                        if col is None or col >= len(row):
                            vals_ok = False
                            break
                        extracted[k] = float(row[col])
                    if not vals_ok:
                        continue
                except Exception:
                    continue
                d = data[sid]
                d['t'].append(t)
                for k in ['Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz']:
                    d[k].append(extracted[k])
                present_set.add(sid)

        return data, sorted(present_set)


def downsample(x: List[float], y: List[float], max_points: int):
    n = min(len(x), len(y))
    if max_points <= 0 or n <= max_points:
        return x, y
    stride = max(1, n // max_points)
    return x[::stride], y[::stride]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--csv', default='sensor_data.csv', help='path to CSV file (default: sensor_data.csv)')
    ap.add_argument('--sensors', default='all', help="comma-separated sensor indices or 'all'")
    ap.add_argument('--max-points', type=int, default=20000, help='max points per plotted line (downsampled if exceeded)')
    ap.add_argument('--no-grid', action='store_true', help='disable grid for performance')
    ap.add_argument('--save', default=None, help='optional path to save the figure instead of showing')
    args = ap.parse_args()

    # Resolve CSV path (try CWD first, then script directory if relative and missing)
    csv_path = args.csv
    if not os.path.isabs(csv_path):
        if not os.path.exists(csv_path):
            script_dir_candidate = os.path.join(os.path.dirname(os.path.abspath(__file__)), csv_path)
            if os.path.exists(script_dir_candidate):
                csv_path = script_dir_candidate
    if not os.path.exists(csv_path):
        print(f'CSV file not found: {args.csv}')
        print('Tried:')
        print(f'  - {os.path.abspath(args.csv)}')
        if not os.path.isabs(args.csv):
            print(f'  - {os.path.join(os.path.dirname(os.path.abspath(__file__)), args.csv)}')
        return

    data, present = load_csv(csv_path)
    if not present:
        print('No data found in CSV.')
        return
    sensors = parse_sensors(args.sensors, present)

    # Build figure
    fig, axs = plt.subplots(2, 3, figsize=(13, 6), sharex=True)
    axs = axs.ravel()
    comp_keys = ['Fx', 'Fy', 'Fz', 'Tx', 'Ty', 'Tz']
    # Use mathtext tau; single leading backslash inside raw string
    comp_titles = ['Fx [N]', 'Fy [N]', 'Fz [N]', r'$\tau_x$ [N·m]', r'$\tau_y$ [N·m]', r'$\tau_z$ [N·m]']
    colors = ['tab:red', 'tab:blue', 'tab:green', 'tab:orange', 'tab:purple', 'tab:brown']

    for ci, ax in enumerate(axs):
        ax.set_title(comp_titles[ci])
        ax.grid(not args.no_grid)
        key = comp_keys[ci]
        for si, sidx in enumerate(sensors):
            d = data.get(sidx)
            if not d or not d['t']:
                continue
            x, y = downsample(d['t'], d[key], args.max_points)
            ax.plot(x, y, '-', color=colors[si % len(colors)], label=f'S{sidx}')

    axs[0].legend(loc='upper right', ncols=min(len(sensors), 3), fontsize=8)
    axs[3].set_xlabel('Time [s]')
    axs[4].set_xlabel('Time [s]')
    axs[5].set_xlabel('Time [s]')
    fig.suptitle(f'CSV Plot: {os.path.basename(csv_path)} (sensors {",".join(map(str, sensors))})', fontsize=12)
    fig.tight_layout()

    if args.save:
        fig.savefig(args.save, dpi=150)
        print(f'Saved figure: {args.save}')
    else:
        plt.show()


if __name__ == '__main__':
    main()
