import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from fpdf import FPDF
from io import BytesIO

st.set_page_config(page_title="Access Control Analyzer", layout="wide")

# Theme toggle
theme = st.sidebar.radio("\U0001F319 Theme", ["Light", "Dark"])
if theme == "Dark":
    st.markdown('<style>body { color: white; background-color: #1E1E1E; }</style>', unsafe_allow_html=True)

# Dummy login
users_db = {'admin': 'password123'}
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    with st.container():
        st.markdown('<div class="login-container" style="position: absolute;top: 50%;left: 50%;transform: translate(-50%, -50%);background-color: rgba(255, 255, 255, 0.9);padding: 2rem 3rem;border-radius: 20px;box-shadow: 0 8px 20px rgba(0,0,0,0.3);width: 400px;text-align: center;">', unsafe_allow_html=True)
        st.image("https://img.icons8.com/fluency/96/000000/fingerprint-scan.png", width=70)
        st.markdown("### \U0001F510 Admin Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if users_db.get(username) == password:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Invalid credentials")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

st.title("\U0001F50D Access Control Log Analyzer")

uploaded_file = st.file_uploader("\U0001F4C2 Upload Access Log (.xls or .xlsx)", type=["xls", "xlsx"])

# PDF Export utility
def generate_pdf_from_df(dataframe, title):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 10, title, align='C')
    pdf.ln(5)

    col_width = 190 // len(dataframe.columns)
    row_height = 8

    for col in dataframe.columns:
        pdf.cell(col_width, row_height, str(col), border=1)
    pdf.ln(row_height)

    for _, row in dataframe.iterrows():
        for item in row:
            pdf.cell(col_width, row_height, str(item), border=1)
        pdf.ln(row_height)

    buffer = BytesIO()
    pdf.output(buffer)
    buffer.seek(0)
    return buffer

if uploaded_file:
    df = pd.read_excel(uploaded_file, engine='xlrd')
    df.columns = [col.strip() for col in df.columns]
    df['Time'] = pd.to_datetime(df['Time'], format='%d/%m/%Y %H:%M:%S')
    df['Date'] = df['Time'].dt.date
    df['Hour'] = df['Time'].dt.hour

    all_users = ['All'] + sorted(df['User'].unique())
    all_depts = ['All'] + sorted(df['Department'].fillna('Unknown').astype(str).unique())

    with st.sidebar.expander("\U0001F9BC Filters", expanded=True):
        user_filter = st.selectbox("\U0001F464 Select User", options=all_users)
        dept_filter = st.selectbox("\U0001F3E2 Select Department", options=all_depts)
        min_date = df['Date'].min()
        max_date = df['Date'].max()
        date_range = st.date_input("\U0001F4C5 Select Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

    filtered = df.copy()
    if user_filter != 'All':
        filtered = filtered[filtered['User'] == user_filter]
    if dept_filter != 'All':
        filtered = filtered[filtered['Department'] == dept_filter]
    filtered = filtered[(filtered['Date'] >= date_range[0]) & (filtered['Date'] <= date_range[1])]

    col1, col2, col3 = st.columns(3)
    col1.metric("\U0001F465 Unique Users", filtered['User'].nunique())
    col2.metric("\U0001F6AA Total Accesses", len(filtered))

    if 'Body Temp' in filtered.columns and not filtered['Body Temp'].dropna().empty:
        temp_series = filtered['Body Temp'].astype(str).str.replace('°C', '', regex=False)
        temp_values = pd.to_numeric(temp_series, errors='coerce')
        high_temp_count = (temp_values > 37.5).sum()
        display_value = f"{high_temp_count} \u26A0\uFE0F"
    else:
        display_value = "N/A"

    col3.metric("\U0001F321\uFE0F High Temps", display_value)

    st.markdown("### ⏳ Access Timeline")
    filtered['TempFlag'] = pd.to_numeric(filtered['Body Temp'].astype(str).str.replace('°C', '', regex=False), errors='coerce') > 37.5

    fig = px.scatter(filtered, x="Time", y="User", color="Entry/Exit", symbol="Entry/Exit",
                     color_discrete_map={"Entry": "green", "Exit": "blue"},
                     hover_data=["Body Temp"])
    fig.update_traces(marker=dict(size=8))
    for _, row in filtered[filtered['TempFlag']].iterrows():
        fig.add_scatter(x=[row['Time']], y=[row['User']], mode='markers',
                        marker=dict(size=12, color='red', symbol='x'), name='High Temp')
    st.plotly_chart(fig, use_container_width=True)
    st.download_button("\U0001F4C4 Download Timeline PDF", data=generate_pdf_from_df(filtered[['Time','User','Entry/Exit','Body Temp']], "Access Timeline"), file_name="timeline.pdf", mime="application/pdf")

    st.markdown("### 🔥 Presence Heatmap (Hour vs Day by User)")
    heatmap_data = filtered.groupby(['User', 'Date', 'Hour'])['Card ID'].count().reset_index()
    fig = px.density_heatmap(heatmap_data, x='Date', y='Hour', z='Card ID', facet_row='User', color_continuous_scale="Viridis")
    st.plotly_chart(fig, use_container_width=True)
    st.download_button("\U0001F4C4 Download Heatmap Data PDF", data=generate_pdf_from_df(heatmap_data, "Heatmap Data"), file_name="heatmap.pdf", mime="application/pdf")

    st.markdown("### \U0001F4C8 Weekly Presence Trend (Total Hours per User)")
    presence = []
    for user in filtered['User'].unique():
        user_data = filtered[filtered['User'] == user]
        for date in user_data['Date'].unique():
            day_data = user_data[user_data['Date'] == date].sort_values('Time')
            entries = day_data[day_data["Entry/Exit"] == "Entry"]['Time'].tolist()
            exits = day_data[day_data["Entry/Exit"] == "Exit"]['Time'].tolist()
            total_duration = timedelta()
            for entry, exit in zip(entries, exits):
                if exit > entry:
                    total_duration += (exit - entry)
            hours = round(total_duration.total_seconds() / 3600, 2)
            presence.append({"Date": date, "User": user, "Hours": hours})
    trend_df = pd.DataFrame(presence)
    st.plotly_chart(px.line(trend_df, x="Date", y="Hours", color="User", markers=True), use_container_width=True)
    st.download_button("\U0001F4C4 Download Trend PDF", data=generate_pdf_from_df(trend_df, "Weekly Presence Trend"), file_name="trend.pdf", mime="application/pdf")

    st.markdown("### \U0001F551 Daily Detailed Presence Time")
    detailed = []
    for user in filtered['User'].unique():
        user_data = filtered[filtered['User'] == user]
        for date in user_data['Date'].unique():
            day_data = user_data[user_data['Date'] == date].sort_values('Time')
            entries = day_data[day_data["Entry/Exit"] == "Entry"]['Time'].tolist()
            exits = day_data[day_data["Entry/Exit"] == "Exit"]['Time'].tolist()
            total_duration = timedelta()
            for entry, exit in zip(entries, exits):
                if exit > entry:
                    total_duration += (exit - entry)
            h, r = divmod(total_duration.total_seconds(), 3600)
            m, s = divmod(r, 60)
            readable = f"{int(h)}h {int(m)}m {int(s)}s"
            detailed.append({"Date": date, "User": user, "Presence Time": readable})
    detailed_df = pd.DataFrame(detailed)
    st.dataframe(detailed_df)
    st.download_button("\U0001F4C4 Download Detailed Presence PDF", data=generate_pdf_from_df(detailed_df, "Daily Detailed Presence"), file_name="detailed_presence.pdf", mime="application/pdf")
