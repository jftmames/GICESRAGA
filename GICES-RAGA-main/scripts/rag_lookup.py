import json, re
from pathlib import Path
IDX = Path("rag/index.jsonl")

def search(query: str, limit=5):
    items = []
    for line in IDX.read_text(encoding="utf-8").splitlines():
        obj = json.loads(line)
        hay = (query.lower() in obj["id"].lower()) or (re.search(query, obj["title"], re.I) is not None)
        if hay:
            items.append(obj)
        if len(items) >= limit: break
    return items

if __name__ == "__main__":
    import sys
    q = sys.argv[1] if len(sys.argv)>1 else "E1"
    print(json.dumps(search(q), indent=2, ensure_ascii=False))
