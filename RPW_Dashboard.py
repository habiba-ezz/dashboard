# RPW_Dashboard.py
import streamlit as st
import pandas as pd
import os
import matplotlib.pyplot as plt
from PIL import Image

# -------- CONFIG --------
DATA_DIR = "D:/Data"  # Change this to the correct full path if needed

if not os.path.exists(DATA_DIR):
    st.error(f"DATA_DIR not found: {DATA_DIR}")
    st.stop()

# -------- SETUP --------
st.set_page_config(layout="wide")
st.title("🌴 Palm Health Dashboard")

# -------- HELPERS --------
def get_all_dates():
    return sorted([d for d in os.listdir(DATA_DIR) if os.path.isdir(os.path.join(DATA_DIR, d))])

def load_data(date_folder):
    path = os.path.join(DATA_DIR, date_folder, "classified_index.csv")
    if os.path.exists(path):
        df = pd.read_csv(path)
        df.columns = df.columns.str.lower().str.strip()
        if 'class' in df.columns:
            df['class'] = df['class'].str.lower()
        df['__date__'] = date_folder
        return df
    return None

def load_image_if_exists(path):
    return Image.open(path) if os.path.exists(path) else None

def classify_health(row):
    if row['class'] != 'palm':
        return 'Soil'
    elif row['ndvi'] >= 0.6:
        return 'Healthy'
    elif row['ndvi'] >= 0.3:
        return 'Moderate'
    else:
        return 'Unhealthy'

# -------- LOAD ALL DATA --------
all_dates = get_all_dates()
if not all_dates:
    st.error("No dated folders found inside the 'data' directory.")
    st.stop()

all_data = []
for d in all_dates:
    df = load_data(d)
    if df is not None:
        all_data.append(df)

if not all_data:
    st.error("No valid CSV files found in any dated folder.")
    st.stop()

# Combine all dates into one DataFrame
full_df = pd.concat(all_data, ignore_index=True)

# ✅ Assign health_status before slicing
if 'health_status' not in full_df.columns:
    if 'ndvi' in full_df.columns:
        full_df['health_status'] = full_df.apply(classify_health, axis=1)
    else:
        st.error("Missing NDVI column — can't classify health.")
        st.stop()

# Sidebar: Date selection
selected_date = st.sidebar.selectbox("🗓️ Select a Date", all_dates)
selected_df = full_df[full_df['__date__'] == selected_date]
selected_palm_df = selected_df[selected_df['class'] == 'palm']

# -------- KPIs --------
st.markdown(f"### 📊 Palm Health KPIs for {selected_date}")
col1, col2, col3, col4 = st.columns(4)
h = selected_palm_df[selected_palm_df['health_status'] == 'Healthy'].shape[0]
m = selected_palm_df[selected_palm_df['health_status'] == 'Moderate'].shape[0]
u = selected_palm_df[selected_palm_df['health_status'] == 'Unhealthy'].shape[0]
t = selected_palm_df.shape[0]
col1.metric("🌿 Healthy", h)
col2.metric("⚠️ Moderate", m)
col3.metric("🛑 Unhealthy", u)
col4.metric("🌴 Total Palms", t)

# -------- PIE CHART --------
st.markdown("### Health Distribution Pie Chart")
pie_data = selected_palm_df['health_status'].value_counts()
colors = {'Healthy': "#07af52", 'Moderate': "#faba08", 'Unhealthy': "#ec0505"}
fig, ax = plt.subplots()
ax.pie(pie_data.values, labels=pie_data.index, autopct='%1.1f%%', colors=[colors.get(k, "#ccc") for k in pie_data.index])
ax.axis('equal')
st.pyplot(fig)

# -------- RESI BAR CHART --------
if 'resi' in selected_palm_df.columns:
    st.markdown("### 📈 RESI by Health Status")
    resi_avg = selected_palm_df.groupby('health_status')['resi'].mean()
    st.bar_chart(resi_avg)
    
# -------- HEALTH MAP IMAGE --------
map_path = os.path.join(DATA_DIR, selected_date, "visualizations", f"{selected_date}_health_grid.png")
st.markdown("### 🗺️ Health Map")
map_img = load_image_if_exists(map_path)
if map_img:
    st.image(map_img, caption="Health Grid Map", use_container_width=True)
else:
    st.info("No health map found for this date.")

# --------- INDEX HEATMAPS ---------
st.markdown("---")
st.subheader("🌡️ Vegetation Index Heatmaps")

index_names = ['NDVI', 'NDWI', 'RESI', 'SQRT(IR_R)', 'GVI', 'DVI', 'RDVI']
cols = st.columns(3)

for idx, index in enumerate(index_names):
    image_filename = f"{selected_date}_{index}_grid1.png"
    image_path = os.path.join(DATA_DIR, selected_date, image_filename)
    img = load_image_if_exists(image_path)
    with cols[idx % 3]:
        if img:
            st.image(img, caption=f"{index} Grid Heatmap", use_container_width=True)
        else:
            st.info(f"{index} heatmap not found.")

# -------- MODERATE & UNHEALTHY PALM LOCATIONS --------
st.markdown("### 📍 At-Risk Palm Tree Locations (Moderate + Unhealthy)")

# Filter for palm only, moderate/unhealthy
risky_palms = selected_palm_df[selected_palm_df['health_status'].isin(['Moderate', 'Unhealthy'])]

if not risky_palms.empty:
    # Only display useful columns
    display_cols = ['health_status', 'latitude', 'longitude']
    st.dataframe(risky_palms[display_cols].sort_values(by='health_status'), use_container_width=True)

    # Optionally add download
    csv_data = risky_palms[display_cols].to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Locations CSV",
        data=csv_data,
        file_name=f"{selected_date}_at_risk_palm_locations.csv",
        mime="text/csv"
    )
else:
    st.info("✅ No moderate or unhealthy palms found for this date.")


# -------- TIME SERIES LINE CHART --------
st.markdown("### 📉 Health Trends Over Time")
palm_df = full_df[full_df['class'] == 'palm']
time_series = palm_df.groupby(['__date__', 'health_status']).size().unstack(fill_value=0)
st.line_chart(time_series)

# -------- DOWNLOAD BUTTON --------
st.download_button(
    label="📥 Download All Palm Data",
    data=palm_df.to_csv(index=False).encode('utf-8'),
    file_name="all_palm_health_data.csv",
    mime="text/csv"
)

