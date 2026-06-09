"""
Milestone 3 — Document pipeline for "The Unofficial Guide" RAG system.

Two jobs (per planning.md): load the 13 documents and split them into clean,
self-contained chunks the embedding model can work with.

Pipeline:  fetch HTML -> clean (trafilatura) -> load_documents() -> chunk_text() -> chunks.json

Run:  .venv/bin/python ingest.py
"""

import html
import json
import os
import re
import sys
import textwrap

import requests
import trafilatura
from lxml import html as lhtml

# --- config (planning.md Chunking Strategy) ---
# Started at 600/100, but Milestone-4 retrieval testing showed 600 split key facts
# across boundaries (Dr. Rachel Paul's salad-bar formula) and fragmented conversational
# reviews, leaving their source out of the top-4 for Q3/Q5. Raised to 1100/180, which
# puts every eval query's expected source in the top-4 with all distances < 0.5.
CHUNK_SIZE = 1100
CHUNK_OVERLAP = 180

RAW_DIR = "documents/raw"
CLEAN_DIR = "documents/clean"
CHUNKS_PATH = "chunks.json"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Mirrors the planning.md Documents table. 12 fetchable web pages + 1 local file
# (SNHU, source #13, which blocks automated fetch and is pasted in by hand).
SOURCES = [
    {"id": 1,  "name": "ISU Dining — Meal Plans & Rates",
     "url": "https://www.dining.iastate.edu/meal-plans/"},
    {"id": 2,  "name": "ISU Dining — Sustainability",
     "url": "https://www.dining.iastate.edu/sustainability/"},
    {"id": 3,  "name": "ISU Dining — Meal Plan FAQs",
     "url": "https://www.dining.iastate.edu/meal-plans/faqs/"},
    {"id": 4,  "name": "ISU Dining — Nutrition",
     "url": "https://www.dining.iastate.edu/nutrition/"},
    {"id": 5,  "name": "ISU Dining — Accommodations / Special Diet Kitchen",
     "url": "https://www.dining.iastate.edu/nutrition/accommodations/"},
    {"id": 6,  "name": "ISU Dining — Union Drive Marketplace",
     "url": "https://www.dining.iastate.edu/location/union-drive-marketplace-2-2/"},
    {"id": 7,  "name": "ISU Student Health & Wellness — Nutrition & Body Image",
     "url": "https://cyclonehealth.iastate.edu/nutrition-body-image"},
    {"id": 8,  "name": "Iowa State Daily — Students share favorite campus dining spots",
     "url": "https://iowastatedaily.com/320101/news-student-life/isu-students-share-favorite-campus-dining-spots/"},
    {"id": 9,  "name": "Iowa State Daily — Dietitian on campus boosts healthy eating",
     "url": "https://iowastatedaily.com/127879/news/dietitian-on-campus-works-to-help-boost-healthy-eating/"},
    {"id": 10, "name": "Iowa State Daily — Grocery shopping options in Ames",
     "url": "https://iowastatedaily.com/149775/special-sections/know-your-grocery-shopping-options-in-ames/"},
    {"id": 11, "name": "Iowa State Daily — Campus dining for all ISU students",
     "url": "https://iowastatedaily.com/135432/special-sections/campus-dining-for-all-isu-students/"},
    {"id": 12, "name": "Dr. Rachel Paul — Eating Healthy in a College Cafeteria",
     "url": "https://www.drrachelpaul.com/blog/eating-healthy-in-a-college-cafeteria/"},
    # Source #13 blocks automated fetch (HTTP 403) — paste the article text here by hand.
    {"id": 13, "name": "SNHU — How to Eat Healthy in College (Avoid the Freshman 15)",
     "file": "documents/manual/snhu.txt"},
]


def slug(source):
    """Stable filename stem for a source, e.g. '03-isu-dining-meal-plan-faqs'."""
    base = re.sub(r"[^a-z0-9]+", "-", source["name"].lower()).strip("-")
    return f"{source['id']:02d}-{base}"[:80]


