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
            "title": c.get("title", ""),
            "citation": f"{c.get('title', '')} — {c.get('heading', '')}"
        })
    return results

def bm25_only_search(rag_engine_instance, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """Evaluates BM25 retrieval tier alone without dense embeddings or RRF fusion."""
    bm25_hits = rag_engine_instance.search_bm25(query, top_n=top_k)
    results = []
    for idx, score in bm25_hits:
        chunk = rag_engine_instance.chunks[idx]
        results.append({
            "document_id": chunk.get("document_id", ""),
            "section": chunk.get("heading", chunk.get("section", "")),
            "score": round(score, 4),
            "title": chunk.get("title", ""),
            "citation": f"{chunk.get('title', '')} — {chunk.get('heading', '')}"
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

def print_batch_table(title: str, old_m: Dict[str, Any], bm25_m: Dict[str, Any], hybrid_m: Dict[str, Any], n_cases: int):
    print(f"\n### {title} (N = {n_cases})")
    header = f"| {'Metric':<10} | {'Old Lexical':<12} | {'BM25-only':<12} | {'Hybrid (BM25+Dense)':<20} | {'Hybrid vs BM25 Gain':<20} |"
    sep =    f"|{'-'*12}|{'-'*14}|{'-'*14}|{'-'*22}|{'-'*22}|"
    print(header)
    print(sep)

    def gain_fmt(curr, base, is_pct=False):
        diff = curr - base
        sign = "+" if diff > 0 else ""
        if is_pct:
            return f"{sign}{diff:.2f}%"
        return f"{sign}{diff:.4f}"

    metrics = [
        ("Hit@1", f"{old_m['hit@1']:.2f}%", f"{bm25_m['hit@1']:.2f}%", f"{hybrid_m['hit@1']:.2f}%", gain_fmt(hybrid_m['hit@1'], bm25_m['hit@1'], True)),
        ("Hit@3", f"{old_m['hit@3']:.2f}%", f"{bm25_m['hit@3']:.2f}%", f"{hybrid_m['hit@3']:.2f}%", gain_fmt(hybrid_m['hit@3'], bm25_m['hit@3'], True)),
        ("MRR", f"{old_m['mrr']:.4f}", f"{bm25_m['mrr']:.4f}", f"{hybrid_m['mrr']:.4f}", gain_fmt(hybrid_m['mrr'], bm25_m['mrr'])),
        ("nDCG@10", f"{old_m['ndcg@10']:.4f}", f"{bm25_m['ndcg@10']:.4f}", f"{hybrid_m['ndcg@10']:.4f}", gain_fmt(hybrid_m['ndcg@10'], bm25_m['ndcg@10'])),
    ]

    for name, old_val, bm25_val, hyb_val, gain in metrics:
        print(f"| {name:<10} | {old_val:<12} | {bm25_val:<12} | {hyb_val:<20} | {gain:<20} |")

def run_retrieval_benchmark():
    eval_path = os.path.join(base_dir, "Data", "eval", "retrieval_eval_v1.json")
    chunks_path = os.path.join(base_dir, "Data", "canonical_chunks.json")

    with open(eval_path, "r", encoding="utf-8") as f:
        eval_data = json.load(f)
    cases = eval_data["cases"]

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    from Scripts.rag_engine import rag_engine

    # Define engine search functions
    old_fn = lambda q, top_k=10: old_lexical_search(chunks, q, top_k=top_k)
    bm25_fn = lambda q, top_k=10: bm25_only_search(rag_engine, q, top_k=top_k)
    hybrid_fn = lambda q, top_k=10: rag_engine.search(q, top_k=top_k)

    # Separate batches
    batch_original = [c for c in cases if c.get("answerable") and int(c["id"].replace("TC-", "")) <= 14]
    batch_paraphrased = [c for c in cases if c.get("answerable") and int(c["id"].replace("TC-", "")) >= 16]
    batch_all = [c for c in cases if c.get("answerable")]
    negative_cases = [c for c in cases if not c.get("answerable")]

    # Evaluate Batch 1: Original Clinical
    b1_old = evaluate_engine(old_fn, batch_original)
    b1_bm25 = evaluate_engine(bm25_fn, batch_original)
    b1_hybrid = evaluate_engine(hybrid_fn, batch_original)

    # Evaluate Batch 2: Paraphrased / Lay
    b2_old = evaluate_engine(old_fn, batch_paraphrased)
    b2_bm25 = evaluate_engine(bm25_fn, batch_paraphrased)
    b2_hybrid = evaluate_engine(hybrid_fn, batch_paraphrased)

    # Evaluate Overall: All Answerable
    all_old = evaluate_engine(old_fn, batch_all)
    all_bm25 = evaluate_engine(bm25_fn, batch_all)
    all_hybrid = evaluate_engine(hybrid_fn, batch_all)

    print("=" * 86)
    print("      MEDPLAB 3-WAY RETRIEVAL ABLATION BENCHMARK (LEXICAL vs BM25 vs HYBRID)")
    print("=" * 86)
    print(f"Total Cases: {len(cases)} (Original Clinical: {len(batch_original)}, Paraphrased: {len(batch_paraphrased)}, Negative Control: {len(negative_cases)})")

    print_batch_table("Batch 1: Original Clinical Terms (TC-001 to TC-014)", b1_old, b1_bm25, b1_hybrid, len(batch_original))
    print_batch_table("Batch 2: Paraphrased / Lay Queries (TC-016 to TC-021)", b2_old, b2_bm25, b2_hybrid, len(batch_paraphrased))
    print_batch_table("Overall Benchmark: All Answerable Cases Combined", all_old, all_bm25, all_hybrid, len(batch_all))

    print("\n" + "=" * 86)
    print("      PARAPHRASED TEST CASES DETAILED DIAGNOSTIC BREAKDOWN")
    print("=" * 86)
    print(f"{'Case ID':<8} | {'BM25 Rank':<10} | {'Hybrid Rank':<12} | {'Query (snippet)':<50}")
    print("-" * 86)
    for b_case, h_case in zip(b2_bm25["case_results"], b2_hybrid["case_results"]):
        b_rank = str(b_case["gold_rank"]) if b_case["gold_rank"] is not None else "MISS (>10)"
        h_rank = str(h_case["gold_rank"]) if h_case["gold_rank"] is not None else "MISS (>10)"
        q_snip = (b_case["query"][:47] + "...") if len(b_case["query"]) > 50 else b_case["query"]
        print(f"{b_case['id']:<8} | {b_rank:<10} | {h_rank:<12} | {q_snip:<50}")

    # Check Negative Controls
    print("\n" + "=" * 86)
    print("      NEGATIVE CONTROL / OUT-OF-DOMAIN EVALUATION")
    print("=" * 86)
    for unans in negative_cases:
        unans_hits = hybrid_fn(unans["query"], top_k=1)
        top_score = unans_hits[0]["score"] if unans_hits else 0.0
        top_cit = unans_hits[0]["citation"] if unans_hits else "None"
        print(f"Query [{unans['id']}]: '{unans['query']}'")
        print(f" -> Top Match: '{top_cit}' (Score: {top_score})")
        print(f" -> Result: {'PASS (Low confidence/safe)' if top_score < 0.05 else 'REVIEW'}")
    print("=" * 86 + "\n")

    return {
        "batch_original": {"old": b1_old, "bm25": b1_bm25, "hybrid": b1_hybrid},
        "batch_paraphrased": {"old": b2_old, "bm25": b2_bm25, "hybrid": b2_hybrid},
        "overall": {"old": all_old, "bm25": all_bm25, "hybrid": all_hybrid},
    }

if __name__ == "__main__":
    run_retrieval_benchmark()
