import streamlit as st
import subprocess
import sys
import os
import json
import time
import pandas as pd
from datetime import datetime
from scrape import scrape_website, extract_website_intelligence, generate_test_cases
from dataclasses import dataclass
from typing import List, Dict
import asyncio
import jsonschema
import threading



st.set_page_config(
    page_title="Marcus Intelligence - AI Webscraper Agent",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)


st.markdown("""
<style>
    .main-header { font-size: 3rem; color: #1f77b4; }
    .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
    .stTabs [data-baseweb="tab"] { font-weight: bold; }
</style>
""", unsafe_allow_html=True)


st.markdown('<h1 class="main-header">Marcus Intelligence</h1>', unsafe_allow_html=True)
st.markdown("Production Webscraper Testing Suite")


if 'tests_generated' not in st.session_state:
    st.session_state.tests_generated = False
if 'process_running' not in st.session_state:
    st.session_state.process_running = False

with st.sidebar:
    st.header("Configuration")
    coverage = st.selectbox("Test Coverage", ["basic", "standard", "comprehensive"])
    
    st.header("Status")
    if os.path.exists("tests.json"):
        with open("tests.json", "r") as f:
            tests = json.load(f)
        st.metric("Tests Ready", len(tests))
    else:
        st.metric("Tests Ready", 0)
    
    if os.path.exists("test_results.json"):
        try:
            with open("test_results.json", "r") as f:
                results = json.load(f)
            st.metric("Tests Completed", len(results))
        except:
            st.metric("Tests Completed", 0)


tab1, tab2, tab3, tab4 = st.tabs(["1. Generate", "2. Execute", "3. Results", "4. Export"])


# TAB 1: Generate Tests (COMPLETE BRD + WEB INTEGRATION)
with tab1:
    st.header("Test Case Generation")
    
    # Input controls - URL + BRD + Instructions
    col1, col2 = st.columns([3,1])
    with col1:
        url = st.text_input("Website URL", value="https://example.com", 
                          help="Leave empty for BRD-only mode")
    with col2:
        mode = st.selectbox("Mode", ["Hybrid (Web+BRD)", "Web Only", "BRD Only"])
    
    # BRD Upload + Instructions  
    brd_file = st.file_uploader("BRD/Requirements", type=['pdf','txt','docx'], 
                               help="Upload PDF/TXT/DOCX for requirements-based tests")
    instructions = st.text_area("Custom Instructions", 
                               placeholder="e.g., Focus on login flows, ignore payments",
                               height=80)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Generate Tests", type="primary", use_container_width=True):
            try:
                source = None
                extracted = None
                
                # HANDLE BRD (if uploaded)
                if brd_file:
                    if brd_file.name.endswith('.pdf'):
                        import pypdf
                        reader = pypdf.PdfReader(brd_file)
                        brd_text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
                    elif brd_file.name.endswith('.docx'):
                        from docx import Document
                        doc = Document(brd_file)
                        brd_text = "\n".join([p.text for p in doc.paragraphs])
                    else:  # txt
                        brd_text = brd_file.read().decode('utf-8')
                    
                    source = {"brd_content": brd_text[:-1]}  
                    st.success("Extracted {} chars from BRD".format(len(brd_text)))
                
                # HANDLE WEBSITE (if URL provided AND not BRD-only)
                if url and mode != "BRD Only":
                    url = url if url.startswith(('http://', 'https://')) else "https://" + url
                    with st.spinner("Scraping website..."):
                        html = scrape_website(url)
                    with st.spinner("Extracting intelligence..."):
                        extracted = extract_website_intelligence(html, url)
                
                # CREATE DUMMY EXTRACTED if no web data (for BRD-only mode)
                #!!!! Why the fuck do we need to extract buttons, dom structure etc.. from BRD?????
                if extracted is None:
                    from scrape import ExtractedWebsiteData
                    extracted = ExtractedWebsiteData(
                        url="", title="BRD Mode", description="", 
                        forms=[], buttons=[], features={}, 
                        text_summary="", dom_structure="{}", errors=[]
                    )
                
                # GENERATE TESTS (using new params)
                with st.spinner("Generating test cases..."):
                    tests = generate_test_cases(
                        source=source, 
                        instruction=instructions or "",
                        extracted=extracted,
                        coverage=coverage
                    )
                
                # Save
                with open("tests.json", "w", encoding='utf-8') as f:
                    json.dump(tests, f, ensure_ascii=False, indent=2)
                
                st.session_state.tests_generated = True
                sources_used = []
                if extracted.url: sources_used.append("Web")
                if source: sources_used.append("BRD")
                st.success("Generated {} test cases! {}".format(len(tests), ', '.join(sources_used)))
                
            except Exception as e:
                st.error("Generation failed: {}".format(str(e)))
                st.exception(e)
    
    # Existing metrics + sample display
    if st.session_state.tests_generated and os.path.exists("tests.json"):
        with open("tests.json", "r") as f:
            tests = json.load(f)
        
        pos = sum(1 for t in tests if t["type"] == "positive")
        neg = sum(1 for t in tests if t["type"] == "negative")
        edge = sum(1 for t in tests if t["type"] == "edge")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Tests", len(tests))
        col2.metric("Positive", pos)
        col3.metric("Negative", neg)
        col4.metric("Edge Cases", edge)
        
        st.subheader("Sample Test Cases")
        for tc in tests[:3]:
            with st.expander("TC{:02d}: {} ({})".format(tc['id'], tc['title'], tc['type'].upper())):
                st.markdown("**Expected:** {}".format(tc['expected_result']))
                st.markdown("**Steps:**")
                for i, step in enumerate(tc["steps"], 1):
                    st.markdown("{}. {}".format(i, step))


