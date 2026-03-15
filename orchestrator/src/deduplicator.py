import math
from typing import List, Dict, Optional, Tuple

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot_product = sum(a * b for a, b in zip(v1, v2))
    magnitude1 = math.sqrt(sum(a * a for a in v1))
    magnitude2 = math.sqrt(sum(a * a for a in v2))
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)

class TaskDeduplicator:
    """
    Handles semantic deduplication of tasks using embeddings provided by Ollama.
    """
    def __init__(self, ollama_wrapper):
        self.ollama = ollama_wrapper
        self.existing_cache: List[Tuple[str, List[float]]] = []

    async def prepare_existing_tasks(self, existing_tasks: List[Dict]):
        """
        Pre-calculates embeddings for all existing tasks to speed up comparison.
        """
        print(f"[*] Pre-calculating embeddings for {len(existing_tasks)} existing tasks...")
        self.existing_cache = []
        for t in existing_tasks:
            name = t.get('name', 'Untitled')
            # Use name + description for a better semantic signature
            text = f"{name} {t.get('description', '')}".strip()
            if text:
                embedding = await self.ollama.getEmbedding(text)
                self.existing_cache.append((name, embedding))

    async def find_duplicate(self, new_task_data: Dict, threshold: float = 0.65) -> Tuple[Optional[str], float]:
        """
        Checks if the new task is semantically similar to any existing task.
        Returns (existing_task_name, similarity_score) if a duplicate is found.
        """
        new_name = new_task_data.get('name', 'Untitled')
        new_text = f"{new_name} {new_task_data.get('description', '')}".strip()
        
        if not new_text:
            return None, 0.0
            
        new_vec = await self.ollama.getEmbedding(new_text)
        
        best_match_name = None
        best_score = 0.0
        
        for existing_name, existing_vec in self.existing_cache:
            score = cosine_similarity(new_vec, existing_vec)
            if score > threshold and score > best_score:
                best_score = score
                best_match_name = existing_name
                
        if best_match_name:
            return best_match_name, best_score
            
        return None, 0.0
