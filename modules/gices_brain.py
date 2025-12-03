import os
import json
import fitz  # PyMuPDF
from openai import OpenAI
from pathlib import Path

# Configuración del Cliente OpenAI
# Intenta obtener la clave de las variables de entorno o secretos de Streamlit
api_key = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None

# --- 1. CAPACIDAD VISUAL (Leer PDFs) ---
def ingest_pdfs(pdf_dir):
    """Convierte PDFs académicos en fragmentos de texto procesables."""
    knowledge = []
    pdf_path = Path(pdf_dir)
    
    if not pdf_path.exists():
        return []
    
    print(f"📂 Leyendo PDFs desde: {pdf_path}")
    for f in pdf_path.glob("*.pdf"):
        try:
            doc = fitz.open(f)
            for i, page in enumerate(doc):
                text = page.get_text().replace("\n", " ").strip()
                # Solo guardamos párrafos con contenido sustancial
                if len(text) > 100:
                    # Guardamos metadatos clave para la cita académica
                    knowledge.append({
                        "source": f.name,
                        "page": i + 1,
                        "content": text
                    })
        except Exception as e:
            print(f"⚠️ Error leyendo {f.name}: {e}")
            
    return knowledge

def retrieve_context(query, knowledge_base, k=4):
    """Busca los fragmentos más relevantes en la base de conocimiento."""
    if not knowledge_base:
        return []
        
    scored = []
    query_terms = set(query.lower().split())
    
    for item in knowledge_base:
        # Puntuación simple: coincidencia de palabras clave
        content_lower = item["content"].lower()
        score = sum(1 for term in query_terms if term in content_lower)
        if score > 0:
            scored.append((score, item))
    
    # Ordenar por relevancia
    scored.sort(key=lambda x: x[0], reverse=True)
    return [s[1] for s in scored[:k]]

# --- 2. CAPACIDAD DE RAZONAMIENTO (Motor Deliberativo) ---
def deliberative_analysis(data_point, context_chunks, mode="Academic Validation"):
    """Genera el Acta de Razonamiento comparando el dato con la norma."""
    
    if not client:
        return {
            "narrative": "Error: No se detectó OPENAI_API_KEY. Configura los secretos.",
            "compliance_check": "ERROR",
            "citations": []
        }

    # Formatear la evidencia para que la IA la lea
    evidence_str = "\n\n".join([f"- [Fuente: {c['source']} Pág.{c['page']}] {c['content'][:600]}..." for c in context_chunks])
    
    prompt = f"""
    Actúa como un investigador experto en {mode} (CSRD/ESRS).
    
    OBJETIVO: Validar la integridad ética y jurídica del siguiente dato reportado.
    DATO: {json.dumps(data_point)}
    
    EVIDENCIA NORMATIVA (Debes basarte EXCLUSIVAMENTE en esto):
    {evidence_str}
    
    INSTRUCCIONES:
    1. Analiza si el proyecto cumple con los criterios de "Alta Integridad" o "Restauración".
    2. Identifica riesgos de Greenwashing.
    3. Cita explícitamente los documentos PDF proporcionados.
    
    Genera un JSON válido con este formato:
    {{
        "narrative": "Análisis crítico de 3-4 frases.",
        "compliance_check": "CUMPLE / RIESGO ALTO / NO CUMPLE",
        "citations": ["Lista de nombres de archivos PDF usados"],
        "key_risk": "El riesgo principal detectado"
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o", # O gpt-3.5-turbo si prefieres
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.2 # Bajo para ser riguroso
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"narrative": f"Error en deliberación: {e}", "compliance_check": "FAIL"}
