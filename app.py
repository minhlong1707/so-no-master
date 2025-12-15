import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from datetime import datetime

# --- 1. CẤU HÌNH TRANG WEB ---
st.set_page_config(
    page_title="Sổ Nợ Master",
    page_icon="💸",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS GIAO DIỆN (GIỮ NGUYÊN) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    h1, h2, h3, h4, h5, h6, span, p, div, label { color: #FAFAFA !important; }
    
    /* Tab Style */
    div[role="radiogroup"] {
        flex-direction: row; gap: 5px; background-color: #161B22; padding: 5px 5px 0px 5px;
        border-radius: 10px 10px 0 0; border-bottom: 2px solid #4DB6AC; width: 100%;
    }
    div[role="radiogroup"] label[data-baseweb="radio"] {
        background-color: #0E1117; padding: 10px 20px; border-radius: 8px 8px 0 0;
        border: 1px solid #30363D; border-bottom: none; margin-right: 0px; cursor: pointer; flex-grow: 1; justify-content: center;
    }
    div[role="radiogroup"] label[data-baseweb="radio"]:hover { background-color: #262730; color: #FFF; }
    div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child { background-color: #4DB6AC !important; }
    div[role="radiogroup"] > :first-child { display: none; }
    div[data-testid="stRadio"] > label { display: none; }
    div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-weight: bold; font-size: 14px; }

    /* Card & Table */
    div[data-testid="stMetric"] { background-color: #262730; border: 1px solid #3b3c45; padding: 15px; border-radius: 12px; }
    div[data-testid="stMetricValue"] { color: #4DB6AC !important; font-weight: bold; }
    div[data-testid="stMetricLabel"] { color: #B0BEC5 !important; }
    .stDataFrame { background-color: #262730; border-radius: 10px; padding: 5px; }
    
    /* Button */
    div.stButton > button { background-color: #1f77b4; color: white; border: none; padding: 0.5rem 1rem; border-radius: 5px; width: 100%; }
    div.stButton > button:hover { background-color: #4DB6AC; color: black; }
</style>
""", unsafe_allow_html=True)

# --- 3. TẠO POPUP THÔNG BÁO ---
@st.dialog("🔔 Thông báo")
def show_popup():
    st.write("Vui lòng đọc kỹ thông tin bên dưới:")
    st.markdown("👉 **Điều khoản:** [https://tinyurl.com/dieukhoan29](https://tinyurl.com/dieukhoan29)")
    st.write("") 

    if st.button("❌ Đóng", width="stretch"):
        st.session_state['popup_closed'] = True
        st.rerun()

if 'popup_closed' not in st.session_state:
    show_popup()

# --- 4. HÀM FORMAT ---
def format_vnd(value):
    if pd.isna(value) or value == 0: return "-"
    return "{:,.0f}".format(value).replace(",", ".") + " VNĐ"

def format_percent(value):
    if pd.isna(value): return "0%"
    return "{:.0%}".format(value)

# --- 5. XỬ LÝ DỮ LIỆU ---
@st.cache_data 
def load_data():
    file_path = 'solieu.xlsx'
    if not os.path.exists(file_path): return None, None
    try:
        xl = pd.ExcelFile(file_path, engine='openpyxl')
        
        # --- SHEET NỢ ---
        sheet_no = next((s for s in xl.sheet_names if "NỢ" in s.upper()), xl.sheet_names[0])
        df_no = pd.read_excel(xl, sheet_name=sheet_no, header=0)
        
        try:
            df_no = df_no.iloc[:, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 12]]
            df_no.columns = ['STT', 'Họ tên', 'Nội dung', 'Phải trả', 'Đã trả', 'Còn lại', 
                             'Bonus', 'Thuế (%)', 'Tiền Thuế', 'Ngày bắt đầu', 'Hạn trả', 'Trạng thái']
        except: return None, None

        # Lọc bỏ dòng trống
        df_no = df_no[pd.to_numeric(df_no['STT'], errors='coerce').notnull()]
        
        # Chuyển STT sang số nguyên (int)
        df_no['STT'] = df_no['STT'].astype(int)

        if 'Họ tên' in df_no.columns: 
            df_no['Họ tên'] = df_no['Họ tên'].astype(str).str.strip()

        for c in ['Phải trả', 'Đã trả', 'Còn lại', 'Bonus', 'Tiền Thuế']: 
            df_no[c] = pd.to_numeric(df_no[c], errors='coerce').fillna(0)
        df_no['Thuế (%)'] = pd.to_numeric(df_no['Thuế (%)'], errors='coerce').fillna(0)
        
        df_no['Tiến độ'] = df_no.apply(lambda x: (x['Đã trả'] / x['Phải trả'] * 100) if x['Phải trả'] > 0 else 0, axis=1)
        
        for d in ['Ngày bắt đầu', 'Hạn trả']:
            df_no[d] = pd.to_datetime(df_no[d], errors='coerce').dt.date

        # --- LOGIC TÍNH NGÀY CÒN LẠI (TIMEZONE VN) ---
        # [CẬP NHẬT MỚI] Lấy giờ Việt Nam (UTC+7)
        today = pd.Timestamp.now(tz='Asia/Ho_Chi_Minh').date()
        
        def tinh_ngay_con(row):
            trang_thai = str(row['Trạng thái']).strip()
            
            if trang_thai.lower() == 'đã trả đủ':
                return "✔️ Đã xong"
            
            if pd.isna(row['Hạn trả']):
                return "-"
            
            delta = (row['Hạn trả'] - today).days
            
            if delta >= 0:
                ngay_con = delta + 1
                return f"Còn {ngay_con} ngày"
            else:
                return f"⚠️ Quá hạn {abs(delta)} ngày"

        df_no['Thời gian'] = df_no.apply(tinh_ngay_con, axis=1)
        # ---------------------------------------------

        # --- SHEET NẠP ---
        sheet_nap = next((s for s in xl.sheet_names if "NẠP" in s.upper()), None)
        df_nap_long = pd.DataFrame()
        if sheet_nap:
            df_nap = pd.read_excel(xl, sheet_name=sheet_nap)
            df_nap = df_nap[df_nap.iloc[:, 0] != 'Tổng:']
            df_nap.rename(columns={df_nap.columns[0]: 'Thời gian'}, inplace=True)
            df_nap['Thời gian'] = pd.to_datetime(df_nap['Thời gian'], errors='coerce')
            df_nap_long = df_nap.melt(id_vars=['Thời gian'], var_name='Người nạp', value_name='Số tiền')
            df_nap_long['Số tiền'] = pd.to_numeric(df_nap_long['Số tiền'], errors='coerce').fillna(0)
            df_nap_long = df_nap_long[df_nap_long['Số tiền'] > 0]
            df_nap_long['Người nạp'] = df_nap_long['Người nạp'].astype(str)
            
        return df_no, df_nap_long
    except: return None, None

df_no, df_nap = load_data()

# --- 6. GIAO DIỆN CHÍNH ---
if df_no is None:
    st.error("⚠️ Lỗi file 'solieu.xlsx'.")
    st.stop()

# Header + Nút Cập Nhật
col_head1, col_head2 = st.columns([4, 1])
with col_head1:
    st.title("💸 QUẢN LÝ TÀI CHÍNH")
with col_head2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 Cập nhật ngay"):
        st.cache_data.clear()
        st.rerun()

# --- MENU 2 TAB ---
tab1, tab2 = st.tabs(["📋 SỔ NỢ CHI TIẾT", "📊 DASHBOARD TỔNG QUAN"])

# === 1. TAB SỔ NỢ ===
with tab1:
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 2])
    search = c1.text_input("🔍 Tìm tên:", "")
    
    all_stt = [str(x) for x in df_no['Trạng thái'].unique() if str(x).lower() != 'nan']
    trang_thai = c2.multiselect("Lọc trạng thái:", all_stt, default=all_stt)

    df_show = df_no.copy()
    if search: df_show = df_show[df_show['Họ tên'].str.contains(search, case=False, na=False)]
    if trang_thai: df_show = df_show[df_show['Trạng thái'].astype(str).isin(trang_thai)]

    # Format hiển thị
    for col in ['Phải trả', 'Đã trả', 'Còn lại', 'Bonus', 'Tiền Thuế']:
        df_show[col] = df_show[col].apply(format_vnd)
    df_show['Thuế (%)'] = df_show['Thuế (%)'].apply(format_percent)

    cols_order = ['STT', 'Họ tên', 'Nội dung', 'Phải trả', 'Đã trả', 'Còn lại', 'Tiến độ', 
                  'Bonus', 'Thuế (%)', 'Tiền Thuế', 'Ngày bắt đầu', 'Hạn trả', 'Thời gian', 'Trạng thái']
    
    # HÀM TÔ MÀU
    def highlight_row(row):
        trang_thai = str(row['Trạng thái'])
        thoi_gian = str(row['Thời gian'])
        han_tra = row['Hạn trả']

        if 'Đã xong' in trang_thai or 'Đã trả đủ' in trang_thai:
            return ['background-color: rgba(46, 204, 113, 0.3)'] * len(row) # Xanh lá
        
        if 'Còn 1 ngày' in thoi_gian:
            return ['background-color: rgba(231, 76, 60, 0.3)'] * len(row) # Đỏ

        if pd.isna(han_tra) or str(han_tra) == 'NaT':
            return ['background-color: rgba(52, 152, 219, 0.3)'] * len(row) # Xanh dương
        
        return [''] * len(row)

    st.dataframe(
        df_show[cols_order].style.apply(highlight_row, axis=1), 
        width="stretch", 
        hide_index=True, 
        height=700,
        column_config={
            "STT": st.column_config.TextColumn("STT", width=None),
            
            # Autosize cho 2 cột này
            "Phải trả": st.column_config.TextColumn("Phải trả", width=None),
            "Còn lại": st.column_config.TextColumn("Còn lại", width=None),
            
            "Đã trả": st.column_config.TextColumn("Đã trả", width="small"),
            "Tiến độ": st.column_config.ProgressColumn(
                "Tiến độ trả", format="%.0f%%", min_value=0, max_value=100, width="small" 
            ),
            "Ngày bắt đầu": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Hạn trả": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Thời gian": st.column_config.TextColumn("Thời gian", width="small"),
        }
    )

# === 2. TAB DASHBOARD ===
with tab2:
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    
    tong_no = df_no['Phải trả'].sum()
    con_lai = df_no['Còn lại'].sum()
    da_tra = df_no['Đã trả'].sum()

    col1.metric("Tổng Phải Thu", format_vnd(tong_no))
    col2.metric("Đã Thu Về", format_vnd(da_tra), delta=f"{(da_tra/tong_no)*100:.0f}%" if tong_no > 0 else "0%")
    col3.metric("Còn Nợ Đọng", format_vnd(con_lai), delta="Thu gấp!", delta_color="inverse")

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.subheader("🚨 Top Con Nợ")
    
    df_chart = df_no[df_no['Họ tên'].str.lower() != 'nan']
    df_chart = df_chart[df_chart['Họ tên'] != '']
    
    top_no = df_chart.groupby('Họ tên')['Còn lại'].sum().sort_values(ascending=False).head(10).reset_index()
    
    fig1 = px.bar(top_no, x='Còn lại', y='Họ tên', orientation='h', text='Còn lại', 
                  color='Còn lại', color_continuous_scale='Rainbow', template='plotly_dark')
    fig1.update_traces(texttemplate='%{text:,.0f} VNĐ', textposition='inside')
    fig1.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
    
    st.plotly_chart(fig1, width="stretch")
