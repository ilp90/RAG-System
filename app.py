"""
Milestone 5 — Gradio query interface for "The Unofficial Guide".

Run:  .venv/bin/python app.py   ->   open http://localhost:7860
(Build the vector index first with `python retrieval.py` if you haven't.)
"""

import gradio as gr

from generation import ask

EXAMPLE_QUESTIONS = [
    "What's the difference between Flex Meals and Dining Dollars on an ISU meal plan?",
    "How does a student with a food allergy get accommodated at ISU Dining?",
    "What salad-bar formula does Dr. Rachel Paul recommend?",
    "Which Ames grocery store is cheapest for students?",
    "What dining spots do ISU students say are their favorites?",
]


def handle_query(question):
    if not question or not question.strip():
        return "Please enter a question.", ""
    result = ask(question)
    if result["sources"]:
        sources = "\n".join(f"• {s}" for s in result["sources"])
    else:
        sources = "(no source above the relevance threshold — question likely outside the corpus)"
    return result["answer"], sources


with gr.Blocks(title="The Unofficial Guide — ISU Dining") as demo:
    gr.Markdown(
        "# 🍎 The Unofficial Guide\n"
        "Eating well as an **Iowa State University** student — answers are grounded "
        "**only** in 13 curated sources (dining plans, accommodations, student reviews, "
        "dietitian guides, Ames groceries). If the sources don't cover your question, "
        "the assistant will say so rather than guess."
    )
    inp = gr.Textbox(
        label="Your question",
        placeholder="e.g. What's the difference between Flex Meals and Dining Dollars?",
    )
    btn = gr.Button("Ask", variant="primary")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from (source documents)", lines=4)

    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])

    gr.Examples(examples=EXAMPLE_QUESTIONS, inputs=inp)


if __name__ == "__main__":
    demo.launch()
