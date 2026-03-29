import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import json
import os
import io
import base64
import mammoth
from pptx import Presentation
from pptx.util import Inches, Pt, Emu

BACKEND_HOST = os.environ.get("BACKEND_URL", "http://backend:8000")
API_URL = f"{BACKEND_HOST}/api/v1"
API_V2_URL = f"{BACKEND_HOST}/api/v2/memo"

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

    /* Landing page cards - Dark theme */
    .workflow-card {
        background: #004d2e;
        border: 1px solid #2E7D32;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        transition: border-color 0.2s;
        color: #E8F5E9;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        margin-bottom: 20px;
    }
    .workflow-card:hover {
        border-color: #4CAF50;
        box-shadow: 0 4px 12px rgba(46,125,50,0.3);
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
    
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="workflow-card">
            <h3>Workflow I</h3>
            <h4>Synthetic Data Engine</h4>
            <p>Collapse PoC timelines from 6mo to 60 seconds.</p>
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
                    time.sleep(15) # simulate work
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
                    time.sleep(10)
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
    firm_name = st.text_input("Firm Name", "Meridian Growth Partners")
    memo_type = st.selectbox("Memo Type", ["both", "ic_memo", "exec_deck"])
    
    st.write("Sections to Include:")
    sec_exec = st.checkbox("Executive Summary", True)
    sec_thesis = st.checkbox("Investment Thesis", True)
    sec_market = st.checkbox("Market Analysis", True)
    sec_financial = st.checkbox("Financial Projections", True)
    sec_deal = st.checkbox("Deal Structure", True)
    sec_risk = st.checkbox("Risk Mitigation", True)
    
    if st.button("Generate Deliverables", type="primary", key="gen2"):
        if "session_id" not in st.session_state and not st.session_state.get("demo_mode"):
            st.warning("No session found. Please upload source documents or enter a session ID manually if supported.")
            session_id = str(int(time.time()))
            st.session_state["session_id"] = session_id
            
        with st.spinner("Generating Deliverables..."):
            if st.session_state.get("demo_mode"):
                time.sleep(15)
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
                        "sections": sections
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
                    
            # --- Document Preview Viewers ---
            VIEWER_CSS = """
                <style>
                    .viewer-wrap { position:relative; border:1px solid #444; border-radius:8px; overflow:hidden; background:#1e1e1e; }
                    .viewer-bar { display:flex; align-items:center; padding:8px 16px; background:#2d2d2d; border-bottom:1px solid #444; }
                    .viewer-bar span { color:#ccc; font-weight:600; font-size:14px; }
                    .viewer-body { height:500px; overflow-y:auto; }

                    /* Slide styles */
                    .slide { background:linear-gradient(135deg,#0f1729,#1a2744); border:1px solid #334; border-radius:8px;
                             padding:28px 36px; margin-bottom:16px; min-height:200px; position:relative; }
                    .slide-num { position:absolute; top:10px; right:14px; color:#556; font-size:11px; font-weight:600; }
                    .slide-title { color:#e8eaf6; font-size:20px; font-weight:700; margin:0 0 16px; letter-spacing:0.5px; text-transform:uppercase; border-bottom:2px solid #4CAF50; padding-bottom:8px; }
                    .slide-subtitle { color:#b0bec5; font-size:15px; font-weight:600; margin:4px 0 12px; }
                    .slide-body p { color:#cfd8dc; font-size:13px; line-height:1.7; margin:4px 0; }
                    .slide-body li { color:#cfd8dc; font-size:13px; line-height:1.7; margin:2px 0; }
                    .slide-body ul { padding-left:18px; margin:6px 0; }

                    /* KPI row */
                    .kpi-row { display:flex; gap:12px; flex-wrap:wrap; margin:12px 0 16px; }
                    .kpi-card { background:#1b2a4a; border:1px solid #334; border-radius:6px; padding:12px 16px; text-align:center; flex:1; min-width:100px; }
                    .kpi-value { color:#4CAF50; font-size:22px; font-weight:700; }
                    .kpi-label { color:#90a4ae; font-size:11px; margin-top:2px; }

                    /* Numbered items */
                    .numbered-item { display:flex; gap:14px; margin:12px 0; }
                    .num-badge { background:#4CAF50; color:#fff; width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:14px; flex-shrink:0; margin-top:2px; }
                    .num-content h4 { color:#e0e0e0; font-size:14px; font-weight:600; margin:0 0 4px; }
                    .num-content p { color:#b0bec5; font-size:12.5px; line-height:1.6; margin:0; }

                    /* Two-column layout */
                    .two-col { display:flex; gap:24px; margin-top:12px; }
                    .two-col > div { flex:1; }
                    .col-title { color:#b0bec5; font-size:14px; font-weight:600; margin-bottom:8px; border-bottom:1px solid #334; padding-bottom:4px; }

                    /* Metric table */
                    .metric-table { width:100%; border-collapse:collapse; margin:8px 0; }
                    .metric-table td { padding:6px 10px; border-bottom:1px solid #263238; font-size:13px; }
                    .metric-table td:first-child { color:#90a4ae; }
                    .metric-table td:last-child { color:#e0e0e0; font-weight:600; text-align:right; }

                    /* DOCX body */
                    .docx-body { padding:28px 36px; background:#fafafa; color:#222; font-family:'Georgia',serif; font-size:14px; line-height:1.7; }
                    .docx-body h1,.docx-body h2,.docx-body h3 { color:#1a237e; }
                    .docx-body table { border-collapse:collapse; width:100%; margin:12px 0; }
                    .docx-body td,.docx-body th { border:1px solid #ccc; padding:6px 10px; }
                </style>
            """

            def render_docx_preview(file_path):
                """Convert DOCX to HTML and render in a preview viewer."""
                with open(file_path, "rb") as f:
                    result = mammoth.convert_to_html(f)
                    html_content = result.value
                viewer_html = f"""
                {VIEWER_CSS}
                <div id="docx-viewer" class="viewer-wrap">
                    <div class="viewer-bar">
                        <span>IC Memo Preview</span>
                    </div>
                    <div class="viewer-body docx-body">{html_content}</div>
                </div>
                """
                st.components.v1.html(viewer_html, height=560, scrolling=False)

            def render_pptx_preview(file_path):
                """Position-aware PPTX renderer with spatial layout."""
                prs = Presentation(file_path)
                sw = float(prs.slide_width or 12192000)

                def emu_pct(val, ref):
                    return round(float(val) / ref * 100, 1)

                slides_html = []
                for i, slide in enumerate(prs.slides):
                    # Collect all text shapes with positions
                    shapes_data = []
                    for shape in slide.shapes:
                        if not shape.has_text_frame and not shape.has_table:
                            continue
                        text = ""
                        if shape.has_text_frame:
                            text = "\n".join(p.text for p in shape.text_frame.paragraphs).strip()
                        shapes_data.append({
                            "text": text,
                            "x": float(shape.left or 0),
                            "y": float(shape.top or 0),
                            "w": float(shape.width or 0),
                            "h": float(shape.height or 0),
                            "has_table": shape.has_table,
                            "shape": shape,
                        })

                    if not shapes_data:
                        slides_html.append(f'<div class="slide"><div class="slide-num">Slide {i+1}</div><p style="color:#556;text-align:center;padding-top:60px;"><em>Visual slide</em></p></div>')
                        continue

                    # Sort by Y then X
                    shapes_data.sort(key=lambda s: (s["y"], s["x"]))

                    # Group into rows (shapes within 10% Y of each other)
                    rows = []
                    current_row = [shapes_data[0]]
                    for s in shapes_data[1:]:
                        if abs(s["y"] - current_row[0]["y"]) < 200000:  # ~0.5cm tolerance
                            current_row.append(s)
                        else:
                            rows.append(current_row)
                            current_row = [s]
                    rows.append(current_row)

                    # Detect slide title (first row, single wide shape near top)
                    slide_content = []
                    title_text = ""
                    for row_idx, row in enumerate(rows):
                        texts_in_row = [s["text"] for s in row if s["text"]]
                        if not texts_in_row:
                            continue

                        # Title detection: first row with text, near the top
                        if row_idx == 0 and len(row) <= 2 and row[0]["y"] < 1000000:
                            title_text = " — ".join(texts_in_row) if len(texts_in_row) > 1 else texts_in_row[0]
                            continue

                        # KPI row detection: 3+ items at same Y, short text
                        if len(row) >= 3 and all(len(s["text"]) < 30 for s in row if s["text"]):
                            # Check if alternating value/label pattern (paired rows)
                            kpi_cards = []
                            row.sort(key=lambda s: s["x"])
                            for s in row:
                                if s["text"]:
                                    kpi_cards.append(s["text"])
                            # Check next row for labels
                            if row_idx + 1 < len(rows):
                                next_row = rows[row_idx + 1]
                                next_texts = sorted([(s["x"], s["text"]) for s in next_row if s["text"]], key=lambda t: t[0])
                                if len(next_texts) == len(kpi_cards):
                                    html = '<div class="kpi-row">'
                                    for val, (_, label) in zip(kpi_cards, next_texts):
                                        html += f'<div class="kpi-card"><div class="kpi-value">{val}</div><div class="kpi-label">{label}</div></div>'
                                    html += '</div>'
                                    slide_content.append(html)
                                    rows[row_idx + 1] = []  # mark consumed
                                    continue
                            # Standalone KPI row
                            html = '<div class="kpi-row">'
                            for v in kpi_cards:
                                html += f'<div class="kpi-card"><div class="kpi-value">{v}</div></div>'
                            html += '</div>'
                            slide_content.append(html)
                            continue

                        # KPI label row (already consumed)
                        if not row:
                            continue

                        # Numbered item detection: first shape is a single digit
                        if len(row) >= 2 and row[0]["text"].strip().isdigit() and len(row[0]["text"].strip()) == 1:
                            num = row[0]["text"].strip()
                            rest = row[1:]
                            heading = rest[0]["text"] if rest else ""
                            body = ""
                            if len(rest) > 1:
                                body = rest[1]["text"]
                            # Check if next row is the body for this numbered item
                            elif row_idx + 1 < len(rows):
                                next_row = rows[row_idx + 1]
                                next_texts = [s["text"] for s in next_row if s["text"]]
                                if next_texts and not next_texts[0].strip().isdigit():
                                    # Check it's indented similarly (body text)
                                    if next_row[0]["x"] > 900000:
                                        body = next_texts[0]
                                        rows[row_idx + 1] = []
                            html = f'<div class="numbered-item"><div class="num-badge">{num}</div><div class="num-content"><h4>{heading}</h4>'
                            if body:
                                # Split on sentence-like boundaries for bullet points
                                parts = [p.strip() for p in body.replace("\u25a0", "\n").split("\n") if p.strip()]
                                if len(parts) > 1:
                                    html += "<ul>" + "".join(f"<li>{p}</li>" for p in parts) + "</ul>"
                                else:
                                    html += f"<p>{body}</p>"
                            html += '</div></div>'
                            slide_content.append(html)
                            continue

                        # Two-column detection: 2 shapes side by side with substantial width
                        if len(row) == 2 and all(s["w"] > sw * 0.3 for s in row):
                            row.sort(key=lambda s: s["x"])
                            # Gather subsequent rows that belong to each column
                            left_x = row[0]["x"]
                            right_x = row[1]["x"]
                            mid = (left_x + right_x) / 2
                            left_items = [row[0]["text"]]
                            right_items = [row[1]["text"]]
                            # Look ahead for child rows
                            for future_idx in range(row_idx + 1, min(row_idx + 8, len(rows))):
                                fr = rows[future_idx]
                                if not fr:
                                    continue
                                if len(fr) == 2 and abs(fr[0]["x"] - left_x) < 500000:
                                    fr.sort(key=lambda s: s["x"])
                                    left_items.append(fr[0]["text"])
                                    right_items.append(fr[1]["text"])
                                    rows[future_idx] = []
                                else:
                                    break
                            html = '<div class="two-col"><div>'
                            html += f'<div class="col-title">{left_items[0]}</div>'
                            if len(left_items) > 1:
                                html += '<table class="metric-table">'
                                for item in left_items[1:]:
                                    if item:
                                        html += f'<tr><td colspan="2">{item}</td></tr>'
                                html += '</table>'
                            html += '</div><div>'
                            html += f'<div class="col-title">{right_items[0]}</div>'
                            if len(right_items) > 1:
                                html += '<table class="metric-table">'
                                for ri_idx, item in enumerate(right_items[1:]):
                                    if item:
                                        html += f'<tr><td colspan="2">{item}</td></tr>'
                                html += '</table>'
                            html += '</div></div>'
                            slide_content.append(html)
                            continue

                        # Two paired shapes (label + value) side by side
                        if len(row) == 2 and any(s["w"] < sw * 0.3 for s in row):
                            row.sort(key=lambda s: s["x"])
                            slide_content.append(f'<table class="metric-table"><tr><td>{row[0]["text"]}</td><td>{row[1]["text"]}</td></tr></table>')
                            continue

                        # Default: body text
                        for s in row:
                            if not s["text"]:
                                continue
                            if s.get("has_table"):
                                table = s["shape"].table
                                tbl = '<table class="metric-table">'
                                for r_idx, trow in enumerate(table.rows):
                                    tbl += '<tr>'
                                    for cell in trow.cells:
                                        tbl += f'<td>{cell.text}</td>'
                                    tbl += '</tr>'
                                tbl += '</table>'
                                slide_content.append(tbl)
                            else:
                                lines = s["text"].split("\n")
                                for line in lines:
                                    line = line.strip()
                                    if not line:
                                        continue
                                    # Bullet-like lines
                                    if line.startswith(("•", "-", "▪", "●")):
                                        slide_content.append(f'<div class="slide-body"><ul><li>{line.lstrip("•-▪● ")}</li></ul></div>')
                                    else:
                                        slide_content.append(f'<div class="slide-body"><p>{line}</p></div>')

                    title_html = f'<div class="slide-title">{title_text}</div>' if title_text else ""
                    # For slide 1 (cover), center everything
                    if i == 0:
                        inner = "".join(slide_content)
                        slides_html.append(f'''<div class="slide" style="text-align:center;display:flex;flex-direction:column;justify-content:center;min-height:260px;">
                            <div class="slide-num">Slide {i+1}</div>
                            {title_html}
                            {inner}
                        </div>''')
                    else:
                        inner = "".join(slide_content)
                        slides_html.append(f'''<div class="slide">
                            <div class="slide-num">Slide {i+1}</div>
                            {title_html}
                            {inner}
                        </div>''')

                all_slides = "\n".join(slides_html)
                viewer_html = f"""
                {VIEWER_CSS}
                <div id="pptx-viewer" class="viewer-wrap">
                    <div class="viewer-bar">
                        <span>Exec Deck Preview</span>
                    </div>
                    <div class="viewer-body" style="padding:16px 20px; background:#0a0e1a;">
                        {all_slides}
                    </div>
                </div>
                """
                st.components.v1.html(viewer_html, height=560, scrolling=False)

            urls = status_data.get("download_urls", {})

            # Show document previews
            if st.session_state.get("demo_mode"):
                docx_path = "demo_data/phase2_sample_memo.docx"
                pptx_path = "demo_data/phase2_sample_deck.pptx"
            else:
                docx_path = None
                pptx_path = None

            tab_memo, tab_deck = st.tabs(["IC Memo (DOCX)", "Exec Deck (PPTX)"])

            with tab_memo:
                if docx_path and os.path.exists(docx_path):
                    render_docx_preview(docx_path)
                    with open(docx_path, "rb") as f:
                        st.download_button("Download DOCX", f.read(), file_name="memo.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", use_container_width=True)
                elif urls and urls.get("docx"):
                    host = BACKEND_HOST
                    st.markdown(f"**[Download DOCX]({host}{urls['docx']})**")

            with tab_deck:
                if pptx_path and os.path.exists(pptx_path):
                    render_pptx_preview(pptx_path)
                    with open(pptx_path, "rb") as f:
                        st.download_button("Download PPTX", f.read(), file_name="deck.pptx", mime="application/vnd.openxmlformats-officedocument.presentationml.presentation", use_container_width=True)
                elif urls and urls.get("pptx"):
                    host = BACKEND_HOST
                    st.markdown(f"**[Download PPTX]({host}{urls['pptx']})**")

            # Audit trail download separately
            if urls and urls.get("audit_trail"):
                if not st.session_state.get("demo_mode"):
                    host = BACKEND_HOST
                    st.markdown(f"**[Download Audit Trail JSON]({host}{urls['audit_trail']})**")
        elif status == "failed":
            st.error("Job failed")

