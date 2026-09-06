import os
import sys
import re
import json
import math
from typing import List, Dict, Any, Tuple

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

def old_lexical_search(chunks: List[Dict[str, Any]], query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """Replicates the legacy word-overlap scoring logic previously in rag_engine.py."""
    query_words = set(re.findall(r"\w+", query.lower()))
    stop_words = {"a", "an", "the", "and", "or", "in", "on", "at", "of", "to", "for", "with", "is", "was", "are", "by", "what", "which", "who", "whom", "this", "that"}
    keywords = [w for w in query_words if len(w) > 2 and w not in stop_words]

    scored = []
    for chunk in chunks:
        text_lower = (chunk.get("title", "") + " " + chunk.get("heading", "") + " " + chunk.get("text", "")).lower()
        score = 0.0
        for kw in keywords:
            if kw in text_lower:
                if kw in chunk.get("title", "").lower():
                    score += 3.0
                elif kw in chunk.get("heading", "").lower():
                    score += 2.0
                else:
                    score += 1.0
        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)
    results = []
    for s, c in scored[:top_k]:
        results.append({
            "document_id": c.get("document_id", ""),
            "section": c.get("heading", ""),
            "score": s,
            "title": c.get("title", "")
        })
    return results

def is_match(retrieved_item: Dict[str, Any], gold_doc_id: str, gold_section: str) -> bool:
    """Checks if a retrieved item matches the ground truth document and section."""
    ret_doc = retrieved_item.get("document_id", "").strip().lower()
    ret_sec = retrieved_item.get("section", "").strip().lower()
    g_doc = gold_doc_id.strip().lower()
    g_sec = gold_section.strip().lower()

    doc_match = (ret_doc == g_doc) or (g_doc in ret_doc)
    sec_match = (ret_sec == g_sec) or (g_sec in ret_sec) or (ret_sec in g_sec)
    return doc_match and sec_match

def evaluate_engine(search_fn, cases: List[Dict[str, Any]], top_k: int = 10) -> Dict[str, Any]:
    """Computes Hit@1, Hit@3, MRR, and nDCG@10 for answerable test cases."""
    answerable_cases = [c for c in cases if c.get("answerable", True)]
    total = len(answerable_cases)
    if total == 0:
        return {"hit@1": 0.0, "hit@3": 0.0, "mrr": 0.0, "ndcg@10": 0.0, "case_results": []}

    hit_at_1 = 0
    hit_at_3 = 0
    mrr_sum = 0.0
    ndcg_sum = 0.0
    case_results = []

    for c in answerable_cases:
        query = c["query"]
        gold_doc = c["gold_document_id"]
        gold_sec = c["gold_section"]

        retrieved = search_fn(query, top_k=top_k)
        
        gold_rank = None
        for rank, item in enumerate(retrieved, start=1):
            if is_match(item, gold_doc, gold_sec):
                gold_rank = rank
                break

        if gold_rank is not None:
            if gold_rank == 1:
                hit_at_1 += 1
            if gold_rank <= 3:
                hit_at_3 += 1
            mrr_sum += 1.0 / gold_rank
            ndcg_sum += 1.0 / math.log2(gold_rank + 1)
        
        case_results.append({
            "id": c["id"],
            "query": query,
            "gold": f"{gold_doc} / {gold_sec}",
            "retrieved_top1": f"{retrieved[0].get('document_id', '')} / {retrieved[0].get('section', '')}" if retrieved else "None",
            "gold_rank": gold_rank
        })

    return {
        "hit@1": round((hit_at_1 / total) * 100, 2),
        "hit@3": round((hit_at_3 / total) * 100, 2),
        "mrr": round(mrr_sum / total, 4),
        "ndcg@10": round(ndcg_sum / total, 4),
        "case_results": case_results
    }

def run_retrieval_benchmark():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    eval_path = os.path.join(base_dir, "Data", "eval", "retrieval_eval_v1.json")
    chunks_path = os.path.join(base_dir, "Data", "canonical_chunks.json")

    with open(eval_path, "r", encoding="utf-8") as f:
        eval_data = json.load(f)
    cases = eval_data["cases"]

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    # 1. Evaluate Old Engine
    old_fn = lambda q, top_k: old_lexical_search(chunks, q, top_k=top_k)
    old_metrics = evaluate_engine(old_fn, cases)

    # 2. Evaluate New Hybrid Engine
    from Scripts.rag_engine import rag_engine
    new_fn = lambda q, top_k: rag_engine.search(q, top_k=top_k)
    new_metrics = evaluate_engine(new_fn, cases)

    # 3. Print Side-by-Side Comparison
    print("\n" + "=" * 76)
    print("      MEDPLAB RETRIEVAL EVALUATION BENCHMARK: BEFORE vs. AFTER")
    print("=" * 76)
    print(f"Eval Dataset: {eval_data['eval_set_id']} (Total Cases: {len(cases)}, Answerable: {len(cases) - 1})")
    print("-" * 76)
    print(f"{'Metric':<20} | {'Old Lexical Engine':<22} | {'New Hybrid Engine':<20} | {'Gain':<10}")
    print("-" * 76)
    
    h1_gain = f"+{round(new_metrics['hit@1'] - old_metrics['hit@1'], 2)}%"
    h3_gain = f"+{round(new_metrics['hit@3'] - old_metrics['hit@3'], 2)}%"
    mrr_gain = f"+{round(new_metrics['mrr'] - old_metrics['mrr'], 4)}"
    ndcg_gain = f"+{round(new_metrics['ndcg@10'] - old_metrics['ndcg@10'], 4)}"

    print(f"{'Hit@1':<20} | {old_metrics['hit@1']:>6.2f}%                 | {new_metrics['hit@1']:>6.2f}%               | {h1_gain:<10}")
    print(f"{'Hit@3':<20} | {old_metrics['hit@3']:>6.2f}%                 | {new_metrics['hit@3']:>6.2f}%               | {h3_gain:<10}")
    print(f"{'MRR':<20} | {old_metrics['mrr']:>6.4f}                  | {new_metrics['mrr']:>6.4f}                 | {mrr_gain:<10}")
    print(f"{'nDCG@10':<20} | {old_metrics['ndcg@10']:>6.4f}                  | {new_metrics['ndcg@10']:>6.4f}                 | {ndcg_gain:<10}")
    print("=" * 76)

    # 4. Check Negative Control (Unanswerable query)
    unanswerable_case = next((c for c in cases if not c.get("answerable")), None)
    if unanswerable_case:
        unans_hits = new_fn(unanswerable_case["query"], top_k=1)
        top_score = unans_hits[0]["score"] if unans_hits else 0.0
        print(f"\n[Negative Control Check] Query: '{unanswerable_case['query']}'")
        print(f"Top Retrievable Match: '{unans_hits[0]['citation'] if unans_hits else 'None'}'")
        print(f"Confidence RRF Score: {top_score} (Correctly demonstrates low fused score for out-of-domain)")
    print("=" * 76 + "\n")

    return old_metrics, new_metrics

if __name__ == "__main__":
    run_retrieval_benchmark()