# --- stage 1: fetch -----------------------------------------------------------
def fetch_html(source):
    """Fetch a web source to documents/raw/<slug>.html. Idempotent: skips if cached."""
    os.makedirs(RAW_DIR, exist_ok=True)
    path = os.path.join(RAW_DIR, slug(source) + ".html")
    if os.path.exists(path):
        return path
    resp = requests.get(source["url"], headers={"User-Agent": USER_AGENT}, timeout=30)
    resp.raise_for_status()
    with open(path, "w", encoding="utf-8") as f:
        f.write(resp.text)
    return path


# --- stage 2: clean -----------------------------------------------------------
def clean_text_from_html(raw_html):
    """Extract main article content, dropping nav/footer/ads/cookie banners."""
    text = trafilatura.extract(
        raw_html,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
    ) or ""
    # belt-and-suspenders: unescape stray entities and normalize whitespace
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # drop trailing nav boilerplate trafilatura sometimes keeps
    text = re.sub(r"\s*\n(Read Next|Read More|Share this[^\n]*|Related[^\n]*)\s*$", "", text, flags=re.I)
    return text.strip()


def _block_text(el):
    """Text of an element with block children joined by newlines (avoids run-together text)."""
    blocks = el.xpath(".//p | .//li | .//h1 | .//h2 | .//h3 | .//h4 | .//h5 | .//h6")
    if blocks:
        lines = [re.sub(r"\s+", " ", b.text_content()).strip() for b in blocks]
        return "\n".join(l for l in lines if l)
    return re.sub(r"\s+", " ", el.text_content()).strip()


def extract_accordions(raw_html):
    """Pull collapsible accordion Q&A pairs that trafilatura discards as widget chrome.

    The ISU Dining FAQ/plan pages render their substance inside
    <div class="accordion-button"> (question) + <div class="accordion-body"> (answer).
    Returns a list of "Question\\nAnswer" strings — one self-contained Q&A per entry,
    which keeps each pair together through chunking (per planning.md).
    """
    try:
        root = lhtml.fromstring(raw_html)
    except Exception:
        return []
    buttons = root.xpath("//*[contains(@class,'accordion-button')]")
    bodies = root.xpath("//*[contains(@class,'accordion-body')]")
    pairs = []
    for btn, body in zip(buttons, bodies):
        q = re.sub(r"\s+", " ", btn.text_content()).strip()
        a = _block_text(body)
        if q and a:
            pairs.append(html.unescape(f"{q}\n{a}"))
    return pairs


# --- stage 3: load all documents ----------------------------------------------
def load_documents():
    """Return [{name, source, text}] for every source, writing cleaned text to disk.

    Warns (and skips) on empty extractions or a missing manual file rather than
    silently producing junk chunks.
    """
    os.makedirs(CLEAN_DIR, exist_ok=True)
    docs = []
    for source in SOURCES:
        if "file" in source:  # local, hand-pasted source
            if not os.path.exists(source["file"]):
                print(f"  ⚠️  SKIP #{source['id']} {source['name']} — "
                      f"manual file not found: {source['file']}")
                continue
            with open(source["file"], encoding="utf-8") as f:
                text = html.unescape(f.read()).strip()
            origin = source["file"]
        else:  # web source
            try:
                raw_path = fetch_html(source)
            except requests.RequestException as e:
                print(f"  ⚠️  SKIP #{source['id']} {source['name']} — fetch failed: {e}")
                continue
            with open(raw_path, encoding="utf-8") as f:
                raw = f.read()
            # main article text + any accordion Q&A the extractor would otherwise drop
            parts = [clean_text_from_html(raw)] + extract_accordions(raw)
            text = "\n\n".join(p for p in parts if p.strip()).strip()
            origin = source["url"]

        if len(text.strip()) < 100:
            print(f"  ⚠️  SKIP #{source['id']} {source['name']} — "
                  f"cleaned text too short ({len(text)} chars), check extraction")
            continue

        with open(os.path.join(CLEAN_DIR, slug(source) + ".txt"), "w", encoding="utf-8") as f:
            f.write(text)
        docs.append({"name": source["name"], "source": origin, "text": text})
        print(f"  ✓  #{source['id']:>2} {source['name'][:48]:<48} {len(text):>6} chars")
    return docs


