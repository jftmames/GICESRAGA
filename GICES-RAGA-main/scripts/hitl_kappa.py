import pandas as pd
from sklearn.metrics import cohen_kappa_score
from pathlib import Path
import json  # <<< ESTO FALTABA

MAP = {"valido":2, "revision":1, "incorrecto":0}

def main():
    # El script asume que docs/hitl_reviews.csv existe
    df = pd.read_csv("docs/hitl_reviews.csv")
    
    # κ par-a-par y media simple
    pairs = [("rev1","rev2"),("rev1","rev3"),("rev2","rev3")]
    kappas = {}
    for a,b in pairs:
        # cohen_kappa_score requiere que las etiquetas sean numéricas
        ka = cohen_kappa_score(df[a].map(MAP), df[b].map(MAP))
        kappas[f"{a}-{b}"] = round(ka, 3)
        
    mean_k = round(sum(kappas.values())/len(kappas), 3)
    out = {"kappas": kappas, "kappa_mean": mean_k, "n": len(df)}
    
    # Escribe el resultado como JSON válido en ops/hitl_kappa.json
    Path("ops/hitl_kappa.json").write_text(json.dumps(out, indent=2))
    print(out)

if __name__ == "__main__":
    main()
