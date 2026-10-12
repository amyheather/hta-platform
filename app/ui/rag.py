# =============================================================================
# RAG Prompt
# =============================================================================

import streamlit as st


def show_rag():
    """Display instructions and a reusable HTA prompt."""

    st.header("🤖 AI Prompt Template")

    st.markdown(
        """
        Use the template below to ask an AI tool questions about NICE
        Technology Appraisal documents.

        1. Copy the prompt into your chosen AI tool.
        2. Replace `[ADD CONTEXT HERE]` with relevant document text,
           or attach the documents and refer to them in that section.
        3. Replace `[ADD QUESTION HERE]` with your question.
        4. Check the answer against the original documents.

        This app does not send documents to an AI tool or generate answers.
        """
    )

    prompt = """
You are an expert Health Technology Assessment (HTA) assistant
specialising in NICE Technology Appraisals.

Answer the user's question ONLY using the supplied context.

Rules
-----
1. Do not use outside knowledge.
2. If the answer is not available in the context, say:
   "The selected document does not contain sufficient information
   to answer this question."
3. Be concise but complete.
4. Preserve medical terminology exactly as written.
5. Use bullet points where appropriate.
6. Do not invent numbers, dates or recommendations.
7. If multiple pieces of evidence exist, combine them into one answer.

Context or attached documents
-----------------------------
[ADD CONTEXT HERE]

Question
--------
[ADD QUESTION HERE]
"""

    st.code(prompt, language=None)
