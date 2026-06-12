import streamlit as st
import subprocess

# 1. 將網頁設定為「寬屏模式」
st.set_page_config(layout="wide") 

st.title("🤖 Verifier-in-the-loop AI 導師")

# 2. 將畫面斬開兩邊：左邊 col1，右邊 col2
col1, col2 = st.columns(2)

# ================= 左邊：入 CODE 區 =================
with col1:
    st.subheader("📝 代碼輸入區")
    # 預設畀少少有 Bug 嘅 Code 佢
    default_code = "for i in range(5)\n    print(i)"
    student_code = st.text_area("請輸入 Python 程式碼：", value=default_code, height=300)
    
    # 執行按鈕
    run_btn = st.button("▶️ 執行並診斷")

# ================= 右邊：FEEDBACK 區 =================
with col2:
    st.subheader("🤖 系統診斷反饋")
    
    # 當學生撳咗執行按鈕先會有反應
    if run_btn:
        if student_code:
            with open("temp.py", "w") as f:
                f.write(student_code)
                
            # 行 Compiler
            result = subprocess.run(["python", "temp.py"], capture_output=True, text=True)
            
            # 出 Feedback
            if result.returncode == 0:
                st.success(f"🎉 執行成功！\n\n**輸出：**\n{result.stdout}")
            else:
                # 呢度未來換成 LLM
                mock_hint = f"💡 **系統提示：** 程式發生錯誤。\n\n請檢查迴圈的語法，是否漏了特定的標點符號？\n\n---\n**原始報錯：**\n{result.stderr}"
                st.error(mock_hint)
        else:
            st.warning("請先輸入代碼！")