import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

API_URL = "http://backend:8000/api/v1"

st.set_page_config(page_title="Synthetic Data Generator", layout="wide")
st.title("Tracelight Synthetic Data Generator")

@st.cache_data(ttl=60)
def fetch_templates():
    try:
        resp = requests.get(f"{API_URL}/templates")
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Failed to fetch templates: {e}")
        return []

templates = fetch_templates()
template_names = [t["name"] for t in templates] + ["Custom"]

st.sidebar.header("Configuration")
selected_preset = st.sidebar.selectbox("Select a preset", template_names)

use_llm = st.sidebar.checkbox("Use LLM Profiler", value=False)
nl_scenario = ""
if use_llm:
    nl_scenario = st.sidebar.text_area("Natural Language Scenario", 
                                       "Distressed PE LBO, mid-market European industrials, high leverage, declining margins")

num_entities = st.sidebar.number_input("Num Entities", min_value=1, max_value=10000, value=50)
time_horizon = st.sidebar.number_input("Time Horizon (Years)", min_value=1, max_value=30, value=5)
frequency = st.sidebar.selectbox("Frequency", ["monthly", "quarterly", "annual"], index=1)

st.sidebar.subheader("Privacy")
dp_enabled = st.sidebar.checkbox("Enable Differential Privacy")
dp_epsilon = st.sidebar.slider("Epsilon", 0.1, 10.0, 1.0)

output_format = st.sidebar.radio("Output Format", ["csv", "json"])

if st.sidebar.button("Generate Synthetic Data", type="primary"):
    payload = {
        "scenario": {
            "natural_language": nl_scenario,
            "use_llm_profiler": use_llm
        },
        "privacy": {
            "enabled": dp_enabled,
            "epsilon": dp_epsilon
        },
        "output_format": output_format,
        "seed": 42
    }

    if not use_llm:
        if selected_preset == "Custom":
            st.error("Please select a valid preset or enable LLM Profiler.")
            st.stop()
        else:
            profile = next(t["profile"] for t in templates if t["name"] == selected_preset)
            profile["num_entities"] = num_entities
            profile["time_horizon_years"] = time_horizon
            profile["frequency"] = frequency
            payload["profile_override"] = profile

    with st.spinner("Generating data..."):
        try:
            resp = requests.post(f"{API_URL}/generate", json=payload)
            if not resp.ok:
                st.error(f"Error: {resp.status_code} - {resp.text}")
                st.stop()
            result = resp.json()
            st.success("Data generated successfully!")
            
            job_id = result["job_id"]
            report = result["validation_report"]
            profile_used = result["profile_used"]
            var_names = list(profile_used["variables"].keys())

            st.subheader("Data Preview")
            
            data_resp = requests.get(f"{API_URL}/download/{job_id}")
            if output_format == "csv":
                import io
                df = pd.read_csv(io.StringIO(data_resp.text))
            else:
                import io
                df = pd.read_json(io.StringIO(data_resp.text), orient="records")
            
            st.dataframe(df.head(20))

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("Distributions")
                var_to_plot = st.selectbox("Select variable to plot", var_names)
                fig = px.histogram(df, x=var_to_plot, nbins=50, marginal="box")
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("Correlation Matrix (Empirical)")
                corr_matrix = df[var_names].corr()
                fig2 = px.imshow(corr_matrix, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r")
                st.plotly_chart(fig2, use_container_width=True)

            with st.expander("Validation Report", expanded=True):
                st.write(f"**Rows generated:** {report['row_count']}")
                st.write(f"**Correlation RMSE:** {report['correlation_rmse']}")
                
                if report['dp_applied']:
                    st.write(f"**Differential Privacy Applied:** Epsilon = {report['dp_epsilon']}")
                    st.write(f"**Post-DP KS Tests Passed:** {report['post_dp_ks_all_passed']}")
                
                st.write("### KS Test Results")
                ks_df = pd.DataFrame(report['ks_tests']).T
                st.dataframe(ks_df)

            st.download_button(
                label=f"Download {output_format.upper()}",
                data=data_resp.content,
                file_name=f"synthetic_data_{job_id}.{output_format}",
                mime=f"text/{output_format}" if output_format == "csv" else "application/json"
            )

        except Exception as e:
            st.error(f"Error generating data: {e}")
