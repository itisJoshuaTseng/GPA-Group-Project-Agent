import streamlit as st
import time
import datetime
# REMOVED: import graphviz (Fixes Issue #15)
import re
from google_utils import get_google_service, create_doc_with_content, create_slides_presentation, share_file_permissions, send_gmail
from llm_helper import extract_text_from_pdf, generate_project_plan

# --- 頁面設定 ---
st.set_page_config(page_title="Course Agent", page_icon="🤖", layout="wide")

# --- 狀態圖繪製 ---
def draw_dag():
    """
    Returns a Graphviz DOT string directly.
    This avoids the dependency on the 'graphviz' python library and system binaries.
    """
    return """
    digraph {
        rankdir="LR";
        
        A [label="Start", shape="oval"];
        B [label="LLM Analysis", shape="box", style="filled", fillcolor="lightblue"];
        C1 [label="Create Doc", shape="box", style="filled", fillcolor="lightyellow"];
        C2 [label="Create Slide", shape="box", style="filled", fillcolor="lightyellow"];
        D [label="Set Permissions", shape="box", style="filled", fillcolor="lightyellow"];
        E [label="Send Email", shape="box", style="filled", fillcolor="lightyellow"];
        F [label="End", shape="oval", style="filled", fillcolor="lightgreen"];

        A -> B;
        B -> C1;
        B -> C2;
        C1 -> D;
        C2 -> D;
        D -> E;
        E -> F;
    }
    """