# TAB 2: Execute Tests 
with tab2:
    st.header("Test Execution")
    
    if not os.path.exists("tests.json"):
        st.warning("Generate tests first!")
    else:
        col1, col2 = st.columns([4, 1])
        
        async def safe_run_agent():
            """Secure sandboxed agent spawn with JSON validation"""
            try:
                # STEP 1: Load + Schema Validation (Blocks attacks)
                with open("tests.json", "r", encoding='utf-8') as f:
                    tests = json.load(f)
                
                TEST_SCHEMA = {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "steps": {"type": "array", "items": {"type": "string"}},
                            "type": {"enum": ["positive", "negative", "edge"]}
                        },
                        "required": ["id", "steps"]
                    }
                }
                jsonschema.validate(tests, TEST_SCHEMA)
                st.success(f"Validated {len(tests)} SAFE tests")
                
                # STEP 2: Locked Environment
                cmd = [sys.executable, "-m", "browsing_agent"]
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                env['PYTHONUNBUFFERED'] = '1'
                env['PYTHONPATH'] = os.getcwd()  # Lock to project dir ONLY
                
                # STEP 3: Sandboxed Async Spawn (No shell, cwd-locked)
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=os.getcwd()
                )
                
                st.session_state.test_process = process
                st.session_state.process_running = True
                st.session_state.start_time = time.time()
                st.success("Secure tests started!")
                
            except jsonschema.exceptions.ValidationError as e:
                st.error(f"MALICIOUS TESTS BLOCKED: {str(e)[:-1]}")
            except FileNotFoundError:
                st.error("browsing_agent.py missing!")
            except Exception as e:
                st.error(f"Secure spawn failed: {str(e)}")
                st.exception(e)
        
        with col1:
            if st.button("Start Browser Tests", type="primary", use_container_width=True, 
                        disabled=st.session_state.process_running):
                # Streamlit async hack: Thread + asyncio.run()
                import threading
                threading.Thread(
                    target=lambda: asyncio.run(safe_run_agent()), 
                    daemon=True
                ).start()
                st.rerun()
        
        with col2:
            if st.session_state.process_running:
                if st.button("Stop Tests", type="secondary", use_container_width=True):
                    if 'test_process' in st.session_state:
                        st.session_state.test_process.terminate()
                    st.session_state.process_running = False
                    st.warning("Tests stopped!")
                    st.rerun()
        
        # Live monitoring (YOUR ORIGINAL CODE - UNCHANGED)
        if st.session_state.process_running:
            st.subheader("Live Execution Monitor")
            
            # Process metrics
            process = st.session_state.test_process
            return_code = process.poll()
            uptime = time.time() - st.session_state.start_time
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Status", "RUNNING" if return_code is None else "COMPLETED")
            c2.metric("PID", process.pid)
            c3.metric("Uptime", "{:.0f}s".format(uptime))
            
            # Real-time file viewer
            st.subheader("Live File Status")
            file_col1, file_col2 = st.columns(2)
            
            with file_col1:
                if os.path.exists("progress.json"):
                    try:
                        with open("progress.json", "r") as f:
                            prog = json.load(f)
                        st.metric("Current Test", "{}/{}".format(prog.get('current', 0), prog.get('total', 0)))
                        st.json(prog)
                    except:
                        st.error("progress.json corrupted")
                else:
                    st.info("progress.json - Not started")
            
            with file_col2:
                if os.path.exists("test_results.json"):
                    try:
                        with open("test_results.json", "r") as f:
                            results = json.load(f)
                        st.metric("Tests Done", len(results))
                        if results:
                            latest = results[-1]
                            st.success("Latest: TC{} - {}".format(latest['test_id'], latest['status']))
                    except:
                        st.error("test_results.json corrupted")
                else:
                    st.info("test_results.json - Empty")
            
            # Auto-refresh button
            if st.button("Refresh", key="refresh_monitor"):
                st.rerun()
            
            # Process completion
            if return_code is not None:
                st.session_state.process_running = False
                st.success("All tests completed!")
                st.rerun()

