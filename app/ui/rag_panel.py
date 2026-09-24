# =============================================================================
# RAG Question Answering
# =============================================================================

import traceback

import rag
import repository
import streamlit as st

# =============================================================================
# Main UI
# =============================================================================


def show_rag_panel():
    """
    Retrieval Augmented Generation (RAG)
    """

    st.header("🤖 RAG Question Answering")

    st.markdown("""
Ask questions about a NICE Technology Appraisal using Retrieval
Augmented Generation (RAG).
""")

    st.divider()

    # -------------------------------------------------------------------------
    # Session State
    # -------------------------------------------------------------------------

    if "rag_ready" not in st.session_state:
        st.session_state.rag_ready = False

    if "rag_result" not in st.session_state:
        st.session_state.rag_result = None

    if "rag_document" not in st.session_state:
        st.session_state.rag_document = None

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # -------------------------------------------------------------------------
    # Repository
    # -------------------------------------------------------------------------

    try:
        repository_df = repository.load_repository_index()

    except Exception as error:
        st.error(error)

        return

    downloaded = repository.get_downloaded_pdfs(repository_df)

    if downloaded.empty:
        st.warning("No downloaded PDF documents available.")

        return

    st.subheader("Check Repository")

    # -------------------------------------------------------------------------
    # TA Selection
    # -------------------------------------------------------------------------

    selected_ta = (
        st.text_input("Enter TA Number", placeholder="Example: TA970", key="rag_ta")
        .strip()
        .upper()
    )

    if selected_ta == "":
        st.info("Enter a TA Number to load documents.")

        return

    filtered_documents = downloaded[
        downloaded["TA Number"].astype(str).str.upper() == selected_ta
    ]

    if filtered_documents.empty:
        st.error(f"No documents found for {selected_ta}")

        return

    st.write("")

    st.subheader("Available Documents")

    selected_index = st.selectbox(
        "Select Document",
        options=list(filtered_documents.index),
        format_func=lambda x: (
            f"{filtered_documents.loc[x, 'Document ID']} - "
            f"{filtered_documents.loc[x, 'Document Name']}"
        ),
        key="rag_document_selector",
    )

    document = filtered_documents.loc[selected_index]

    # Reset RAG if the selected document changes

    current_document = document["Document ID"]

    if st.session_state.get("rag_document") != current_document:
        st.session_state.rag_ready = False

        st.session_state.rag_result = None

        st.session_state.chat_history = []

        st.session_state.rag_document = current_document

    st.divider()

    st.subheader("Process Document")

    st.write("")

    st.markdown("### Page Range")

    col1, col2 = st.columns(2)

    with col1:
        page_from = st.number_input(
            "From", min_value=1, value=1, step=1, key="rag_page_from"
        )

    with col2:
        page_to = st.number_input(
            "To", min_value=1, value=20, step=1, key="rag_page_to"
        )

    st.write("")

    if st.button("Process Document", type="primary", use_container_width=True):
        with st.spinner("Building RAG pipeline..."):
            try:
                rag.build_rag(document, page_from=page_from, page_to=page_to)

            except Exception as error:
                st.error(error)

                return

        st.session_state.rag_ready = True

        st.success("RAG pipeline ready.")

    if not st.session_state.rag_ready:
        return

    st.divider()

    st.subheader("Conversation")

    if len(st.session_state.chat_history) > 0:
        for i, chat in enumerate(st.session_state.chat_history, start=1):
            st.markdown(f"### 👤 Question {i}")

            st.info(chat["question"])

            st.markdown("### 🤖 Answer")

            st.markdown(chat["answer"])

            st.divider()

    st.divider()

    st.subheader(" Ask Question")

    question = st.text_area(
        "Question",
        height=120,
        placeholder="Ask a question about the selected document...",
        key="rag_Question",
    )

    if st.button("Ask Question", use_container_width=True):
        if not question.strip():
            st.warning("Please enter a question.")

            return

        with st.spinner("Generating answer..."):
            try:
                result = rag.ask_question(question)

            except Exception:
                st.code(traceback.format_exc())

                return

        st.session_state.rag_result = result

        st.session_state.chat_history.append(
            {"question": question, "answer": result["answer"]}
        )

        st.rerun()

    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        if st.button("🗑 Clear Chat"):
            st.session_state.chat_history = []

            st.session_state.rag_result = None

            st.rerun()

    chat_text = ""

    for i, chat in enumerate(st.session_state.chat_history, start=1):
        chat_text += f"Question {i}\n"

        chat_text += chat["question"]

        chat_text += "\n\n"

        chat_text += "Answer\n"

        chat_text += chat["answer"]

        chat_text += "\n\n"

        chat_text += "-" * 80

        chat_text += "\n\n"

    with col2:
        st.download_button(
            label="⬇ Download Conversation",
            data=chat_text,
            file_name="RAG_Conversation.txt",
            mime="text/plain",
        )

    if st.session_state.rag_result is not None:
        result = st.session_state.rag_result

        sources = result["sources"]

        st.subheader("Supporting Evidence")

        evidence = []

        for source in sources:
            evidence.append(
                {
                    "Page": source["page"],
                    "Chunks": ", ".join(map(str, source["chunks"])),
                }
            )

        st.dataframe(evidence, hide_index=True, use_container_width=True)

        st.divider()

        st.subheader("Performance")

        performance = result["performance"]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Retrieved Chunks", performance["retrieved_chunks"])

        with col2:
            st.metric("Retrieval Time (s)", performance["retrieval_time"])

        with col3:
            st.metric("Response Time (s)", performance["response_time"])
