#!/usr/bin/env python3
"""Make Graph 1, 2 and 3 for Milestone 4 from the CSV files in results/."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

R, G = "results", "results/graphs"
os.makedirs(G, exist_ok=True)
REQ_M = 100   # CPU request per pod (millicores); utilisation % = usage / request

# ---------- Graph 1: average response time vs request rate ----------
s = pd.read_csv(f"{R}/summary.csv")
s["avg_response_ms"] = pd.to_numeric(s["avg_response_ms"], errors="coerce")
fig, ax = plt.subplots(figsize=(8, 5))
for n, d in s.groupby("replicas"):
    d = d.sort_values("target_rate")
    ax.plot(d["target_rate"], d["avg_response_ms"], marker="o",
            label=f"{n} replica" + ("s" if n > 1 else ""))
ax.set_xlabel("Request rate (req/s)")
ax.set_ylabel("Average response time (ms)")
ax.set_title("Graph 1: Average response time vs request rate")
ax.set_xticks(sorted(s["target_rate"].unique()))
ax.grid(True, alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig(f"{G}/graph1_response_time.png", dpi=150)
plt.close(fig)

# Graph 1b: errors per run (explains the high-rate points)
e = s.pivot(index="target_rate", columns="replicas", values="errors_total")
e.columns = [f"{c} replica" + ("s" if c > 1 else "") for c in e.columns]
ax = e.plot(kind="bar", figsize=(8, 5))
ax.set_xlabel("Request rate (req/s)")
ax.set_ylabel("Errors (out of 60 s x rate requests)")
ax.set_title("Graph 1b: Errors per run")
ax.grid(True, axis="y", alpha=0.3)
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(f"{G}/graph1b_errors.png", dpi=150)
plt.close()

# ---------- Graph 2: per-pod CPU, 100 req/s with 3 replicas ----------
p = pd.read_csv(f"{R}/g2_r3_rate100_pods.csv")
p = p[p["pod"].str.startswith("emi-web")].copy()
p["t"] = p["epoch"] - p["epoch"].min()
p["cpu_pct"] = p["cpu_millicores"] / REQ_M * 100
fig, ax = plt.subplots(figsize=(8, 5))
for pod, d in p.groupby("pod"):
    ax.plot(d["t"], d["cpu_pct"], marker="o", label="pod ..." + pod[-5:])
ax.axhline(250, ls="--", color="gray", label="CPU limit (250m = 250%)")
ax.set_xlabel("Time (s)")
ax.set_ylabel("CPU utilisation (% of 100m request)")
ax.set_title("Graph 2: CPU per pod, 100 req/s, 3 replicas")
ax.grid(True, alpha=0.3)
ax.legend()
fig.tight_layout()
fig.savefig(f"{G}/graph2_cpu_per_pod.png", dpi=150)
plt.close(fig)

# ---------- Graph 3: autoscaling test, shared time axis ----------
ph = pd.read_csv(f"{R}/hpa_phases.csv")
rp = pd.read_csv(f"{R}/hpa_replicas.csv")
pp = pd.read_csv(f"{R}/hpa_pods.csv")
t0 = ph["start_epoch"].min()
for c in ["spec_replicas", "ready_replicas", "hpa_cpu_percent"]:
    rp[c] = pd.to_numeric(rp[c], errors="coerce")
rp["t"] = rp["epoch"] - t0
pp = pp[pp["pod"].str.startswith("emi-web")]
avg = pp.groupby("epoch")["cpu_millicores"].mean().reset_index()
avg["t"] = avg["epoch"] - t0
avg["cpu_pct"] = avg["cpu_millicores"] / REQ_M * 100

fig, (a1, a2, a3) = plt.subplots(3, 1, sharex=True, figsize=(10, 9))
for _, r in ph.iterrows():
    a1.plot([r["start_epoch"] - t0, r["end_epoch"] - t0], [r["rate"], r["rate"]],
            color="tab:blue", lw=3)
a1.set_ylabel("Request rate (req/s)")
a1.set_title("Graph 3: Autoscaling test (10 min)")
a1.grid(True, alpha=0.3)

a2.plot(avg["t"], avg["cpu_pct"], marker="o", label="average over web pods (kubectl top)")
h = rp.dropna(subset=["hpa_cpu_percent"])
a2.plot(h["t"], h["hpa_cpu_percent"], ls="--", marker="x", label="reported by HPA")
a2.axhline(50, ls=":", color="red", label="target 50%")
a2.set_ylabel("Average CPU utilisation (%)")
a2.grid(True, alpha=0.3)
a2.legend()

a3.step(rp["t"], rp["spec_replicas"], where="post", lw=2, label="desired replicas")
a3.step(rp["t"], rp["ready_replicas"], where="post", ls="--", label="ready replicas")
a3.set_ylabel("Web replicas")
a3.set_xlabel("Time since start of test (s)")
a3.set_yticks(range(0, 6))
a3.grid(True, alpha=0.3)
a3.legend()
fig.tight_layout()
fig.savefig(f"{G}/graph3_autoscaling.png", dpi=150)
plt.close(fig)
print("saved:")
for f in sorted(os.listdir(G)):
    print("  ", f"{G}/{f}")
