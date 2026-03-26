import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="RevPAR & Occupancy Efficiency Analyzer", layout="wide")

st.title("RevPAR & Occupancy Efficiency Analyzer")
st.write("Upload a hotel bookings CSV file to calculate RevPAR, compare market segments, and identify where revenue is being lost compared to peak performance.")

# STUDENT NOTE: These columns are required for the app to calculate RevPAR
# and generate the required visuals without crashing.
REQUIRED_COLUMNS = [
    'hotel',
    'reservation_status',
    'adr',
    'arrival_date_year',
    'arrival_date_month',
    'arrival_date_day_of_month',
    'stays_in_weekend_nights',
    'stays_in_week_nights',
    'market_segment'
]

uploaded_file = st.file_uploader("Upload your hotel bookings CSV", type="csv")

if uploaded_file is not None:
    # STUDENT NOTE: Read the uploaded CSV file into a pandas DataFrame
    # so the rest of the metric can be calculated from the user's file.
    df = pd.read_csv(uploaded_file)

    # STUDENT NOTE: Check if any required columns are missing.
    # If they are missing, stop the app and show the exact columns needed.
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        st.error(f"Missing required columns: {missing}. Please check your file.")
        st.stop()

    st.subheader("Data Preview")
    st.dataframe(df.head(10))

    # STUDENT NOTE: Create a hotel filter so the user can analyze one hotel
    # or all hotels together. This changes all the numbers and charts below.
    hotel_options = ['All'] + sorted(df['hotel'].dropna().unique().tolist())
    selected_hotel = st.selectbox("Filter by Hotel Type", hotel_options)

    # STUDENT NOTE: Apply the hotel filter only if one hotel is selected.
    if selected_hotel != 'All':
        df = df[df['hotel'] == selected_hotel]

    # STUDENT NOTE: Keep only checked-out bookings because those represent
    # completed stays that actually generated revenue.
    df_stayed = df[df['reservation_status'] == 'Check-Out'].copy()

    # STUDENT NOTE: Stop the app safely if there are no checked-out bookings
    # after the filter is applied, so the app does not break.
    if df_stayed.empty:
        st.warning("No checked-out bookings are available for the selected hotel filter.")
        st.stop()

    # STUDENT NOTE: Combine the separate arrival year, month, and day columns
    # into one real date column so bookings can be grouped by month and day.
    df_stayed['arrival_date'] = pd.to_datetime(
        df_stayed['arrival_date_year'].astype(str) + '-' +
        df_stayed['arrival_date_month'] + '-' +
        df_stayed['arrival_date_day_of_month'].astype(str),
        format='%Y-%B-%d'
    )

    # STUDENT NOTE: Calculate total nights stayed for each booking.
    # This is useful context for hotel stay patterns even though RevPAR is
    # mainly built from ADR and occupancy.
    df_stayed['total_nights'] = df_stayed['stays_in_weekend_nights'] + df_stayed['stays_in_week_nights']

    # STUDENT NOTE: Cap ADR at the 99th percentile to reduce the impact of
    # extreme outliers that would distort monthly averages.
    adr_cap = df_stayed['adr'].quantile(0.99)
    df_stayed['adr_capped'] = df_stayed['adr'].clip(upper=adr_cap)

    # STUDENT NOTE: Convert arrival dates into year-month periods so RevPAR
    # can be analyzed by month as required by the assignment.
    df_stayed['year_month'] = df_stayed['arrival_date'].dt.to_period('M')
    df_stayed['year_month_str'] = df_stayed['year_month'].astype(str)

    # STUDENT NOTE: Count completed bookings per month.
    # This is used as the occupancy part of the RevPAR calculation.
    total_bookings_per_month = df_stayed.groupby('year_month_str').size().reset_index(name='total_bookings')

    # STUDENT NOTE: Calculate the average capped ADR per month.
    # This gives the pricing side of monthly RevPAR.
    avg_adr_per_month = df_stayed.groupby('year_month_str')['adr_capped'].mean().reset_index(name='avg_adr')

    # STUDENT NOTE: Merge monthly booking volume and average ADR into one table
    # so RevPAR can be calculated in one monthly result DataFrame.
    monthly = total_bookings_per_month.merge(avg_adr_per_month, on='year_month_str')

    # STUDENT NOTE: Normalize booking counts against the busiest month to create
    # a relative occupancy rate between 0 and 1.
    peak_bookings = monthly['total_bookings'].max()
    monthly['occupancy_rate'] = monthly['total_bookings'] / peak_bookings

    # STUDENT NOTE: Calculate RevPAR using the standard formula:
    # RevPAR = Occupancy Rate × Average Daily Rate.
    monthly['revpar'] = monthly['occupancy_rate'] * monthly['avg_adr']

    # STUDENT NOTE: Identify the peak RevPAR and compare every month against it
    # to calculate the revenue gap.
    peak_revpar = monthly['revpar'].max()
    monthly['revenue_gap'] = peak_revpar - monthly['revpar']

    # STUDENT NOTE: Calculate the main KPI values that will appear at the top
    # of the app as metric cards.
    avg_revpar = monthly['revpar'].mean()
    total_gap = monthly['revenue_gap'].sum()
    peak_month = monthly.loc[monthly['revpar'].idxmax(), 'year_month_str']

    # STUDENT NOTE: Calculate average ADR and booking counts by market segment
    # to compare which segments are strongest on rate and occupancy together.
    segment_adr = df_stayed.groupby('market_segment')['adr_capped'].mean().reset_index(name='avg_adr')
    segment_count = df_stayed.groupby('market_segment').size().reset_index(name='total_bookings')

    # STUDENT NOTE: Merge the segment summaries so each segment has its average
    # ADR and booking count in one place.
    segment = segment_adr.merge(segment_count, on='market_segment')

    # STUDENT NOTE: Normalize booking counts against the largest segment so
    # segment occupancy can be compared on a relative basis.
    peak_segment_bookings = segment['total_bookings'].max()
    segment['occupancy_rate'] = segment['total_bookings'] / peak_segment_bookings

    # STUDENT NOTE: Calculate segment-level RevPAR so the user can see which
    # segments combine price and booking volume most effectively.
    segment['revpar'] = segment['occupancy_rate'] * segment['avg_adr']
    segment = segment.sort_values('revpar', ascending=False).reset_index(drop=True)

    # STUDENT NOTE: Extract month name and day of week from the arrival date
    # so a seasonal pricing heatmap can be built.
    df_stayed['day_of_week'] = df_stayed['arrival_date'].dt.day_name()
    df_stayed['month_name'] = df_stayed['arrival_date'].dt.month_name()

    # STUDENT NOTE: Calculate average ADR by month and day of week to show
    # where pricing tends to be strongest across the calendar.
    heatmap_data = df_stayed.groupby(['month_name', 'day_of_week'])['adr_capped'].mean().reset_index(name='avg_adr')

    # STUDENT NOTE: Pivot the grouped data into matrix form because Plotly
    # heatmaps need rows and columns instead of a long table.
    heatmap_pivot = heatmap_data.pivot(index='day_of_week', columns='month_name', values='avg_adr')

    # STUDENT NOTE: Reorder the heatmap rows and columns into normal calendar
    # order so the chart is easier for a business user to read.
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    heatmap_pivot = heatmap_pivot.reindex(index=day_order, columns=month_order)

    st.subheader("Key Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Average RevPAR", f"EUR {avg_revpar:.2f}")
    col2.metric("Peak RevPAR", f"EUR {peak_revpar:.2f}", f"Peak month: {peak_month}")
    col3.metric("Total Revenue Gap", f"EUR {total_gap:.2f}")

    st.subheader("Monthly RevPAR Trend")

    # STUDENT NOTE: Build a line chart to show how RevPAR changes over time
    # and make it easy to spot strong and weak months.
    fig1 = px.line(
        monthly,
        x='year_month_str',
        y='revpar',
        title='Monthly RevPAR Trend',
        labels={
            'year_month_str': 'Month',
            'revpar': 'RevPAR (EUR)'
        },
        markers=True
    )
    fig1.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig1, use_container_width=True)

    st.subheader("ADR vs Occupancy Rate by Market Segment")

    # STUDENT NOTE: Build a scatter plot to compare segments on both average ADR
    # and occupancy at the same time, with bubble size showing RevPAR strength.
    fig2 = px.scatter(
        segment,
        x='occupancy_rate',
        y='avg_adr',
        text='market_segment',
        size='revpar',
        title='ADR vs Occupancy Rate by Market Segment',
        labels={
            'occupancy_rate': 'Occupancy Rate (relative)',
            'avg_adr': 'Average Daily Rate (EUR)',
            'revpar': 'RevPAR'
        },
        color='market_segment'
    )
    fig2.update_traces(textposition='top center')
    fig2.update_layout(showlegend=False)
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("ADR Heatmap by Day of Week and Month")

    # STUDENT NOTE: Build a heatmap to show which month and day combinations
    # have the strongest average daily rate patterns.
    fig3 = px.imshow(
        heatmap_pivot,
        title='Average ADR by Day of Week and Month',
        labels={'x': 'Month', 'y': 'Day of Week', 'color': 'Avg ADR (EUR)'},
        color_continuous_scale='RdYlGn',
        aspect='auto'
    )
    st.plotly_chart(fig3, use_container_width=True)

    # STUDENT NOTE: Add a plain-English interpretation panel so a business user
    # understands what the metric means and what to focus on.
    st.info(
        f"RevPAR shows how well a hotel turns available rooms into revenue by combining room rate and occupancy. "
        f"For the current selection, the average RevPAR is EUR {avg_revpar:.2f}, while the peak RevPAR is EUR {peak_revpar:.2f} in {peak_month}. "
        f"The total revenue gap is EUR {total_gap:.2f}, which shows how much performance falls below the strongest month. "
        f"Segments with strong ADR but weaker occupancy should be targeted first, because improving volume in those segments can help close the revenue gap."
    )
