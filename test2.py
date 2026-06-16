import streamlit as st
import streamlit.components.v1 as components

st.title("🎓 瀏覽器原生 AI 導師 (免 API Key)")

# 這段 HTML 會直接在瀏覽器呼叫 WebLLM
webllm_html = """
<script type="module">
  import { CreateWebWorkerMLCEngine } from "https://esm.run/@mlc-ai/web-llm";

  async function main() {
    const engine = await CreateWebWorkerMLCEngine(
      new Worker("worker.js", { type: "module" }),
      "Llama-3-8B-Instruct-v1" // 自動下載模型
    );
    const reply = await engine.chat.completions.create({
      messages: [{ role: "user", content: "教我費氏數列的概念" }]
    });
    document.body.innerHTML += `<p>${reply.choices[0].message.content}</p>`;
  }
  main();
</script>
"""

components.html(webllm_html, height=600)