import json
from statistics import mean

def calculate_eee(tracker) -> float:
    """
    Calcula el Índice de Equilibrio Erotético (EEE) a partir de los datos
    registrados en el tracker.
    """
    log = json.loads(tracker.export())
    tree = log.get("inquiry", [])
    
    # Función recursiva para medir la profundidad
    def depth(node):
        return 1 + max((depth(child) for child in node.get("children", [])), default=0)
    
    prof = depth(tree[0]) if tree else 0
    
    # Pluralidad: número medio de respuestas por nodo
    resp_counts = [len(v) for v in log.get("responses", {}).values()]
    plural = mean(resp_counts) if resp_counts else 0
    
    # Reversibilidad: número de sugerencias de foco aplicadas
    rev = len(log.get("focus", []))
    
    # Normalizar cada dimensión
    d_norm = min(prof / 5, 1)
    p_norm = min(plural / 3, 1)
    r_norm = min(rev / 2, 1)
    
    # EEE es la media de las tres dimensiones
    return mean([d_norm, p_norm, r_norm])
