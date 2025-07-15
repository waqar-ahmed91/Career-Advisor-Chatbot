# 💼 Career Advisor Chatbot

An AI-powered career guidance assistant that helps job seekers get personalized advice based on their **resume**, **conversation history**, and a curated **knowledge base**. The bot uses a combination of **vector search (RAG)** and **LLM-based responses** (OpenAI or Hugging Face) to deliver high-quality, actionable insights for career advancement.

---

## 🚀 Features

- ✅ Upload your **resume/CV** for personalized feedback
- ✅ Ask career-related questions (e.g., interviews, resume, learning path)
- ✅ Leverages a **private knowledge base** (PDF, .txt, .md) for context
- ✅ Integrates **sponsor/ad referrals** based on user profile
- ✅ Supports **OpenAI**, **local LLMs**, or **Hugging Face models**
- ✅ Real-time **streaming responses** with Markdown formatting

---

## 🧠 Tech Stack

- **Frontend**: [Streamlit](https://streamlit.io/)
- **Backend**: Python, FastAPI (optional)
- **LLMs**: OpenAI (`gpt-4o`, `gpt-3.5` etc..) / Hugging Face models / Local LLM
- **Embeddings + RAG**: `sentence-transformers`, `ChromaDB`
- **Document Parsing**: `PyPDF2`, `.txt`, `.md` loader
- **Streaming & Formatting**: Markdown rendering, sponsor insertion, chunked UI updates

---

## 🗂 Folder Structure

```
career-chatbot/
├── app.py                # Main Streamlit app
├── backend/              # Sponsor matching, LLM querying
├── knowledge_base/       # Markdown, PDF, and text files for RAG
├── chroma_db/            # Vector DB (auto-generated)
├── requirements.txt
└── README.md

```

## 💡 Sponsor Tips Logic

This chatbot optionally appends sponsored advice based on your resume and query intent. Sponsors are configured in backend/sponsors.json and are matched using simple keyword-based logic.

```
Example Output:

💡 Sponsored Tip: Based on your background, check out Advanced Data Science Career Track to take your skills to the next level.
```

## ✨ Roadmap

- [x] Resume-based personalization
- [x] RAG-enabled answers
- [x] Streaming support (OpenAI + local)
- [x] Sponsor matching
- [ ] Gradio version
- [ ] Multilingual support

## 📄 License

This project is licensed under the MIT License.

## 🤝 Contributions

Feel free to open an issue or submit a PR. Let’s improve career guidance with AI!
