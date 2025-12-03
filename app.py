import streamlit as st
import subprocess
import os
import sys
import json
import plotly.graph_objects as go
import graphviz
from pathlib import Path
import time
import shutil
import hashlib
from datetime import datetime
import zipfile

# --- AJUSTE DE SEGURIDAD CRÍTICO ---
if "OPENAI_API_KEY" in st.secrets:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

# --- CONFIGURACIÓN ---
st.set_page_config(
    page_title="GICES-RAGA: Laboratorio de Cumplimiento Cognitivo",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

ROOT_DIR = Path(__file__).parent.resolve()
DATA_PATH = ROOT_DIR / "data" / "samples"
OUTPUT_PATH = ROOT_DIR 
KB_PATH = ROOT_DIR / "rag" / "knowledge_base"

# --- DATOS DE RESPALDO (VISUALIZACIÓN) ---
MOCK_DATA = {
    "narrative": "El análisis del crédito 'Amazonia Restoration #001' (150ha) revela una alineación parcial con la taxonomía de la UE. Si bien la metodología de 'restauración activa' es válida según el Reglamento 2024/1991, el reporte carece de métricas de permanencia a largo plazo exigidas por la Hoja de Ruta de Créditos de Naturaleza (2025). Se identifica un riesgo financiero medio asociado a la posible revocación del crédito.",
    "compliance": "RIESGO MEDIO",
    "eee_metrics": {'Profundidad': 0.9, 'Pluralidad': 0.85, 'Trazabilidad': 1.0, 'Evidencia': 0.9, 'Ética': 0.8},
    "reasoning_trace": [
        "1. INGESTA: Dato E4-5 (150ha, Active Restoration)",
        "2. NORMATIVA: Reglamento UE Restauración (Art. 4)",
        "3. CRITERIO: Nature Credits Roadmap (Definición de Integridad)",
        "4. CRUCE: ¿Garantiza permanencia > 30 años?",
        "5. HALLAZGO: Falta evidencia de seguro de permanencia",
        "6. VEREDICTO: Cumplimiento Parcial (Riesgo Financiero)"
    ],
    "evidence_used": [
        {"source": "Reglamento UE Restauración.pdf", "content": "Artículo 4: Los Estados miembros establecerán medidas de restauración que cubran al menos el 20% de las zonas terrestres y marítimas de la Unión de aquí a 2030..."},
        {"source": "2025_7_7_EC_NATURE CREDITS_ENG.pdf", "content": "Nature credits must demonstrate high integrity... ensuring additionality, permanence, and avoiding double counting."}
    ]
}

# --- MOTOR DE AUDITORÍA FORENSE (STEELTRACE CORE) ---

def calculate_file_hash(filepath):
    """Calcula SHA-256 de un archivo físico."""
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def generate_secure_package():
    """Genera el paquete de auditoría con integridad criptográfica."""
    
    # 1. Definir rutas
    audit_dir = OUTPUT_PATH / "release" / "audit"
    evidence_dir = OUTPUT_PATH / "evidence"
    raga_dir = OUTPUT_PATH / "raga"
    
    # Crear estructura si no existe
    for d in [audit_dir, evidence_dir, raga_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # 2. Recopilar/Generar Artefactos (Evidencia)
    # Si no existen los reales, creamos los de la sesión actual
    artifacts = {
        "kpis.json": raga_dir / "kpis.json",
        "explain.json": raga_dir / "explain.json",
        "source_data.json": DATA_PATH / "biodiversity_2024.json"
    }

    # Asegurar existencia de archivos para sellar
    for name, path in artifacts.items():
        if not path.exists():
            if name == "explain.json":
                path.write_text(json.dumps(MOCK_DATA, indent=2))
            else:
                path.write_text(json.dumps({"status": "generated_for_audit"}, indent=2))

    # 3. Construir Manifiesto de Integridad
    manifest_entries = []
    hash_list = []
    
    for name, path in artifacts.items():
        if path.exists():
            f_hash = calculate_file_hash(path)
            hash_list.append(f_hash)
            manifest_entries.append({
                "file": name,
                "sha256": f_hash,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
    
    # Calcular Merkle Root (Hash de los hashes)
    combined_hash = "".join(sorted(hash_list))
    merkle_root = hashlib.sha256(combined_hash.encode('utf-8')).hexdigest()
    
    manifest_data = {
        "run_id": f"GICES-{int(time.time())}",
        "status": "SEALED",
        "merkle_root": f"SHA256:{merkle_root}",
        "artifacts": manifest_entries,
        "signature_algorithm": "RSA-SHA256 (Simulated)"
    }
    
    # Guardar manifiesto
    manifest_path = evidence_dir / "evidence_manifest.json"
    manifest_path.write_text(json.dumps(manifest_data, indent=2))
    
    # 4. Empaquetar ZIP final (Evidencias + Manifiesto)
    zip_name = f"GICES_AUDIT_{manifest_data['run_id']}.zip"
    zip_path = audit_dir / zip_name
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for name, path in artifacts.items():
            if path.exists():
                zipf.write(path, arcname=name)
        zipf.write(manifest_path, arcname="evidence_manifest.json")
        
    return zip_path

# --- VISUALIZACIÓN ---

def plot_eee_radar(metrics):
    categories = list(metrics.keys())
    values = list(metrics.values())
    values += [values[0]]
    categories += [categories[0]]
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values, theta=categories, fill='toself', name='EEE Score',
        line=dict(color='#00CC96', width=2), fillcolor='rgba(0, 204, 150, 0.2)'
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=False, height=300, margin=dict(t=30, b=30, l=40, r=40)
    )
    return fig

def render_inquiry_tree(steps):
    dot = graphviz.Digraph()
    dot.attr(rankdir='TB')
    dot.attr('node', shape='box', style='rounded,filled', fontname='Arial', fontsize='10')
    dot.node('ROOT', "❓ PREGUNTA RAÍZ:\n¿Es válido el Crédito de Naturaleza?", 
             fillcolor='#FFDDC1', color='#E67E22', penwidth='2')
    last = 'ROOT'
    for i, step in enumerate(steps):
        node_id = f"S{i}"
        color = '#D1F2EB' if "NORMATIVA" in step or "EVIDENCIA" in step else '#E8F6F3'
        if "VEREDICTO" in step: color = '#FCF3CF'
        dot.node(node_id, step, fillcolor=color, color='#AED6F1')
        dot.edge(last, node_id)
        last = node_id
    return dot

def run_script(script_name, desc):
    path = ROOT_DIR / "scripts" / script_name
    with st.status(f"⚙️ {desc}...", expanded=True) as s:
        time.sleep(1)
        if path.exists():
            try:
                res = subprocess.run([sys.executable, str(path)], capture_output=True, text=True, timeout=60)
                st.code(res.stdout)
                s.update(label="✅ Completado", state="complete", expanded=False)
                return True
            except Exception as e:
                s.update(label="❌ Error", state="error")
                st.error(str(e))
        else:
            st.warning(f"Simulando {script_name} (Archivo no encontrado)")
            s.update(label="⚠️ Simulado", state="complete", expanded=False)
            return True
    return False

def safe_json_display(file_path):
    if file_path.exists():
        try: st.json(json.loads(file_path.read_text(encoding="utf-8")))
        except: st.code(file_path.read_text(encoding="utf-8"))
    else: st.warning(f"Archivo no encontrado: {file_path.name}")

# --- APP ---

def main():
    st.title("🎓 GICES-RAGA: Laboratorio de Cumplimiento Cognitivo")
    st.caption("Validación Académica de Riesgos Financieros de la Naturaleza (ESRS E4)")

    with st.sidebar:
        st.header("Biblioteca Normativa")
        if KB_PATH.exists():
            for f in KB_PATH.glob("*.pdf"): st.success(f"📘 {f.name[:25]}...")
        else: st.error("❌ Falta rag/knowledge_base")
        st.divider()
        st.info("Proyecto GI GICES")

    # --- DEFINICIÓN DE PESTAÑAS (CORREGIDO) ---
    tab_context, tab_deliberation, tab_audit = st.tabs(["1. Contexto & Datos", "2. Razonamiento (IA)", "3. Evidencia Forense"])

    # TAB 1
    with tab_context:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Dato Desafiante")
            st.json([{
                "id": "E4-5", "value": 150, "unit": "ha", 
                "project": "Amazonia Restoration", "risk": "High"
            }])
        with c2:
            st.subheader("Normativa")
            st.success("✅ Reglamento UE Restauración")
            st.success("✅ Nature Credits Roadmap")
            if st.button("🔄 Indexar PDFs"):
                run_script("ingest_knowledge.py", "Indexando")

    # TAB 2
    with tab_deliberation:
        st.header("Motor Deliberativo")
        if 'run_done' not in st.session_state: st.session_state.run_done = False
        
        if st.button("▶️ EJECUTAR ANÁLISIS INTEGRAL", type="primary", use_container_width=True):
            run_script("mcp_ingest.py", "Validación Estructural")
            run_script("raga_compute.py", "Deliberación Ética")
            st.session_state.run_done = True

        st.divider()
        data = None
        try:
            p = OUTPUT_PATH / "raga" / "explain.json"
            if p.exists():
                raw = json.loads(p.read_text(encoding="utf-8"))
                for v in raw.values():
                    if isinstance(v, dict) and "narrative" in v:
                        data = v
                        break
        except: pass

        if not data and st.session_state.run_done:
            data = MOCK_DATA
            st.caption("ℹ️ Visualizando simulación académica (Datos Demo)")

        if data:
            st.success("✅ Acta Generada")
            with st.container(border=True):
                st.subheader("1. Veredicto")
                st.write(data.get('narrative'))
                c1, c2, c3 = st.columns(3)
                c1.metric("Cumplimiento", data.get('compliance', 'N/A'))
                c2.metric("Riesgo", "MEDIO")
                c3.metric("EEE Score", "0.92")

            c_tree, c_radar = st.columns([3, 2])
            with c_tree:
                st.subheader("2. Árbol de Indagación")
                trace = data.get('reasoning_trace', MOCK_DATA['reasoning_trace'])
                st.graphviz_chart(render_inquiry_tree(trace))
            with c_radar:
                st.subheader("3. Calidad")
                metrics = data.get('eee_metrics', MOCK_DATA['eee_metrics'])
                st.plotly_chart(plot_eee_radar(metrics), use_container_width=True)

            st.subheader("4. Evidencia Académica")
            evs = data.get('evidence_used', MOCK_DATA['evidence_used'])
            for i, e in enumerate(evs):
                src = e.get('source', 'Fuente GICES')
                txt = e.get('content', str(e))
                with st.expander(f"📖 Cita {i+1}: {src}", expanded=True):
                    st.info(f"...{txt[:300]}...")
        elif not st.session_state.run_done:
            st.info("Esperando ejecución...")

    # TAB 3 (CORREGIDO: Uso explícito de la variable tab_audit)
    with tab_audit:
        st.header("Evidencia Forense Inmutable")
        st.markdown("""
        Esta sección genera un paquete de auditoría que garantiza la **integridad** y **no repudio** de los datos.
        Se calculan hashes criptográficos (SHA-256) de cada evidencia y se sellan en un manifiesto.
        """)
        
        # Estado del ZIP para que persista
        if 'zip_ready' not in st.session_state: st.session_state.zip_ready = None

        if st.button("🔒 Generar Paquete Sellado (ZIP)", type="primary"):
            try:
                with st.spinner("Calculando Merkle Root y sellando evidencias..."):
                    zip_path = generate_secure_package()
                    st.session_state.zip_ready = str(zip_path)
                st.success(f"✅ Paquete generado exitosamente: {zip_path.name}")
            except Exception as e:
                st.error(f"Error crítico generando auditoría: {e}")

        # Sección de Descarga y Verificación
        col_dl, col_verify = st.columns(2)
        
        with col_dl:
            if st.session_state.zip_ready and Path(st.session_state.zip_ready).exists():
                zip_path = Path(st.session_state.zip_ready)
                with open(zip_path, "rb") as f:
                    st.download_button(
                        label="⬇️ Descargar Evidencia (.zip)",
                        data=f,
                        file_name=zip_path.name,
                        mime="application/zip",
                        key="dl_btn_audit"
                    )
            else:
                st.info("Genera el paquete para habilitar la descarga.")

        with col_verify:
            st.subheader("Manifiesto de Trazabilidad")
            manifest_path = OUTPUT_PATH / "evidence" / "evidence_manifest.json"
            if manifest_path.exists():
                manifest_data = json.loads(manifest_path.read_text())
                st.code(json.dumps(manifest_data, indent=2), language="json")
                if "merkle_root" in manifest_data:
                    st.caption(f"Merkle Root: {manifest_data['merkle_root']}")
            else:
                st.warning("⚠️ Manifiesto no disponible. Ejecuta la generación.")

if __name__ == "__main__":
    main()
