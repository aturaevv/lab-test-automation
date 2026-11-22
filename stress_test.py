#!/usr/bin/env python3
"""
Stress test with logging: loads CPU and disk, logs system metrics to CSV,
prints a PASS/FAIL summary and saves a plot.

Example:
    python stress_test.py --duration 30 --interval 1
"""
import argparse
import csv
import multiprocessing as mp
import os
import statistics
import sys
import tempfile
import time
from datetime import datetime

import psutil


def cpu_worker(stop_event):
    """Keep one CPU core busy until told to stop."""
    x = 0
    while not stop_event.is_set():
        for i in range(100_000):
            x += i * i


def disk_worker(stop_event, directory):
    """Write 1 MB blocks to a temp file (max 256 MB) until told to stop."""
    path = os.path.join(directory, "stress_io.tmp")
    block = os.urandom(1024 * 1024)
    try:
        with open(path, "wb") as f:
            while not stop_event.is_set():
                f.write(block)
                f.flush()
                os.fsync(f.fileno())
                if f.tell() >= 256 * 1024 * 1024:
                    f.seek(0)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def parse_args():
    p = argparse.ArgumentParser(description="CPU and disk stress test with CSV logging.")
    p.add_argument("--duration", type=int, default=30, help="test length in seconds (default 30)")
    p.add_argument("--interval", type=float, default=1.0, help="seconds between samples (default 1)")
    p.add_argument("--workers", type=int, default=os.cpu_count() or 1,
                   help="number of CPU load processes (default: all cores)")
    p.add_argument("--no-disk", action="store_true", help="skip the disk write load")
    p.add_argument("--mem-limit", type=float, default=90.0,
                   help="FAIL if memory usage exceeds this percent (default 90)")
    p.add_argument("--output", default="results.csv", help="CSV file name (default results.csv)")
    return p.parse_args()


def save_plot(rows, png_path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed, skipping plot (pip install matplotlib)")
        return
    t = [r["elapsed_s"] for r in rows]
    fig, ax = plt.subplots(3, 1, figsize=(8, 7), sharex=True)
    ax[0].plot(t, [r["cpu_percent"] for r in rows])
    ax[0].set_ylabel("CPU %")
    ax[1].plot(t, [r["mem_percent"] for r in rows], color="tab:orange")
    ax[1].set_ylabel("Memory %")
    ax[2].plot(t, [r["disk_write_mb_s"] for r in rows], color="tab:green")
    ax[2].set_ylabel("Disk write MB/s")
    ax[2].set_xlabel("Elapsed time, s")
    fig.suptitle("Stress test")
    fig.tight_layout()
    fig.savefig(png_path, dpi=120)
    print(f"Plot saved: {png_path}")


def main():
    args = parse_args()
    stop = mp.Event()
    procs = [mp.Process(target=cpu_worker, args=(stop,)) for _ in range(args.workers)]
    tmpdir = tempfile.mkdtemp(prefix="stress_")
    if not args.no_disk:
        procs.append(mp.Process(target=disk_worker, args=(stop, tmpdir)))

    for p in procs:
        p.start()
    print(f"Started {len(procs)} load processes for {args.duration} s")

    psutil.cpu_percent(interval=None)  # first call is a baseline
    last_io = psutil.disk_io_counters()
    rows = []
    start = time.time()
    died = False

    try:
        while time.time() - start < args.duration:
            time.sleep(args.interval)
            io = psutil.disk_io_counters()
            write_mb_s = (io.write_bytes - last_io.write_bytes) / args.interval / 1_000_000
            last_io = io
            row = {
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "elapsed_s": round(time.time() - start, 1),
                "cpu_percent": psutil.cpu_percent(interval=None),
                "mem_percent": psutil.virtual_memory().percent,
                "disk_write_mb_s": round(write_mb_s, 2),
            }
            rows.append(row)
            print(f"{row['elapsed_s']:>6}s  CPU {row['cpu_percent']:>5}%  "
                  f"MEM {row['mem_percent']:>5}%  DISK {row['disk_write_mb_s']:>7} MB/s")
            if not all(p.is_alive() for p in procs):
                died = True
                print("A load process stopped unexpectedly.")
                break
    except KeyboardInterrupt:
        print("Interrupted by user.")
    finally:
        stop.set()
        for p in procs:
            p.join(timeout=5)
            if p.is_alive():
                p.terminate()

    if not rows:
        print("No samples collected.")
        sys.exit(1)

    with open(args.output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    cpu = [r["cpu_percent"] for r in rows]
    mem = [r["mem_percent"] for r in rows]
    mem_ok = max(mem) <= args.mem_limit
    passed = mem_ok and not died

    print("\n--- Summary ---")
    print(f"Samples:  {len(rows)}")
    print(f"CPU %:    min {min(cpu)}  max {max(cpu)}  avg {statistics.mean(cpu):.1f}")
    print(f"Memory %: min {min(mem)}  max {max(mem)}  avg {statistics.mean(mem):.1f}")
    print(f"Memory limit {args.mem_limit}%: {'OK' if mem_ok else 'EXCEEDED'}")
    print(f"Load processes alive: {'yes' if not died else 'NO'}")
    print(f"RESULT: {'PASS' if passed else 'FAIL'}")
    print(f"Log saved: {args.output}")

    save_plot(rows, os.path.splitext(args.output)[0] + ".png")
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
