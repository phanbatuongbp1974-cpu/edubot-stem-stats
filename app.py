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
# 1. CẤU HÌNH GIAO DIỆN WEB & CSS HỖ TRỢ TỰ ĐỘNG LIGHT / DARK MODE
# =====================================================================
st.set_page_config(page_title="EduBot STEM & Statistics", page_icon="🎓", layout="wide")

st.markdown("""
<style>
    .stChatMessage { 
        border-radius: 16px; 
        padding: 16px; 
        margin-bottom: 14px; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid rgba(128, 128, 128, 0.2); 
    }
    .stButton>button { 
        border-radius: 12px; 
        font-weight: 600; 
        width: 100%; 
        border: 1px solid rgba(128, 128, 128, 0.3); 
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        padding: 10px 15px;
    }
    .stButton>button:hover { 
        border-color: #2563eb; 
        color: #2563eb !important; 
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.15);
        transform: translateY(-1px);
    }
    .metric-card { 
        border: 1px solid rgba(128, 128, 128, 0.2); 
        padding: 16px; 
        border-radius: 16px; 
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-val { font-size: 28px; font-weight: 800; color: #2563eb; }
    .metric-lbl { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 4px; opacity: 0.8; }
    .analytics-box { 
        border-left: 5px solid #2563eb; 
        border-top: 1px solid rgba(128, 128, 128, 0.2);
        border-right: 1px solid rgba(128, 128, 128, 0.2);
        border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        padding: 20px; border-radius: 4px 16px 16px 4px; margin-bottom: 15px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .countdown-card { 
        background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); 
        color: white !important; padding: 24px; border-radius: 16px; text-align: center; margin-bottom: 20px;
        box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.25);
    }
    .countdown-card h2 { color: white !important; margin: 0; font-weight: 800;}
    .countdown-card p { color: #bfdbfe !important; margin-top: 8px; font-size: 14px;}
    h1, h2, h3, h4 { font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. HỆ THỐNG XOAY VÒNG 5 API KEY THÔNG MINH
# =====================================================================
if "key_index" not in st.session_state:
    st.session_state.key_index = 0

API_KEYS_POOL = [
    "AQ.Ab8RN6LAu14G0gb8ntVPkeG2tbU2yR8dEDu3F63AIGznFGcgcA",
    "AQ.Ab8RN6IW7njatVnaw7Ml4mkM1xG1KEfnJ5cxM-VNqJMSdQsXIQ",
    "AQ.Ab8RN6LO8xRuz1IesGqR48Y10wTW02AtovsmfgV_o8-y97JSqQ",
    "AQ.Ab8RN6KFz4jALbfPCmM0jkggHl2t7HeZpvRdbeiRzW0MKwQ4aA",
    "AQ.Ab8RN6JJfSyC8WB1C8c8IgA5tFxDoLgeVQz08g26r_s0MFzXMA"
]

try:
    if "GEMINI_API_KEY_1" in st.secrets:
        API_KEYS_POOL = [
            st.secrets.get("GEMINI_API_KEY_1", API_KEYS_POOL[0]),
            st.secrets.get("GEMINI_API_KEY_2", API_KEYS_POOL[1]),
            st.secrets.get("GEMINI_API_KEY_3", API_KEYS_POOL[2]),
            st.secrets.get("GEMINI_API_KEY_4", API_KEYS_POOL[3]),
            st.secrets.get("GEMINI_API_KEY_5", API_KEYS_POOL[4]),
        ]
except Exception:
    pass

def get_active_client():
    current_key = API_KEYS_POOL[st.session_state.key_index]
    return genai.Client(api_key=current_key)

def rotate_to_next_key():
    st.session_state.key_index = (st.session_state.key_index + 1) % len(API_KEYS_POOL)
    st.warning(f"🔄 Đã tự động chuyển sang API Key dự phòng số {st.session_state.key_index + 1} do hết hạn mức!")
    st.session_state.genai_client = get_active_client()
    st.session_state.pop("chat_session", None)

if "genai_client" not in st.session_state:
    st.session_state.genai_client = get_active_client()

client = st.session_state.genai_client

if "messages" not in st.session_state:
    st.session_state.messages = []
if "uploaded_sources" not in st.session_state:
    st.session_state.uploaded_sources = []
if "stats_questions" not in st.session_state:
    st.session_state.stats_questions = 0
if "stats_exercises" not in st.session_state:
    st.session_state.stats_exercises = 0

st.markdown("<h1 style='text-align: center; margin-bottom: 30px;'>🎓 EduBot STEM & Statistics</h1>", unsafe_allow_html=True)

# =====================================================================
# 3. SIDEBAR ĐIỀU HƯỚNG & QUẢN LÝ TÀI LIỆU
# =====================================================================
with st.sidebar:
    st.markdown("### ⚙️ Cấu Hình Học Tập")
    bac_hoc = st.selectbox("Chọn bậc học:", ["Cấp 1 (Tiểu học)", "Cấp 2 (THCS)", "Cấp 3 (THPT)"])
    
    if bac_hoc == "Cấp 1 (Tiểu học)":
        khoi_lop = st.selectbox("Chọn khối lớp:", ["Lớp 1", "Lớp 2", "Lớp 3", "Lớp 4", "Lớp 5"])
        danh_sach_mon = ["Tiếng Việt", "Toán", "Đạo đức", "Ngoại ngữ 1", "Tự nhiên và Xã hội", "Khoa học (Lớp 4-5)", "Tin học"]
    elif bac_hoc == "Cấp 2 (THCS)":
        khoi_lop = st.selectbox("Chọn khối lớp:", ["Lớp 6", "Lớp 7", "Lớp 8", "Lớp 9"])
        danh_sach_mon = ["Ngữ văn", "Toán", "Vật lý", "Hóa học", "Sinh học", "Lịch sử", "Địa lý", "Tin học", "Thống kê & Xác suất cơ bản"]
    else:
        khoi_lop = st.selectbox("Chọn khối lớp:", ["Lớp 10", "Lớp 11", "Lớp 12", "Ôn thi THPT Quốc gia"])
        danh_sach_mon = ["Ngữ văn", "Toán", "Vật lý", "Hóa học", "Sinh học", "Lịch sử", "Địa lý", "Thống kê toán học & Khoa học dữ liệu", "Tin học"]
        
    mon_hoc = st.selectbox("Chọn môn học:", danh_sach_mon)
    st.divider()
    
    st.markdown("### 📚 Thư Viện Tài Liệu")
    uploaded_file = st.file_uploader("📁 Tải tệp hỗ trợ bài học:", type=None)
    if uploaded_file is not None:
        file_name = uploaded_file.name
        if file_name not in [s['name'] for s in st.session_state.uploaded_sources]:
            file_extension = os.path.splitext(file_name)[1].lower()
            if file_extension in ['.png', '.jpg', '.jpeg', '.webp']:
                img_obj = Image.open(uploaded_file)
                st.session_state.uploaded_sources.append({'name': file_name, 'type': 'image', 'data': img_obj})
            else:
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                try:
                    file_ref = client.files.upload(file=tmp_path)
                    st.session_state.uploaded_sources.append({'name': file_name, 'type': 'file_ref', 'data': file_ref})
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
            st.success(f"Đã thêm '{file_name}' vào thư viện!")
            st.rerun()

    selected_sources_for_chat = []
    if st.session_state.uploaded_sources:
        st.caption("Danh sách tài liệu đính kèm hoạt động:")
        for idx, src in enumerate(st.session_state.uploaded_sources):
            col_check, col_del = st.columns([3, 1])
            with col_check:
                is_checked = st.checkbox(f"📎 {src['name']}", value=True, key=f"chk_src_{idx}")
                if is_checked:
                    selected_sources_for_chat.append(src['data'])
            with col_del:
                if st.button("❌", key=f"del_src_{idx}"):
                    st.session_state.uploaded_sources.pop(idx)
                    st.rerun()
                    
    st.divider()
    st.markdown("### 📊 Tiến Độ")
    col_m1, col_m2 = st.columns(2)
    with col_m1:
        st.markdown(f"<div class='metric-card'><div class='metric-val'>{st.session_state.stats_questions}</div><div class='metric-lbl'>Câu hỏi</div></div>", unsafe_allow_html=True)
    with col_m2:
        st.markdown(f"<div class='metric-card'><div class='metric-val'>{st.session_state.stats_exercises}</div><div class='metric-lbl'>Bài luyện</div></div>", unsafe_allow_html=True)
        
    st.divider()
    if st.button("🧹 Xóa hội thoại hiện tại"):
        st.session_state.messages = []
        st.session_state.pop("chat_session", None)
        st.rerun()

current_config = f"{bac_hoc}_{khoi_lop}_{mon_hoc}"
if "last_config" not in st.session_state or st.session_state.last_config != current_config:
    st.session_state.last_config = current_config
    st.session_state.pop("chat_session", None)

system_instruction = f"""
Bạn là một Gia sư Giáo dục & Chuyên gia Thống kê - Khoa học STEM tại Việt Nam đối với trình độ: {bac_hoc} - {khoi_lop} - Môn học: {mon_hoc}.
QUY TẮC SƯ PHẠM BẮT BUỘC:
1. CHỈ GIẢI ĐÁP CÁC CÂU HỎI VỀ HỌC TẬP, TOÁN HỌC, THỐNG KÊ VÀ STEM thuộc môn {mon_hoc}. Từ chối khéo léo nếu nội dung ngoài lề.
2. KHÔNG cung cấp ngay đáp án cuối cùng. Hãy hướng dẫn tư duy logic theo từng bước ngắn (Step-by-step).
3. Sử dụng chuẩn hiển thị công thức LaTeX ($...$ hoặc $$...$$) đối với mọi số liệu toán học/thống kê.
4. Luôn kết thúc câu bằng 1 câu hỏi gợi mở để người học tự hoàn thành bài tập.
"""

if "chat_session" not in st.session_state:
    st.session_state.chat_session = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.3
        )
    )

# =====================================================================
# 4. KHÔNG GIAN TABS CHỨC NĂNG CHÍNH
# =====================================================================
tab_chat, tab_stat_viz, tab_analytics, tab_time, tab_research = st.tabs([
    "💬 Trò Chuyện Học Tập", 
    "📊 Mô Hình Thống Kê & STEM",
    "📈 Phân Tích Năng Lực",
    "⏰ Quản Lý Thời Gian",
    "🔍 Tra Cứu Học Thuật"
])

with tab_chat:
    st.markdown("#### ⚡ Công Cụ Hỗ Trợ Nhanh")
    qc_cols = st.columns(4)
    quick_action_prompt = None

    with qc_cols[0]:
        if st.button("📝 Tóm tắt lý thuyết"):
            quick_action_prompt = f"Hãy tóm tắt các điểm kiến thức cốt lõi, định luật hoặc công thức thống kê quan trọng của môn {mon_hoc} ({khoi_lop})."
    with qc_cols[1]:
        if st.button("🎯 Tạo bài trắc nghiệm"):
            quick_action_prompt = f"Hãy tạo 3 câu hỏi trắc nghiệm bám sát môn {mon_hoc} ({khoi_lop}) để kiểm tra kiến thức (chưa đưa đáp án vội)."
    with qc_cols[2]:
        if st.button("💡 Giải thích công thức"):
            quick_action_prompt = f"Hãy giải thích chi tiết ý nghĩa thực tiễn và cách áp dụng các công thức quan trọng trong môn {mon_hoc}."
    with qc_cols[3]:
        if st.button("🗺️ Sơ đồ tư duy"):
            quick_action_prompt = f"Hãy thiết kế sơ đồ tư duy tóm tắt chủ đề môn {mon_hoc} bằng mã nguồn Mermaid.js (trong code block ```mermaid ... ```)."

    st.divider()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

    prompt = st.chat_input("Nhập câu hỏi học tập, bài toán thống kê hoặc yêu cầu hướng dẫn...")
    user_input_content = None

    if quick_action_prompt:
        user_input_content = quick_action_prompt
    elif prompt:
        user_input_content = prompt

    if user_input_content is not None:
        contents_payload = list(selected_sources_for_chat)
        contents_payload.append(user_input_content)

        with st.chat_message("user"):
            st.markdown(user_input_content)
            st.session_state.messages.append({"role": "user", "content": user_input_content})

        st.session_state.stats_questions += 1

        with st.chat_message("assistant"):
            try:
                success = False
                bot_reply = ""
                for attempt in range(len(API_KEYS_POOL)):
                    try:
                        response_stream = st.session_state.chat_session.send_message_stream(contents_payload)
                        def stream_generator():
                            for chunk in response_stream:
                                if chunk.text: yield chunk.text
                        bot_reply = st.write_stream(stream_generator())
                        success = True
                        break
                    except Exception as api_err:
                        err_str = str(api_err)
                        if "429" in err_str or "401" in err_str or "RESOURCE_EXHAUSTED" in err_str or "UNAUTHENTICATED" in err_str:
                            rotate_to_next_key()
                        else:
                            raise api_err
                
                if success:
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                else:
                    st.error("⚠️ Tất cả 5 API Key đều đã vượt quá hạn mức hoặc gặp lỗi xác thực. Vui lòng thử lại sau!")
            except Exception as e:
                st.error(f"Lỗi kết nối AI: {e}")

with tab_stat_viz:
    st.subheader("📊 Trực Quan Hóa Dữ Liệu Thống Kê & STEM")
    raw_data_input = st.text_input("Chuỗi số liệu mẫu:", "12, 15, 18, 20, 22, 25, 28, 30, 35, 40")
    
    if st.button("📊 Phân Tích Thống Kê & Vẽ Biểu Đồ"):
        try:
            data_list = [float(x.strip()) for x in raw_data_input.split(",") if x.strip()]
            if not data_list:
                st.warning("Vui lòng nhập dữ liệu hợp lệ!")
            else:
                s = pd.Series(data_list)
                mean_val, median_val, std_val, var_val = s.mean(), s.median(), s.std(ddof=1), s.var(ddof=1)
                
                col_s1, col_s2, col_s3, col_s4 = st.columns(4)
                col_s1.metric("Trung bình mẫu (Mean)", f"{mean_val:.2f}")
                col_s2.metric("Trung vị (Median)", f"{median_val:.2f}")
                col_s3.metric("Độ lệch chuẩn (Std)", f"{std_val:.2f}")
                col_s4.metric("Phương sai (Var)", f"{var_val:.2f}")
                
                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
                ax1.hist(data_list, bins='auto', color='#2563eb', edgecolor='white', alpha=0.8)
                ax1.set_title("Biểu đồ Tần suất (Histogram)")
                ax2.boxplot(data_list, vert=True, patch_artist=True, boxprops=dict(facecolor="#93c5fd", color="#2563eb"))
                ax2.set_title("Biểu đồ Hộp (Boxplot)")
                st.pyplot(fig)
                
                with st.spinner("AI đang phân tích ý nghĩa thống kê..."):
                    ai_stat_analysis = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=f"Dữ liệu: {data_list}. Mean={mean_val:.2f}, Median={median_val:.2f}, Std={std_val:.2f}. Nhận xét khoa học."
                    )
                    st.markdown("### 🤖 Nhận định chuyên gia:")
                    st.markdown(ai_stat_analysis.text)
        except Exception as e:
            st.error(f"Lỗi xử lý dữ liệu: {e}")

with tab_analytics:
    st.subheader("📈 Phân Tích Năng Lực & Lộ Trình")
    if len(st.session_state.messages) < 2:
        st.info("💡 Hãy trao đổi với gia sư AI ở tab Trò chuyện học tập để hệ thống thu thập dữ liệu!")
    else:
        if st.button("📊 Phân Tích Năng Lực Ngay", use_container_width=True):
            with st.spinner("Đang phân tích dữ liệu..."):
                chat_history_summary = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                analysis_res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"Phân tích điểm mạnh/yếu môn {mon_hoc} dựa trên lịch sử: {chat_history_summary}"
                )
                st.markdown(f"<div class='analytics-box'>{analysis_res.text}</div>", unsafe_allow_html=True)

with tab_time:
    st.subheader("⏰ Quản Lý Thời Gian & Ôn Tập (Spaced Repetition)")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        exam_name = st.text_input("Tên kỳ thi:", "Kỳ thi học kỳ")
        exam_date = st.date_input("Chọn ngày diễn ra:", datetime.date.today() + datetime.timedelta(days=30))
        if st.button("📌 Tính toán thời gian & Lập lịch"):
            days_left = (exam_date - datetime.date.today()).days
            st.markdown(f"<div class='countdown-card'><h2>🚨 Còn lại {days_left} ngày</h2><p><b>{exam_name}</b></p></div>", unsafe_allow_html=True)
            with st.spinner("Đang thiết lập lịch ôn tập..."):
                schedule_res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"Thiết kế lịch ôn Spaced Repetition môn {mon_hoc} trong {days_left} ngày."
                )
                st.markdown(schedule_res.text)
    with col_t2:
        st.info("Hệ thống tự động nhắc nhở ôn lại theo các mốc khoa học.")

with tab_research:
    st.subheader("🔍 Tra Cứu Học Thuật (Google Search Grounding)")
    research_query = st.text_input("Nhập chủ đề cần tra cứu:")
    if st.button("🔎 Truy Vấn Google Search"):
        if research_query:
            with st.spinner("Đang tìm kiếm thông tin..."):
                grounding_res = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"Tìm kiếm thông tin uy tín về: '{research_query}' cho môn {mon_hoc}.",
                    config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())])
                )
                st.markdown("### 🌐 Kết quả:")
                st.markdown(grounding_res.text)
        else:
            st.warning("Vui lòng nhập chủ đề!")
