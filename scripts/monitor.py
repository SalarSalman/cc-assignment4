#!/usr/bin/env python3
"""Profiling: host CPU every 1 s; per-pod CPU/memory and replica counts every 15 s -> CSV."""
import argparse, csv, datetime, subprocess, threading, time
import psutil


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def sh(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return ""


def host_loop(path, stop):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "epoch", "host_cpu_percent"])
        psutil.cpu_percent(None)
        while not stop.wait(1):
            w.writerow([now(), int(time.time()), psutil.cpu_percent(None)])
            f.flush()


def pods_loop(path, stop, ns, interval):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "epoch", "pod", "cpu_millicores", "memory_mi"])
        while not stop.is_set():
            t0 = time.time()
            out = sh(["kubectl", "top", "pods", "-n", ns, "--no-headers"])
            ts, ep = now(), int(time.time())
            for line in out.splitlines():
                p = line.split()
                if len(p) >= 3:
                    w.writerow([ts, ep, p[0], p[1].rstrip("m"), p[2].rstrip("Mi")])
            f.flush()
            stop.wait(max(0, interval - (time.time() - t0)))


def replicas_loop(path, stop, ns, interval):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "epoch", "spec_replicas", "ready_replicas",
                    "hpa_current", "hpa_desired", "hpa_cpu_percent"])
        while not stop.is_set():
            t0 = time.time()
            d = sh(["kubectl", "get", "deploy", "emi-web", "-n", ns, "-o",
                    "jsonpath={.spec.replicas} {.status.readyReplicas}"]).split()
            h = sh(["kubectl", "get", "hpa", "emi-web", "-n", ns, "-o",
                    "jsonpath={.status.currentReplicas} {.status.desiredReplicas} "
                    "{.status.currentMetrics[0].resource.current.averageUtilization}"]).split()
            d += [""] * (2 - len(d))
            h += [""] * (3 - len(h))
            w.writerow([now(), int(time.time())] + d[:2] + h[:3])
            f.flush()
            stop.wait(max(0, interval - (time.time() - t0)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results")
    ap.add_argument("--tag", default="run")
    ap.add_argument("--ns", default="emi")
    ap.add_argument("--interval", type=int, default=15)
    ap.add_argument("--duration", type=int, default=0, help="seconds; 0 = until Ctrl+C")
    a = ap.parse_args()

    stop = threading.Event()
    base = f"{a.out}/{a.tag}"
    threads = [
        threading.Thread(target=host_loop, args=(base + "_host_cpu.csv", stop)),
        threading.Thread(target=pods_loop, args=(base + "_pods.csv", stop, a.ns, a.interval)),
        threading.Thread(target=replicas_loop, args=(base + "_replicas.csv", stop, a.ns, a.interval)),
    ]
    for t in threads:
        t.start()
    try:
        if a.duration:
            stop.wait(a.duration)
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    stop.set()
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
