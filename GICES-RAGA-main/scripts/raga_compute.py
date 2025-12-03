import json
import sys
from pathlib import Path

# Importar el cerebro
sys.path.append(str(Path(__file__).parent.parent))
from modules.gices_brain import retrieve_context, deliberative_analysis

DATA_DIR = Path("data/normalized")
RAGA_DIR = Path("raga")
INDEX_FILE = Path("rag/index.json")

def load_json(path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []

def main():
    print("⚙️ Iniciando Cálculo RAGA...")
    RAGA_DIR.mkdir(exist_ok=True)
    
    # 1. Cargar Datos Normalizados
    # Primero ejecutamos mcp_ingest (paso previo en el pipeline), aquí leemos el resultado
    energy_data = load_json(DATA_DIR / "energy_2024-01.json")
    biodiv_data = load_json(DATA_DIR / "biodiversity_2024.json") # El dato nuevo
    
    kpis = {}
    explanations = {}

    # --- A. Lógica Determinista (Energía) ---
    if energy_data:
        total_co2 = sum(r["kwh"] * 0.23 for r in energy_data) / 1000
        kpis["E1-1.co2e"] = total_co2
        explanations["E1-1"] = {"narrative": "Cálculo aritmético directo (kWh * Factor)."}

    # --- B. Lógica Deliberativa (Biodiversidad) ---
    if biodiv_data:
        print("🦋 Dato de Biodiversidad detectado. Activando Validación Académica...")
        
        # Cargar Conocimiento (Fase 0)
        knowledge_base = load_json(INDEX_FILE)
        if not knowledge_base:
            print("⚠️ Advertencia: No hay base de conocimiento. Ejecuta ingest_knowledge.py primero.")
            knowledge_base = []

        # Procesar cada registro de biodiversidad
        for i, record in enumerate(biodiv_data):
            kpi_id = f"E4-5.project_{i+1}"
            kpis[kpi_id] = record["ecosystem_area_ha"]
            
            # 1. Recuperar Evidencia (RAGA)
            query = f"nature credits restoration integrity {record.get('project_type', '')} {record.get('financial_risk_exposure', '')}"
            context = retrieve_context(query, knowledge_base)
            
            # 2. Deliberar (AI)
            analysis = deliberative_analysis(record, [c["content"] for c in context])
            
            # 3. Guardar Explicación Estructurada
            explanations[kpi_id] = {
                "type": "deliberative_validation",
                "narrative": analysis.get("narrative"),
                "compliance": analysis.get("compliance_check"),
                "evidence_used": [c["source"] for c in context]
            }

    # Guardar Resultados
    (RAGA_DIR / "kpis.json").write_text(json.dumps(kpis, indent=2, ensure_ascii=False))
    (RAGA_DIR / "explain.json").write_text(json.dumps(explanations, indent=2, ensure_ascii=False))
    
    print("✅ RAGA Compute Finalizado.")

if __name__ == "__main__":
    main()
