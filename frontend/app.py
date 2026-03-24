import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import json
import os
import io

API_URL = "http://backend:8000/api/v1"
API_V2_URL = "http://backend:8000/api/v2/memo"
API_V3_URL = "http://backend:8000/api/v3/compliance"

st.set_page_config(page_title="Tracelight", layout="wide")

st.markdown("""
<style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Custom metric cards */
    [data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
    }

    /* Confidence badge colors */
    .confidence-high { color: #4CAF50; font-weight: bold; }
    .confidence-med { color: #FF9800; font-weight: bold; }
    .confidence-low { color: #F44336; font-weight: bold; }

    /* Landing page cards - Light theme */
    .workflow-card {
        background: #ffffff;
        border: 1px solid #004d2e;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        transition: border-color 0.2s;
        color: #000000;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .workflow-card:hover {
        border-color: #008f51;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "landing"

if "demo_mode" not in st.session_state:
    st.session_state["demo_mode"] = True

# Sidebar
with st.sidebar:
    st.image("assets/logo.jpeg", width=200)
    st.markdown("### Settings")
    st.session_state["demo_mode"] = st.toggle("Demo Mode (No API Calls)", value=st.session_state["demo_mode"])
    
    st.markdown("---")
    if st.button("← Back to Home"):
        st.session_state["current_page"] = "landing"
        st.rerun()
    
    with st.expander("About Tracelight"):
        st.write("Tracelight Ecosystem — Agentic Sidecar Demos.")

if st.session_state["current_page"] == "landing":
    st.image("assets/logo.jpeg", width=200)
    st.markdown("## Tracelight Ecosystem — Agentic Sidecar Demos")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="workflow-card">
            <h3>Workflow I</h3>
            <h4>Synthetic Data Engine</h4>
            <p>Collapse PoC timelines from 6mo to 6 minutes.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Launch Workflow I →", key="launch_1", use_container_width=True):
            st.session_state["current_page"] = "phase1"
            st.rerun()
            
    with col2:
        st.markdown("""
        <div class="workflow-card">
            <h3>Workflow II</h3>
            <h4>Deliverable Engine</h4>
            <p>Auto-generate IC memos & exec decks from model outputs.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Launch Workflow II →", key="launch_2", use_container_width=True):
            st.session_state["current_page"] = "phase2"
            st.rerun()
            
    with col3:
        st.markdown("""
        <div class="workflow-card">
            <h3>Workflow III</h3>
            <h4>Compliance Engine</h4>
            <p>Auto-complete SIG/CAIQ vendor questionnaires in minutes.</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Launch Workflow III →", key="launch_3", use_container_width=True):
            st.session_state["current_page"] = "phase3"
            st.rerun()

elif st.session_state["current_page"] == "phase1":
    st.header("Phase 1: Synthetic Data Generator")
    
    @st.cache_data(ttl=60)
    def fetch_templates():
        if st.session_state.get("demo_mode"):
            return [{"name": "Mid-market PE LBO", "profile": {"variables": {"Revenue": {}, "EBITDA": {}}}}]
        try:
            resp = requests.get(f"{API_URL}/templates")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            st.error(f"Failed to fetch templates: {e}")
            return []

    templates = fetch_templates()
    template_names = [t["name"] for t in templates] + ["Custom"]

    selected_preset = st.selectbox("Select a preset", template_names, key="preset")

    use_llm = st.checkbox("Use LLM Profiler", value=False, key="use_llm")
    nl_scenario = ""
    if use_llm:
        nl_scenario = st.text_area("Natural Language Scenario", 
                                        "Distressed PE LBO, mid-market European industrials, high leverage, declining margins", key="nl")

    col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
    with col_cfg1:
        num_entities = st.number_input("Num Entities", min_value=1, max_value=10000, value=50)
    with col_cfg2:
        time_horizon = st.number_input("Time Horizon (Years)", min_value=1, max_value=30, value=5)
    with col_cfg3:
        frequency = st.selectbox("Frequency", ["monthly", "quarterly", "annual"], index=1)

    st.subheader("Privacy")
    col_priv1, col_priv2 = st.columns(2)
    with col_priv1:
        dp_enabled = st.checkbox("Enable Differential Privacy", key="dp")
    with col_priv2:
        dp_epsilon = st.slider("Epsilon", 0.1, 10.0, 1.0, key="eps")

    output_format = st.radio("Output Format", ["csv", "json"], key="fmt")

    if st.button("Generate Synthetic Data", type="primary", key="gen1"):
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

        if not use_llm and not st.session_state.get("demo_mode"):
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
                if st.session_state.get("demo_mode"):
                    time.sleep(1) # simulate work
                    with open("demo_data/phase1_sample_response.json") as f:
                        result = json.load(f)
                    df = pd.read_csv("demo_data/phase1_sample_data.csv")
                    if output_format == "json":
                        data_content = df.to_json(orient="records")
                    else:
                        data_content = df.to_csv(index=False)
                    data_bytes = data_content.encode('utf-8')
                else:
                    resp = requests.post(f"{API_URL}/generate", json=payload)
                    if not resp.ok:
                        st.error(f"Error: {resp.status_code} - {resp.text}")
                        st.stop()
                    result = resp.json()
                    job_id = result["job_id"]
                    data_resp = requests.get(f"{API_URL}/download/{job_id}")
                    if output_format == "csv":
                        df = pd.read_csv(io.StringIO(data_resp.text))
                    else:
                        df = pd.read_json(io.StringIO(data_resp.text), orient="records")
                    data_bytes = data_resp.content

                st.success("Data generated successfully!")
                
                job_id = result["job_id"]
                st.session_state["last_job_id"] = job_id
                
                report = result["validation_report"]
                profile_used = result["profile_used"]
                var_names = list(profile_used["variables"].keys())

                st.subheader("Scenario Preview")
                st.write(f"**Variables generated:** {', '.join(var_names)}")

                st.subheader("Data Preview")
                st.dataframe(df.head(20))

                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Distributions")
                    var_to_plot = st.selectbox("Select variable to plot", var_names)
                    if var_to_plot in df.columns:
                        fig = px.histogram(df, x=var_to_plot, nbins=50, marginal="box")
                        st.plotly_chart(fig, use_container_width=True)

                with col2:
                    st.subheader("Correlation Matrix (Empirical)")
                    # Handle case where non-numeric columns might exist
                    numeric_df = df.select_dtypes(include='number')
                    if not numeric_df.empty:
                        corr_matrix = numeric_df.corr()
                        fig2 = px.imshow(corr_matrix, text_auto=".2f", aspect="auto", color_continuous_scale="RdBu_r")
                        st.plotly_chart(fig2, use_container_width=True)

                with st.expander("Validation Report", expanded=True):
                    st.write(f"**Rows generated:** {report.get('row_count', 0)}")
                    st.write(f"**Correlation RMSE:** {report.get('correlation_rmse', 0)}")
                    
                    if report.get('dp_applied', False):
                        st.write(f"**Differential Privacy Applied:** Epsilon = {report.get('dp_epsilon', 0)}")
                        st.write(f"**Post-DP KS Tests Passed:** {report.get('post_dp_ks_all_passed', False)}")
                    
                    st.write("### KS Test Results")
                    if 'ks_tests' in report:
                        ks_df = pd.DataFrame(report['ks_tests']).T
                        
                        def highlight_ks(val):
                            if isinstance(val, bool):
                                return 'color: #4CAF50' if val else 'color: #F44336'
                            return ''
                        
                        st.dataframe(ks_df.style.map(highlight_ks))

                st.download_button(
                    label=f"Download {output_format.upper()}",
                    data=data_bytes,
                    file_name=f"synthetic_data_{job_id}.{output_format}",
                    mime=f"text/{output_format}" if output_format == "csv" else "application/json"
                )

            except Exception as e:
                st.error(f"Error generating data: {e}")

elif st.session_state["current_page"] == "phase2":
    st.header("Phase 2: Deliverable Engine")
    
    st.subheader("1. Upload Sources (Qualitative Context)")
    uploaded_files = st.file_uploader("Upload CIM, Management Presentations, Expert Calls (PDF/DOCX/TXT)", accept_multiple_files=True)
    if st.button("Process Documents", key="proc_docs"):
        if not uploaded_files and not st.session_state.get("demo_mode"):
            st.warning("Please upload at least one file.")
        else:
            with st.spinner("Processing and vectorizing documents..."):
                if st.session_state.get("demo_mode"):
                    time.sleep(1)
                    session_id = "demo_session_abc"
                else:
                    files = [("files", (f.name, f.getvalue(), f.type)) for f in uploaded_files]
                    resp = requests.post(f"{API_V2_URL}/upload-sources", files=files)
                    if resp.ok:
                        session_id = resp.json()["session_id"]
                    else:
                        st.error(f"Error: {resp.status_code}")
                        st.stop()
                st.session_state["session_id"] = session_id
                st.success(f"Documents indexed! Session ID: {session_id}")
    
    st.subheader("2. Financial Data")
    fin_job_id = st.text_input("Financial Data Job ID (from Phase 1)", value=st.session_state.get("last_job_id", ""))
    
    st.subheader("3. Configure Memo")
    firm_name = st.text_input("Firm Name", "Acme Capital")
    memo_type = st.selectbox("Memo Type", ["both", "ic_memo", "exec_deck"])
    
    st.write("Sections to Include:")
    sec_exec = st.checkbox("Executive Summary", True)
    sec_thesis = st.checkbox("Investment Thesis", True)
    sec_market = st.checkbox("Market Analysis", True)
    sec_financial = st.checkbox("Financial Projections", True)
    sec_deal = st.checkbox("Deal Structure", True)
    sec_risk = st.checkbox("Risk Mitigation", True)
    
    confidence_thresh = st.slider("Confidence Threshold", 0.0, 1.0, 0.7)
    
    if st.button("Generate Deliverables", type="primary", key="gen2"):
        if "session_id" not in st.session_state and not st.session_state.get("demo_mode"):
            st.warning("No session found. Please upload source documents or enter a session ID manually if supported.")
            session_id = str(int(time.time()))
            st.session_state["session_id"] = session_id
            
        with st.spinner("Generating Deliverables..."):
            if st.session_state.get("demo_mode"):
                time.sleep(2)
                with open("demo_data/phase2_sample_response.json") as f:
                    status_data = json.load(f)
                status = "completed"
            else:
                sections = []
                if sec_exec: sections.append("executive_summary")
                if sec_thesis: sections.append("investment_thesis")
                if sec_market: sections.append("market_analysis")
                if sec_financial: sections.append("financial_projections")
                if sec_deal: sections.append("deal_structure")
                if sec_risk: sections.append("risk_mitigation")
                
                payload = {
                    "session_id": st.session_state.get("session_id", "demo"),
                    "financial_data_job_id": fin_job_id if fin_job_id else None,
                    "config": {
                        "memo_type": memo_type,
                        "firm_name": firm_name,
                        "sections": sections,
                        "confidence_threshold": confidence_thresh
                    }
                }
                
                resp = requests.post(f"{API_V2_URL}/generate", json=payload)
                if not resp.ok:
                    st.error(f"Error: {resp.text}")
                    st.stop()
                    
                job_id = resp.json()["job_id"]
                st.info(f"Job started! ID: {job_id}")
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                while True:
                    status_resp = requests.get(f"{API_V2_URL}/status/{job_id}")
                    if status_resp.ok:
                        status_data = status_resp.json()
                        status = status_data["status"]
                        status_text.text(f"Status: {status.capitalize()}")
                        if status in ["completed", "failed"]:
                            progress_bar.progress(100)
                            break
                        progress_bar.progress(50)
                    else:
                        st.error("Failed to poll status")
                        status = "error"
                        break
                    time.sleep(2)

        if status == "completed":
            st.success("Deliverables generated successfully!")
            
            st.subheader("Review Dashboard")
            for sec in status_data.get("sections", []):
                conf_class = "confidence-high" if sec['confidence'] > 0.8 else "confidence-med" if sec['confidence'] > 0.5 else "confidence-low"
                with st.expander(f"{sec['title']} (Confidence: {sec['confidence']:.2f})"):
                    st.markdown(f"<span class='{conf_class}'>Confidence: {sec['confidence']:.2f}</span>", unsafe_allow_html=True)
                    if sec['needs_review']:
                        st.warning("Needs Review: Low confidence or missing data")
                    st.markdown(sec['content'])
                    
            urls = status_data.get("download_urls", {})
            if urls:
                col_dl1, col_dl2, col_dl3 = st.columns(3)
                if st.session_state.get("demo_mode"):
                    try:
                        with open("demo_data/phase2_sample_memo.docx", "rb") as f:
                            col_dl1.download_button("Download DOCX", f, file_name="memo.docx")
                        with open("demo_data/phase2_sample_deck.pptx", "rb") as f:
                            col_dl2.download_button("Download PPTX", f, file_name="deck.pptx")
                    except:
                        pass
                else:
                    host = "http://backend:8000"
                    if urls.get('docx'):
                        col_dl1.markdown(f"**[Download DOCX]({host}{urls['docx']})**")
                    if urls.get('pptx'):
                        col_dl2.markdown(f"**[Download PPTX]({host}{urls['pptx']})**")
                    if urls.get('audit_trail'):
                        col_dl3.markdown(f"**[Download Audit Trail JSON]({host}{urls['audit_trail']})**")
        elif status == "failed":
            st.error("Job failed")

elif st.session_state["current_page"] == "phase3":
    st.header("Phase 3: InfoSec & Vendor Risk Automation Pipeline")

    col_upload_1, col_upload_2 = st.columns(2)
    with col_upload_1:
        st.subheader("1. Upload Knowledge Base")
        st.write("Upload SOC 2 reports, pentest summaries, security policies.")
        kb_files = st.file_uploader("Upload KB Docs", accept_multiple_files=True, key="kb_up")
        if st.button("Index to KB", key="kb_idx"):
            if not kb_files and not st.session_state.get("demo_mode"):
                st.warning("Please upload at least one file.")
            else:
                with st.spinner("Indexing to persistent ChromaDB..."):
                    if st.session_state.get("demo_mode"):
                        time.sleep(1)
                        st.success("Indexed to KB successfully.")
                    else:
                        files = [("files", (f.name, f.getvalue(), f.type)) for f in kb_files]
                        resp = requests.post(f"{API_V3_URL}/upload-kb", files=files)
                        if resp.ok:
                            st.success(resp.json().get("message", "Success"))
                        else:
                            st.error(f"Error: {resp.status_code}")

    with col_upload_2:
        st.subheader("2. Upload Questionnaire")
        st.write("Upload inbound vendor questionnaire (CSV, DOCX, PDF, JSON). No XLSX.")
        q_file = st.file_uploader("Upload Questionnaire", accept_multiple_files=False, key="q_up")
        if st.button("Parse Questionnaire", key="q_parse"):
            if not q_file and not st.session_state.get("demo_mode"):
                st.warning("Please upload a file.")
            elif q_file and q_file.name.endswith(".xlsx"):
                st.error("XLSX files are strictly forbidden (DMZ rule).")
            else:
                with st.spinner("Parsing format and framework..."):
                    if st.session_state.get("demo_mode"):
                        time.sleep(1)
                        st.session_state["q_session_id"] = "demo_q_123"
                        st.success("Parsed 20 questions (Framework: SIG Lite)")
                    else:
                        files = {"file": (q_file.name, q_file.getvalue(), q_file.type)}
                        resp = requests.post(f"{API_V3_URL}/upload-questionnaire", files=files)
                        if resp.ok:
                            data = resp.json()
                            st.session_state["q_session_id"] = data["questionnaire_session_id"]
                            st.success(f"Parsed {data['total_questions']} questions (Framework: {data['framework']})")
                            if data['domains']:
                                st.write(f"Detected Domains: {', '.join(data['domains'][:5])}...")
                        else:
                            st.error(f"Error: {resp.text}")

    st.subheader("3. Configure & Generate")
    c_col1, c_col2, c_col3, c_col4 = st.columns(4)
    with c_col1:
        comp_name = st.text_input("Company Name", "Tracelight")
    with c_col2:
        tone = st.selectbox("Tone", ["formal", "concise", "technical"], index=0)
    with c_col3:
        conf_thresh = st.slider("Review Threshold", 0.0, 1.0, 0.8)
    with c_col4:
        auto_thresh = st.slider("Auto-Approve Threshold", 0.0, 1.0, 0.9)

    if st.button("Generate Responses", type="primary", key="gen3"):
        if "q_session_id" not in st.session_state and not st.session_state.get("demo_mode"):
            st.warning("Please upload and parse a questionnaire first.")
        else:
            with st.spinner("Generating..."):
                if st.session_state.get("demo_mode"):
                    time.sleep(1)
                    st.session_state["comp_job_id"] = "demo_job_789"
                else:
                    payload = {
                        "kb_session_id": "persistent",
                        "questionnaire_session_id": st.session_state["q_session_id"],
                        "config": {
                            "company_name": comp_name,
                            "default_tone": tone,
                            "confidence_threshold": conf_thresh,
                            "auto_approve_above": auto_thresh
                        }
                    }
                    try:
                        resp = requests.post(f"{API_V3_URL}/generate", json=payload)
                        if not resp.ok:
                            st.error(f"Error: {resp.text}")
                        else:
                            job_id = resp.json()["job_id"]
                            st.session_state["comp_job_id"] = job_id
                            st.info(f"Compliance job started! ID: {job_id}")
                    except Exception as e:
                        st.error(f"Exception: {e}")

    if "comp_job_id" in st.session_state:
        if st.session_state.get("demo_mode"):
            with open("demo_data/phase3_sample_response.json") as f:
                data = json.load(f)
            status_ok = True
        else:
            job_id = st.session_state["comp_job_id"]
            status_resp = requests.get(f"{API_V3_URL}/status/{job_id}")
            status_ok = status_resp.ok
            if status_ok:
                data = status_resp.json()
        
        if status_ok:
            st.write(f"**Status:** {data['status'].capitalize()}")
            
            if data['status'] == 'completed':
                st.subheader("4. Review Dashboard")
                m_col1, m_col2, m_col3 = st.columns(3)
                m_col1.metric("Total Questions", data['total_questions'])
                m_col2.metric("Auto-Approved", data['auto_approved'], delta_color="normal")
                m_col3.metric("Needs Review", data['needs_review'], delta_color="inverse")
                
                responses = data.get("responses", [])
                
                filter_choice = st.radio("Filter", ["Show all", "Needs review only", "Auto-approved only"], horizontal=True)
                
                if responses:
                    for r in responses:
                        if filter_choice == "Needs review only" and r['status'] == "auto_approved": continue
                        if filter_choice == "Auto-approved only" and r['status'] != "auto_approved": continue
                        
                        badge_color = "🟢" if r['status'] == "auto_approved" else "🟠"
                        with st.expander(f"{badge_color} [{r['status']}] {r['question_id']} (Conf: {r['confidence']}) - {r['question_text'][:60]}..."):
                            st.write(f"**Question:** {r['question_text']}")
                            st.write(f"**Domain:** {r['domain']} | **Type:** {r['response_type']}")
                            
                            new_text = st.text_area("Drafted Response", r.get('response_text', ''), key=f"text_{r['question_id']}")
                            new_bool = r.get('boolean_value')
                            if r.get('response_type') == "boolean":
                                new_bool = st.radio("Boolean Answer", [True, False, None], index=[True, False, None].index(r.get('boolean_value')) if r.get('boolean_value') in [True, False, None] else 2, key=f"bool_{r['question_id']}")
                                
                            notes = st.text_input("Reviewer Notes", r.get('reviewer_notes', ''), key=f"notes_{r['question_id']}")
                            
                            c1, c2 = st.columns(2)
                            if c1.button("Approve", key=f"app_{r['question_id']}"):
                                st.success("Approved!")
                                
                            if c2.button("Override", key=f"over_{r['question_id']}"):
                                st.warning("Overridden!")
                                
                st.subheader("5. Export")
                if st.session_state.get("demo_mode"):
                    dl_c1, dl_c2, dl_c3 = st.columns(3)
                    try:
                        with open("demo_data/phase3_sample_questionnaire.csv", "rb") as f:
                            dl_c1.download_button("Download CSV", f, file_name="questionnaire.csv")
                        with open("demo_data/phase3_sample_completed.docx", "rb") as f:
                            dl_c2.download_button("Download DOCX", f, file_name="completed.docx")
                    except:
                        pass
                else:
                    urls = data.get("download_urls", {})
                    host = "http://backend:8000"
                    if urls:
                        dl_c1, dl_c2, dl_c3 = st.columns(3)
                        if urls.get("csv"):
                            dl_c1.markdown(f"**[Download CSV]({host}{urls['csv']})**")
                        if urls.get("docx"):
                            dl_c2.markdown(f"**[Download DOCX]({host}{urls['docx']})**")
                        if urls.get("json"):
                            dl_c3.markdown(f"**[Download JSON]({host}{urls['json']})**")
