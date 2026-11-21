#!/usr/bin/env python3
"""Fixed-replica load tests with httperf: random POST /api/emi through the Ingress."""
import argparse, csv, json, os, random, re, subprocess, sys, time


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def make_sessions(path, n):
    with open(path, "w") as f:
        for _ in range(n):
            body = json.dumps({"principal": random.randint(10000, 5000000),
                               "rate": round(random.uniform(1, 30), 2),
                               "months": random.randint(1, 360)}, separators=(",", ":"))
            f.write("/api/emi method=POST contents='%s'\n\n" % body)


def num(pattern, text, cast=float, default=""):
    m = re.search(pattern, text)
    return cast(m.group(1)) if m else default


def scale(replicas):
    run(["kubectl", "scale", "deployment", "emi-web", "-n", "emi", f"--replicas={replicas}"])
    run(["kubectl", "rollout", "status", "deployment/emi-web", "-n", "emi", "--timeout=180s"])
    time.sleep(15)


def one_run(replicas, rate, duration, host, port, outdir, prefix, summary):
    tag = f"{prefix}r{replicas}_rate{rate}"
    sessions = rate * duration
    sess_file = f"{outdir}/raw/{tag}_sessions.txt"
    make_sessions(sess_file, min(sessions, 1000))

    mon = subprocess.Popen([sys.executable, "scripts/monitor.py", "--out", outdir,
                            "--tag", tag, "--duration", str(duration + 8)])
    time.sleep(3)
    cmd = (f"ulimit -n 8192 2>/dev/null; httperf --hog --server {host} --port {port} "
           f"--wsesslog={sessions},0,{sess_file} --rate {rate} --timeout 5 "
           f"--add-header='Content-Type: application/json\\n'")
    t0 = time.strftime("%Y-%m-%d %H:%M:%S")
    res = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
    out = res.stdout + res.stderr
    open(f"{outdir}/raw/{tag}_httperf.txt", "w").write(out)
    mon.wait()

    row = {
        "start_time": t0, "replicas": replicas, "target_rate": rate, "duration_s": duration,
        "sessions": sessions,
        "requests": num(r"Total: connections \d+ requests (\d+)", out, int),
        "replies": num(r"replies (\d+)", out, int),
        "test_duration_s": num(r"test-duration ([\d.]+)", out),
        "avg_response_ms": num(r"Reply time \[ms\]: response ([\d.]+)", out),
        "replies_2xx": num(r"2xx=(\d+)", out, int),
        "replies_5xx": num(r"5xx=(\d+)", out, int),
        "errors_total": num(r"Errors: total (\d+)", out, int),
        "client_timo": num(r"client-timo (\d+)", out, int),
        "connreset": num(r"connreset (\d+)", out, int),
    }
    new = not os.path.exists(summary)
    with open(summary, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)
    print(f"[{tag}] avg={row['avg_response_ms']} ms  2xx={row['replies_2xx']}  "
          f"errors={row['errors_total']}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--replicas", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--rates", type=int, nargs="+", default=[10, 25, 50, 100, 200])
    ap.add_argument("--duration", type=int, default=60)
    ap.add_argument("--host", default="emi.local")
    ap.add_argument("--port", type=int, default=8082)
    ap.add_argument("--out", default="results")
    ap.add_argument("--prefix", default="")
    ap.add_argument("--summary", default="results/summary.csv")
    a = ap.parse_args()
    os.makedirs(f"{a.out}/raw", exist_ok=True)
    for r in a.replicas:
        scale(r)
        for rate in a.rates:
            one_run(r, rate, a.duration, a.host, a.port, a.out, a.prefix, a.summary)
            time.sleep(20)


if __name__ == "__main__":
    main()
