# The Unofficial Guide — Project 1

A retrieval-augmented (RAG) assistant that answers questions about **eating well as an Iowa State University student**, grounded only in a curated corpus of 13 sources. Ask a question → it retrieves the most relevant chunks from a local vector store → a Groq LLM answers using *only* that retrieved context, with source attribution. If the corpus doesn't cover the question, it declines instead of guessing.

**Pipeline:** Ingestion ([ingest.py](ingest.py)) → Chunking → Embedding + ChromaDB ([retrieval.py](retrieval.py)) → Retrieval → Grounded Generation ([generation.py](generation.py)) → Gradio UI ([app.py](app.py)).

**Run it:**
```bash
pip install -r requirements.txt          # into a venv
echo "GROQ_API_KEY=..." > .env            # free key at console.groq.com
python ingest.py        # fetch + clean + chunk 13 sources -> chunks.json
python retrieval.py     # embed -> ChromaDB, then sanity-test the 5 eval queries
python app.py           # Gradio UI at http://localhost:7860
```

---

## Domain

This system covers **how to eat well as an Iowa State University (ISU) student** — navigating meal plans and dining centers, getting dietary/allergy accommodations, healthy-eating technique in a cafeteria, and grocery shopping in Ames.

The practical answer to "how do I actually eat well here?" is fragmented across three kinds of sources that no official channel connects:

1. **Official ISU Dining pages** tell you *what exists* (plan prices, what a Flex Meal is, that a Special Diet Kitchen exists) but are written to explain policy, not to advise — they won't tell you which dining center students actually like or whether a plan is worth the cost.
2. **Student journalism** (Iowa State Daily) captures *lived experience* — which stations are good, which foods are favorites — but it's scattered across years of articles and isn't searchable as one knowledge base.
3. **Dietitian / health-education guides** (Dr. Rachel Paul, SNHU, ISU Student Health) give *how-to technique* (the plate method, salad-bar formulas) but are generic or buried on a wellness page a student would never think to search.

A new or budget-conscious student has to stitch all three together manually. This knowledge is valuable precisely because it's fragmented and partly informal — official channels won't editorialize, and student opinion isn't indexed anywhere. A RAG system that retrieves across all three perspectives at once is more useful than any single source.

---

## Document Sources

13 sources, ingested via `requests` + `trafilatura` (with an `lxml` extractor to recover the JS-accordion FAQ content). Source #13 (SNHU) blocks standard automated fetches, so its text was saved to a local file.

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | ISU Dining — Meal Plans & Rates | Official web page | https://www.dining.iastate.edu/meal-plans/ |
| 2 | ISU Dining — Sustainability | Official web page | https://www.dining.iastate.edu/sustainability/ |
| 3 | ISU Dining — Meal Plan FAQs | Official web page (accordion Q&A) | https://www.dining.iastate.edu/meal-plans/faqs/ |
| 4 | ISU Dining — Nutrition | Official web page | https://www.dining.iastate.edu/nutrition/ |
| 5 | ISU Dining — Accommodations / Special Diet Kitchen | Official web page | https://www.dining.iastate.edu/nutrition/accommodations/ |
| 6 | ISU Dining — Union Drive Marketplace | Official web page | https://www.dining.iastate.edu/location/union-drive-marketplace-2-2/ |
| 7 | ISU Student Health & Wellness — Nutrition & Body Image | Official web page | https://cyclonehealth.iastate.edu/nutrition-body-image |
| 8 | Iowa State Daily — Students share favorite campus dining spots | Student journalism | https://iowastatedaily.com/320101/news-student-life/isu-students-share-favorite-campus-dining-spots/ |
| 9 | Iowa State Daily — Dietitian on campus boosts healthy eating | Student journalism | https://iowastatedaily.com/127879/news/dietitian-on-campus-works-to-help-boost-healthy-eating/ |
| 10 | Iowa State Daily — Grocery shopping options in Ames | Student journalism | https://iowastatedaily.com/149775/special-sections/know-your-grocery-shopping-options-in-ames/ |
| 11 | Iowa State Daily — Campus dining for all ISU students | Student journalism | https://iowastatedaily.com/135432/special-sections/campus-dining-for-all-isu-students/ |
| 12 | Dr. Rachel Paul — Eating Healthy in a College Cafeteria | Dietitian blog/guide | https://www.drrachelpaul.com/blog/eating-healthy-in-a-college-cafeteria/ |
| 13 | SNHU — How to Eat Healthy in College (Avoid the Freshman 15) | Dietitian guide (local file) | documents/manual/snhu.txt |

