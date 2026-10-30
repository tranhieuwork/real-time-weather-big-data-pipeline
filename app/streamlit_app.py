import streamlit as st
import pandas as pd
import s3fs

# =========================
# CONFIG
# =========================
st.set_page_config(
    page_title="Temperature Forecast & Travel Recommendation",
    layout="wide"
)

st.title("🌡️ Temperature Forecast & City Recommendation System")
st.markdown(
    "Hệ thống dự đoán nhiệt độ theo thời gian và đề xuất thành phố du lịch phù hợp."
)

# =========================
# MINIO CONNECTION
# =========================
@st.cache_data(ttl=300)
def load_csv_from_minio(path):
    fs = s3fs.S3FileSystem(
        key="minioadmin",
        secret="minioadmin",
        client_kwargs={"endpoint_url": "http://18.219.196.163:9000"}
    )
    with fs.open(path, mode="rb") as f:
        df = pd.read_csv(f)
    return df

# =========================
# LOAD DATA
# =========================
CITY_FILES = {
    "Cần Thơ": "iot-data/prediction/7day_forecast_Can_Tho.csv",
    "Đà Nẵng": "iot-data/prediction/7day_forecast_Da_Nang.csv",
    "Hà Nội": "iot-data/prediction/7day_forecast_Ha_Noi.csv",
    "Hải Phòng": "iot-data/prediction/7day_forecast_Hai_Phong.csv",
}

city_data = {}
for city, path in CITY_FILES.items():
    df = load_csv_from_minio(path)

    # Normalize schema
    df = df.rename(columns={
        "timestamp": "date",
        "predicted_temperature": "temp"
    })

    df["date"] = pd.to_datetime(df["date"])
    df["city"] = city
    city_data[city] = df

# =========================
# SIDEBAR
# =========================
menu = st.sidebar.radio(
    "📂 Chọn chức năng",
    ["📊 Dự đoán nhiệt độ", "🏖️ Đề xuất thành phố"]
)

# =====================================================
# TAB 1: TEMPERATURE FORECAST
# =====================================================
if menu == "📊 Dự đoán nhiệt độ":

    city_selected = st.selectbox("Chọn thành phố", city_data.keys())
    df = city_data[city_selected]

    st.subheader("📋 Dữ liệu dự đoán")
    st.dataframe(df[["date", "hour", "temp"]], use_container_width=True)

    # --- Chart 1: Time series ---
    st.subheader("📈 Nhiệt độ theo thời gian")
    st.line_chart(df.set_index("date")["temp"])

    # --- Chart 2: Hourly pattern ---
    st.subheader("🕒 Nhiệt độ trung bình theo giờ")
    hourly_avg = df.groupby("hour")["temp"].mean()
    st.line_chart(hourly_avg)

    # --- Chart 3: Temperature distribution (FIXED) ---
    st.subheader("📊 Phân bố nhiệt độ")

    temp_bins = pd.cut(df["temp"], bins=8)
    temp_dist = temp_bins.value_counts().sort_index()

    # 🔧 FIX QUAN TRỌNG: Interval → string
    temp_dist.index = temp_dist.index.astype(str)

    st.bar_chart(temp_dist)

# =====================================================
# TAB 2: CITY RECOMMENDATION
# =====================================================
else:
    st.subheader("🏖️ Đề xuất thành phố cho ngày mai")

    temp_pref = st.selectbox(
        "Bạn thích thời tiết như thế nào?",
        ["Lạnh (≤ 20°C)", "Mát mẻ (20–30°C)", "Nóng (≥ 30°C)"]
    )

    def temp_score(temp):
        if temp_pref == "Lạnh (≤ 20°C)":
            return 1 if temp <= 20 else 0
        if temp_pref == "Mát mẻ (20–30°C)":
            return 1 if 20 < temp <= 30 else 0
        return 1 if temp >= 30 else 0

    results = []
    for city, df in city_data.items():
        avg_temp = df["temp"].mean()
        score = temp_score(avg_temp)

        results.append({
            "city": city,
            "avg_temp": round(avg_temp, 2),
            "score": score
        })

    result_df = pd.DataFrame(results).sort_values("score", ascending=False)

    st.subheader("📋 Kết quả đánh giá")
    st.dataframe(result_df, use_container_width=True)

    best = result_df.iloc[0]
    st.success(
        f"🏆 **Thành phố phù hợp nhất: {best['city']}**\n\n"
        f"🌡️ Nhiệt độ trung bình dự đoán: **{best['avg_temp']}°C**"
    )

    # --- Chart 4: Avg temperature comparison ---
    st.subheader("📊 So sánh nhiệt độ trung bình")
    st.bar_chart(result_df.set_index("city")["avg_temp"])

    # --- Chart 5: Suitability score ---
    st.subheader("⭐ Mức độ phù hợp theo nhu cầu người dùng")
    st.bar_chart(result_df.set_index("city")["score"])
