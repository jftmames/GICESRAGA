import json, re
from pathlib import Path
from datetime import datetime

CFG = Path("ops/eee_gate.yaml")
KPIS = Path("raga/kpis.json")
EXPL = Path("raga/explain.json")
VAL  = Path("ontology/validation.log")

def load_yaml(p: Path):
    import yaml
    return yaml.safe_load(p.read_text(encoding="utf-8"))

def exists(path: str) -> bool:
    return Path(path).exists()

def evidence_component(cfg) -> tuple[float, dict]:
    arts = cfg["eee_gate"]["required_artifacts"]
    ok = sum(1 for a in arts if exists(a))
    comp = ok / max(1, len(arts))
    return comp, {"artifacts_present": ok, "artifacts_total": len(arts)}

def explicit_component(explain: dict) -> tuple[float, dict]:
    """
    mide completitud de explicaciones:
      - hipótesis presente
      - lista de evidencias no vacía
      - cita RAG disponible
    score = media sobre todos los DP
    """
    dps = list(explain.keys())
    if not dps:
        return 0.0, {"details":[]}
    scores = []
    details = []
    for dp, ex in explain.items():
        hyp = 1.0 if ex.get("hypothesis") else 0.0
        ev  = 1.0 if ex.get("evidence") else 0.0
        cit = 1.0 if ex.get("citations") else 0.0
        s = (hyp + ev + cit) / 3.0
        scores.append(s)
        details.append({"dp": dp, "hyp": hyp, "ev": ev, "cit": cit, "score": s})
    return sum(scores)/len(scores), {"details": details}

def epistemic_component(explain: dict) -> tuple[float, dict]:
    """
    heurística epistémica simple basada en 'residual' ∈ [0,1]:
      residual <= 0.01 → 1.0
      0.01 < residual <= 0.05 → 0.7
      > 0.05 → 0.3
    score = media sobre DPs
    """
    dps = list(explain.keys())
    if not dps:
        return 0.0, {"details":[]}
    m = []
    details = []
    for dp, ex in explain.items():
        r = float(ex.get("residual", 1.0))
        if r <= 0.01: s = 1.0
        elif r <= 0.05: s = 0.7
        else: s = 0.3
        m.append(s)
        details.append({"dp": dp, "residual": r, "score": s})
    return sum(m)/len(m), {"details": details}

def decision(score: float, th: float) -> str:
    if score >= th: return "publish"
    if score >= (th - 0.1): return "review"
    return "block"

def main():
    cfg = load_yaml(CFG)
    th  = cfg["eee_gate"]["threshold_score"]
    w   = cfg["eee_gate"]["weights"]

    # cargar explicaciones y kpis
    kpis = json.loads(KPIS.read_text(encoding="utf-8"))
    explain = json.loads(EXPL.read_text(encoding="utf-8"))

    # componentes
    ev_score, ev_meta = evidence_component(cfg)
    ex_score, ex_meta = explicit_component(explain)
    ep_score, ep_meta = epistemic_component(explain)

    eee_score = round(
        w["epistemic"]*ep_score + w["explicit"]*ex_score + w["evidence"]*ev_score, 4
    )

    # decisión por DP (simple: aplica el mismo score; en real podrías granularizar por DP)
    details = []
    for dp in kpis.keys():
        details.append({
            "dp": dp,
            "epistemic": ep_score,
            "explicit": ex_score,
            "evidence": ev_score,
            "eee_score": eee_score,
            "decision": decision(eee_score, th)
        })

    report = {
        "generated_utc": datetime.utcnow().isoformat()+"Z",
        "weights": w,
        "components": {
            "epistemic": ep_score,
            "explicit": ex_score,
            "evidence": ev_score
        },
        "eee_score": eee_score,
        "threshold": th,
        "global_decision": decision(eee_score, th),
        "meta": {
            "evidence": ev_meta,
            "explicit": ex_meta,
            "epistemic": ep_meta
        },
        "details": details
    }

    Path("ops").mkdir(exist_ok=True)
    Path("eee").mkdir(exist_ok=True)
    Path("ops/gate_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    # resumen compacto para auditoría
    Path("eee/eee_report.json").write_text(json.dumps({
        "utc": report["generated_utc"],
        "eee_score": eee_score,
        "decision": report["global_decision"]
    }, indent=2, ensure_ascii=False))

    print(f"EEE-Score: {eee_score} → {report['global_decision']}")
    print("→ ops/gate_report.json, eee/eee_report.json")

if __name__ == "__main__":
    main()
