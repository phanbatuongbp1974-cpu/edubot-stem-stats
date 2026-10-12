import streamlit as st
from google import genai
from google.genai import types
from PIL import Image
import tempfile
import os
import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# =====================================================================
# 1. CẤU HÌNH GIAO DIỆN WEB & CSS
# =====================================================================
st.set_page_config(page_title="EduBot STEM & Statistics - THCS", page_icon="🎓", layout="wide")

st.markdown("""
<style>
    .stChatMessage { border-radius: 16px; padding: 16px; margin-bottom: 14px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); border: 1px solid rgba(128, 128, 128, 0.2); }
    .stButton>button { border-radius: 12px; font-weight: 600; width: 100%; border: 1px solid rgba(128, 128, 128, 0.3); transition: all 0.2s ease; padding: 10px 15px; }
    .stButton>button:hover { border-color: #2563eb; color: #2563eb !important; box-shadow: 0 4px 12px rgba(37, 99, 235, 0.15); transform: translateY(-1px); }
    .metric-card { border: 1px solid rgba(128, 128, 128, 0.2); padding: 16px; border-radius: 16px; text-align: center; }
    .metric-val { font-size: 28px; font-weight: 800; color: #2563eb; }
    .metric-lbl { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; opacity: 0.8; }
    .analytics-box { border-left: 5px solid #2563eb; border: 1px solid rgba(128, 128, 128, 0.2); padding: 20px; border-radius: 4px 16px 16px 4px; margin-bottom: 15px; }
    .countdown-card { background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white !important; padding: 24px; border-radius: 16px; text-align: center; margin-bottom: 20px; }
    .countdown-card h2 { color: white !important; margin: 0; font-weight: 800;}
    .countdown-card p { color: #bfdbfe !important; margin-top: 8px; font-size: 14px;}
    h1, h2, h3, h4 { font-weight: 700; }
</style>
""", unsafe_allow_html=True)

MODEL_NAME = "gemini-3.8-flash"

# =====================================================================
# 2. HỆ THỐNG 20 API KEY XOAY VÒNG CHẠY NGẦM
# =====================================================================
if "key_index" not in st.session_state:
    st.session_state.key_index = 0

try:
    API_KEYS_POOL = [
        st.secrets.get(f"GEMINI_API_KEY_{i}", "") for i in range(1, 21)
    ]
    API_KEYS_POOL = [k for k in API_KEYS_POOL if k]
except Exception:
    API_KEYS_POOL = []

def get_active_client():
    if not API_KEYS_POOL:
        return None
    current_key = API_KEYS_POOL[st.session_state.key_index % len(API_KEYS_POOL)]
    return genai.Client(api_key=current_key)

if "genai_client" not in st.session_state:
    st.session_state.genai_client = get_active_client()

def rotate_to_next_key():
    if not API_KEYS_POOL:
        return
    st.session_state.key_index = (st.session_state.key_index + 1) % len(API_KEYS_POOL)
    st.session_state.genai_client = get_active_client()
    if "chat_session" in st.session_state:
        st.session_state.chat_session = st.session_state.genai_client.chats.create(
            model=MODEL_NAME,
            config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.2)
        )

def safe_generate_content(contents, config=None, model=MODEL_NAME):
    for _ in range(max(1, len(API_KEYS_POOL))):
        try:
            curr_client = st.session_state.genai_client
            if not curr_client:
                raise Exception("Thiếu API Key.")
            if config:
                return curr_client.models.generate_content(model=model, contents=contents, config=config)
            else:
                return curr_client.models.generate_content(model=model, contents=contents)
        except Exception as e:
            if any(c in str(e) for c in ["429", "503", "403", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "PERMISSION_DENIED"]):
                rotate_to_next_key()
            else:
                raise e
    return st.session_state.genai_client.models.generate_content(model=model, contents=contents)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_sources" not in st.session_state:
    st.session_state.uploaded_sources = []
