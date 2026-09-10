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
    batch_nice_exact = [c for c in cases if c.get("answerable") and int(c["id"].replace("TC-", "")) <= 14]
    batch_nice_paraphrased = [c for c in cases if c.get("answerable") and 16 <= int(c["id"].replace("TC-", "")) <= 21]
    batch_gmc = [c for c in cases if c.get("answerable") and 22 <= int(c["id"].replace("TC-", "")) <= 33]
    batch_ng222 = [c for c in cases if c.get("answerable") and 35 <= int(c["id"].replace("TC-", "")) <= 45]
    batch_all = [c for c in cases if c.get("answerable")]
    negative_cases = [c for c in cases if not c.get("answerable")]

    # Evaluate Batch 1: NICE Acute Original Clinical Terms
    b1_old = evaluate_engine(old_fn, batch_nice_exact)
    b1_bm25 = evaluate_engine(bm25_fn, batch_nice_exact)
    b1_hybrid = evaluate_engine(hybrid_fn, batch_nice_exact)

    # Evaluate Batch 2: NICE Acute Paraphrased / Lay Queries
    b2_old = evaluate_engine(old_fn, batch_nice_paraphrased)
    b2_bm25 = evaluate_engine(bm25_fn, batch_nice_paraphrased)
    b2_hybrid = evaluate_engine(hybrid_fn, batch_nice_paraphrased)

    # Evaluate Batch 3: GMC Ethics & Professional Standards (TC-022 to TC-033)
    b3_old = evaluate_engine(old_fn, batch_gmc)
    b3_bm25 = evaluate_engine(bm25_fn, batch_gmc)
    b3_hybrid = evaluate_engine(hybrid_fn, batch_gmc)

    # Evaluate Batch 4: NICE Mental Health (NG222) (TC-035 to TC-045)
    b4_old = evaluate_engine(old_fn, batch_ng222)
    b4_bm25 = evaluate_engine(bm25_fn, batch_ng222)
    b4_hybrid = evaluate_engine(hybrid_fn, batch_ng222)

    # Evaluate Overall: All 43 Answerable Cases Combined (NICE-acute + GMC + NG222)
    all_old = evaluate_engine(old_fn, batch_all)
    all_bm25 = evaluate_engine(bm25_fn, batch_all)
    all_hybrid = evaluate_engine(hybrid_fn, batch_all)

    print("=" * 86)
    print("   MEDPLAB MULTI-SOURCE RETRIEVAL ABLATION BENCHMARK (NICE + GMC + NG222)")
    print("=" * 86)
    print(f"Total Cases: {len(cases)} (NICE Acute Exact: {len(batch_nice_exact)}, NICE Acute Lay: {len(batch_nice_paraphrased)}, GMC Ethics: {len(batch_gmc)}, NICE MH NG222: {len(batch_ng222)}, Negative Controls: {len(negative_cases)})")

    print_batch_table("Batch 1: NICE Acute Original Clinical Terms (TC-001 to TC-014)", b1_old, b1_bm25, b1_hybrid, len(batch_nice_exact))
    print_batch_table("Batch 2: NICE Acute Paraphrased / Lay Queries (TC-016 to TC-021)", b2_old, b2_bm25, b2_hybrid, len(batch_nice_paraphrased))
    print_batch_table("Batch 3: GMC Ethics & Professional Standards (TC-022 to TC-033)", b3_old, b3_bm25, b3_hybrid, len(batch_gmc))
    print_batch_table("Batch 4: NICE Mental Health (NG222) (TC-035 to TC-045)", b4_old, b4_bm25, b4_hybrid, len(batch_ng222))
    print_batch_table(f"All Sources Overall: Combined Multi-Source Retrieval (N = {len(batch_all)})", all_old, all_bm25, all_hybrid, len(batch_all))

    # Cross-Source Contamination Audit across 3 source domains
    print("\n" + "=" * 86)
    print("      CROSS-SOURCE CONTAMINATION AUDIT (NICE-Acute vs GMC vs NG222)")
    print("=" * 86)

    def get_source_domain(doc_id: str) -> str:
        if "good_medical_practice" in doc_id or "gmc" in doc_id:
            return "GMC"
        elif "depression" in doc_id or "ng222" in doc_id:
            return "NG222"
        elif "nice" in doc_id:
            return "NICE-acute"
        return "Unknown"

    domains = ["NICE-acute", "GMC", "NG222"]
    domain_cases = {
        "NICE-acute": {
            "all": [c for c in cases if c.get("answerable") and get_source_domain(c.get("gold_document_id", "")) == "NICE-acute"],
            "exact": [c for c in cases if c.get("answerable") and get_source_domain(c.get("gold_document_id", "")) == "NICE-acute" and int(c["id"].replace("TC-", "")) <= 14],
            "paraphrased": [c for c in cases if c.get("answerable") and get_source_domain(c.get("gold_document_id", "")) == "NICE-acute" and 16 <= int(c["id"].replace("TC-", "")) <= 21]
        },
        "GMC": {
            "all": [c for c in cases if c.get("answerable") and get_source_domain(c.get("gold_document_id", "")) == "GMC"],
            "exact": [c for c in cases if c.get("answerable") and get_source_domain(c.get("gold_document_id", "")) == "GMC" and int(c["id"].replace("TC-", "")) <= 31],
            "paraphrased": [c for c in cases if c.get("answerable") and get_source_domain(c.get("gold_document_id", "")) == "GMC" and int(c["id"].replace("TC-", "")) in [32, 33]]
        },
        "NG222": {
            "all": [c for c in cases if c.get("answerable") and get_source_domain(c.get("gold_document_id", "")) == "NG222"],
            "exact": [c for c in cases if c.get("answerable") and get_source_domain(c.get("gold_document_id", "")) == "NG222" and int(c["id"].replace("TC-", "")) <= 43],
            "paraphrased": [c for c in cases if c.get("answerable") and get_source_domain(c.get("gold_document_id", "")) == "NG222" and int(c["id"].replace("TC-", "")) in [44, 45]]
        }
    }

    # Contamination tracking: matrix[src][target] = {"all": [], "exact": [], "paraphrased": []}
    contamination_matrix = {s: {t: {"all": [], "exact": [], "paraphrased": []} for t in domains if t != s} for s in domains}

    for src_d in domains:
        for c in domain_cases[src_d]["all"]:
            hits = hybrid_fn(c["query"], top_k=3)
            is_para = c in domain_cases[src_d]["paraphrased"]
            for target_d in domains:
                if src_d == target_d:
                    continue
                matching_hits = [h for h in hits if get_source_domain(h.get("document_id", "")) == target_d]
                if matching_hits:
                    entry = (c["id"], c["query"], [h.get("citation", "") for h in matching_hits])
                    contamination_matrix[src_d][target_d]["all"].append(entry)
                    if is_para:
                        contamination_matrix[src_d][target_d]["paraphrased"].append(entry)
                    else:
                        contamination_matrix[src_d][target_d]["exact"].append(entry)

    # Print 3x3 contamination matrix table
    print("\nPairwise Contamination Matrix (Top-3 hits contaminated by different source domain):")
    matrix_header = f"| {'Query Domain':<14} | {'NICE-acute Contam':<22} | {'GMC Contam':<22} | {'NG222 Contam':<22} |"
    matrix_sep =    f"|{'-'*16}|{'-'*24}|{'-'*24}|{'-'*24}|"
    print(matrix_header)
    print(matrix_sep)

    for src_d in domains:
        cells = []
        for target_d in domains:
            if src_d == target_d:
                cells.append("N/A (Self)")
            else:
                c_data = contamination_matrix[src_d][target_d]
                n_src = len(domain_cases[src_d]["all"])
                cnt = len(c_data["all"])
                pct = (cnt / n_src * 100) if n_src > 0 else 0.0
                cells.append(f"{cnt}/{n_src} ({pct:.1f}%)")
        print(f"| {src_d:<14} | {cells[0]:<22} | {cells[1]:<22} | {cells[2]:<22} |")

    # Print detailed Exact vs Paraphrased breakdown
    print("\nContamination Breakdown by Query Formulation (Exact vs Paraphrased):")
    print(f"{'Query Domain':<14} | {'Contaminating Target':<22} | {'Total':<15} | {'Exact Terms':<15} | {'Paraphrased':<15}")
    print("-" * 86)
    for src_d in domains:
        for target_d in domains:
            if src_d == target_d:
                continue
            c_data = contamination_matrix[src_d][target_d]
            n_all = len(domain_cases[src_d]["all"])
            n_ex = len(domain_cases[src_d]["exact"])
            n_pa = len(domain_cases[src_d]["paraphrased"])

            all_str = f"{len(c_data['all'])}/{n_all} ({(len(c_data['all'])/n_all*100) if n_all else 0:.1f}%)"
            ex_str = f"{len(c_data['exact'])}/{n_ex} ({(len(c_data['exact'])/n_ex*100) if n_ex else 0:.1f}%)"
            pa_str = f"{len(c_data['paraphrased'])}/{n_pa} ({(len(c_data['paraphrased'])/n_pa*100) if n_pa else 0:.1f}%)"
            print(f"{src_d:<14} | {target_d:<22} | {all_str:<15} | {ex_str:<15} | {pa_str:<15}")

    # Print any contaminated queries
    any_contam = False
    print("\nDetailed Listing of Contaminated Queries:")
    for src_d in domains:
        for target_d in domains:
            if src_d == target_d:
                continue
            entries = contamination_matrix[src_d][target_d]["all"]
            if entries:
                any_contam = True
                print(f"  [{src_d} queries contaminated by {target_d}]:")
                for cid, q, hits in entries:
                    print(f"    * [{cid}] '{q}' -> Contaminating Chunks: {hits}")
    if not any_contam:
        print("  None - Complete isolation across all domains.")

    # Paraphrased Test Cases Diagnostic Breakdown
    print("\n" + "=" * 86)
    print("      PARAPHRASED TEST CASES DIAGNOSTIC BREAKDOWN (NICE + GMC + NG222)")
    print("=" * 86)
    print(f"{'Case ID':<8} | {'Domain':<10} | {'BM25 Rank':<10} | {'Hybrid Rank':<12} | {'Query (snippet)':<40}")
    print("-" * 86)
    paraphrased_cases = [c for c in cases if c.get("id") in [
        "TC-016", "TC-017", "TC-018", "TC-019", "TC-020", "TC-021",
        "TC-032", "TC-033",
        "TC-044", "TC-045"
    ]]
    for c in paraphrased_cases:
        b_hits = bm25_fn(c["query"], top_k=10)
        h_hits = hybrid_fn(c["query"], top_k=10)
        b_rank = None
        for r, item in enumerate(b_hits, 1):
            if is_match(item, c["gold_document_id"], c["gold_section"]):
                b_rank = r
                break
        h_rank = None
        for r, item in enumerate(h_hits, 1):
            if is_match(item, c["gold_document_id"], c["gold_section"]):
                h_rank = r
                break
        dom = get_source_domain(c["gold_document_id"])
        b_str = str(b_rank) if b_rank is not None else "MISS (>10)"
        h_str = str(h_rank) if h_rank is not None else "MISS (>10)"
        q_snip = (c["query"][:37] + "...") if len(c["query"]) > 40 else c["query"]
        print(f"{c['id']:<8} | {dom:<10} | {b_str:<10} | {h_str:<12} | {q_snip:<40}")

    # Negative Controls
    print("\n" + "=" * 86)
    print("      NEGATIVE CONTROL / OUT-OF-DOMAIN EVALUATION")
    print("=" * 86)
    for unans in negative_cases:
        unans_hits = hybrid_fn(unans["query"], top_k=1)
        top_score = unans_hits[0]["score"] if unans_hits else 0.0
        top_cit = unans_hits[0]["citation"] if unans_hits else "None"
        print(f"Query [{unans['id']}]: '{unans['query']}'")
        print(f" -> Top Match: '{top_cit}' (Score: {top_score:.4f})")
        print(f" -> Result: {'PASS (Low confidence/safe)' if top_score < 0.05 else 'REVIEW'}")
    print("=" * 86 + "\n")

    return {
        "batch_nice_exact": {"old": b1_old, "bm25": b1_bm25, "hybrid": b1_hybrid},
        "batch_nice_paraphrased": {"old": b2_old, "bm25": b2_bm25, "hybrid": b2_hybrid},
        "batch_gmc": {"old": b3_old, "bm25": b3_bm25, "hybrid": b3_hybrid},
        "batch_ng222": {"old": b4_old, "bm25": b4_bm25, "hybrid": b4_hybrid},
        "overall": {"old": all_old, "bm25": all_bm25, "hybrid": all_hybrid},
        "contamination_matrix": contamination_matrix
    }

if __name__ == "__main__":
    run_retrieval_benchmark()
