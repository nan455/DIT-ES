from fastapi import FastAPI
from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings, OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from fastapi.responses import HTMLResponse

app = FastAPI()

# Load embeddings
embeddings = OllamaEmbeddings(model="nomic-embed-text")

# Load vector database
vectorstore = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embeddings
)

# Load LLM
# llm = OllamaLLM(model="deepseek-coder:1.3b-instruct-q4_0")
llm = OllamaLLM(model="qwen2.5:7b-instruct-q5_K_M")
# Create retriever
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# Simple prompt template
prompt = PromptTemplate.from_template(
"""
You are an internal code assistant.

IMPORTANT RULES:
- Answer ONLY using the provided context.
-generate a code for the answer 
- If the answer is present in the context, provide a concise and accurate answer.
- If the answer is present in the context, you MUST provide the relevant code snippet in markdown format, wrapped in triple backticks.
- If the answer is present in the context, you MUST provide a brief explanation of the code snippet.
- If the answer is present in the context, you MUST provide a step-by-step explanation of how the code works.
- If the answer is not present in the context, say:
  "The requested information is not found in the project code."
- Do NOT use external knowledge.
- Do NOT guess.

Context:
{context}

Question:
{question}

Answer strictly based on context:
"""
)
parser = StrOutputParser()

@app.get("/ask")
def ask(question: str):
    docs = retriever.invoke(question)
    context = "\n\n".join([doc.page_content for doc in docs])

    chain = prompt | llm | parser
    response = chain.invoke({
        "context": context,
        "question": question
    })

    return {"answer": response}
@app.get("/", response_class=HTMLResponse)
def home():
    return """
<!DOCTYPE html>
<html>
<head>
<title>Internal Code Assistant</title>

<link href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>

<style>
body {
    margin: 0;
    font-family: Arial, sans-serif;
    background: #0f172a;
    color: white;
}

.chat-container {
    max-width: 900px;
    margin: auto;
    height: 100vh;
    display: flex;
    flex-direction: column;
}

.chat-box {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
}

.message {
    margin-bottom: 20px;
    padding: 14px;
    border-radius: 10px;
    max-width: 80%;
    white-space: pre-wrap;
}

.user {
    background: #2563eb;
    align-self: flex-end;
}

.bot {
    background: #1e293b;
    align-self: flex-start;
}

.bot pre {
    background: #0f172a;
    padding: 10px;
    border-radius: 6px;
    overflow-x: auto;
}

.input-area {
    display: flex;
    padding: 15px;
    background: #1e293b;
}

input {
    flex: 1;
    padding: 12px;
    border-radius: 6px;
    border: none;
    outline: none;
}

button {
    margin-left: 10px;
    padding: 12px 18px;
    border: none;
    border-radius: 6px;
    background: #22c55e;
    color: white;
    cursor: pointer;
}

button:hover {
    background: #16a34a;
}
</style>
</head>
<body>

<div class="chat-container">
    <div class="chat-box" id="chatBox"></div>

    <div class="input-area">
        <input type="text" id="question" placeholder="Ask about your code..." onkeypress="handleKey(event)">
        <button onclick="askAI()">Send</button>
    </div>
</div>

<script>
const chatBox = document.getElementById("chatBox");

function addMessage(text, type) {
    const msg = document.createElement("div");
    msg.classList.add("message", type);

    if(type === "bot") {
        msg.innerHTML = formatResponse(text);
    } else {
        msg.innerText = text;
    }

    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;

    document.querySelectorAll('pre code').forEach((block) => {
        hljs.highlightElement(block);
    });
}

function formatResponse(text) {
    // Convert triple backticks to code blocks
    return text
        .replace(/```(.*?)```/gs, function(match, p1) {
            return "<pre><code>" + p1.trim() + "</code></pre>";
        })
        .replace(/\\n/g, "<br>");
}

function handleKey(e) {
    if (e.key === "Enter") {
        askAI();
    }
}

async function askAI() {
    const input = document.getElementById("question");
    const question = input.value.trim();
    if (!question) return;

    addMessage(question, "user");
    input.value = "";

    const loadingMsg = document.createElement("div");
    loadingMsg.classList.add("message", "bot");
    loadingMsg.innerText = "Thinking...";
    chatBox.appendChild(loadingMsg);
    chatBox.scrollTop = chatBox.scrollHeight;

    const res = await fetch(`/ask?question=${encodeURIComponent(question)}`);
    const data = await res.json();

    loadingMsg.remove();
    addMessage(data.answer, "bot");
}
</script>

</body>
</html>
    """



    
    