# --- 主程式 ---
def main():
    st.title("🎓 GPA (Group Project Agent)")
    st.markdown("### Intelligent Agent for Group Projects")
    
    # 左側邊欄
    with st.sidebar:
        st.header("⚙️ 系統設定")
        st.info("請先登入 Google 帳號以啟用 Agent 工具")
        
        if 'services' not in st.session_state:
            st.session_state.services = None

        # 🟢 Authentication Check
        # If secrets are configured or token exists, we might already be logged in.
        # But for this UI, we keep the manual button or check status.
        if st.button("🔑 登入 Google"):
            try:
                # get_google_service now handles the complexity internally
                gmail, drive, docs, slides = get_google_service()
                if gmail:
                    st.session_state.services = (gmail, drive, docs, slides)
                    st.success("登入成功！")
            except Exception as e:
                st.error(f"登入失敗: {e}")
        
        if st.session_state.services:
            st.success("✅ Google 服務已連線")
        
        st.divider()
        st.markdown("**System Logic (DAG)**")
        
        # Streamlit handles strings natively without requiring the system binary
        st.graphviz_chart(draw_dag())

    # 主畫面
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1️⃣ 輸入專案資訊")
        with st.form("project_input"):
            course_name = st.text_input("課程名稱", "計算理論")
            raw_ids = st.text_area("組員學號或 Email (用逗號分隔)", "f74122030, joshuatseng0233@gmail.com")
            uploaded_file = st.file_uploader("上傳作業說明 (PDF)", type="pdf")
            default_deadline = datetime.date.today() + datetime.timedelta(days=14)
            deadline = st.date_input("📅 報告截止日期", default_deadline)
            
            st.write("📄 **選擇產出格式 (至少選一項)**")
            use_docs = st.checkbox("Google Docs (企劃書)", value=True)
            use_slides = st.checkbox("Google Slides (簡報)", value=False)
            
            submitted = st.form_submit_button("🚀 啟動 Agent")

    with col2:
        st.subheader("2️⃣ Agent 執行日誌")
        log_container = st.container(height=400)

    # --- 執行邏輯 ---
    if submitted:
        if not st.session_state.services:
            st.error("請先在左側欄登入 Google！")
            st.stop()
        if not uploaded_file:
            st.error("請上傳 PDF 作業說明檔！")
            st.stop()
        if not use_docs and not use_slides:
            st.error("⚠️ 請至少選擇一種產出格式 (Docs 或 Slides)！")
            st.stop()

        # 取得服務物件
        gmail_svc, drive_svc, docs_svc, slides_svc = st.session_state.services
        
        # 🟢 【修正點 1：過濾無效輸入】
        student_ids_list = [s.strip() for s in raw_ids.split(',') if s.strip()]
        emails = [f"{sid}@gs.ncku.edu.tw" if "@" not in sid else sid for sid in student_ids_list]
        
        today_str = str(datetime.date.today())
        deadline_str = str(deadline)
        
        # 初始化成功旗標
        is_success = True

        # --- 1. 讀取 PDF ---
        with log_container:
            st.write("📂 讀取 PDF 中...")
            pdf_text = extract_text_from_pdf(uploaded_file)
            if not pdf_text:
                st.error("❌ 無法讀取 PDF 內容")
                st.stop()
            st.success(f"✅ PDF 讀取完成 ({len(pdf_text)} 字)")

        doc_url = None
        slide_url = None

        # --- 2. 處理 Google Docs ---
        if use_docs:
            with log_container:
                st.info("📝 正在處理 Google Docs 任務...")
                with st.spinner("🤖 AI 正在撰寫企劃書..."):
                    plan_docs = generate_project_plan(course_name, raw_ids, pdf_text, today_str, deadline_str, "Docs")
                
                if plan_docs.startswith("❌"):
                    st.error(f"Docs 生成失敗: {plan_docs}")
                    is_success = False
                else:
                    doc_title = f"[{course_name}] 期末報告企劃書"
                    try:
                        doc_id, doc_url = create_doc_with_content(docs_svc, drive_svc, doc_title, plan_docs)
                        if doc_url:
                            st.success(f"✅ 企劃書建立成功: [點擊開啟]({doc_url})")
                            share_file_permissions(drive_svc, doc_id, emails)
                        else:
                            st.error("❌ 企劃書建立失敗 (API 回傳空值)")
                            is_success = False
                    except Exception as e:
                        st.error(f"❌ 企劃書建立過程發生錯誤: {e}")
                        is_success = False

        # --- 3. 處理 Google Slides ---
        if use_slides:
            with log_container:
                st.info("📊 正在處理 Google Slides 任務...")
                with st.spinner("🤖 AI 正在規劃簡報架構..."):
                    plan_slides = generate_project_plan(course_name, raw_ids, pdf_text, today_str, deadline_str, "Slides")
                
                if plan_slides.startswith("❌"):
                    st.error(f"Slides 生成失敗: {plan_slides}")
                    is_success = False
                else:
                    slide_title = f"[{course_name}] 期末報告簡報"
                    try:
                        slide_id, slide_url = create_slides_presentation(slides_svc, drive_svc, slide_title, plan_slides)
                        
                        if slide_url:
                            st.success(f"✅ 簡報建立成功: [點擊開啟]({slide_url})")
                            share_file_permissions(drive_svc, slide_id, emails)
                        else:
                            st.error("❌ 簡報建立失敗 (JSON 解析錯誤或 API 權限問題)")
                            is_success = False
                    except Exception as e:
                        st.error(f"❌ 簡報建立過程發生錯誤: {e}")
                        is_success = False

        # --- 4. 寄信通知 ---
        with log_container:
            # 檢查是否全部成功 (煞車機制)
            if not is_success:
                st.error("⛔️ 由於部分檔案生成失敗，系統已終止，不會發送 Email 以免誤導組員。")
                st.stop()

            st.write("📧 正在寄信通知組員...")
            subject = f"[{course_name}] 期末報告分工通知 (AI Agent)"
            
            links_text = ""
            if doc_url:
                links_text += f"📄 企劃書連結：{doc_url}\n"
            if slide_url:
                links_text += f"📊 簡報連結：{slide_url}\n"

            email_body = f"""
            各位同學好：
            
            這是一封由 AI Agent 自動發送的通知。
            針對 {course_name} 的期末報告，我已經根據作業 PDF 產生了初步架構。
            
            請大家到以下連結開始協作：
            {links_text}
            
            祝 報告順利！
            """
            
            # 🟢 【修正點 2：美化錯誤訊息顯示】
            try:
                success_emails, failed_emails = send_gmail(gmail_svc, emails, subject, email_body)
                
                # 1. 顯示成功名單 (綠色)
                if success_emails:
                    st.success(f"✅ Email 發送成功 ({len(success_emails)} 人)：\n" + ", ".join(success_emails))
                
                # 2. 顯示失敗名單 (紅色 + 轉換為人話)
                if failed_emails:
                    st.error(f"⚠️ 發送失敗 ({len(failed_emails)} 人)：")
                    for email, error_msg in failed_emails:
                        # 錯誤翻譯機
                        reason = "未知錯誤"
                        if "Invalid To header" in error_msg:
                            reason = "Email 格式錯誤 (可能缺少使用者名稱)"
                        elif "Address not found" in error_msg:
                            reason = "找不到此 Email 地址 (查無此人)"
                        elif "The specified emailAddress is invalid" in error_msg:
                            reason = "Email 地址無效"
                        else:
                            # 嘗試只擷取 Google API 回傳的具體原因
                            if "returned" in error_msg:
                                match = re.search(r'returned "(.*?)"', error_msg)
                                if match:
                                    reason = match.group(1)
                                else:
                                    reason = "系統連線被拒"
                            else:
                                reason = "系統連線錯誤"

                        st.write(f"❌ **{email}** → {reason}")
                
                # 3. 最終慶祝 (只有在至少有一人成功時才顯示)
                if success_emails:
                    st.balloons()
                    st.success("🏆 所有流程執行完畢！")

            except Exception as e:
                 st.error(f"⚠️ 寄信功能發生系統錯誤: {e}")

if __name__ == "__main__":
    main()
