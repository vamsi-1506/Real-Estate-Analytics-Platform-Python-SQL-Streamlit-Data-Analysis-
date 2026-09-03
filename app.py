"""
🏠 REAL ESTATE DATA EXPLORER
A comprehensive Streamlit app for real estate data analysis, visualization, and management
"""

import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from datetime import datetime


# ==================== PAGE CONFIGURATION ====================
st.set_page_config(
    page_title="🏠 Real Estate Data Explorer",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== DATABASE CONNECTION ====================
@st.cache_resource
def get_db_connection():
    """Create and cache database connection"""
    connection = sqlite3.connect(
        "real_estate.db",
        check_same_thread=False
    )
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

conn = get_db_connection()

# ==================== SIDEBAR - NAVIGATION ====================
st.sidebar.title("🏢 Real Estate Explorer")
page = st.sidebar.radio(
    "Select Page",
    ["📊 Dashboard", "🔍 Filters & Search", "📈 Visualizations", "⚙️ CRUD Operations", "🔎 SQL Queries"]
)

# ==================== PAGE 1: DASHBOARD ====================
if page == "📊 Dashboard":
    st.title("🏠 Real Estate Data Dashboard")
    st.markdown("---")
    
    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_listings = pd.read_sql("SELECT COUNT(*) as count FROM listings", conn)['count'].iloc[0]
        st.metric("Total Listings", f"{total_listings:,}")
    
    with col2:
        avg_price = pd.read_sql("SELECT ROUND(AVG(Price), 2) as price FROM listings", conn)['price'].iloc[0]
        st.metric("Average Price", f"{avg_price:,.2f}")
    
    with col3:
        total_sales = pd.read_sql("SELECT COUNT(*) as count FROM sales", conn)['count'].iloc[0]
        st.metric("Total Sales", f"{total_sales:,}")
    
    with col4:
        active_agents = pd.read_sql("SELECT COUNT(*) as count FROM agents", conn)['count'].iloc[0]
        st.metric("Active Agents", f"{active_agents:,}")
    
    st.markdown("---")
    
    # Quick Stats
    st.subheader("📊 Quick Statistics")
    col1, col2 = st.columns(2)
    
    with col1:
        city_stats = pd.read_sql("""
            SELECT City, COUNT(*) as Properties, ROUND(AVG(Price), 2) as Avg_Price
            FROM listings
            GROUP BY City
            ORDER BY Properties DESC
        """, conn)
        st.dataframe(city_stats, use_container_width=True)
    
    with col2:
        property_stats = pd.read_sql("""
            SELECT Property_Type, COUNT(*) as Count, ROUND(AVG(Price), 2) as Avg_Price
            FROM listings
            GROUP BY Property_Type
            ORDER BY Count DESC
        """, conn)
        st.dataframe(property_stats, use_container_width=True)


# ==================== PAGE 2: FILTERS & SEARCH ====================
elif page == "🔍 Filters & Search":
    st.title("🔍 Advanced Filters & Search")
    st.markdown("---")

    with st.form("filter_form"):
        col1, col2 = st.columns(2)

        # City Filter
        with col1:
            cities = pd.read_sql(
                "SELECT DISTINCT City FROM listings ORDER BY City",
                conn
            )['City'].tolist()

            selected_cities = st.multiselect(
                "🏙️ Select Cities",
                cities,
                default=cities[:2]
            )

        # Property Type Filter
        with col2:
            prop_types = pd.read_sql(
                "SELECT DISTINCT Property_Type FROM listings ORDER BY Property_Type",
                conn
            )['Property_Type'].tolist()

            selected_types = st.multiselect(
                "🏠 Property Types",
                prop_types,
                default=prop_types
            )

        col1, col2 = st.columns(2)

        price_stats = pd.read_sql("""
            SELECT MIN(Price) AS min_price,
                MAX(Price) AS max_price
            FROM listings
        """, conn)

        min_price = int(price_stats["min_price"].iloc[0])
        max_price = int(price_stats["max_price"].iloc[0])

        # Price Range
        with col1:
            price_range = st.slider(
                "💰 Price Range",
                min_value=min_price,
                max_value=max_price,
                value=(min_price, max_price)
            )

        # Agent Filter
        with col2:
            agents = pd.read_sql(
                "SELECT DISTINCT Name FROM agents ORDER BY Name",
                conn
            )['Name'].tolist()

            selected_agent = st.selectbox(
                "👤 Filter by Agent (Optional)",
                ["All Agents"] + agents
            )

        # Date Range
        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input(
                "📅 Start Date",
                value=datetime(2023, 1, 1)
            )

        with col2:
            end_date = st.date_input(
                "📅 End Date",
                value=datetime.now()
            )

        col1, col2 = st.columns([1, 3])

        with col1:
            submit_btn = st.form_submit_button(
                "🔍 Search",
                use_container_width=True
            )

    # ============================================================
    # RUN SEARCH ONLY WHEN SEARCH BUTTON IS CLICKED
    # ============================================================

    if submit_btn:

        # Prevent empty IN clauses
        if not selected_cities:
            st.warning("Please select at least one city.")
            st.stop()

        if not selected_types:
            st.warning("Please select at least one property type.")
            st.stop()

        # Create placeholders for SQL IN clauses
        city_placeholders = ",".join(["?"] * len(selected_cities))
        type_placeholders = ",".join(["?"] * len(selected_types))

        query = f"""
            SELECT
                l.*,
                pa.bedrooms,
                pa.bathrooms,
                pa.furnishing_status,
                pa.year_built
            FROM listings l
            LEFT JOIN property_attributes pa
                ON l.Listing_ID = pa.listing_id
            WHERE l.City IN ({city_placeholders})
            AND l.Property_Type IN ({type_placeholders})
            AND l.Price BETWEEN ? AND ?
            AND l.Date_Listed BETWEEN ? AND ?
        """

        params = (
            selected_cities
            + selected_types
            + [
                price_range[0],
                price_range[1],
                str(start_date),
                str(end_date)
            ]
        )

        # Agent filter
        if selected_agent != "All Agents":
            query += """
                AND l.Agent_ID IN (
                    SELECT Agent_ID
                    FROM agents
                    WHERE Name = ?
                )
            """
            params = list(params)
            params.append(selected_agent)
            params = tuple(params)

        query += " LIMIT 1000"

        try:
            results = pd.read_sql(
                query,
                conn,
                params=params
            )

            # SAVE RESULTS IN SESSION STATE
            st.session_state["search_results"] = results

        except Exception as e:
            st.error(f"❌ Error: {e}")
            st.stop()

    # ============================================================
    # DISPLAY SAVED SEARCH RESULTS
    # ============================================================

    if "search_results" in st.session_state:

        results = st.session_state["search_results"]

        st.subheader(f"✅ Found {len(results)} Listings")

        if len(results) > 0:

            # Results per page
            page_size = st.selectbox(
                "Results per page",
                [10, 25, 50, 100],
                index=1,
                key="search_page_size"
            )

            # Calculate number of pages
            num_pages = max(
                1,
                (len(results) + page_size - 1) // page_size
            )

            # Page number
            page_num = st.number_input(
                "Page",
                min_value=1,
                max_value=num_pages,
                value=1,
                step=1,
                key="search_page_num"
            )

            # Calculate rows to display
            start_idx = (page_num - 1) * page_size
            end_idx = min(
                start_idx + page_size,
                len(results)
            )

            # Display records
            st.dataframe(
                results.iloc[start_idx:end_idx],
                use_container_width=True,
                height=400
            )

            st.caption(
                f"Page {page_num} of {num_pages} | "
                f"Showing records {start_idx + 1}–{end_idx} "
                f"of {len(results)}"
            )

        else:
            st.warning(
                "❌ No listings found matching your criteria"
            )


# ==================== PAGE 3: VISUALIZATIONS ====================
elif page == "📈 Visualizations":
    st.title("📈 Data Visualizations")
    st.markdown("---")

    viz_type = st.selectbox(
        "📊 Select Visualization",
        [
            "City Price Distribution",
            "Property Type Distribution",
            "Price by City",
            "Monthly Sales Trend",
            "Agent Performance",
            "Bedrooms Impact",
            "Price Buckets"
        ],
        key="viz_type"
    )

    # ==================== 1. CITY PRICE DISTRIBUTION ====================
    if viz_type == "City Price Distribution":
        st.subheader("📊 Average Price by City")

        data = pd.read_sql("""
            SELECT
                City,
                COUNT(*) AS Listings,
                ROUND(AVG(Price), 2) AS Avg_Price
            FROM listings
            GROUP BY City
            ORDER BY Avg_Price DESC
        """, conn)

        fig = px.bar(
            data,
            x="City",
            y="Avg_Price",
            title="Average Property Price by City",
            color="Avg_Price",
            color_continuous_scale="Viridis"
        )

        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(data, use_container_width=True)

    # ==================== 2. PROPERTY TYPE DISTRIBUTION ====================
    elif viz_type == "Property Type Distribution":
        st.subheader("🏠 Property Type Distribution")

        data = pd.read_sql("""
            SELECT
                Property_Type,
                COUNT(*) AS Count
            FROM listings
            GROUP BY Property_Type
        """, conn)

        fig = px.pie(
            data,
            names="Property_Type",
            values="Count",
            title="Distribution of Property Types"
        )

        st.plotly_chart(fig, use_container_width=True)

    # ==================== 3. PRICE BY CITY ====================
    elif viz_type == "Price by City":
        st.subheader("💰 Price Range by City")

        data = pd.read_sql("""
            SELECT
                City,
                ROUND(MIN(Price), 2) AS Min_Price,
                ROUND(AVG(Price), 2) AS Avg_Price,
                ROUND(MAX(Price), 2) AS Max_Price
            FROM listings
            GROUP BY City
            ORDER BY Avg_Price DESC
        """, conn)

        fig = px.bar(
            data,
            x="City",
            y=["Min_Price", "Avg_Price", "Max_Price"],
            title="Price Range by City",
            barmode="group"
        )

        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(data, use_container_width=True)

    # ==================== 4. MONTHLY SALES TREND ====================
    elif viz_type == "Monthly Sales Trend":
        st.subheader("📈 Monthly Sales Trend")

        data = pd.read_sql("""
            SELECT
                strftime('%Y-%m', Date_Sold) AS Sale_Month,
                COUNT(*) AS Sales,
                ROUND(AVG(Sale_Price), 2) AS Avg_Sale
            FROM sales
            GROUP BY strftime('%Y-%m', Date_Sold)
            ORDER BY Sale_Month
        """, conn)

        if len(data) > 0:
            fig = px.line(
                data,
                x="Sale_Month",
                y="Sales",
                title="Sales Trend Over Time"
            )

            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(data, use_container_width=True)

        else:
            st.warning("No sales data available")

    # ==================== 5. AGENT PERFORMANCE ====================
    elif viz_type == "Agent Performance":
        st.subheader("👥 Top Agent Performance")

        data = pd.read_sql("""
            SELECT
                a.Name,
                a.deals_closed,
                ROUND(a.rating, 2) AS rating,
                a.commission_rate
            FROM agents a
            ORDER BY a.deals_closed DESC
            LIMIT 10
        """, conn)

        fig = px.bar(
            data,
            x="Name",
            y="deals_closed",
            color="rating",
            title="Top 10 Agents by Deals Closed",
            hover_data=["commission_rate"]
        )

        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(data, use_container_width=True)

    # ==================== 6. BEDROOMS IMPACT ====================
    elif viz_type == "Bedrooms Impact":
        st.subheader("🛏️ Price by Number of Bedrooms")

        data = pd.read_sql("""
            SELECT
                pa.bedrooms,
                ROUND(AVG(l.Price), 2) AS Avg_Price,
                COUNT(*) AS Count
            FROM listings l
            JOIN property_attributes pa
                ON l.Listing_ID = pa.listing_id
            GROUP BY pa.bedrooms
            ORDER BY pa.bedrooms
        """, conn)

        fig = px.bar(
            data,
            x="bedrooms",
            y="Avg_Price",
            title="Average Price by Bedrooms",
            color="Count",
            color_continuous_scale="Blues"
        )

        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(data, use_container_width=True)

    # ==================== 7. PRICE BUCKETS ====================
    elif viz_type == "Price Buckets":
        st.subheader("💵 Market Distribution by Price Bucket")

        data = pd.read_sql("""
            SELECT
                CASE
                    WHEN Price < 500000 THEN 'Under $500K'
                    WHEN Price < 1000000 THEN '$500K - $1M'
                    WHEN Price < 1500000 THEN '$1M - $1.5M'
                    WHEN Price < 2000000 THEN '$1.5M - $2M'
                    WHEN Price < 3000000 THEN '$2M - $3M'
                    ELSE '$3M+'
                END AS Bucket,
                COUNT(*) AS Count
            FROM listings
            GROUP BY Bucket
            ORDER BY COUNT(*) DESC
        """, conn)

        fig = px.pie(
            data,
            names="Bucket",
            values="Count",
            title="Properties by Price Bucket"
        )

        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(data, use_container_width=True)



# ==================== PAGE 4: CRUD OPERATIONS ====================
elif page == "⚙️ CRUD Operations":

    st.title("⚙️ CRUD Operations")
    st.markdown("---")

    # Table selection
    tables = {
        "AGENTS": "agents",
        "LISTINGS": "listings",
        "PROPERTY_ATTRIBUTES": "property_attributes",
        "BUYERS": "buyers",
        "SALES": "sales"
    }

    table_label = st.selectbox(
        "Select Table",
        list(tables.keys())
    )

    table = tables[table_label]

    operation = st.radio(
        "Select Operation",
        ["➕ Create", "📖 Read", "✏️ Update", "🗑️ Delete"],
        horizontal=True
    )

    # Get table structure
    info = pd.read_sql(
        f"PRAGMA table_info({table})",
        conn
    )

    columns = info["name"].tolist()

    # Primary key
    pk_rows = info[info["pk"] == 1]

    if not pk_rows.empty:
        pk = pk_rows.iloc[0]["name"]
    else:
        pk = columns[0]

    # ============================================================
    # CREATE
    # ============================================================

    if operation == "➕ Create":

        st.subheader(f"➕ Add {table_label} Record")

        values = {}

        with st.form("create_form"):

            for _, row in info.iterrows():

                col = row["name"]
                dtype = str(row["type"]).upper()

                # Skip integer primary key
                if row["pk"] == 1 and "INT" in dtype:
                    continue

                if "INT" in dtype:
                    values[col] = st.number_input(
                        col,
                        step=1
                    )

                elif any(x in dtype for x in ["REAL", "FLOAT", "DOUBLE"]):
                    values[col] = st.number_input(
                        col,
                        format="%.2f"
                    )

                else:
                    values[col] = st.text_input(col)

            save = st.form_submit_button(
                "💾 Save Record",
                use_container_width=True
            )

        if save:

            try:

                cols = list(values.keys())

                query = f"""
                    INSERT INTO {table}
                    ({",".join(f'"{c}"' for c in cols)})
                    VALUES ({",".join("?" for _ in cols)})
                """

                conn.execute(
                    query,
                    list(values.values())
                )

                conn.commit()

                st.success("✅ Record created successfully!")
                

            except Exception as e:

                conn.rollback()
                st.error(f"❌ Error: {e}")

    # ============================================================
    # READ
    # ============================================================

    elif operation == "📖 Read":

        st.subheader(f"📖 {table_label} Records")

        try:

            data = pd.read_sql(
                f"SELECT * FROM {table}",
                conn
            )

            st.write(f"Total Records: **{len(data)}**")

            page_size = st.selectbox(
                "Records per page",
                [10, 25, 50, 100]
            )

            pages = max(
                1,
                (len(data) + page_size - 1) // page_size
            )

            page_no = st.number_input(
                "Page",
                1,
                pages,
                1
            )

            start = (page_no - 1) * page_size

            st.dataframe(
                data.iloc[start:start + page_size],
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                f"Page {page_no} of {pages}"
            )

        except Exception as e:

            st.error(f"❌ Error: {e}")

    # ============================================================
    # UPDATE
    # ============================================================

    elif operation == "✏️ Update":

        st.subheader(f"✏️ Update {table_label} Record")

        data = pd.read_sql(
            f"SELECT * FROM {table}",
            conn
        )

        if data.empty:

            st.warning("No records available.")
            st.stop()

        # Select record
        selected_pk = st.selectbox(
            f"Select {pk}",
            data[pk].tolist()
        )

        record = data[
            data[pk] == selected_pk
        ].iloc[0]

        updated = {}

        with st.form("update_form"):

            for _, row in info.iterrows():

                col = row["name"]
                dtype = str(row["type"]).upper()

                if col == pk:

                    st.text_input(
                        f"{col} 🔑",
                        value=str(record[col]),
                        disabled=True
                    )

                    continue

                current = record[col]

                if "INT" in dtype:

                    updated[col] = st.number_input(
                        col,
                        value=int(current) if pd.notna(current) else 0,
                        step=1
                    )

                elif any(x in dtype for x in ["REAL", "FLOAT", "DOUBLE"]):

                    updated[col] = st.number_input(
                        col,
                        value=float(current) if pd.notna(current) else 0.0,
                        format="%.2f"
                    )

                else:

                    updated[col] = st.text_input(
                        col,
                        value="" if pd.isna(current) else str(current)
                    )

            update = st.form_submit_button(
                "✏️ Update Record",
                use_container_width=True
            )

        if update:

            try:

                set_clause = ", ".join(
                    f'"{c}" = ?'
                    for c in updated
                )

                query = f"""
                    UPDATE {table}
                    SET {set_clause}
                    WHERE "{pk}" = ?
                """

                conn.execute(
                    query,
                    list(updated.values()) + [selected_pk]
                )

                conn.commit()

                st.success("✅ Record updated successfully!")
                

            except Exception as e:

                conn.rollback()
                st.error(f"❌ Error: {e}")

    # ============================================================
    # DELETE
    # ============================================================

    elif operation == "🗑️ Delete":

        st.subheader(f"🗑️ Delete {table_label} Record")

        data = pd.read_sql(
            f"SELECT * FROM {table}",
            conn
        )

        if data.empty:

            st.warning("No records available.")
            st.stop()

        selected_pk = st.selectbox(
            f"Select {pk} to Delete",
            data[pk].tolist()
        )

        record = data[
            data[pk] == selected_pk
        ]

        st.dataframe(
            record,
            use_container_width=True,
            hide_index=True
        )

        confirm = st.checkbox(
            "I understand this record will be permanently deleted."
        )

        if st.button(
            "🗑️ Delete Record",
            disabled=not confirm,
            type="primary",
            use_container_width=True
        ):

            try:

                conn.execute(
                    f"""
                    DELETE FROM {table}
                    WHERE "{pk}" = ?
                    """,
                    (selected_pk,)
                )

                conn.commit()

                st.success("✅ Record deleted successfully!")
               

            except Exception as e:

                conn.rollback()
                st.error(f"❌ Error: {e}")





# ==================== PAGE 5: SQL QUERIES ====================
elif page == "🔎 SQL Queries":
    st.title("🔎 Pre-built SQL Queries")
    st.markdown("---")

    queries = {

    # ==================== PROPERTY & PRICING ====================

    "1. Average Listing Price by City": """
        SELECT
            City,
            ROUND(AVG(Price), 2) as Average_Listing_Price
        FROM listings
        GROUP BY City
        ORDER BY Average_Listing_Price DESC
    """,

    "2. Average Price Per Square Foot by Property Type": """
        SELECT
            Property_Type,
            ROUND(AVG(Price / Sqft), 2) as Average_Price_Per_Sqft
        FROM listings
        GROUP BY Property_Type
        ORDER BY Average_Price_Per_Sqft DESC
    """,

    "3. How Furnishing Status Impacts Property Prices": """
        SELECT
            pa.furnishing_status,
            ROUND(AVG(l.Price), 2) as Average_Price
        FROM listings l
        JOIN property_attributes pa
            ON l.Listing_ID = pa.listing_id
        GROUP BY pa.furnishing_status
        ORDER BY Average_Price DESC
    """,

    "4. Do Properties Closer to Metro Stations Command Higher Prices?": """
        SELECT
            CASE
                WHEN metro_distance_km <= 1 THEN '0-1 km (Very Close)'
                WHEN metro_distance_km <= 5 THEN '1-5 km (Close)'
                WHEN metro_distance_km <= 10 THEN '5-10 km (Moderate)'
                ELSE '10+ km (Far)'
            END as Metro_Distance_Category,
            ROUND(AVG(l.Price), 2) as Average_Price,
            ROUND(AVG(l.Price / l.Sqft), 2) as Avg_Price_Per_Sqft
        FROM listings l
        JOIN property_attributes pa
            ON l.Listing_ID = pa.listing_id
        GROUP BY Metro_Distance_Category
        ORDER BY Average_Price DESC
    """,

    "5. Are Rented Properties Priced Differently From Non-Rented Ones?": """
        SELECT
            pa.is_rented,
            ROUND(AVG(l.Price), 2) as Average_Price,
            COUNT(*) as Number_of_Properties
        FROM listings l
        JOIN property_attributes pa
            ON l.Listing_ID = pa.listing_id
        GROUP BY pa.is_rented
        ORDER BY Average_Price DESC
    """,

    "6. How Do Bedrooms and Bathrooms Affect Pricing?": """
        SELECT
            pa.bedrooms,
            pa.bathrooms,
            ROUND(AVG(l.Price), 2) as Average_Price,
            COUNT(*) as Number_of_Properties
        FROM listings l
        JOIN property_attributes pa
            ON l.Listing_ID = pa.listing_id
        GROUP BY pa.bedrooms, pa.bathrooms
        ORDER BY Average_Price DESC
        LIMIT 20
    """,

    "7. Do Properties with Parking and Power Backup Sell at Higher Prices?": """
        SELECT
            pa.parking_available,
            pa.power_backup,
            ROUND(AVG(l.Price), 2) as Average_Price,
            COUNT(*) as Number_of_Properties
        FROM listings l
        JOIN property_attributes pa
            ON l.Listing_ID = pa.listing_id
        GROUP BY pa.parking_available, pa.power_backup
        ORDER BY Average_Price DESC
    """,

    "8. How Does Year Built Influence Listing Price?": """
        SELECT
            CASE
                WHEN pa.year_built >= 2020 THEN '2020s (New)'
                WHEN pa.year_built >= 2010 THEN '2010s (Modern)'
                WHEN pa.year_built >= 2000 THEN '2000s (Recent)'
                ELSE 'Pre-2000 (Older)'
            END as Year_Built_Category,
            ROUND(AVG(l.Price), 2) as Average_Price,
            COUNT(*) as Number_of_Properties
        FROM listings l
        JOIN property_attributes pa
            ON l.Listing_ID = pa.listing_id
        GROUP BY Year_Built_Category
        ORDER BY Average_Price DESC
    """,

    "9. Which Cities Have the Highest Average Property Prices?": """
        SELECT
            City,
            ROUND(AVG(Price), 2) as Average_Property_Price,
            COUNT(*) as Number_of_Properties
        FROM listings
        GROUP BY City
        ORDER BY Average_Property_Price DESC
        LIMIT 5
    """,

    "10. How Are Properties Distributed Across Price Buckets?": """
        SELECT
            CASE
                WHEN Price < 500000 THEN 'Under 500K'
                WHEN Price >= 500000 AND Price < 1000000 THEN '500K - 1M'
                WHEN Price >= 1000000 AND Price < 2000000 THEN '1M - 2M'
                WHEN Price >= 2000000 AND Price < 3000000 THEN '2M - 3M'
                ELSE '3M+'
            END as Price_Bucket,
            COUNT(*) as Number_of_Properties,
            ROUND(
                100.0 * COUNT(*) /
                (SELECT COUNT(*) FROM listings),
                2
            ) as Percentage_of_Total
        FROM listings
        GROUP BY Price_Bucket
        ORDER BY
            CASE Price_Bucket
                WHEN 'Under 500K' THEN 1
                WHEN '500K - 1M' THEN 2
                WHEN '1M - 2M' THEN 3
                WHEN '2M - 3M' THEN 4
                ELSE 5
            END
    """,

    # ==================== SALES & MARKET PERFORMANCE ====================

    "11. Average Days on Market by City": """
        SELECT
            l.City,
            ROUND(AVG(s.Days_on_Market), 2) as Avg_Days_on_Market,
            COUNT(s.Listing_ID) as Total_Sales
        FROM sales s
        JOIN listings l
            ON s.Listing_ID = l.Listing_ID
        GROUP BY l.City
        ORDER BY Avg_Days_on_Market ASC
    """,

    "12. Which Property Types Sell the Fastest?": """
        SELECT
            l.Property_Type,
            ROUND(AVG(s.Days_on_Market), 2) as Avg_Days_on_Market,
            COUNT(s.Listing_ID) as Total_Sales
        FROM sales s
        JOIN listings l
            ON s.Listing_ID = l.Listing_ID
        GROUP BY l.Property_Type
        ORDER BY Avg_Days_on_Market ASC
    """,

    "13. What Percentage of Properties are Sold Above Listing Price?": """
        SELECT
            CASE
                WHEN s.Sale_Price > l.Price
                    THEN 'Sold Above Listing Price'
                WHEN s.Sale_Price = l.Price
                    THEN 'Sold At Listing Price'
                ELSE 'Sold Below Listing Price'
            END as Price_Category,
            COUNT(*) as Number_of_Sales,
            ROUND(
                100.0 * COUNT(*) /
                (SELECT COUNT(*) FROM sales),
                2
            ) as Percentage_of_Total_Sales
        FROM sales s
        JOIN listings l
            ON s.Listing_ID = l.Listing_ID
        GROUP BY Price_Category
        ORDER BY Number_of_Sales DESC
    """,

    "14. What is the Sale-to-List Price Ratio by City?": """
        SELECT
            l.City,
            ROUND(AVG(s.Sale_Price), 2) as Avg_Sale_Price,
            ROUND(AVG(l.Price), 2) as Avg_Listing_Price,
            ROUND(
                AVG(s.Sale_Price) / AVG(l.Price),
                4
            ) as Sale_to_List_Ratio,
            COUNT(s.Listing_ID) as Total_Sales
        FROM sales s
        JOIN listings l
            ON s.Listing_ID = l.Listing_ID
        GROUP BY l.City
        ORDER BY Sale_to_List_Ratio DESC
    """,

    "15. Which Listings Took More Than 90 Days to Sell?": """
        SELECT
            l.Listing_ID,
            l.City,
            l.Property_Type,
            l.Price as Listing_Price,
            s.Sale_Price,
            s.Days_on_Market
        FROM sales s
        JOIN listings l
            ON s.Listing_ID = l.Listing_ID
        WHERE s.Days_on_Market > 90
        ORDER BY s.Days_on_Market DESC
        LIMIT 10
    """,

    "16. How Does Metro Distance Affect Time on Market?": """
        SELECT
            CASE
                WHEN pa.metro_distance_km <= 2
                    THEN '0-2 km (Very Close)'
                WHEN pa.metro_distance_km <= 5
                    THEN '2-5 km (Close)'
                WHEN pa.metro_distance_km <= 10
                    THEN '5-10 km (Moderate)'
                ELSE '10+ km (Far)'
            END as Metro_Distance_Category,
            ROUND(AVG(s.Days_on_Market), 2) as Avg_Days_on_Market,
            COUNT(s.Listing_ID) as Total_Sales
        FROM sales s
        JOIN property_attributes pa
            ON s.Listing_ID = pa.listing_id
        GROUP BY Metro_Distance_Category
        ORDER BY Avg_Days_on_Market ASC
    """,

    "17. What is the Monthly Sales Trend?": """
        SELECT
            strftime('%Y-%m', Date_Sold) as Sales_Month,
            COUNT(*) as Total_Sales,
            ROUND(SUM(Sale_Price), 2) as Total_Sales_Value,
            ROUND(AVG(Days_on_Market), 2) as Avg_Days_on_Market
        FROM sales
        GROUP BY Sales_Month
        ORDER BY Sales_Month ASC
    """,

    "18. Which Properties are Currently Unsold?": """
        SELECT
            l.Listing_ID,
            l.City,
            l.Property_Type,
            l.Price,
            l.Date_Listed,
            pa.bedrooms,
            pa.bathrooms,
            pa.year_built
        FROM listings l
        LEFT JOIN sales s
            ON l.Listing_ID = s.Listing_ID
        JOIN property_attributes pa
            ON l.Listing_ID = pa.listing_id
        WHERE s.Listing_ID IS NULL
        LIMIT 10
    """,

    # ==================== AGENT PERFORMANCE ====================

    "19. Which Agents Have Closed the Most Sales?": """
        SELECT
            a.Agent_ID,
            a.Name,
            a.deals_closed as Total_Deals,
            a.experience_years,
            a.commission_rate,
            ROUND(a.rating, 2) as Rating,
            a.avg_closing_days
        FROM agents a
        ORDER BY a.deals_closed DESC
        LIMIT 15
    """,

    "20. Who are the Top Agents by Total Sales Revenue?": """
        SELECT
            a.Agent_ID,
            a.Name,
            COUNT(s.Listing_ID) as Sales_Closed,
            ROUND(SUM(s.Sale_Price), 2) as Total_Revenue,
            ROUND(AVG(s.Sale_Price), 2) as Avg_Sale_Price,
            ROUND(a.commission_rate, 2) as Commission_Rate,
            ROUND(
                SUM(s.Sale_Price) * a.commission_rate / 100,
                2
            ) as Est_Commission_Earned
        FROM agents a
        LEFT JOIN listings l
            ON a.Agent_ID = l.Agent_ID
        LEFT JOIN sales s
            ON l.Listing_ID = s.Listing_ID
        GROUP BY a.Agent_ID, a.Name, a.commission_rate
        HAVING Sales_Closed > 0
        ORDER BY Total_Revenue DESC
        LIMIT 15
    """,

    "21. Which Agents Close Deals Fastest?": """
        SELECT
            a.Agent_ID,
            a.Name,
            a.deals_closed as Total_Deals,
            ROUND(a.avg_closing_days, 1) as Avg_Days_to_Close,
            a.rating,
            a.experience_years,
            a.commission_rate
        FROM agents a
        WHERE a.deals_closed > 0
        ORDER BY a.avg_closing_days ASC
        LIMIT 15
    """,

    "22. Does Experience Correlate with Deals Closed?": """
        SELECT
            CASE
                WHEN experience_years >= 20 THEN '20+ years'
                WHEN experience_years >= 15 THEN '15-20 years'
                WHEN experience_years >= 10 THEN '10-15 years'
                WHEN experience_years >= 5 THEN '5-10 years'
                ELSE '0-5 years'
            END as Experience_Level,
            COUNT(*) as Agent_Count,
            ROUND(AVG(deals_closed), 1) as Avg_Deals_Closed,
            ROUND(MIN(deals_closed), 0) as Min_Deals,
            ROUND(MAX(deals_closed), 0) as Max_Deals,
            ROUND(AVG(rating), 2) as Avg_Rating
        FROM agents
        GROUP BY Experience_Level
        ORDER BY
            CASE Experience_Level
                WHEN '20+ years' THEN 1
                WHEN '15-20 years' THEN 2
                WHEN '10-15 years' THEN 3
                WHEN '5-10 years' THEN 4
                ELSE 5
            END
    """,

    "23. Do Agents with Higher Ratings Close Deals Faster?": """
        SELECT
            CASE
                WHEN rating >= 4.5 THEN 'Excellent (4.5+)'
                WHEN rating >= 4.0 THEN 'Very Good (4.0-4.5)'
                WHEN rating >= 3.5 THEN 'Good (3.5-4.0)'
                WHEN rating >= 3.0 THEN 'Fair (3.0-3.5)'
                ELSE 'Below Average (<3.0)'
            END as Rating_Category,
            COUNT(*) as Agent_Count,
            ROUND(AVG(rating), 2) as Avg_Rating,
            ROUND(AVG(deals_closed), 1) as Avg_Deals,
            ROUND(AVG(avg_closing_days), 1) as Avg_Days_to_Close,
            ROUND(AVG(commission_rate), 2) as Avg_Commission_Rate
        FROM agents
        GROUP BY Rating_Category
        ORDER BY Avg_Rating DESC
    """,

    "24. What is the Average Commission Earned by Each Agent?": """
        SELECT
            a.Agent_ID,
            a.Name,
            a.commission_rate,
            COUNT(s.Listing_ID) as Sales_Closed,
            ROUND(AVG(s.Sale_Price), 2) as Avg_Sale_Price_per_Deal,
            ROUND(SUM(s.Sale_Price), 2) as Total_Sales_Volume,
            ROUND(
                SUM(s.Sale_Price) * a.commission_rate / 100,
                2
            ) as Total_Commission_Earned,
            ROUND(
                (SUM(s.Sale_Price) * a.commission_rate / 100)
                / COUNT(s.Listing_ID),
                2
            ) as Avg_Commission_per_Deal
        FROM agents a
        LEFT JOIN listings l
            ON a.Agent_ID = l.Agent_ID
        LEFT JOIN sales s
            ON l.Listing_ID = s.Listing_ID
        WHERE s.Listing_ID IS NOT NULL
        GROUP BY a.Agent_ID, a.Name, a.commission_rate
        ORDER BY Total_Commission_Earned DESC
        LIMIT 15
    """,

    "25. Which Agents Currently Have the Most Active Listings?": """
        SELECT
            a.Agent_ID,
            a.Name,
            COUNT(l.Listing_ID) as Total_Active_Listings,
            ROUND(AVG(l.Price), 2) as Avg_Listing_Price,
            a.rating,
            a.experience_years
        FROM agents a
        JOIN listings l
            ON a.Agent_ID = l.Agent_ID
        LEFT JOIN sales s
            ON l.Listing_ID = s.Listing_ID
        WHERE s.Listing_ID IS NULL
        GROUP BY a.Agent_ID, a.Name, a.rating, a.experience_years
        ORDER BY Total_Active_Listings DESC
        LIMIT 15
    """,

    # ==================== BUYER & FINANCING ====================

    "26. What Percentage of Buyers are Investors vs End Users?": """
        SELECT
            buyer_type,
            COUNT(*) as Total_Buyers,
            ROUND(
                100.0 * COUNT(*) /
                (SELECT COUNT(*) FROM buyers),
                2
            ) as Percentage
        FROM buyers
        GROUP BY buyer_type
        ORDER BY Total_Buyers DESC
    """,

    "27. Which Cities Have the Highest Loan Uptake Rate?": """
        SELECT
            l.City,
            COUNT(
                CASE WHEN b.loan_taken = 1 THEN 1 END
            ) as Buyers_with_Loan,
            COUNT(*) as Total_Buyers,
            ROUND(
                100.0 *
                COUNT(CASE WHEN b.loan_taken = 1 THEN 1 END)
                / COUNT(*),
                2
            ) as Loan_Uptake_Rate
        FROM buyers b
        JOIN listings l
            ON b.sale_id = l.Listing_ID
        GROUP BY l.City
        ORDER BY Loan_Uptake_Rate DESC
    """,

    "28. What is the Average Loan Amount by Buyer Type?": """
        SELECT
            buyer_type,
            ROUND(AVG(loan_amount), 2) as Average_Loan_Amount,
            COUNT(*) as Total_Loan_Transactions
        FROM buyers
        WHERE loan_taken = 1
        GROUP BY buyer_type
        ORDER BY Average_Loan_Amount DESC
    """,

    "29. Which Payment Mode is Most Commonly Used?": """
        SELECT
            payment_mode,
            COUNT(*) as Total_Transactions,
            ROUND(
                100.0 * COUNT(*) /
                (SELECT COUNT(*) FROM buyers),
                2
            ) as Percentage
        FROM buyers
        GROUP BY payment_mode
        ORDER BY Total_Transactions DESC
    """,

    "30. Do Loan-Backed Purchases Take Longer to Close?": """
        SELECT
            CASE
                WHEN b.loan_taken = 1
                    THEN 'Loan-Backed'
                ELSE 'Cash Purchase'
            END as Purchase_Type,
            ROUND(AVG(s.Days_on_Market), 2) as Avg_Days_on_Market,
            COUNT(*) as Total_Sales
        FROM buyers b
        JOIN sales s
            ON b.sale_id = s.Listing_ID
        GROUP BY Purchase_Type
        ORDER BY Avg_Days_on_Market DESC
    """
}


    
    selected_query = st.selectbox("📋 Select Query", list(queries.keys()))
    
    st.code(queries[selected_query], language="sql")
    
    if st.button("▶️ Execute Query"):
        try:
            results = pd.read_sql(queries[selected_query], conn)
            results = results.reset_index(drop=True)
            st.subheader(f"✅ Results ({len(results)} rows)")
            st.dataframe(results, use_container_width=True, height=400,hide_index=False)
            
            # Download option
            csv = results.to_csv(index=False)
            st.download_button(
                label="📥 Download as CSV",
                data=csv,
                file_name=f"query_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.error(f"❌ Error executing query: {e}")

# ==================== FOOTER ====================
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.9em;'>
    🏠 Real Estate Data Explorer | Built with Streamlit & SQLite
    <br>
    Database: real_estate.db | Last Updated: 2026-08-30
</div>
""", unsafe_allow_html=True)
