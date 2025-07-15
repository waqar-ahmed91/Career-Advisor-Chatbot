import streamlit as st
import base64
import requests
import re
st.set_page_config(page_title="Career Advisor Bot", layout="wide")

st.title("🎯 Career Advisor Chatbot")
st.markdown("Get personalized guidance based on your profile and industry knowledge. Upload your resume and start chatting.")

# --- Sidebar ---
st.sidebar.header("Upload Your Resume")
uploaded_file = st.sidebar.file_uploader("Choose a PDF or DOCX file", type=["pdf", "docx"])
use_local_llm = st.sidebar.checkbox("Use Local LLM (e.g. QWEN, LLaMA3)", value=True)

if uploaded_file:
    resume_bytes = uploaded_file.read()
    resume_b64 = base64.b64encode(resume_bytes).decode("utf-8")
    st.sidebar.success("Resume uploaded successfully ✅")
else:
    resume_b64 = None

def strip_excessive_bold(text: str) -> str:
    return re.sub(r"\*\*(.{80,}?)\*\*", r"\1", text)

def format_markdown(text: str) -> str:
    import re

    text = re.sub(r'#{1,6}', '###', text)
    text = re.sub(r'(?<!\n)(#{2,6} )', r'\n\n\1', text)
    text = re.sub(r'^(\d+(\.\d+)?)(?=\w)', r'\1 ', text)
    text = re.sub(r'\n?\*([^\n:*]+):\*', r'\n\n### \1\n', text)
    text = re.sub(r'(?<=\d)\.(?=[A-Z])', '. ', text)
    text = re.sub(r'(?<!\n)(?=\d+\.)', r'\n\n', text)
    text = re.sub(r'(?<!\n)- ', r'\n- ', text)
    lines = text.split('\n')
    fixed_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()

        if i > 0:
            prev_line = lines[i - 1].strip()
            if (re.match(r'^\d+\.', prev_line) or prev_line.endswith(':')):
                if re.match(r'^([\-◦○•‣▪️➤▶️>]+)', stripped):
                    line = '    ' + stripped
        fixed_lines.append(line)

    text = '\n'.join(fixed_lines)

    text = re.sub(r'\n\s*[-◦○o•‣]+[ \t]*$', '', text)

    text = re.sub(r'\n\d+\.\s*(?=\n|$)', '', text)

    text = re.sub(r'\n{3,}', '\n\n', text)

    text = re.sub(r'\n\d+\.\s*(?=\Z)', '', text)
    text = re.sub(r'(\d(?:\.\d)?/5)([A-Z])', r'\1 \2', text)

    return text.strip()



def strip_code_fencing(md: str) -> str:
    return re.sub(r"```(?:markdown)?\n?", "", md).replace("```", "").strip()

def stream_chat_response(payload):
    with requests.post("http://localhost:8000/chat", json=payload, stream=True) as r:
        for line in r.iter_lines(decode_unicode=True):
            if line:
                yield line
def get_clean_history(messages):
    cleaned = []
    for m in messages:
        content = m["content"]
        if m["role"] == "assistant":
            content = content.split("[[SPONSOR_BLOCK_START]]")[0].strip()
        cleaned.append({"role": m["role"], "content": content})
    return cleaned[-5:]


if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hi! 👋 Upload your resume and ask any career-related question."}]

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask me anything about your career..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        stream_container = st.empty()
        full_response = ""

        try:
            payload = {
                "query": prompt,
                "resume": resume_b64,
                "use_local": use_local_llm,
                "history": get_clean_history(st.session_state.messages)
            }

            for token in stream_chat_response(payload):
                full_response += token
                if len(full_response) % 10 == 0 or token.endswith(('.', '\n')):
                    clean_chunk = full_response.replace("  ", "\n\n").replace("\\n", "\n")
                    clean_chunk = strip_excessive_bold(clean_chunk)
                    stream_container.markdown(format_markdown(clean_chunk) + "▌")

            final_response = strip_code_fencing(full_response)
            clean_response = format_markdown(final_response)
            chunks = clean_response.split("[[SPONSOR_BLOCK_START]]")
            main_response = chunks[0].strip()
            sponsor_block = chunks[1].strip() if len(chunks) > 1 else ""

            stream_container.markdown(format_markdown(main_response))

            if sponsor_block and sponsor_block not in main_response:
                st.markdown("---")
                st.markdown(
                    f"""
                    <div style="
                        font-size: 0.85rem;
                        color: #444;
                        background-color: #f9f9f9;
                        border-left: 4px solid #ccc;
                        padding: 0.75rem 1rem;
                        border-radius: 6px;
                        margin-top: 0.1rem;
                    ">
                        {sponsor_block}
                    </div>
                    """,
                    unsafe_allow_html=True
                )

            st.session_state.messages.append({
                "role": "assistant",
                "content": main_response
            })

        except Exception as e:
            stream_container.error(f"❌ Streaming failed: {e}")


        # else:
        #     stream_container.markdown(full_response)
        #     st.session_state.messages.append({"role": "assistant", "content": full_response})
