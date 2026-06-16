import streamlit as st
import google.generativeai as genai
import pandas as pd
import plotly.express as px
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# --- CẤU HÌNH ---
load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash') # Chú ý: 'gemini-1.5-flash' là model ổn định hiện tại

st.set_page_config(page_title="IELTS Master Hub", layout="wide")

# --- HÀM QUẢN LÝ DB NGƯỜI DÙNG ---
def load_db():
    if not os.path.exists("database.json"): return {}
    with open("database.json", "r") as f: return json.load(f)

def save_db(db):
    with open("database.json", "w") as f: json.dump(db, f)

# --- KHỞI TẠO SESSION ---
if "logged_in" not in st.session_state: st.session_state.logged_in = False
if "username" not in st.session_state: st.session_state.username = None

# --- SIDEBAR: ĐĂNG NHẬP & THÔNG TIN ---
with st.sidebar:
    if not st.session_state.logged_in:
        st.header("👤 Đăng nhập")
        user = st.text_input("Tên tài khoản")
        pwd = st.text_input("Mật khẩu", type="password")
        if st.button("Đăng nhập"):
            db = load_db()
            if user in db and db[user]["password"] == pwd:
                st.session_state.logged_in = True
                st.session_state.username = user
                st.rerun()
            else: st.error("Sai tài khoản hoặc mật khẩu!")
        if st.button("Đăng ký"):
            db = load_db()
            if user not in db:
                db[user] = {"password": pwd, "history": [], "profile": {"age": 20, "free_time": 2, "target": 7.0}}
                save_db(db)
                st.success("Đăng ký thành công!")
            else: st.error("Tài khoản đã tồn tại!")
    else:
        st.write(f"Chào {st.session_state.username}!")
        if st.button("Đăng xuất"):
            st.session_state.logged_in = False
            st.rerun()
        st.divider()
        st.header("👤 Thông tin cá nhân")
        age = st.number_input("Tuổi:", 10, 80, 20)
        free_time = st.slider("Giờ rảnh/ngày:", 1, 12, 2)
        target = st.number_input("Mục tiêu Overall:", 0.0, 9.0, 7.0, 0.5)
        exam_date = st.date_input("Ngày thi:", datetime.today())

st.title("🎓 IELTS Master Hub")

if not st.session_state.logged_in:
    st.info("Vui lòng đăng nhập để bắt đầu hành trình luyện thi!")
    st.stop()

# --- TABS ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🎯 Lộ trình", "📝 Chấm bài", "📅 Luyện đề"])

# --- TAB 1: DASHBOARD ---
with tab1:
    db = load_db()
    history = db[st.session_state.username]["history"]
    if history:
        df = pd.DataFrame(history)
        col_l, col_r = st.columns(2)
        with col_l:
            fig_pie = px.pie(df, values='score', names='skill', title='Tỷ trọng Band')
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_r:
            fig_line = px.line(df, x='date', y='score', color='skill', markers=True, title='Tiến độ Band')
            fig_line.update_yaxes(range=[0, 9])
            st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu, hãy sang tab 'Luyện đề'!")