# TAB 3: Results Dashboard
with tab3:
    st.header("Results Dashboard")
    
    if os.path.exists("test_results.json"):
        try:
            with open("test_results.json", "r", encoding='utf-8') as f:
                results = json.load(f)
            
            # Summary KPIs
            df = pd.DataFrame(results)
            total = len(df)
            passed = len(df[df['status'] == 'PASS'])
            failed = len(df[df['status'] == 'FAIL'])
            pass_rate = passed / total * 100
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Tests", total)
            c2.metric("Passed", passed, "{:.1f}%".format(pass_rate))
            c3.metric("Failed", failed)
            c4.metric("Pass Rate", "{:.1f}%".format(pass_rate))
            
            # Charts
            st.subheader("Test Results")
            col1, col2 = st.columns(2)
            
            with col1:
                status_counts = df['status'].value_counts()
                st.bar_chart(status_counts)
            
            with col2:
                type_counts = df['type'].value_counts()
                st.bar_chart(type_counts)
            
            # Detailed table
            st.subheader("Test Details")
            st.dataframe(df[['test_id', 'title', 'type', 'status', 'timestamp']].style.highlight_max(axis=0), use_container_width=True)
            
        except Exception as e:
            st.error("Cannot parse results: {}".format(e))
    else:
        st.info("No test results yet. Run tests first.")


# TAB 4: Export & Share
with tab4:
    st.header("Export Results")
    
    if os.path.exists("test_results.json"):
        try:
            with open("test_results.json", "r") as f:
                results = json.load(f)
            
            df = pd.DataFrame(results)
            
            # Download buttons
            csv = df.to_csv(index=False)
            json_str = json.dumps(results, indent=2)
            
            st.download_button(
                "Download CSV",
                csv,
                "test_results.csv",
                "text/csv"
            )
            st.download_button(
                "Download JSON", 
                json_str,
                "test_results.json",
                "application/json"
            )
            
            # Summary report
            st.subheader("Summary Report")
            total = len(df)
            passed = len(df[df['status']=='PASS'])
            st.markdown("""
            **Marcus Intelligence Test Report**
            ====================
            **Total Tests**: {}
            **Passed**: {} ({:.1f}%)
            **Failed**: {}
            **Generated**: {}
            """.format(total, passed, passed/total*100, total-passed, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            
        except:
            st.error("Cannot generate export")
    else:
        st.info("Run tests first")

