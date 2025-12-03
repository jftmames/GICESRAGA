import json
from datetime import datetime

class ReasoningTracker:
    def __init__(self, root_question):
        self.log = {
            "root": root_question,
            "inquiry": None,
            "responses": {},
            "focus": [],
            "times": [],
            "steps": [],
            "feedback": {},
            "node_states": {}
        }

    def log_inquiry(self, tree):
        self.log["inquiry"] = tree
        self._stamp("inquiry")

    def log_responses(self, resp):
        """Registra o actualiza todas las respuestas multiperspectiva."""
        self.log["responses"] = resp
        self._stamp("responses")

    def log_focus_change(self, s):
        """Registra sugerencias de reformulación/foco (puede ser lista o string)."""
        self.log["focus"].append(s)
        self._stamp("focus")

    def log_event(self, event_type, content, marco=None, parent_node=None):
        self.log["steps"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "content": content,
            "marco": marco,
            "parent_node": parent_node
        })

    def add_feedback(self, node_or_step_id, comment, author="Anónimo", tipo="Humano"):
        if node_or_step_id not in self.log["feedback"]:
            self.log["feedback"][node_or_step_id] = []
        self.log["feedback"][node_or_step_id].append({
            "comment": comment,
            "author": author,
            "tipo": tipo,
            "timestamp": datetime.utcnow().isoformat()
        })

    def set_node_state(self, node, state):
        self.log["node_states"][node] = {
            "state": state,
            "timestamp": datetime.utcnow().isoformat()
        }

    def _stamp(self, evt):
        self.log["times"].append({evt: datetime.utcnow().isoformat()})

    def export(self):
        return json.dumps(self.log, ensure_ascii=False, indent=2)
