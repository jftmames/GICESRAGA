import json, re
from pathlib import Path
from datetime import datetime
import pandas as pd
from jsonschema import Draft202012Validator
from utils_hash import sha256_file, sha256_json, write_json
import yaml # pyyaml es necesario para load_yaml

# -------- Config --------
SAMPLES = {
    "energy": {
        "input": "data/samples/energy_2024-01.json",
        "schema": "contracts/erp_energy.schema.json",
        "normalized": "data/normalized/energy_2024-01.json"
    },
    "hr": {
        "input": "data/samples/hr_2024-01.json",
        "schema": "contracts/hr_people.schema.json",
        "normalized": "data/normalized/hr_2024-01.json"
    },
    "ethics": {
        "input": "data/samples/ethics_2024-01.json",
        "schema": "contracts/ethics_cases.schema.json",
        "normalized": "data/normalized/ethics_2024-01.json"
    }
}
DQ_RULES_FILE = "contracts/dq_rules.yaml"

# -------- Helpers DQ --------
def is_date_iso(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except Exception:
        return False

def is_yyyy_mm(s: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}", s))

def within_month(date_str: str, month: str) -> bool:
    # month = 'YYYY-MM'
    return date_str.startswith(month)

def apply_rule(row: dict, rule: dict, domain: str) -> bool:
    # Supports simple predicates used in dq_rules.yaml
    name = rule.get("rule")
    field = rule.get("field")
    if name == "not_null":
        return row.get(field) is not None
    if name == "is_date":
        return is_date_iso(str(row.get(field, "")))
    if name == "is_yyyy_mm":
        return is_yyyy_mm(str(row.get(field, "")))
    if name == ">=0":
        try:
            val = row.get(field)
            if val is None: return False
            return float(val) >= 0
        except Exception:
            return False
    if name and name.startswith("within_month("):
        m = re.search(r"within_month\('([^']+)'\)", name)
        month = m.group(1) if m else ""
        return within_month(str(row.get(field, "")), month)
    if name and name.startswith("equals("):
        m = re.search(r"equals\('([^']+)'\)", name)
        ref = m.group(1) if m else ""
        return str(row.get(field, "")) == ref
    if name == "period_start <= period_end":
        try:
            ps = datetime.strptime(row.get("period_start"), "%Y-%m-%d")
            pe = datetime.strptime(row.get("period_end"), "%Y-%m-%d")
            return ps <= pe
        except Exception:
            return False
    if name == "employees_end <= employees_start + 1000":
        try:
            return int(row.get("employees_end", 0)) <= int(row.get("employees_start", 0)) + 1000
        except Exception:
            return False
    if name == "closed_with_resolution <= cases_closed":
        try:
            return int(row.get("closed_with_resolution", 0)) <= int(row.get("cases_closed", 0))
        except Exception:
            return False
    return True

def evaluate_dq(records: list[dict], rules: dict, domain: str) -> dict:
    res = {"completeness": [], "validity": [], "consistency": [], "timeliness": []}
    for cat in res.keys():
        for r in rules.get(cat, []):
            passed = sum(1 for row in records if apply_rule(row, r, domain))
            total = max(1, len(records))
            res[cat].append({"rule": r, "pass_rate": passed / total})
    # Aggregate
    agg = {k: (sum(x["pass_rate"] for x in v) / max(1, len(v))) if v else 1.0 for k, v in res.items()}
    agg["dq_pass"] = all(v >= 0.95 for v in agg.values())
    return {"by_rule": res, "aggregate": agg}

# -------- Load DQ rules --------
def load_yaml(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def json_load(path: str) -> dict | list:
    return json.loads(Path(path).read_text(encoding="utf-8"))

# -------- Main --------
def main():
    dq_rules = load_yaml(DQ_RULES_FILE)

    normalized_paths = []
    dq_summary = {}

    for domain, cfg in SAMPLES.items():
        src = Path(cfg["input"])
        sch = Path(cfg["schema"])
        dst = Path(cfg["normalized"])
        dst.parent.mkdir(parents=True, exist_ok=True)

        # 1) Cargar datos
        records = json_load(src)
        if not isinstance(records, list):
            raise ValueError(f"{src} debe ser una lista de objetos JSON")

        # 2) Validar JSON Schema
        schema = json_load(sch)
        validator = Draft202012Validator(schema)
        valid_records, errors = [], []
        for i, rec in enumerate(records):
            errs = sorted(validator.iter_errors(rec), key=lambda e: e.path)
            if errs:
                errors.append({"index": i, "errors": [e.message for e in errs]})
            else:
                valid_records.append(rec)

        # 3) Escribir normalizados (solo válidos)
        write_json(dst, valid_records)
        normalized_paths.append(str(dst))

        # 4) DQ por reglas
        rules = dq_rules.get(domain, {})
        dq = evaluate_dq(valid_records, rules, domain)
        dq_summary[domain] = {
            "source": str(src),
            "schema": str(sch),
            "records_total": len(records),
            "records_valid": len(valid_records),
            "schema_errors": errors,
            "dq": dq
        }

    # 5) Linaje y hashes
    lineage_path = Path("data/lineage.jsonl")
    lineage_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for domain, cfg in SAMPLES.items():
        src = Path(cfg["input"])
        dst = Path(cfg["normalized"])
        lines.append(json.dumps({
            "domain": domain,
            "src": str(src),
            "src_sha256": sha256_file(src),
            "normalized": str(dst),
            "normalized_sha256": sha256_file(dst),
            "utc": datetime.utcnow().isoformat() + "Z"
        }))

    lineage_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 6) Reporte DQ agregado
    def ok(dom):
        agg = dq_summary[dom]["dq"]["aggregate"]
        return all(agg[k] >= 0.95 for k in ["completeness","validity","consistency","timeliness"])

    dq_report = {
        "domains": dq_summary,
        "dq_pass": all(ok(dom) for dom in dq_summary.keys())
    }
    write_json("data/dq_report.json", dq_report)

    print("Ingesta/DQ completada.")
    print("data/dq_report.json escrito.")
    print("data/lineage.jsonl escrito.")
    for p in normalized_paths:
        print("OK →", p)

if __name__ == "__main__":
    main()
