import json
from pathlib import Path
from datetime import datetime
from rdflib import Graph, Namespace, Literal, RDF, XSD, URIRef
from pyshacl import validate

ROOT = Path(".")
ONTOLOGY_FILE = ROOT / "ontology" / "esrs.owl"
SHACL_E1 = ROOT / "contracts" / "shacl_e1.ttl"
SHACL_S1 = ROOT / "contracts" / "shacl_s1.ttl"
SHACL_G1 = ROOT / "contracts" / "shacl_g1.ttl"
OUT_VALIDATION = ROOT / "ontology" / "validation.log"
OUT_LINEAGE    = ROOT / "ontology" / "linaje.ttl"

EX = Namespace("http://example.com/esrs#")

def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def _add_evidence(g: Graph, subj: URIRef, ev_path: str):
    ev = URIRef(str(subj) + "/evidence/1")
    g.add((subj, EX.hasEvidence, ev))
    g.add((ev, RDF.type, EX.Evidencia))
    g.add((ev, EX.evidencePath, Literal(ev_path, datatype=XSD.string)))

def materialize_e1(g: Graph, data_path: Path):
    records = _load_json(data_path)
    for i, r in enumerate(records, start=1):
        subj = URIRef(f"http://example.com/esrs#E1Record/{i}")
        g.add((subj, RDF.type, EX.E1Record))
        if "company_id" in r: g.add((subj, EX.companyId, Literal(r["company_id"], datatype=XSD.string)))
        if "period_start" in r: g.add((subj, EX.periodStart, Literal(r["period_start"], datatype=XSD.date)))
        if "period_end" in r: g.add((subj, EX.periodEnd, Literal(r["period_end"], datatype=XSD.date)))
        if "kwh" in r: g.add((subj, EX.kwh, Literal(r["kwh"], datatype=XSD.decimal)))
        if "emission_factor_co2e" in r: g.add((subj, EX.emissionFactor, Literal(r["emission_factor_co2e"], datatype=XSD.decimal)))
        _add_evidence(g, subj, ev_path=f"data/normalized/{data_path.name}")

def materialize_s1(g: Graph, data_path: Path):
    records = _load_json(data_path)
    for i, r in enumerate(records, start=1):
        subj = URIRef(f"http://example.com/esrs#S1Record/{i}")
        g.add((subj, RDF.type, EX.S1Record))
        for k, prop, dtype in [
            ("company_id", EX.companyId, XSD.string),
            ("period", EX.period, XSD.string),
            ("employees_start", EX.employeesStart, XSD.integer),
            ("employees_end", EX.employeesEnd, XSD.integer),
            ("exits", EX.exits, XSD.integer),
        ]:
            if k in r: g.add((subj, prop, Literal(r[k], datatype=dtype)))
        _add_evidence(g, subj, ev_path=f"data/normalized/{data_path.name}")

def materialize_g1(g: Graph, data_path: Path):
    records = _load_json(data_path)
    for i, r in enumerate(records, start=1):
        subj = URIRef(f"http://example.com/esrs#G1Record/{i}")
        g.add((subj, RDF.type, EX.G1Record))
        for k, prop, dtype in [
            ("company_id", EX.companyId, XSD.string),
            ("period", EX.period, XSD.string),
            ("cases_opened", EX.casesOpened, XSD.integer),
            ("cases_closed", EX.casesClosed, XSD.integer),
            ("closed_with_resolution", EX.closedWithResolution, XSD.integer),
        ]:
            if k in r: g.add((subj, prop, Literal(r[k], datatype=dtype)))
        _add_evidence(g, subj, ev_path=f"data/normalized/{data_path.name}")

def run_shacl(data_graph: Graph, shape_path: Path, title: str) -> tuple[bool, str]:
    sh = Graph(); sh.parse(shape_path, format="turtle")
    conforms, _, results_text = validate(
        data_graph=data_graph, shacl_graph=sh,
        inference="rdfs", abort_on_first=False,
        allow_infos=True, allow_warnings=True
    )
    header = f"=== {title} ===\nconforms = {conforms}\n"
    return conforms, header + results_text + "\n"

def main():
    OUT_VALIDATION.parent.mkdir(parents=True, exist_ok=True)

    g = Graph()
    if ONTOLOGY_FILE.exists():
        g.parse(ONTOLOGY_FILE, format="turtle")

    e1 = ROOT / "data" / "normalized" / "energy_2024-01.json"
    s1 = ROOT / "data" / "normalized" / "hr_2024-01.json"
    g1 = ROOT / "data" / "normalized" / "ethics_2024-01.json"
    for p in [e1, s1, g1]:
        if not p.exists():
            raise SystemExit(f"No existe {p}. Ejecuta primero mcp_ingest.py")

    materialize_e1(g, e1)
    materialize_s1(g, s1)
    materialize_g1(g, g1)

    results = []
    c1, t1 = run_shacl(g, SHACL_E1, "SHACL E1")
    c2, t2 = run_shacl(g, SHACL_S1, "SHACL S1")
    c3, t3 = run_shacl(g, SHACL_G1, "SHACL G1")

    ts = datetime.utcnow().isoformat() + "Z"
    report = f"[{ts}] GLOBAL_CONFORMS = {all([c1,c2,c3])}\n\n" + t1 + "\n" + t2 + "\n" + t3
    OUT_VALIDATION.write_text(report, encoding="utf-8")
    g.serialize(destination=OUT_LINEAGE, format="turtle")

    print("SHACL GLOBAL:", "OK" if all([c1,c2,c3]) else "CONSTRAINTS FAILED")
    print(f"- Reporte: {OUT_VALIDATION}")
    print(f"- Linaje RDF: {OUT_LINEAGE}")

if __name__ == "__main__":
    main()
