#!/usr/bin/env python3
"""10-minute autoscaling test: 2 min @10 req/s, 5 min @100 req/s, 3 min @10 req/s."""
import csv, subprocess, sys, time
from loadtest import make_sessions, num

PHASES = [(10, 120), (100, 300), (10, 180)]   # (requests/s, seconds)
HOST, PORT, OUT = "emi.local", 8082, "results"

mon = subprocess.Popen([sys.executable, "scripts/monitor.py", "--out", OUT, "--tag", "hpa",
                        "--duration", str(sum(d for _, d in PHASES) + 45)])
time.sleep(5)
rows = []
for i, (rate, dur) in enumerate(PHASES, 1):
    sessions = rate * dur
    sf = f"{OUT}/raw/hpa_phase{i}_sessions.txt"
    make_sessions(sf, min(sessions, 1000))
    cmd = (f"ulimit -n 8192 2>/dev/null; httperf --hog --server {HOST} --port {PORT} "
           f"--wsesslog={sessions},0,{sf} --rate {rate} --timeout 5 "
           f"--add-header='Content-Type: application/json\\n'")
    t0 = int(time.time())
    out = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
    text = out.stdout + out.stderr
    open(f"{OUT}/raw/hpa_phase{i}_httperf.txt", "w").write(text)
    t1 = int(time.time())
    rows.append([i, rate, dur, t0, t1, num(r"Reply time \[ms\]: response ([\d.]+)", text),
                 num(r"2xx=(\d+)", text, int), num(r"Errors: total (\d+)", text, int)])
    print(f"phase {i}: {rate} req/s for {dur}s -> avg={rows[-1][5]} ms 2xx={rows[-1][6]} "
          f"errors={rows[-1][7]}", flush=True)
mon.wait()
with open(f"{OUT}/hpa_phases.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["phase", "rate", "duration_s", "start_epoch", "end_epoch",
                "avg_response_ms", "replies_2xx", "errors_total"])
    w.writerows(rows)
print("done")
