import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="RevPAR & Occupancy Efficiency Analyzer", layout="wide")
st.title("RevPAR & Occupancy Efficiency Analyzer")
st.write("Upload your hotel bookings CSV to analyze Revenue Per Available Room and identify revenue gaps across time periods and market segments.")

# --- REQUIRED COLUMNS ---
REQUIRED_COLUMNS = [
    'reservation_status', 'adr', 'arrival_date_year',
    'arrival_date_month', 'arrival_date_day_of_month',
    'stays_in_weekend_nights', 'stays_in_week_nights', 'market_segment'
]

# --- FILE UPLOAD ---
uploaded_file = st.file_uploader("Upload your hotel bookings CSV", type="csv")

if uploaded_file is not None:

    # STUDENT NOTE: Load the uploaded CSV into a DataFrame
    df = pd.read_csv(uploaded_file)

    # STUDENT NOTE: Validate required columns are present before proceeding
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        st.error(f"Missing required columns: {missing}. Please check your file.")
        st.stop()

    st.subheader("Data Preview")
    st.dataframe(df.head(10))
```

Then **File → Save** and close Notepad.

Back in Command Prompt, also copy your `dataset.csv` into the `revpar_tool` folder. 

Then type:
```
streamlit run app.py