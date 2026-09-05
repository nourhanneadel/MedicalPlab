import os
import re
from typing import List, Dict, Any

class MedicalRAGEngine:
    """
    RAG Engine for retrieving evidence-based clinical guidelines (NICE Guidelines).
    Ensures that medical reasoning is grounded in official guidelines to prevent hallucination.
    """
    def __init__(self, guidelines_dir: str = None):
        if guidelines_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            guidelines_dir = os.path.join(base_dir, "Data", "Guidelines")
        self.guidelines_dir = guidelines_dir
        self.chunks = []
        self.load_and_index()

    def load_and_index(self):
        self.chunks = []
        if not os.path.exists(self.guidelines_dir):
            return

        for filename in os.listdir(self.guidelines_dir):
            if filename.endswith(".md"):
                file_path = os.path.join(self.guidelines_dir, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract Title
                title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
                main_title = title_match.group(1) if title_match else filename.replace(".md", "").replace("_", " ").title()

                # Split by ## headers (sections)
                sections = re.split(r"\n(?=##\s+)", content)
                for sec in sections:
                    sec_text = sec.strip()
                    if not sec_text:
                        continue
                    sec_header_match = re.match(r"^##\s+(.+)$", sec_text, re.MULTILINE)
                    sec_title = sec_header_match.group(1) if sec_header_match else "General Guidance"
                    
                    self.chunks.append({
                        "filename": filename,
                        "title": main_title,
                        "section": sec_title,
                        "content": sec_text,
                        "citation": f"{main_title} — {sec_title}"
                    })

    def search(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        if not self.chunks:
            return []

        # Tokenize query words
        query_words = set(re.findall(r"\w+", query.lower()))
        # Filter out common stop words
        stop_words = {"a", "an", "the", "and", "or", "in", "on", "at", "of", "to", "for", "with", "is", "was", "are", "by", "what", "which", "who", "whom", "this", "that"}
        keywords = [w for w in query_words if len(w) > 2 and w not in stop_words]

        scored_chunks = []
        for chunk in self.chunks:
            text_lower = (chunk["title"] + " " + chunk["section"] + " " + chunk["content"]).lower()
            score = 0.0
            
            # Match keywords
            for kw in keywords:
                if kw in text_lower:
                    # Higher weight if keyword is in title or section
                    if kw in chunk["title"].lower():
                        score += 3.0
                    elif kw in chunk["section"].lower():
                        score += 2.0
                    else:
                        score += 1.0

            if score > 0:
                scored_chunks.append((score, chunk))

        # Sort descending by score
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, chunk in scored_chunks[:top_k]:
            results.append({
                "title": chunk["title"],
                "section": chunk["section"],
                "content": chunk["content"],
                "citation": chunk["citation"],
                "score": round(score, 2)
            })

        return results

# Singleton instance
rag_engine = MedicalRAGEngine()

if __name__ == "__main__":
    test_res = rag_engine.search("STEMI chest pain reperfusion")
    print(f"Found {len(test_res)} matches:")
    for r in test_res:
        print(f"-> {r['citation']} (Score: {r['score']})")
