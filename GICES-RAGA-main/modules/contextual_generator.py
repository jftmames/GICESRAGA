# modules/contextual_generator.py

import os
import json
import openai

# Configura tu clave de OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_responses(tree: dict, mode: str) -> dict:
    """
    Recorre el árbol de indagación y genera respuestas desde
    tres marcos teóricos: ética, histórica y crítica.
    """
    responses = {}

    # Detectar raíz del árbol
    if isinstance(tree, list) and tree:
        root = tree[0]
    elif isinstance(tree, dict):
        root = tree
    else:
        return responses

    def recurse(node):
        # Construimos el prompt concatenando cadenas para evitar errores de comillas
        prompt = (
            "Eres un Generador Contextual de IA deliberativa.\n"
            f"Nodo: '{node['node']}'\n"
            f"Modo de usuario: {mode}\n\n"
            "Proporciona tres respuestas argumentadas:\n"
            "1. Perspectiva ética.\n"
            "2. Perspectiva histórica.\n"
            "3. Perspectiva crítica.\n\n"
            "Responde solo en formato JSON así:\n"
            "{\n"
            f'  "node": "{node["node"]}",\n'
            "  \"responses\": [\n"
            "    {\"label\": \"Ética\", \"text\": \"...\"},\n"
            "    {\"label\": \"Histórica\", \"text\": \"...\"},\n"
            "    {\"label\": \"Crítica\", \"text\": \"...\"}\n"
            "  ]\n"
            "}"
        )

        # Llamada usando la API v1
        resp = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            max_tokens=600,
        )
        try:
            data = json.loads(resp.choices[0].message.content)
        except (KeyError, json.JSONDecodeError):
            data = {"responses": []}

        responses[node["node"]] = data.get("responses", [])
        for child in node.get("children", []):
            recurse(child)

    recurse(root)
    return responses
