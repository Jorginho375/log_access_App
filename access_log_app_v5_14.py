
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

st.set_page_config(page_title="Access Control Analyzer", layout="wide")

# Theme toggle
theme = st.sidebar.radio("🌓 Theme", ["Light", "Dark"])
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
        st.markdown("### 🔐 Admin Login")
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

st.title("🔍 Access Control Log Analyzer")

uploaded_file = st.file_uploader("📂 Upload Access Log (.xls or .xlsx)", type=["xls", "xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = [col.strip() for col in df.columns]
    df['Time'] = pd.to_datetime(df['Time'], format='%d/%m/%Y %H:%M:%S')
    df['Date'] = df['Time'].dt.date
    df['Hour'] = df['Time'].dt.hour

    all_users = ['All'] + sorted(df['User'].unique())
    all_depts = ['All'] + sorted(df['Department'].fillna('Unknown').astype(str).unique())


    with st.sidebar.expander("🎛️ Filters", expanded=True):
        user_filter = st.selectbox("👤 Select User", options=all_users)
        dept_filter = st.selectbox("🏢 Select Department", options=all_depts)
        min_date = df['Date'].min()
        max_date = df['Date'].max()
        date_range = st.date_input("📅 Select Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

    filtered = df.copy()
    if user_filter != 'All':
        filtered = filtered[filtered['User'] == user_filter]
    if dept_filter != 'All':
        filtered = filtered[filtered['Department'] == dept_filter]
    filtered = filtered[(filtered['Date'] >= date_range[0]) & (filtered['Date'] <= date_range[1])]

    # Metrics
    col1, col2, col3 = st.columns(3)
    col1.metric("👥 Unique Users", filtered['User'].nunique())
    col2.metric("🚪 Total Accesses", len(filtered))

    # Check if 'Body Temp' column exists and is not empty
    if 'Body Temp' in filtered.columns and not filtered['Body Temp'].dropna().empty:
        temp_series = filtered['Body Temp'].astype(str).str.replace('°C', '', regex=False)
        temp_values = pd.to_numeric(temp_series, errors='coerce')
        high_temp_count = (temp_values > 37.5).sum()
        display_value = f"{high_temp_count} ⚠️"
    else:
        display_value = "N/A"

    # Display the metric
    col3.metric("🌡️ High Temps", display_value)

    
    # col3.metric("🌡️ High Temps", f"{(filtered['Body Temp'].str.replace('°C','').astype(float) > 37.5).sum()} ⚠️")

    # Timeline with temperature alerts
    st.markdown("### ⏳ Access Timeline")
    #filtered['TempFlag'] = filtered['Body Temp'].str.replace('°C','').astype(float) > 37.5
    filtered['TempFlag'] = (
    pd.to_numeric(
        filtered['Body Temp'].astype(str).str.replace('°C', '', regex=False),
        errors='coerce'
    ) > 37.5
)

    fig = px.scatter(filtered, x="Time", y="User", color="Entry/Exit", symbol="Entry/Exit",
                     color_discrete_map={"Entry": "green", "Exit": "blue"},
                     hover_data=["Body Temp"])
    fig.update_traces(marker=dict(size=8))
    for _, row in filtered[filtered['TempFlag']].iterrows():
        fig.add_scatter(x=[row['Time']], y=[row['User']], mode='markers',
                        marker=dict(size=12, color='red', symbol='x'), name='High Temp')
    st.plotly_chart(fig, use_container_width=True)

    # Heatmap
    st.markdown("### 🔥 Presence Heatmap (Hour vs Day by User)")
    heatmap_data = filtered.groupby(['User', 'Date', 'Hour'])['Card ID'].count().reset_index()
    fig = px.density_heatmap(heatmap_data, x='Date', y='Hour', z='Card ID', facet_row='User',
                             color_continuous_scale="Viridis", title="Presence Heatmap")
    st.plotly_chart(fig, use_container_width=True)

    # Weekly trend
    st.markdown("### 📈 Weekly Presence Trend (Total Hours per User)")
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

    # Detailed presence display
    st.markdown("### 🕒 Daily Detailed Presence Time")
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
    st.dataframe(pd.DataFrame(detailed))

    office_start = datetime.strptime("08:00", "%H:%M").time()
    office_end = datetime.strptime("18:00", "%H:%M").time()
    
    # Early Arrivals
    st.markdown("### 🌅 Early Arrivals (Before 08:00 AM)")
    early_arrivals = filtered[(filtered['Entry/Exit'] == 'Entry') & (filtered['Time'].dt.time < office_start)]
    st.info(f"🕗 {len(early_arrivals)} early arrivals detected.")
    with st.expander("📋 Show Early Arrivals"):
        st.dataframe(early_arrivals)

    # First Entry per User
    st.markdown("### 🚪 First Entry per User (in selected range)")
    first_entries = filtered[filtered['Entry/Exit'] == 'Entry'].sort_values('Time').groupby('User').first().reset_index()
    st.dataframe(first_entries[['User', 'Time', 'Department', 'Door', 'Body Temp']])

    # Last Exit per User
    st.markdown("### 🚪 Last Exit per User (in selected range)")
    last_exits = filtered[filtered['Entry/Exit'] == 'Exit'].sort_values('Time').groupby('User').last().reset_index()
    st.dataframe(last_exits[['User', 'Time', 'Department', 'Door', 'Body Temp']])

    # Alerts
    st.markdown("### ⚠️ Alerts")
    late_entries = filtered[(filtered['Entry/Exit'] == 'Entry') & (filtered['Time'].dt.time > office_start)]
    early_exits = filtered[(filtered['Entry/Exit'] == 'Exit') & (filtered['Time'].dt.time < office_end)]
    late_departures = filtered[(filtered['Entry/Exit'] == 'Exit') & (filtered['Time'].dt.time > office_end)]
    st.warning(f"🔻 Late Arrivals: {len(late_entries)}")
    st.warning(f"🔺 Early Exits: {len(early_exits)}")
    st.warning(f"🌙 Late Departures: {len(late_departures)}")

    with st.expander("📋 Show Late Arrivals"):
        st.dataframe(late_entries)
    with st.expander("📋 Show Early Exits"):
        st.dataframe(early_exits)
    with st.expander("📋 Show Late Departures"):
        st.dataframe(late_departures)

    # Absent users
    st.markdown("### 🚫 Absent Users")
    expected_users = df['User'].unique()
    present_users = filtered['User'].unique()
    absent_users = [u for u in expected_users if u not in present_users]
    st.error(f"{len(absent_users)} user(s) absent in selected range.")
    st.write(absent_users)

    # Export
    st.markdown("### 📤 Export Filtered Data")
    st.download_button("Download CSV", data=filtered.to_csv(index=False).encode('utf-8'),
                       file_name="filtered_access_logs.csv", mime="text/csv")
