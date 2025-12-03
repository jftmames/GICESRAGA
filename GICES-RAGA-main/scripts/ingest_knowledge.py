import json
import sys
from pathlib import Path

# Truco para importar módulos desde la carpeta superior
sys.path.append(str(Path(__file__).parent.parent))
from modules.gices_brain import ingest_pdfs

KB_DIR = Path("rag/knowledge_base")
INDEX_FILE = Path("rag/index.json")

def main():
    print("🎓 GICES-RAGA: Iniciando Ingesta de Conocimiento...")
    
    # Crear directorio si no existe (aunque deberías haber subido los PDFs aquí)
    KB_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. Leer PDFs
    knowledge = ingest_pdfs(KB_DIR)
    
    if not knowledge:
        print("⚠️ No se encontraron PDFs en rag/knowledge_base/")
        print("   Por favor sube: Reglamento Restauración, Nature Credits, etc.")
        return

    # 2. Guardar Índice
    Path("rag").mkdir(exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(knowledge, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Ingesta Completada. {len(knowledge)} fragmentos indexados.")
    print(f"📍 Índice guardado en: {INDEX_FILE}")

if __name__ == "__main__":
    main()
