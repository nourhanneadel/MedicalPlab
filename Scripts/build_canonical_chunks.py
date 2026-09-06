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

    # Sort files to ensure deterministic ordering
    filenames = sorted([f for f in os.listdir(guidelines_dir) if f.endswith(".md")])

    for filename in filenames:
        file_path = os.path.join(guidelines_dir, filename)
        with open(file_path, "r", encoding="utf-8") as f:
            raw_content = f.read()

        doc_base = os.path.splitext(filename)[0]
        document_id = f"doc_{doc_base}"

        # Extract Document Title from top # header
        title_match = re.search(r"^#\s+(.+)$", raw_content, re.MULTILINE)
        main_title = title_match.group(1).strip() if title_match else doc_base.replace("_", " ").title()

        # Split content by ## section headers (reusing structure-aware logic from rag_engine)
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

            chunk = {
                "chunk_id": chunk_id,
                "document_id": document_id,
                "source_id": "nice_guidelines",
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
                    "doc_id": document_id
                }
            }

            canonical_chunks.append(chunk)
            block_index += 1

    # Save to canonical_chunks.json
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(canonical_chunks, f, indent=2, ensure_ascii=False)

    print(f"Generated {len(canonical_chunks)} canonical chunks from {len(filenames)} files.")
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
