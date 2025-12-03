# modules/inquiry_engine.py

import os
import json
import openai

# Configura tu clave de OpenAI desde la variable de entorno
openai.api_key = os.getenv("OPENAI_API_KEY")

# Prompt para generar subpreguntas jerárquicas
INQUIRY_PROMPT = """
Eres un generador de subpreguntas para fomentar el pensamiento crítico.
Pregunta raíz: '{question}'
Nivel de usuario: {mode}

1. Identifica 3–5 subpreguntas relevantes.
2. Organízalas jerárquicamente.
Responde **solo** en formato JSON.
"""

def generate_inquiry_tree(root_question: str, mode: str) -> dict:
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{
            "role": "system",
            "content": INQUIRY_PROMPT.format(question=root_question, mode=mode)
        }],
        temperature=0.7,
        max_tokens=500,
    )
    content = response.choices[0].message.content
    return json.loads(content)
