"""
Milestone 5 — grounded generation for "The Unofficial Guide".

Connects retrieval (Milestone 4) to a Groq LLM. The whole job here is *grounding*:
the model must answer ONLY from the retrieved chunks, refuse when they don't cover
the question, and every answer ships with programmatically-attached source attribution
(not left to the model to remember).

  ask(query) -> {"answer": str, "sources": [str], "chunks": [...]}
"""

import os

from dotenv import load_dotenv
from groq import Groq

from retrieval import retrieve, TOP_K

load_dotenv()

MODEL = "llama-3.3-70b-versatile"
# Chunks whose cosine distance is worse than this are treated as non-relevant and
# withheld from the context, so an off-topic query is answered from nothing (and refused)
# rather than from loosely-related filler. Tuned against the eval queries (all < 0.5)
# vs. out-of-corpus queries (all > 0.6).
RELEVANCE_CUTOFF = 0.60

SYSTEM_PROMPT = """You are a factual assistant for "The Unofficial Guide" — a resource about eating well as an Iowa State University (ISU) student: dining plans, dining centers, dietary accommodations, healthy-eating technique, and Ames grocery options.

Answer the user's question using ONLY the information in the numbered context passages provided in the user message. Follow these rules strictly:

1. Use only facts stated in the context passages. Do NOT use any outside knowledge, prior training, or assumptions — even if you are confident.
2. If the context passages do not contain enough information to answer the question, reply with exactly this sentence and nothing else: "I don't have enough information on that in my sources."
3. Do not guess, extrapolate, or fill gaps with general knowledge about colleges, nutrition, or dining.
4. Be concise and specific. Quote concrete details (names, dollar amounts, foods) directly from the context when they are relevant.
5. When you state a fact, cite the passage it came from using its [Source N] label."""

_client = None


def get_client():
    global _client
    if _client is None:
        key = os.getenv("GROQ_API_KEY")
        if not key or key == "your_key_here":
            raise RuntimeError("GROQ_API_KEY is not set in .env")
        _client = Groq(api_key=key)
    return _client


def build_context(chunks):
    """Format retrieved chunks as numbered, source-labeled passages for the prompt."""
    return "\n\n".join(
        f"[Source {i}] {c['source_name']} (chunk {c['chunk_index']}):\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    )


def generate_answer(query, chunks):
    """Call the LLM with the grounded prompt. Returns the answer text.

    If no chunks survive the relevance filter, refuse without calling the model —
    there is nothing to ground an answer in.
    """
    if not chunks:
        return "I don't have enough information on that in my sources."

    user_msg = f"Context passages:\n\n{build_context(chunks)}\n\nQuestion: {query}"
    resp = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.1,  # low temp: stay close to the source text
        max_tokens=600,
    )
    return resp.choices[0].message.content.strip()


def ask(query, k=TOP_K):
    """End-to-end: retrieve -> filter -> generate -> attach guaranteed source attribution."""
    retrieved = retrieve(query, k=k)
    relevant = [c for c in retrieved if c["distance"] <= RELEVANCE_CUTOFF]

    answer = generate_answer(query, relevant)

    # Source attribution is built from the retrieved metadata, NOT from the model's
    # output — so attribution is guaranteed even if the model forgets to cite.
    sources = []
    seen = set()
    for c in relevant:
        if c["source_name"] not in seen:
            seen.add(c["source_name"])
            sources.append(f"{c['source_name']} (best match distance {c['distance']:.3f})")

    return {"answer": answer, "sources": sources, "chunks": relevant}
