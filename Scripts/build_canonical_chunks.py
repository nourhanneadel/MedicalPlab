import os
import re
import json
import hashlib
from typing import List, Dict, Any

def compute_sha256(text: str) -> str:
    """Computes SHA-256 hash of a string for provenance tracking."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def build_canonical_chunks(guidelines_dir: str = None, output_path: str = None) -> List[Dict[str, Any]]:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if guidelines_dir is None:
        guidelines_dir = os.path.join(base_dir, "Data", "Guidelines")
    if output_path is None:
        output_path = os.path.join(base_dir, "Data", "canonical_chunks.json")

    canonical_chunks = []
    
    if not os.path.exists(guidelines_dir):
        print(f"Guidelines directory not found at: {guidelines_dir}")
        return []

    # Recursively discover all .md guideline files (supporting NICE/ and GMC/ subdirs)
    md_files = []
    for root, _, files in os.walk(guidelines_dir):
        for f in sorted(files):
            if f.endswith(".md"):
                md_files.append(os.path.join(root, f))
    md_files.sort()

    for file_path in md_files:
        filename = os.path.basename(file_path)
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        doc_base = os.path.splitext(filename)[0]
        document_id = f"doc_{doc_base}"

        # Extract Document Title from top # header
        title_match = re.search(r"^#\s+(.+)$", raw_content, re.MULTILINE)
        main_title = title_match.group(1).strip() if title_match else doc_base.replace("_", " ").title()

        is_gmc = "gmc" in doc_base.lower() or "gmc" in file_path.lower()
        has_h3 = bool(re.search(r"^###\s+", raw_content, re.MULTILINE))

        if is_gmc:
            source_body = "GMC"
            source_id = "gmc_guidelines"
            clinical_domain = "ethics_professionalism"
            source_authority_note = (
                "UK regulatory/ethical standards — binding professional "
                "requirement for all UK-registered doctors, not a clinical guideline"
            )
        elif "depression" in doc_base.lower() or "ng222" in doc_base.lower():
            source_body = "NICE"
            source_id = "nice_guidelines"
            clinical_domain = "mental_health"
            source_authority_note = (
                "UK national clinical guideline (NICE) — evidence-based clinical recommendations"
            )
        else:
            source_body = "NICE"
            source_id = "nice_guidelines"
            clinical_domain = "acute_physical_medicine"
            source_authority_note = (
                "UK national clinical guideline (NICE) — evidence-based clinical recommendations"
            )

        if not has_h3:
            # Split content by ## section headers (standard NICE structure)
            sections = re.split(r"\n(?=##\s+)", raw_content)
            
            block_index = 0
            for sec in sections:
                sec_text = sec.strip()
                if not sec_text:
                    continue

                sec_header_match = re.match(r"^##\s+(.+)$", sec_text, re.MULTILINE)
                sec_heading = sec_header_match.group(1).strip() if sec_header_match else "Overview & Context"

                chunk_id = f"{document_id}_chunk_{block_index}"
                chunk_hash = compute_sha256(sec_text)
                token_count = len(re.findall(r"\w+", sec_text))

                citation = f"{main_title} \u2014 {sec_heading}"

                chunk = {
                    "chunk_id": chunk_id,
                    "document_id": document_id,
                    "source_id": source_id,
                    "source_body": source_body,
                    "clinical_domain": clinical_domain,
                    "source_authority_note": source_authority_note,
                    "citation": citation,
                    "block_index": block_index,
                    "section_path": [main_title, sec_heading],
                    "heading": sec_heading,
                    "text": sec_text,
                    "content_sha256": chunk_hash,
                    "provenance_type": "local_markdown",
                    "source_locator": f"{filename}#{sec_heading}",
                    # Compatibility fields for existing agents and UI
                    "title": main_title,
                    "section": sec_heading,
                    "token_count": token_count,
                    "metadata": {
                        "source_file": filename,
                        "doc_id": document_id,
                        "clinical_domain": clinical_domain
                    }
                }

                canonical_chunks.append(chunk)
                block_index += 1

        else:
            # Structure-aware chunking at the ### level (GMC document structure)
            h2_blocks = re.split(r"\n(?=##\s+)", raw_content)
            block_index = 0

            for h2_idx, h2_block in enumerate(h2_blocks):
                h2_text = h2_block.strip()
                if not h2_text:
                    continue

                if h2_idx == 0 and not h2_text.startswith("##"):
                    # Top-level document preamble (title & metadata before first ##)
                    chunk_id = f"{document_id}_chunk_{block_index}"
                    chunk_hash = compute_sha256(h2_text)
                    token_count = len(re.findall(r"\w+", h2_text))
                    sec_heading = "Overview & Context"
                    citation = f"{main_title} \u2014 {sec_heading}"

                    canonical_chunks.append({
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "source_id": source_id,
                        "source_body": source_body,
                        "clinical_domain": clinical_domain,
                        "source_authority_note": source_authority_note,
                        "citation": citation,
                        "block_index": block_index,
                        "section_path": [main_title, sec_heading],
                        "heading": sec_heading,
                        "text": h2_text,
                        "content_sha256": chunk_hash,
                        "provenance_type": "local_markdown",
                        "source_locator": f"{filename}#{sec_heading}",
                        "title": main_title,
                        "section": sec_heading,
                        "token_count": token_count,
                        "metadata": {
                            "source_file": filename,
                            "doc_id": document_id,
                            "clinical_domain": clinical_domain
                        }
                    })
                    block_index += 1
                    continue

                # Extract ## section title
                h2_header_match = re.match(r"^##\s+(.+)$", h2_text, re.MULTILINE)
                domain_heading = h2_header_match.group(1).strip() if h2_header_match else "General"

                # Check if this ## block contains ### subsections
                if re.search(r"\n(?=###\s+)", h2_text):
                    h3_subsections = re.split(r"\n(?=###\s+)", h2_text)
                    for sub_idx, sub in enumerate(h3_subsections):
                        sub_text = sub.strip()
                        if not sub_text:
                            continue

                        if sub_idx == 0 and not sub_text.startswith("###"):
                            # Skip if this is just the ## Domain line without any body text
                            lines_without_h2 = [l for l in sub_text.splitlines() if not l.startswith("##")]
                            if not any(lines_without_h2):
                                continue
                            sub_heading = domain_heading
                        else:
                            sub_header_match = re.match(r"^###\s+(.+)$", sub_text, re.MULTILINE)
                            sub_heading = sub_header_match.group(1).strip() if sub_header_match else domain_heading

                        para_numbers = []
                        if is_gmc:
                            para_matches = re.findall(r"(?:^|\n)(\d+)\s+[A-Z]", sub_text)
                            para_numbers = [int(p) for p in para_matches]

                            domain_short_match = re.match(r"(Domain\s+\d+)", domain_heading)
                            domain_short = domain_short_match.group(1) if domain_short_match else domain_heading

                            if para_numbers:
                                min_p = min(para_numbers)
                                max_p = max(para_numbers)
                                para_str = f"para. {min_p}" if min_p == max_p else f"para. {min_p}-{max_p}"
                                citation = f"GMC Good Medical Practice \u2014 {domain_short}, {para_str} ({sub_heading})"
                            else:
                                citation = f"GMC Good Medical Practice \u2014 {domain_short} ({sub_heading})"
                            section_name = f"{domain_heading} > {sub_heading}"
                            meta = {
                                "source_file": filename,
                                "doc_id": document_id,
                                "clinical_domain": clinical_domain,
                                "domain": domain_heading,
                                "paragraphs": para_numbers
                            }
                        else:
                            citation = f"{main_title} — {sub_heading}"
                            section_name = sub_heading
                            meta = {
                                "source_file": filename,
                                "doc_id": document_id,
                                "clinical_domain": clinical_domain,
                                "section": domain_heading
                            }

                        chunk_id = f"{document_id}_chunk_{block_index}"
                        chunk_hash = compute_sha256(sub_text)
                        token_count = len(re.findall(r"\w+", sub_text))

                        canonical_chunks.append({
                            "chunk_id": chunk_id,
                            "document_id": document_id,
                            "source_id": source_id,
                            "source_body": source_body,
                            "clinical_domain": clinical_domain,
                            "source_authority_note": source_authority_note,
                            "citation": citation,
                            "block_index": block_index,
                            "section_path": [main_title, domain_heading, sub_heading],
                            "heading": sub_heading,
                            "text": sub_text,
                            "content_sha256": chunk_hash,
                            "provenance_type": "local_markdown",
                            "source_locator": f"{filename}#{sub_heading}",
                            "title": main_title,
                            "section": section_name,
                            "token_count": token_count,
                            "metadata": meta
                        })
                        block_index += 1
                else:
                    chunk_id = f"{document_id}_chunk_{block_index}"
                    chunk_hash = compute_sha256(h2_text)
                    token_count = len(re.findall(r"\w+", h2_text))
                    if is_gmc:
                        citation = f"GMC Good Medical Practice — {domain_heading}"
                        meta = {
                            "source_file": filename,
                            "doc_id": document_id,
                            "clinical_domain": clinical_domain
                        }
                    else:
                        citation = f"{main_title} — {domain_heading}"
                        meta = {
                            "source_file": filename,
                            "doc_id": document_id,
                            "clinical_domain": clinical_domain,
                            "section": domain_heading
                        }

                    canonical_chunks.append({
                        "chunk_id": chunk_id,
                        "document_id": document_id,
                        "source_id": source_id,
                        "source_body": source_body,
                        "clinical_domain": clinical_domain,
                        "source_authority_note": source_authority_note,
                        "citation": citation,
                        "block_index": block_index,
                        "section_path": [main_title, domain_heading],
                        "heading": domain_heading,
                        "text": h2_text,
                        "content_sha256": chunk_hash,
                        "provenance_type": "local_markdown",
                        "source_locator": f"{filename}#{domain_heading}",
                        "title": main_title,
                        "section": domain_heading,
                        "token_count": token_count,
                        "metadata": meta
                    })
                    block_index += 1

    # Save to canonical_chunks.json
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(canonical_chunks, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(canonical_chunks)} canonical chunks from {len(md_files)} files.")
    print(f"Saved canonical chunks to: {output_path}")

    # Validate against chunk.schema.json if available
    schema_path = os.path.join(base_dir, "schemas", "chunk.schema.json")
    if os.path.exists(schema_path):
        try:
            import jsonschema
            with open(schema_path, "r", encoding="utf-8") as sf:
                schema = json.load(sf)
            for c in canonical_chunks:
                jsonschema.validate(instance=c, schema=schema)
            print("All chunks strictly validated against schemas/chunk.schema.json!")
        except ImportError:
            print("jsonschema not installed, skipping formal schema validation.")
        except Exception as ve:
            print(f"Schema validation warning: {ve}")

    return canonical_chunks

if __name__ == "__main__":
    build_canonical_chunks()