> *Note:* the original source #2 (`flex-meals-dining-dollars-explained-2/`) redirected to the same FAQ page as #3, producing byte-identical content. It was swapped for the Sustainability page to restore source variety; the Flex-Meals/Dining-Dollars content is still covered by #3.

---

## Chunking Strategy

**Chunk size:** ~1100 characters (≈275 tokens). **Overlap:** 180 characters (≈16%). **Final chunk count:** **52** (avg 1024 chars, max 1276).

**Preprocessing before chunking:** `trafilatura` main-content extraction strips nav menus, footers, ads, and cookie banners; HTML entities are unescaped and whitespace normalized; trailing nav boilerplate ("Read Next", etc.) is removed. The ISU FAQ/plan pages render their substance inside JS-style accordions that `trafilatura` discards as widget chrome, so a custom `lxml` extractor pairs each accordion question with its answer (keeping Q&A pairs intact). Exact-duplicate chunks are de-duplicated.

**Why these choices fit the documents:** The corpus is **prose-heavy, not review-heavy** — FAQ Q&A, news articles, official policy pages, and how-to guides — so the tiny (~200-char) chunks used for one-line reviews would slice a single FAQ answer or a dietitian's salad-bar formula into meaningless fragments. I **started at 600 chars** (≈ one FAQ answer / one guide paragraph). That worked for self-contained FAQ queries but, when I tested retrieval against my 5 eval queries (Milestone 4), it **failed exactly where I'd predicted**: Dr. Rachel Paul's salad-bar formula was split across two adjacent chunks (so neither alone answered the question), and the conversational student-favorites reviews were fragmented from their framing, leaving their source out of the top-4. I ran a chunk-size sweep (600/800/900/1000/1100/1200), measuring per query the best distance and whether the expected source reached the top-4. **1100 was the sweet spot:** all five queries put their expected source in the top-4 with every #1 distance < 0.5, the salad-bar formula sits intact in one chunk, and the corpus stays at 52 chunks (above the 50 floor). 1200 pushed Q1 over 0.5 and dropped below 50 chunks; smaller sizes left Q3/Q5 sources outside the top-4.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` (384-dim, runs locally, no API key, no rate limits). Vectors are stored in **ChromaDB** with **cosine** distance and per-chunk metadata (`source_name`, `source`, `chunk_index`). Semantic embeddings are what let a query like *"is the meal plan worth the money?"* match a chunk that says *"it just doesn't seem like a good cost to what you're getting"* despite sharing almost no exact words.