# --- TAB 2: LỘ TRÌNH AI ---
# --- TAB 2: LỘ TRÌNH AI (Đã sửa logic) ---
with tab2:
    st.subheader("Lộ trình học cá nhân hóa")
    if st.button("Tạo lộ trình mới"):
        # 1. Lấy dữ liệu từ database và sidebar
        db = load_db()
        user_data = db[st.session_state.username]
        history_df = pd.DataFrame(user_data["history"])
        
        if history_df.empty:
            st.error("Bạn chưa có dữ liệu lịch sử luyện đề!")
        else:
            # 2. Tính toán các chỉ số
            avg_scores = history_df.groupby('skill')['score'].mean()
            current_overall = avg_scores.mean()
            
            # Tính số ngày còn lại chính xác
            today = datetime.today().date()
            exam_date_val = exam_date # Lấy từ sidebar
            days_left = (exam_date_val - today).days
            
            # 3. Prompt chi tiết gửi cho AI
            prompt = f"""
            Bạn là chuyên gia tư vấn IELTS cấp cao.
            Thông tin học viên:
            - Tên: {st.session_state.username}
            - Điểm trung bình hiện tại: {avg_scores.to_dict()}
            - Overall hiện tại: {current_overall:.1f}
            - Mục tiêu Overall: {target}
            - Thời gian còn lại: {days_left} ngày
            - Thời gian rảnh mỗi ngày: {free_time} giờ
            
            Yêu cầu nhiệm vụ:
            1. Dựa trên số ngày còn lại ({days_left} ngày), hãy phân bổ khối lượng bài tập hợp lý.
            2. So sánh điểm hiện tại với mục tiêu {target} để tìm ra kỹ năng cần ưu tiên nhất.
            3. Lập lộ trình học chi tiết chia theo từng tuần (Week 1, Week 2...).
            4. Phải đưa ra lời khuyên cụ thể cho bài thi trong {days_left} ngày tới.
            """
            
            with st.spinner("AI đang tính toán lộ trình dựa trên ngày thi của bạn..."):
                res = model.generate_content(prompt)
                st.markdown("---")
                st.markdown(res.text)

# --- TAB 3: CHẤM BÀI ---
with tab3:
    st.subheader("📝 Chấm bài IELTS AI")

    task = st.selectbox("Loại bài", ["Writing Task 1", "Writing Task 2", "Speaking Script"])
    content = st.text_area("Dán nội dung:", height=250)

    if st.button("Chấm điểm"):
        if not content.strip():
            st.warning("Chưa có nội dung bài làm!")
            st.stop()

        prompt = f"""
        You are an expert IELTS examiner.

        Task: {task}

        Evaluate the student answer strictly based on IELTS criteria:
        - Task Achievement / Task Response
        - Coherence and Cohesion
        - Lexical Resource
        - Grammatical Range and Accuracy

        Return ONLY valid JSON.
        No markdown.
        No explanation outside JSON.

        JSON format:
        {{
            "TA_TR": number,
            "CC": number,
            "LR": number,
            "GRA": number,
            "overall": number,
            "feedback": "string",
            "improvement": "string"
        }}

        Student answer:
        {content}
        """

        with st.spinner("AI đang chấm bài..."):
            res = model.generate_content(prompt)
            raw = res.text.strip()

            # ---- CLEAN OUTPUT ----
            if "```" in raw:
                raw = raw.replace("```json", "").replace("```", "").strip()

            try:
                result = json.loads(raw)

                st.success("Đã chấm xong!")

                # ---- DISPLAY SCORE ----
                st.subheader("📊 Band Score")

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("TA/TR", result.get("TA_TR", 0))
                col2.metric("CC", result.get("CC", 0))
                col3.metric("LR", result.get("LR", 0))
                col4.metric("GRA", result.get("GRA", 0))

                st.metric("Overall", result.get("overall", 0))

                st.divider()

                # ---- FEEDBACK ----
                st.subheader("💬 Feedback")
                st.write(result.get("feedback", ""))

                st.subheader("🔧 Cần cải thiện")
                st.write(result.get("improvement", ""))

                # ---- SAVE TO DB ----
                db = load_db()

                db[st.session_state.username]["history"].append({
                    "date": str(datetime.today().date()),
                    "skill": "Writing" if "Writing" in task else "Speaking",
                    "score": float(result.get("overall", 0))
                })

                save_db(db)

            except Exception:
                st.error("❌ AI trả về sai định dạng JSON")
                st.code(raw)

# --- TAB 4: LUYỆN ĐỀ ---
with tab4:
    with st.form("input_form"):
        col1, col2 = st.columns(2)
        with col1:
            date_input = st.date_input("Ngày")
            skill = st.selectbox("Kỹ năng", ["Listening", "Reading", "Writing", "Speaking"])
        with col2:
            score = st.slider("Band điểm:", 0.0, 9.0, 6.0, 0.5)
        if st.form_submit_button("Lưu Band điểm"):
            db = load_db()
            db[st.session_state.username]["history"].append({"date": str(date_input), "skill": skill, "score": score})
            save_db(db)
            st.success("Đã lưu!")