if "stats_questions" not in st.session_state:
    st.session_state.stats_questions = 0
if "stats_exercises" not in st.session_state:
    st.session_state.stats_exercises = 0

st.markdown("<h1 style='text-align: center; margin-bottom: 30px;'>🎓 EduBot STEM & Statistics (Cấp 2 - THCS)</h1>", unsafe_allow_html=True)

# =====================================================================
# 3. SIDEBAR CẤU HÌNH HỌC TẬP (CHUYÊN SÂU THCS)
# =====================================================================
with st.sidebar:
    st.markdown("### ⚙️ Cấu Hình Cấp 2 (THCS)")
    bac_hoc = "Cấp 2 (THCS)"
    khoi_lop = st.selectbox("Chọn khối lớp:", ["Lớp 6", "Lớp 7", "Lớp 8", "Lớp 9"])
    
    danh_sach_mon = [
        "Toán học", 
        "Ngữ văn", 
        "Vật lý", 
        "Hóa học", 
        "Sinh học", 
        "Khoa học tự nhiên (STEM)", 
        "Lịch sử & Địa lý", 
        "Tin học", 
        "Thống kê & Xác suất"
    ]
    mon_hoc = st.selectbox("Chọn môn học:", danh_sach_mon)
    st.divider()

    st.markdown("### 📚 Thư Viện Tài Liệu")
    uploaded_file = st.file_uploader("📁 Tải tệp hỗ trợ bài học:", type=None)
    if uploaded_file is not None and st.session_state.genai_client:
        file_name = uploaded_file.name
        if file_name not in [s['name'] for s in st.session_state.uploaded_sources]:
            file_ext = os.path.splitext(file_name)[1].lower()
            if file_ext in ['.png', '.jpg', '.jpeg', '.webp']:
                st.session_state.uploaded_sources.append({'name': file_name, 'type': 'image', 'data': Image.open(uploaded_file)})
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                try:
                    file_ref = st.session_state.genai_client.files.upload(file=tmp_path)
                    st.session_state.uploaded_sources.append({'name': file_name, 'type': 'file_ref', 'data': file_ref})
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
            st.success(f"Đã thêm '{file_name}'!")
            st.rerun()

    selected_sources_for_chat = []
    if st.session_state.uploaded_sources:
        st.caption("Tài liệu đính kèm hoạt động:")
        for idx, src in enumerate(st.session_state.uploaded_sources):
            c1, c2 = st.columns([3, 1])
            with c1:
                if st.checkbox(f"📎 {src['name']}", value=True, key=f"chk_{idx}"):
                    selected_sources_for_chat.append(src['data'])
            with c2:
                if st.button("❌", key=f"del_{idx}"):
                    st.session_state.uploaded_sources.pop(idx)
                    st.rerun()
                    
    st.divider()
    if st.button("🧹 Xóa hội thoại"):
        st.session_state.messages = []
        st.session_state.pop("chat_session", None)
        st.rerun()

current_config = f"{bac_hoc}_{khoi_lop}_{mon_hoc}"
if "last_config" not in st.session_state or st.session_state.last_config != current_config:
    st.session_state.last_config = current_config
    st.session_state.pop("chat_session", None)