**Production tradeoff reflection (if cost weren't a constraint):**
- **Accuracy on domain text:** MiniLM is general-purpose. A larger model (`text-embedding-3-large`, `bge-large`) would better separate near-synonyms that matter here — "Flex Meal" vs "Dining Dollars" vs "Meal Swipe" are distinct concepts a small model can blur, and this likely contributed to my Q5 failure (below).
- **Context length:** MiniLM truncates at 256 tokens; fine for my ~275-token chunks but tight at the top end — a longer-context model would let me grow chunks without losing the tail.
- **Multilingual:** not a priority for an English ISU corpus, so I wouldn't pay for it here.
- **Latency & hosting:** MiniLM is local and instant; an API-hosted model adds network latency and a per-query bill. For a real multi-user deployment I'd weigh whether the accuracy gain justifies the recurring cost and the new external dependency. For a demo, local MiniLM clearly wins.

---

## Grounded Generation

Generation uses Groq's `llama-3.3-70b-versatile` at temperature 0.1. Grounding is enforced by **three mechanisms**, not a single polite instruction:

**1. System prompt grounding instruction** (in [generation.py](generation.py)) — it forbids outside knowledge and mandates an exact refusal sentence:
> "Use only facts stated in the context passages. Do NOT use any outside knowledge, prior training, or assumptions — even if you are confident. If the context passages do not contain enough information to answer the question, reply with exactly this sentence and nothing else: *'I don't have enough information on that in my sources.'* … When you state a fact, cite the passage it came from using its [Source N] label."

**2. A relevance filter** — retrieved chunks with cosine distance > **0.60** are withheld from the context. An out-of-corpus query (whose chunks all score > 0.6) therefore reaches the model with *empty context* and is refused, rather than being answered from loosely-related dining text. Tuned against eval queries (all < 0.5) vs. out-of-corpus probes (all > 0.6).

**3. Programmatic source attribution** — the "Retrieved from" list is built from the retrieved chunks' metadata in `ask()`, **not** parsed from the model's output. Attribution is therefore guaranteed even if the model forgets its inline `[Source N]` citations. The model also cites inline, so the user sees both.

**How source attribution is surfaced in the response:** every answer is returned with a deduplicated list of the source documents it drew from, each with its best-match distance, e.g. `• ISU Dining — Meal Plan FAQs (best match distance 0.221)`. In the Gradio UI this populates the "Retrieved from" panel beside the answer.

---

## Evaluation Report

All 5 questions run end-to-end through `generation.ask()`.

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | What salad-bar formula does Dr. Rachel Paul recommend? | ~2 cups non-starchy veg + 1 protein serving (~120 cal) + 100–200 cal of fats | Returned exactly that formula with the calorie figures and examples, cited to the Dr. Rachel Paul source. | Relevant (0.485, right source) | **Accurate** |
| 2 | Difference between Flex Meals and Dining Dollars? | They're distinct: Flex Meals = set-value swipes for retail; Dining Dollars = declining debit-like balance | "Flex Meals are valued at $13.75 … like a swipe worth a set dollar value … Dining Dollars work like a debit card … you pay any overage with Dining Dollars." Correctly distinguishes fixed-value vs. debit. | Relevant (0.221, all from FAQ) | **Accurate** |
| 3 | How does a student with a food allergy get accommodated; what does the Special Diet Kitchen cover? | Speak with staff / request the Special Diet Kitchen; covers top-9 allergens & medically restricted diets | Named speaking with trained staff, requesting the Special Diet Kitchen (documented medical restrictions, top-9 allergens), labeled options; cited 3 sources incl. Accommodations page. | Relevant (0.242–0.259) | **Accurate** (minor illustrative gluten example lightly paraphrased) |
| 4 | Which Ames grocery store is cheapest, and what's a specialty option? | Aldi = cheapest; Wheatsfield Co-op / Hy-Vee = specialty / larger selection | Correctly named **Aldi as cheapest** (milk under $2/gal) but described the "specialty option" as *Aldi's daily specials* rather than a different specialty store (Wheatsfield/Hy-Vee). | Partially relevant (cheapest chunk retrieved; the Wheatsfield/Hy-Vee chunk ranked outside top-4) | **Partially accurate** |
| 5 | What dining spots/foods do ISU students name as favorites? | Specific named favorites: UDM tacos, Fuse bowls, Friley Windows, Seasons | Retrieved a student quote about eating **off**-campus (Szechuan House) and honestly stated it lacked info on campus favorites — did **not** surface the UDM/Seasons/Friley quotes. | Off-target (answer-bearing chunks ranked 6th & 16th, not top-4) | **Inaccurate** (see Failure Case) |

**Summary:** 3 accurate, 1 partially accurate, 1 inaccurate. Notably, the two weaker cases (Q4, Q5) both trace to **retrieval ranking**, not generation — the generator stayed grounded throughout and never hallucinated; on Q5 it correctly declined rather than invent an answer.

---

## Failure Case Analysis

**Question that failed:** Q5 — *"What dining spots or foods do ISU students name as their campus favorites?"*

**What the system returned:** It cited a student (Malo) who prefers to eat *off* campus at Szechuan House, then correctly stated the context didn't contain campus favorites — so it declined to name any. It never surfaced the actual answers (UDM tacos, Fuse bowls, Friley Windows, Seasons) that *do* exist in the corpus.

**Root cause (tied to a specific pipeline stage): a retrieval/embedding ranking failure, not a generation failure.** The source that names favorites (#8) was chunked correctly, and the answer-bearing chunks exist — but they ranked *outside* the top-4: the chunk where a student says he's "preferring Union Drive Marketplace … Seasons" ranked **6th (distance 0.446)**, and the chunk naming "another of Reynolds' favorite spots is Friley" ranked **16th (0.518)**. Meanwhile the top-4 included a generic campus-dining overview intro (0.341) and, from #8 itself, the chunk about eating *off* campus (0.395). The cause is that the favorite-naming quotes are **conversational and indirect** ("preferring Union Drive Marketplace," "another of Reynolds' favorite spots is…") and carry weak surface signal for the words "campus favorites," whereas the off-campus chunk shares tokens like "eat," "campus," and "restaurants." `all-MiniLM-L6-v2`, a small general-purpose embedder, scored the token-overlapping-but-semantically-wrong chunk higher than the indirectly-phrased correct ones. The generation stage then behaved exactly as designed and declined rather than fabricate — so the breakdown is upstream, in semantic ranking.

**What I would change to fix it:** (a) raise `k` for this kind of broad "what do people like" query, or add a light re-ranker over the top ~10 candidates; (b) try a stronger embedding model (e.g. `bge-large`) that separates indirect sentiment from topical word-overlap better; or (c) at ingestion, attach a short synthetic header to review chunks (e.g. "Student opinions on dining centers:") so the conversational quotes carry clearer retrieval signal.

---

## Spec Reflection

**One way the spec helped me during implementation:** Writing the Evaluation Plan in planning.md *before* coding — with a specific expected answer **and** the source each answer should come from — turned retrieval testing into an objective check instead of a vibe. In Milestone 4 I could measure, per query, whether the *expected* source reached the top-4, which is exactly how I caught that 600-char chunks were splitting the salad-bar formula and dropping the Q3/Q5 sources. Without those concrete expected-source targets I'd have eyeballed "looks relevant" and shipped worse chunking.

**One way my implementation diverged from the spec, and why:** My planning.md committed to **600-char chunks**, reasoning that smaller chunks keep retrieval precise for a prose corpus. Real retrieval results contradicted that: 600 chars split key facts across boundaries and fragmented conversational reviews. I ran a data-driven chunk-size sweep and **raised chunking to 1100/180**, which put every eval query's expected source in the top-4. I updated the Chunking Strategy section to record the change and the evidence for it — the spec was a starting hypothesis, and measurement corrected it.

---

## AI Usage

I used **Claude (via Claude Code)** as my implementation partner, directing it with specific sections of planning.md rather than asking it to invent decisions.

**Instance 1 — Chunking, and overriding the chunk size**
- *What I gave the AI:* my Chunking Strategy section (600 chars / 100 overlap, prose-heavy reasoning) and Documents table, and asked it to implement `load_documents()` and `chunk_text()`.
- *What it produced:* a boundary-aware `chunk_text(text, size=600, overlap=100)` that packs whole paragraphs/Q&A pairs with overlap, plus a `trafilatura` cleaner.
- *What I changed/overrode:* during Milestone 4 retrieval testing, two eval queries had their expected source outside the top-4. Rather than accept the spec's 600, I directed a **chunk-size sweep** and overrode the size to **1100/180** based on the measured per-query results — then had it update planning.md to match. The AI also initially missed that the ISU FAQ content was hidden in JS accordions; I directed it to recover that content, which it did with an `lxml` accordion extractor.

**Instance 2 — Grounding, and making attribution guaranteed**
- *What I gave the AI:* my Anticipated Challenges section (source-attribution and stale-fact risks) and the requirement that answers come *only* from retrieved chunks, with citations.
- *What it produced:* a `generate_answer()` with a grounding system prompt and a Groq call, initially leaning on the model to cite its sources inline.
- *What I changed/overrode:* relying on the LLM to remember citations is exactly the "missing source attribution" risk I'd flagged, so I directed two changes: **(a)** build the source list **programmatically** from chunk metadata so attribution can't be dropped, and **(b)** add a **relevance cutoff (cosine ≤ 0.60)** so out-of-corpus questions hit empty context and are refused — which I verified by probing with "dorm move-in dates" and "basketball head coach" (both correctly declined).
