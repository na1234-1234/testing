import streamlit as st
import subprocess

# --- 模擬呼叫 LLM 的函數 ---
def call_llm(code, error_log):
    # 這裡未來替換成呼叫 OpenAI 或 Gemini API 的代碼
    return f"💡 系統提示：程式發生錯誤。\n\n根據報錯，請檢查語法或邏輯：\n{error_log}"

# --- UI 介面 ---
st.title("🤖 極簡 AI 程式導師")

# 1. 學生入 CODE
student_code = st.text_area("請輸入 Python 程式碼：", height=200)

if st.button("執行並獲取 Feedback"):
    if student_code:
        # 將學生的 Code 寫入暫存檔
        with open("temp.py", "w") as f:
            f.write(student_code)
            
        # 2 & 3. 行個 MODEL (執行程式碼)
        result = subprocess.run(["python", "temp.py"], capture_output=True, text=True)
        
        # 4. RETURN FEEDBACK
        if result.returncode == 0:
            st.success(f"🎉 執行成功！\n輸出結果：\n{result.stdout}")
        else:
            # 如果出錯，將 Code 同 Error 放入 LLM，然後顯示 Hint
            hint = call_llm(student_code, result.stderr)
            st.error(hint)