# Hướng dẫn chi tiết, chuyên sâu tuyệt đối cho cấp THCS
system_instruction = f"""
Bạn là Chuyên gia Giáo dục & Gia sư STEM - Thống kê hàng đầu chuyên sâu cho bậc Cấp 2 (THCS) tại Việt Nam.
Cấu hình hiện tại: {bac_hoc} - {khoi_lop} - Môn: {mon_hoc}.

QUY TẮC CHUYÊN MÔN VÀ SƯ PHẠM ĐẶC BIỆT:
1. ĐỘ CHÍNH XÁC VÀ CHI TIẾT CAO: Mọi giải thích lý thuyết, định lý, công thức, bài toán toán học, vật lý, hóa học, sinh học hay thống kê phải cực kỳ chính xác theo chuẩn chương trình giáo dục phổ thông mới (Sách giáo khoa Bộ GD&ĐT), phân tích sâu sắc, rõ ràng từng bước bản chất hiện tượng hoặc công thức.
2. PHƯƠNG PHÁP SƯ PHẠM DẪN DẮT: Không đưa ngay đáp án cuối cùng. Hãy phân tích đề bài, hướng dẫn tư duy từng bước logic (Step-by-step), giải thích tường tận *vì sao lại làm như vậy*, giúp học sinh hiểu bản chất thay vì học vẹt.
3. CHUẨN TRÌNH BÀY: Bắt buộc sử dụng ký hiệu LaTeX tiêu chuẩn ($...$ hoặc $$...$$) cho mọi biểu thức, công thức, số liệu, phân số hoặc ký hiệu toán học/thống kê.
4. TÍNH CHUYÊN SÂU THEO KHỐI LỚP: Bám sát chuẩn kiến thức trọng tâm của {khoi_lop}, kết hợp các ví dụ thực tiễn sinh động chuẩn lứa tuổi THCS.
5. Luôn kết thúc phản hồi bằng một câu hỏi gợi mở hoặc bài toán nhỏ để học sinh tự tư duy tiếp.
"""

if st.session_state.genai_client and "chat_session" not in st.session_state:
    st.session_state.chat_session = st.session_state.genai_client.chats.create(
        model=MODEL_NAME,
        config=types.GenerateContentConfig(system_instruction=system_instruction, temperature=0.2)
    )

# =====================================================================
# 4. GIAO DIỆN TABS CHÍNH
# =====================================================================
tab_chat, tab_stat_viz, tab_analytics, tab_time, tab_research = st.tabs([
    "💬 Trò Chuyện Học Tập", "📊 Thống Kê & STEM", "📈 Năng Lực", "⏰ Thời Gian", "🔍 Tra Cứu"
])

with tab_chat:
    if not API_KEYS_POOL:
        st.error("⚠️ Chưa cấu hình API Key trong `secrets.toml`!")
    else:
        q_cols = st.columns(3)
        quick_prompt = None
        with q_cols[0]:
            if st.button("📝 Tóm tắt lý thuyết chi tiết"): quick_prompt = f"Hãy tóm tắt chi tiết, đầy đủ kiến thức trọng tâm, công thức và bản chất của chủ đề học tập trong môn {mon_hoc} ({khoi_lop})."
        with q_cols[1]:
            if st.button("🎯 Tạo bài tập rèn luyện"): quick_prompt = f"Hãy tạo 2 bài tập tự luận có kèm hướng dẫn giải chi tiết từng bước bám sát môn {mon_hoc} ({khoi_lop})."
        with q_cols[2]:
            if st.button("💡 Giải thích bản chất"): quick_prompt = f"Hãy phân tích và giải thích cặn kẽ bản chất khoa học hoặc phương pháp giải cốt lõi trong môn {mon_hoc} ({khoi_lop})."

        st.divider()

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"], unsafe_allow_html=True)

        prompt_input = st.chat_input("Nhập câu hỏi bài tập hoặc thắc mắc học tập...")
        user_input = quick_prompt if quick_prompt else prompt_input

        if user_input:
            payload = list(selected_sources_for_chat) + [user_input]
            with st.chat_message("user"):
                st.markdown(user_input)
                st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.stats_questions += 1

            with st.chat_message("assistant"):
                try:
                    bot_reply = ""
                    total_k = max(1, len(API_KEYS_POOL))
                    success = False
                    
                    for _ in range(total_k):
                        try:
                            response_stream = st.session_state.chat_session.send_message_stream(payload)
                            def stream_gen():
                                for chunk in response_stream:
                                    if chunk.text: yield chunk.text
                            bot_reply = st.write_stream(stream_gen())
                            success = True
                            break
                        except Exception as api_err:
                            if any(c in str(api_err) for c in ["429", "503", "403", "RESOURCE_EXHAUSTED", "UNAVAILABLE"]):
                                rotate_to_next_key()
                            else:
                                raise api_err
                    
                    if success:
                        st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                    else:
                        st.error("⚠️ Hệ thống quá tải hoặc hết hạn mức tất cả các Key, vui lòng thử lại sau.")
                except Exception as e:
                    st.error(f"Lỗi kết nối: {e}")

