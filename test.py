import streamlit as st
import subprocess
import os
import re
import json
import google.generativeai as genai

# ==========================================
# 1. 頁面與 UI 初始化設定
# ==========================================
st.set_page_config(page_title="AI 程式導師系統", layout="wide", page_icon="🎓")

# 側邊欄：設定 API Key
st.sidebar.title("⚙️ 系統設定")
api_key = st.sidebar.text_input("請輸入 Google Gemini API Key:", type="password")
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
    """Parser: 檢查提示文字是否違規包含代碼"""
    if "```" in hint_text: 
        return True
    # 檢查常見的 Python 語法關鍵字
    suspicious_patterns = [r"print\(", r"def ", r"while ", r"for ", r"range\("]
    for pattern in suspicious_patterns:
        if re.search(pattern, hint_text):
            return True
    return False

def call_gemini_llm(student_code, error_log):
    """呼叫 Gemini 模型並強制回傳 JSON"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are an expert programming tutor for novices.
    The student's Python code has failed.
    
    Student Code:
    {student_code}
    
    Error Log:
    {error_log}
    
    CRITICAL RULES:
    1. Output valid JSON only. Do not wrap in markdown tags.
    2. "shadow_code": Provide the fully corrected, runnable Python code.
    3. "hint": Explain the concept behind the error in Traditional Chinese. You MUST NOT include any code blocks, direct solutions, variable names, or exact syntax in this hint.
    """
    
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"}
    )
    
    # 清理可能出現的 markdown 標記並解析 JSON
    cleaned_text = re.sub(r'```json\n|```', '', response.text).strip()
    return json.loads(cleaned_text)

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
                    
                    for attempt in range(1, max_retries + 1):
                        st.write(f"🔄 [嘗試 {attempt}/{maxRetries}] 正在生成提示與影子代碼...")
                        
                        try:
                            # 呼叫 LLM
                            ai_response = call_gemini_llm(student_code, error_log)
                            hint = ai_response.get("hint", "")
                            shadow_code = ai_response.get("shadow_code", "")
                            
                            # Parser 攔截關卡
                            st.write("🛡️ 執行 Parser 檢查：驗證提示是否違規包含代碼...")
                            if contains_code_blocks(hint):
                                st.write("❌ Parser 攔截：AI 違規給出代碼答案，要求重寫。")
                                continue # 重新執行迴圈
                                
                            # Compiler 驗證關卡
                            st.write("⚙️ 執行 Compiler 檢查：在沙盒中驗證影子代碼...")
                            is_shadow_success, _, shadow_err = run_python_code(shadow_code, "temp_shadow.py")
                            
                            if not is_shadow_success:
                                st.write("❌ Compiler 攔截：AI 產生的修復代碼執行失敗 (幻覺)，要求重寫。")
                                continue # 重新執行迴圈
                                
                            # 順利通過所有驗證！
                            st.write("✅ 影子驗證通過！提示安全可用。")
                            final_hint = hint
                            break 
                            
                        except Exception as e:
                            st.write(f"⚠️ 發生例外錯誤：{str(e)}")
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