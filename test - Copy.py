import streamlit as st
import subprocess
import os
import re
import json
import google.generativeai as genai
import requests

# ==========================================
# 1. 頁面與 UI 初始化設定
# ==========================================
st.set_page_config(page_title="AI 程式導師系統", layout="wide", page_icon="🎓")

# 側邊欄：設定 API Key
st.sidebar.title("⚙️ 系統設定")

api_key = "AQ.Ab8RN6JIotxu8M0MMtrYmTyJHegtqmvnMIZQP6SgIAsBSyMuaQ"
#st.sidebar.text_input("請輸入 Google Gemini API Key:", type="password")

st.sidebar.markdown("👉 [按此免費獲取 Gemini API Key](https://aistudio.google.com/)")

st.title("🎓 Verifier-in-the-Loop: 零幻覺 AI 程式導師")
st.markdown("本系統透過「影子代碼驗證」與「語法攔截」，確保 AI 導師只給出概念性提示 (Hints)，絕不直接提供代碼答案。")
st.markdown("---")

# ==========================================
# 2. 核心功能函數
# ==========================================
def run_python_code(code_string, filename="temp_student.py"):
    """執行 Python 代碼並回傳結果"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(code_string)
    
    try:
        # 設定 3 秒超時，防止學生寫死迴圈
        result = subprocess.run(["python", filename], capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            return True, result.stdout, ""
        else:
            return False, "", result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Timeout Error: 程式執行超過 3 秒，可能存在死迴圈 (Infinite Loop)。"
    finally:
        if os.path.exists(filename):
            os.remove(filename)

def contains_code_blocks(hint_text):
    """優化版 Parser：精準攔截真正的代碼，減少誤殺"""
    # 1. 攔截 Markdown 代碼區塊 (最常見的洩漏方式)
    if "```" in hint_text: 
        return True
        
    # 2. 攔截明顯的語法特徵 (放寬了 for 和 range，改為攔截括號和賦值)
    suspicious_patterns = [
        r"print\(",       # 攔截 print()
        r"def \w+\(",     # 攔截函數定義 def
        r"\[i\]",         # 攔截陣列取值 [i]
        r"=\s*\["         # 攔截陣列宣告 = [
    ]
    for pattern in suspicious_patterns:
        if re.search(pattern, hint_text):
            return True
            
    return False

def call_gemini_llm(student_code, error_log):
    """優化版 Prompt：嚴格要求純中文概念解釋"""
    
    prompt = f"""
        You are an expert programming tutor.

        Student Code: {student_code}

        Error Log: {error_log}


        CRITICAL RULES (Output valid JSON only):

        1. "shadow_code": Provide the FULL, CORRECTED, and RUNNABLE Python code. 
       - MUST include the original variable definitions
       - AND the corrected logic so the code executes without NameError.

        2. "hint": Follow this strict structure in Traditional Chinese:

        - 【錯誤定位】：明確指出哪個邏輯觀念出錯 (例如: 迴圈範圍超出列表大小)。

        - 【觀念解釋】：解釋觀念，但在關鍵名詞後括號標註英文術語。

        - 【生活舉例】：舉一個生活例子。


        STRICT HINT CONSTRAINTS:
    - ❌ ABSOLUTELY NO referencing the student's actual code.
    - ❌ Do NOT include 'scores', 'print', 'a', or any variable names from the code.
    - ❌ Do NOT include '=', '()', '[]' in your hint explanation.

        - ✅ Use ONLY pure natural language to describe concepts.
        """


    #genai.configure(api_key=api_key)
    #model = genai.GenerativeModel('gemini-2.5-flash-lite')
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "qwen2.5:3b",
        "prompt": prompt,
        "format": "json",
        "stream": False
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        raw_response = data.get('response', '')
        
        # 修正點 2：Ollama 透過 /api/generate 回傳的 response 通常已經是 JSON 字串
        # 如果 raw_response 是空的，代表模型未準備好
        if not raw_response:
            st.error("⚠️ AI 模型尚未準備好，請稍候重試。")
            return None
            
        st.write(f"DEBUG: 原始回應 -> {raw_response}")
        
        # 將字串解析為 Python 字典
        return json.loads(raw_response)
            
    except Exception as e:
        st.error(f"⚠️ 連接或解析失敗: {str(e)}")
        return None


   # response = model.generate_content(
   #     prompt,
   #     generation_config={"response_mime_type": "application/json"}
   # )
    
  #  cleaned_text = re.sub(r'```json\n|```', '', response.text).strip()
   # return json.loads(cleaned_text)

# ==========================================
# 3. 網頁版面設計 (雙欄位 UI)
# ==========================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 代碼輸入區")
    
    student_code = st.text_area("請輸入您的 Python 程式碼：", height=350)
    run_btn = st.button("▶️ 執行並診斷", type="primary", use_container_width=True)

with col2:
    st.subheader("🤖 系統診斷反饋")
    feedback_placeholder = st.container()

# ==========================================
# 4. 點擊按鈕後的主邏輯 (Verification Loop)
# ==========================================
if run_btn:
    if not api_key:
        st.error("⚠️ 請先在左側邊欄輸入 Gemini API Key！")
    elif not student_code.strip():
        st.warning("⚠️ 請先輸入程式碼！")
    else:
        with feedback_placeholder:
            # 步驟 1：執行學生原始代碼
            is_success, output, error_log = run_python_code(student_code, "temp_main.py")
            
            if is_success:
                st.success("🎉 **執行成功！沒有發現錯誤。**")
                st.info(f"**程式輸出：**\n\n{output}")
            else:
                # 步驟 2：進入 Verifier-in-the-Loop 閉環
                with st.status("🔍 系統診斷中，啟動影子驗證迴圈...", expanded=True) as status:
                    st.write("1. 捕捉到系統錯誤，正在呼叫 AI 導師...")
                    
                    max_retries = 3
                    final_hint = ""
                    # 呢個 for loop 就係你論文最核心嘅「Verification Loop (驗證閉環)」！
                    for attempt in range(1, max_retries + 1):
                        st.write(f"🔄 [嘗試 {attempt}/{max_retries}] 正在生成提示與影子代碼...")
                        
                        try:
                            # 呼叫 LLM
                            ai_response = call_gemini_llm(student_code, error_log)
                            if not ai_response: continue

                            hint = ai_response.get("hint", "")
                            shadow_code = ai_response.get("shadow_code", "")
                            
                            # Phase 3A: Parser 檢查
                            if contains_code_blocks(str(hint)):
                                feedback = "上一次的 hint 中包含了禁止的代碼符號（如括號、變數名、代碼塊），請改用純自然語言描述觀念。"
                                st.error(f"❌ Parser 攔截：{feedback}")
                                continue # 重新迴圈，下一次 AI 就會收到上面的 feedback
                                
                            # Phase 3B: Compiler 檢查
                            is_shadow_success, _, shadow_err = run_python_code(shadow_code, "temp_shadow.py")
                            if not is_shadow_success:
                                feedback = f"上一次產生的 shadow_code 執行失敗，錯誤訊息為: {shadow_err}。請確保影子代碼完全正確且能執行。"
                                st.error(f"❌ Compiler 攔截：{feedback}")
                                continue 
                                
                            # 成功！
                            st.write("✅ 影子驗證通過！")
                            final_hint = hint
                            break
                        except Exception as e:
                            feedback = f"系統發生錯誤: {str(e)}，請重新嘗試生成。"
                            continue
                            
                    status.update(label="診斷完成", state="complete", expanded=False)
                
                # 步驟 3：顯示最終結果
                if final_hint:
                    st.error("程式發生錯誤，請參考以下提示修改您的代碼：")
                    st.markdown(f"### 💡 導師概念提示\n**{final_hint}**")
                    with st.expander("查看原始系統報錯 (Advanced)"):
                        st.code(error_log, language="python")
                else:
                    st.error("❌ 系統為確保教學質素，已攔截不安全的 AI 提示。請尋求人類導師協助。")
                    with st.expander("查看原始系統報錯 (Advanced)"):
                        st.code(error_log, language="python")