with tab_stat_viz:
    st.subheader("📊 Trực Quan Hóa Dữ Liệu Thống Kê THCS")
    data_str = st.text_input("Nhập dãy số liệu mẫu (cách nhau bởi dấu phẩy):", "5, 7, 8, 9, 10, 6, 8, 7, 9, 8")
    if st.button("Phân tích thống kê chi tiết"):
        try:
            arr = [float(x.strip()) for x in data_str.split(",") if x.strip()]
            s = pd.Series(arr)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Trung bình (Mean)", f"{s.mean():.2f}")
            c2.metric("Trung vị (Median)", f"{s.median():.2f}")
            c3.metric("Độ lệch chuẩn", f"{s.std(ddof=1):.2f}")
            c4.metric("Phương sai", f"{s.var(ddof=1):.2f}")
            fig, (a1, a2) = plt.subplots(1, 2, figsize=(10, 4))
            a1.hist(arr, bins='auto', color='#2563eb', edgecolor='white')
            a1.set_title("Biểu đồ Tần suất")
            a2.boxplot(arr, patch_artist=True, boxprops=dict(facecolor="#93c5fd"))
            a2.set_title("Biểu đồ Hộp")
            st.pyplot(fig)
        except Exception as e:
            st.error(f"Lỗi xử lý dữ liệu: {e}")

with tab_analytics:
    st.subheader("📈 Phân Tích Năng Lực Học Tập")
    if len(st.session_state.messages) < 2:
        st.info("Hãy trao đổi với EduBot ở tab Trò chuyện học tập để hệ thống ghi nhận dữ liệu đánh giá.")
    else:
        if st.button("Đánh giá năng lực chuyên sâu"):
            history = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
            res = safe_generate_content(contents=f"Đánh giá chi tiết năng lực, điểm mạnh điểm yếu môn {mon_hoc} ({khoi_lop}) dựa trên lịch sử trao đổi: {history}")
            st.markdown(f"<div class='analytics-box'>{res.text}</div>", unsafe_allow_html=True)

with tab_time:
    st.subheader("⏰ Lập Kế Hoạch Ôn Tập Khoa Học")
    exam_name = st.text_input("Tên kỳ thi / Kiểm tra:", "Kiểm tra học kỳ")
    exam_date = st.date_input("Ngày diễn ra:", datetime.date.today() + datetime.timedelta(days=15))
    if st.button("Tạo lộ trình ôn tập chi tiết"):
        days = (exam_date - datetime.date.today()).days
        st.markdown(f"<div class='countdown-card'><h2>🚨 Còn lại {days} ngày</h2><p><b>{exam_name}</b></p></div>", unsafe_allow_html=True)
        res = safe_generate_content(contents=f"Lập lộ trình ôn tập chi tiết từng ngày theo phương pháp Spaced Repetition cho môn {mon_hoc} ({khoi_lop}) trong thời gian {days} ngày.")
        st.markdown(res.text)

with tab_research:
    st.subheader("🔍 Tra Cứu Kiến Thức Học Thuật")
    query = st.text_input("Nhập chủ đề khoa học hoặc toán học cần tra cứu:")
    if st.button("Truy vấn thông tin uy tín") and query:
        res = safe_generate_content(
            contents=f"Tìm kiếm và giải thích chi tiết về: '{query}' phục vụ chương trình học môn {mon_hoc} ({khoi_lop}).",
            config=types.GenerateContentConfig(tools=[{"google_search": {}}])
        )
        st.markdown(res.text)
