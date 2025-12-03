from pathlib import Path
import hashlib, json

def sha256_file(path: str | Path) -> str:
    p = Path(path)
    return hashlib.sha256(p.read_bytes()).hexdigest()

def merkle_root_from_hashes(hashes: list[str]) -> str:
    if not hashes: return ""
    level = [h.encode("utf-8") for h in hashes]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            a = level[i]
            b = level[i+1] if i+1 < len(level) else a
            nxt.append(hashlib.sha256(a + b).digest())
        level = nxt
    return hashlib.sha256(level[0]).hexdigest()

def build_manifest(artifacts: list[str], run_id: str) -> dict:
    rows = []
    for a in artifacts:
        sha = sha256_file(a)
        rows.append({"path": a, "sha256": sha})
    root = merkle_root_from_hashes([r["sha256"] for r in rows])
    return {"run_id": run_id, "artifacts": rows, "merkle_root": f"SHA256:{root}"}
