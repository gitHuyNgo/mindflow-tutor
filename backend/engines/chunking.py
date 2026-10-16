import re
from typing import List, Dict, Any, Optional

DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""]


def baseline_chunk_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 120,
    min_chunk_len: int = 60,
) -> List[str]:
    """
    Legacy baseline chunker from original rag_retriever.py.
    Suffers from overflow bug: paragraphs longer than chunk_size are not split.
    Kept for empirical baseline comparison.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) >= min_chunk_len]
    chunks: List[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = (current + "\n\n" + para).strip()
        else:
            if len(current) >= min_chunk_len:
                chunks.append(current)
            overlap_text = current[-overlap:] if overlap and current else ""
            current = (overlap_text + "\n\n" + para).strip() if overlap_text else para

    if len(current) >= min_chunk_len:
        chunks.append(current)

    return chunks


def split_text_recursive(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    min_chunk_len: int = 40,
    separators: Optional[List[str]] = None,
) -> List[str]:
    """
    Robust recursive hierarchical chunker.
    Guarantees: Every chunk satisfies len(chunk) <= chunk_size.
    Splits along natural boundaries: Paragraphs -> Lines -> Sentences -> Clauses -> Words -> Chars.
    """
    if separators is None:
        separators = DEFAULT_SEPARATORS

    text = text.strip()
    if not text:
        return []

    # If already within limit, return
    if len(text) <= chunk_size:
        return [text] if len(text) >= min_chunk_len else []

    # Find the highest-priority separator present in text
    chosen_sep = ""
    next_separators: List[str] = []
    for i, sep in enumerate(separators):
        if sep == "":
            chosen_sep = ""
            next_separators = []
            break
        if sep in text:
            chosen_sep = sep
            next_separators = separators[i + 1:]
            break

    # Split text by chosen separator
    if chosen_sep:
        splits = text.split(chosen_sep)
    else:
        # Character-level split if no separator matches
        splits = list(text)

    # Recombine splits into chunks up to chunk_size with overlap
    chunks: List[str] = []
    current_parts: List[str] = []
    current_len = 0

    for part in splits:
        part_str = part.strip() if chosen_sep != "" else part
        if not part_str:
            continue

        # If a single part exceeds chunk_size, recursively split that part using finer separators
        if len(part_str) > chunk_size:
            # First flush current accumulated chunk if any
            if current_parts:
                flush_text = chosen_sep.join(current_parts).strip()
                if len(flush_text) >= min_chunk_len:
                    chunks.append(flush_text)
                current_parts = []
                current_len = 0

            # Subdivide oversized part
            sub_chunks = split_text_recursive(
                part_str,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                min_chunk_len=min_chunk_len,
                separators=next_separators,
            )
            chunks.extend(sub_chunks)
            continue

        sep_len = len(chosen_sep) if current_parts else 0
        if current_len + sep_len + len(part_str) <= chunk_size:
            current_parts.append(part_str)
            current_len += sep_len + len(part_str)
        else:
            # Flush accumulated chunk
            if current_parts:
                flush_text = chosen_sep.join(current_parts).strip()
                if len(flush_text) >= min_chunk_len:
                    chunks.append(flush_text)

            # Start new chunk with overlap
            # Take trailing parts from previous chunk to establish overlap
            overlap_parts: List[str] = []
            overlap_len = 0
            for prev_part in reversed(current_parts):
                if overlap_len + len(prev_part) + len(chosen_sep) <= chunk_overlap:
                    overlap_parts.insert(0, prev_part)
                    overlap_len += len(prev_part) + len(chosen_sep)
                else:
                    break

            current_parts = overlap_parts + [part_str]
            current_len = sum(len(p) for p in current_parts) + (len(chosen_sep) * max(0, len(current_parts) - 1))

    if current_parts:
        final_text = chosen_sep.join(current_parts).strip()
        if len(final_text) >= min_chunk_len and (not chunks or final_text != chunks[-1]):
            chunks.append(final_text)

    # Post-assertion guarantee
    bounded_chunks: List[str] = []
    for c in chunks:
        if len(c) <= chunk_size:
            bounded_chunks.append(c)
        else:
            # Hard fallback slice if any edge case exceeded
            for start in range(0, len(c), chunk_size - chunk_overlap):
                slice_chunk = c[start:start + chunk_size].strip()
                if len(slice_chunk) >= min_chunk_len:
                    bounded_chunks.append(slice_chunk)

    return bounded_chunks


def markdown_chunk_text(
    markdown_text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    min_chunk_len: int = 40,
) -> List[Dict[str, Any]]:
    """
    Header-aware markdown chunker.
    Extracts section breadcrumbs (e.g. ['Chapter 1: Newton's Laws', 'Section 1.2: F=ma'])
    and prepends the context prefix to chunks so retrieval has section context.
    """
    lines = markdown_text.splitlines()
    sections: List[Dict[str, Any]] = []
    current_headers = {1: "", 2: "", 3: ""}
    current_content: List[str] = []

    def get_breadcrumb() -> str:
        parts = [current_headers[k] for k in (1, 2, 3) if current_headers[k]]
        return " > ".join(parts)

    for line in lines:
        header_match = re.match(r"^(#{1,3})\s+(.*)$", line.strip())
        if header_match:
            # Flush existing section
            if current_content:
                sections.append({
                    "breadcrumb": get_breadcrumb(),
                    "content": "\n".join(current_content).strip(),
                })
                current_content = []

            level = len(header_match.group(1))
            title = header_match.group(2).strip()
            current_headers[level] = title
            for l in range(level + 1, 4):
                current_headers[l] = ""
        else:
            current_content.append(line)

    if current_content:
        sections.append({
            "breadcrumb": get_breadcrumb(),
            "content": "\n".join(current_content).strip(),
        })

    structured_chunks: List[Dict[str, Any]] = []
    for sec in sections:
        prefix = f"[{sec['breadcrumb']}]\n" if sec["breadcrumb"] else ""
        content = sec["content"]
        if not content:
            continue

        raw_chunks = split_text_recursive(
            content,
            chunk_size=chunk_size - len(prefix),
            chunk_overlap=chunk_overlap,
            min_chunk_len=min_chunk_len,
        )

        for i, rc in enumerate(raw_chunks):
            structured_chunks.append({
                "chunk": f"{prefix}{rc}".strip(),
                "breadcrumb": sec["breadcrumb"],
                "section_index": i,
                "length": len(rc) + len(prefix),
            })

    return structured_chunks