# --- stage 4: chunk -----------------------------------------------------------
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _split_long_paragraph(para, size):
    """Split an over-long paragraph on sentence boundaries (last resort: hard cut)."""
    pieces, buf = [], ""
    for sent in _SENT_SPLIT.split(para):
        if buf and len(buf) + 1 + len(sent) > size:
            pieces.append(buf)
            buf = sent
        else:
            buf = f"{buf} {sent}".strip()
    if buf:
        pieces.append(buf)
    # a single sentence longer than `size` still needs a hard cut
    out = []
    for p in pieces:
        while len(p) > size:
            out.append(p[:size])
            p = p[size:]
        if p:
            out.append(p)
    return out


def chunk_text(text, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Boundary-aware chunking targeting `size` chars with `overlap` carry-over.

    Packs whole paragraphs together rather than cutting mid-sentence, so chunks
    are self-contained. Over-long paragraphs fall back to sentence splitting.
    Overlap carries the tail of the previous chunk into the next so a fact sitting
    on a boundary stays retrievable. Empty/whitespace chunks are filtered out.
    """
    # normalize into paragraph units, exploding any paragraph bigger than `size`
    paragraphs = []
    for para in re.split(r"\n{2,}", text):
        para = para.strip()
        if not para:
            continue
        if len(para) > size:
            paragraphs.extend(_split_long_paragraph(para, size))
        else:
            paragraphs.append(para)

    chunks, buf = [], ""
    for para in paragraphs:
        candidate = f"{buf}\n\n{para}".strip() if buf else para
        if buf and len(candidate) > size:
            chunks.append(buf)
            # start next chunk with the overlap tail of the one we just closed
            tail = buf[-overlap:]
            tail = tail[tail.find(" ") + 1:] if " " in tail else tail  # avoid a cut word
            buf = f"{tail}\n\n{para}".strip()
        else:
            buf = candidate
    if buf.strip():
        chunks.append(buf)

    return [c.strip() for c in chunks if len(c.strip()) > 0]


# --- stage 5: orchestrate + inspect -------------------------------------------
def main():
    print("Loading documents...")
    docs = load_documents()
    if not docs:
        print("No documents loaded — nothing to chunk. Fix sources and rerun.")
        sys.exit(1)

    all_chunks = []
    seen = set()  # drop exact-duplicate chunks (e.g. #2 redirects to the same FAQ page as #3)
    dupes = 0
    for doc in docs:
        for i, chunk in enumerate(chunk_text(doc["text"])):
            key = re.sub(r"\s+", " ", chunk).strip().lower()
            if key in seen:
                dupes += 1
                continue
            seen.add(key)
            all_chunks.append({
                "text": chunk,
                "source_name": doc["name"],
                "source": doc["source"],
                "chunk_index": i,
                "char_len": len(chunk),
            })
    if dupes:
        print(f"  (de-duplicated {dupes} identical chunks across sources)")

    with open(CHUNKS_PATH, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    # ---- inspection block (the milestone's checkpoint) ----
    lengths = [c["char_len"] for c in all_chunks]
    print("\n" + "=" * 70)
    print(f"Documents loaded : {len(docs)} / {len(SOURCES)} sources")
    print(f"TOTAL CHUNKS     : {len(all_chunks)}   (healthy range: 50–2,000)")
    print(f"Chunk length     : min {min(lengths)}  avg {sum(lengths)//len(lengths)}  max {max(lengths)} chars")
    print(f"Saved to         : {CHUNKS_PATH}")
    print("=" * 70)

    # 5 representative chunks spread evenly across the corpus
    n = len(all_chunks)
    sample_idx = sorted({int(i * (n - 1) / 4) for i in range(5)})
    print("\n5 REPRESENTATIVE CHUNKS — each should be a complete, standalone thought:\n")
    for rank, idx in enumerate(sample_idx, 1):
        c = all_chunks[idx]
        print(f"--- chunk #{idx}  ({rank}/5)  | {c['source_name']}  | {c['char_len']} chars ---")
        print(textwrap.fill(c["text"], width=88))
        print()


if __name__ == "__main__":
    main()
