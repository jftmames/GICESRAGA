import zipfile
from pathlib import Path
from datetime import datetime

ARTS = [
    "data/normalized/energy_2024-01.json",
    "data/normalized/hr_2024-01.json",
    "data/normalized/ethics_2024-01.json",
    "ontology/validation.log","ontology/linaje.ttl",
    "raga/kpis.json","raga/explain.json",
    "ops/gate_report.json","eee/eee_report.json",
    "xbrl/informe.xbrl","xbrl/validation.log",
    "evidence/evidence_manifest.json","evidence/tokens/2025Q1.tsr",
    "ops/slo_report.json","ops/hitl_kappa.json"
]

def main():
    run_id = f"{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
    out = Path(f"release/audit/STEELTRACE_LAB_{run_id}.zip")
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in ARTS:
            if Path(p).exists():
                z.write(p)
    print("ZIP listo:", out)

if __name__ == "__main__":
    main()
