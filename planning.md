# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain

<!-- What domain did you choose? Why is this knowledge valuable and hard to find through official channels? -->

---

## Documents

<!-- List your specific sources: URLs, subreddit names, forum threads, or file descriptions.
     Aim for at least 10 sources that together cover different subtopics or perspectives within your domain. -->

| # | Source | Description | URL or location |
|---|--------|-------------|-----------------|
| 1 | ISU Dining — Meal Plans & Rates | Official plan names, prices, what each includes, and which halls require a plan | https://www.dining.iastate.edu/meal-plans/ |
| 2 | ISU Dining — Flex Meals, Dining Dollars & GET&Go Explained | How meal swipes, Dining Dollars, Express, and Flex Meals differ and their dollar values | https://www.dining.iastate.edu/meal-plans/flex-meals-dining-dollars-explained-2/  |
| 3 | ISU Dining — Meal Plan FAQs | Q&A on what's included, where plans work, balances, to-go/order-ahead, sick meals | https://www.dining.iastate.edu/meal-plans/faqs/  |
| 4 | ISU Dining — Nutrition | NetNutrition, ingredient/allergen labels, QR codes, registered-dietitian "Let's Talk" | https://www.dining.iastate.edu/nutrition/  |
| 5 | ISU Dining — Accommodations / Special Diet Kitchen | Special Diet Kitchen, top-9 allergen / gluten-free / dairy-free / vegan / halal options, how to request | https://www.dining.iastate.edu/nutrition/accommodations/ |
| 6 | ISU Dining — Union Drive Marketplace | A dining-center page: payment types accepted, menu filters, allergen disclaimer | https://www.dining.iastate.edu/location/union-drive-marketplace-2-2/  |
| 7 | ISU Student Health & Wellness — Nutrition & Body Image (Joyful Eating) | Non-diet / Health at Every Size approach, campus dietitian, meal-planning & grocery budgeting, eating-disorder support, how to book | https://cyclonehealth.iastate.edu/nutrition-body-image  |
| 8 | Iowa State Daily — ISU students share favorite campus dining spots | Student quotes on best dining halls/foods (UDM tacos, Fuse bowls, Friley Windows, Seasons) and meal-plan convenience | https://iowastatedaily.com/320101/news-student-life/isu-students-share-favorite-campus-dining-spots/  |
| 9 | Iowa State Daily — Dietitian on campus works to help boost healthy eating | Reporting on special-diet support and the push for a campus dietitian; staff quotes on healthy eating | https://iowastatedaily.com/127879/news/dietitian-on-campus-works-to-help-boost-healthy-eating/  |
| 10 | Iowa State Daily — Know your grocery shopping options in Ames | Guide to Aldi, Hy-Vee, Fareway, Wheatsfield co-op, Dahl's — prices, locations, what each is good for | https://iowastatedaily.com/149775/special-sections/know-your-grocery-shopping-options-in-ames/ |
| 11 | Iowa State Daily — Campus dining for all ISU students | Overview of every dining center (Conversations, Seasons, Knapp-Storms, UDCC) and their food stations | https://iowastatedaily.com/135432/special-sections/campus-dining-for-all-isu-students/ |
| 12 | Dr. Rachel Paul — Eating Healthy in a College Cafeteria | Concrete dining-hall technique: plate method, salad-bar formula, station-by-station (grill, soups, pizza, breakfast) | https://www.drrachelpaul.com/blog/eating-healthy-in-a-college-cafeteria/|
| 13 | SNHU — How to Eat Healthy in College: 15 Tips to Avoid the "Freshman 15" | Campus-dietitian's 15 tips: power nutrients, portions, hydration, not skipping meals, sleep, stress, using campus resources | https://www.snhu.edu/about-us/newsroom/health/how-to-eat-healthy-in-college-and-avoid-freshman-15  |

---

## Chunking Strategy

<!-- How will you split documents into chunks?
     State your chunk size (in tokens or characters), overlap size, and explain why those
     numbers fit the structure of your documents.
     A review-heavy corpus warrants different chunking than a long FAQ. -->

**Chunk size:**

**Overlap:**

**Reasoning:**

---

## Retrieval Approach

<!-- Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)?
     How many chunks will you retrieve per query (top-k)?
     If you were deploying this for real users and cost wasn't a constraint, what tradeoffs
     would you weigh in choosing a different embedding model — context length, multilingual
     support, accuracy on domain-specific text, latency? -->

**Embedding model:**

**Top-k:**

**Production tradeoff reflection:**

---

## Evaluation Plan

<!-- List your 5 test questions with their expected correct answers.
     Questions should be specific enough that you can judge whether the system's response
     is right or wrong. "What are good dining halls?" is too vague.
     "What do students say about wait times at [dining hall name] during lunch?" is testable. -->

| # | Question | Expected answer |
|---|----------|-----------------|
| 1 | | |
| 2 | | |
| 3 | | |
| 4 | | |
| 5 | | |

---

## Anticipated Challenges

<!-- What could go wrong? Name at least two specific risks with reasoning.
     Consider: noisy or inconsistent documents, missing source attribution, off-topic
     retrieval, chunks that split key information across boundaries. -->

1.

2.

---

## Architecture

<!-- Draw a diagram of your pipeline showing the five stages:
     Document Ingestion → Chunking → Embedding + Vector Store → Retrieval → Generation
     Label each stage with the tool or library you're using.
     You can use ASCII art, a Mermaid diagram, or embed a sketch as an image.
     You'll use this diagram as context when prompting AI tools to implement each stage. -->

---

## AI Tool Plan

<!-- For each part of the pipeline below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, which requirements)
     - What you expect it to produce
     - How you'll verify the output matches your spec

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Chunking Strategy section and ask it to implement chunk_text()
     with my specified chunk size and overlap" is a plan. -->

**Milestone 3 — Ingestion and chunking:**

**Milestone 4 — Embedding and retrieval:**

**Milestone 5 — Generation and interface:**
