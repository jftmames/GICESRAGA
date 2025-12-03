import json, subprocess, time
from pathlib import Path
from statistics import quantiles
from datetime import datetime

STEPS = [
    ("MCP.ingest",      ["python","scripts/mcp_ingest.py"]),
    ("SHACL.validate",  ["python","scripts/shacl_validate.py"]),
    ("RAGA.compute",    ["python","scripts/raga_compute.py"]),
    ("EEE.gate",        ["python","scripts/eee_gate.py"]),
    ("XBRL.generate",   ["python","scripts/xbrl_generate.py"]),
    ("EVIDENCE.build",  ["python","scripts/evidence_build.py"])
]

SLO_FILE = Path("ops/slo_report.json")
HISTORY  = Path("ops/slo_history.jsonl")

def run_step(name, cmd):
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    t1 = time.perf_counter()
    dur = t1 - t0
    ok  = proc.returncode == 0
    return {"name": name, "ok": ok, "duration_sec": dur, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}

def p95(values):
    if not values:
        return None
    if len(values) < 20:
        # con pocas muestras usamos el max como aproximación
        return max(values)
    return quantiles(values, n=100)[94]

def aggregate(history):
    # history: lista de runs con pasos y duraciones
    agg = {}
    for run in history:
        for s in run["steps"]:
            agg.setdefault(s["name"], []).append(s["duration_sec"])
    return {k: {"count": len(v), "p95_sec": round(p95(v), 4), "mean_sec": round(sum(v)/len(v), 4)} for k,v in agg.items()}

def main():
    Path("ops").mkdir(exist_ok=True)
    steps = [run_step(n,c) for n,c in STEPS]
    run = {"utc": datetime.utcnow().isoformat()+"Z", "steps": steps}
    HISTORY.write_text((HISTORY.read_text() if HISTORY.exists() else "") + json.dumps(run)+"\n")

    # reconstruir historia
    hist = []
    for line in HISTORY.read_text().splitlines():
        try:
            hist.append(json.loads(line))
        except Exception:
            pass

    agg = aggregate(hist)
    SLO_FILE.write_text(json.dumps({"utc": run["utc"], "agg": agg, "last_run": steps}, indent=2, ensure_ascii=False))
    print("SLO report →", SLO_FILE)

if __name__ == "__main__":
    main()
