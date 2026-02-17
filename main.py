"""
Main application for Marcus Intelligence used as frontend for the application.
"""

import streamlit as st

st.set_page_config(
    page_title="Marcus Intelligence",
    page_icon="assets/logo.svg",
    layout="wide",
    initial_sidebar_state="expanded"
)

import subprocess
import sys
import os
import json
import time
import pandas as pd
from datetime import datetime
from scrape import scrape_website, extract_website_intelligence, generate_test_cases, aggregate_crawl_data
from scrape import ExtractedWebsiteData
from crawler import crawl_website
import jsonschema
from dotenv import load_dotenv
from auth import (
    init_session_state, require_auth, sign_out, get_authenticated_client,
    load_user_orgs, refresh_session_if_needed,
)


load_dotenv()

# ─── Auth Gate ───────────────────────────────────────────────────────────────
require_auth()

# ─── User is authenticated from here on ─────────────────────────────────────
refresh_session_if_needed()
load_user_orgs()

# ─── Global CSS ──────────────────────────────────────────────────────────────
from styles import get_app_css
st.markdown(get_app_css(), unsafe_allow_html=True)


# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>Marcus Intelligence</h1>
</div>
<p class="app-subtitle">AI-Powered Test Automation &nbsp;&middot;&nbsp; Generate &nbsp;&middot;&nbsp; Execute &nbsp;&middot;&nbsp; Analyze</p>
""", unsafe_allow_html=True)


# ─── Session state defaults for app logic ────────────────────────────────────
if 'tests_generated' not in st.session_state:
    st.session_state.tests_generated = False
if 'process_running' not in st.session_state:
    st.session_state.process_running = False
if 'current_run_id' not in st.session_state:
    st.session_state.current_run_id = None
if 'process_just_completed' not in st.session_state:
    st.session_state.process_just_completed = False
if 'last_return_code' not in st.session_state:
    st.session_state.last_return_code = None


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_org_test_runs():
    """Get test runs for the current org, newest first."""
    org_id = st.session_state.current_org_id
    if not org_id:
        return []
    client = get_authenticated_client()
    try:
        response = client.table("test_runs") \
            .select("*") \
            .eq("org_id", org_id) \
            .order("created_at", desc=True) \
            .execute()
        return response.data or []
    except Exception:
        return []


def get_run_results(run_id: int):
    """Get test results for a specific run."""
    client = get_authenticated_client()
    try:
        response = client.table("test_results") \
            .select("*") \
            .eq("run_id", run_id) \
            .order("test_id") \
            .execute()
        return response.data or []
    except Exception:
        return []


def status_badge(status: str) -> str:
    """Return HTML for a colored status badge."""
    s = status.upper()
    cls = "badge-pass" if s == "PASS" else \
          "badge-fail" if s == "FAIL" else \
          "badge-running" if s == "RUNNING" else \
          "badge-error" if s in ("ERROR", "TIMEOUT", "JSON_ERROR", "NO_JSON") else \
          "badge-pending"
    return '<span class="badge {}">{}</span>'.format(cls, s)


def stat_cards_html(cards: list) -> str:
    """Build HTML for a row of stat cards.
    cards: list of (value, label, color_class)
    """
    inner = ""
    for value, label, color in cards:
        inner += '<div class="stat-card {c}"><div class="stat-value">{v}</div><div class="stat-label">{l}</div></div>'.format(
            c=color, v=value, l=label)
    return '<div class="stat-row">{}</div>'.format(inner)


def compute_status_breakdown(df):
    """Compute detailed status breakdown from a results DataFrame."""
    total = len(df)
    passed = len(df[df['status'] == 'PASS'])
    failed = len(df[df['status'] == 'FAIL'])
    timeout = len(df[df['status'] == 'TIMEOUT'])
    errors = len(df[df['status'] == 'ERROR'])
    json_err = len(df[df['status'].isin(['JSON_ERROR', 'NO_JSON'])])
    pass_rate = passed / total * 100 if total > 0 else 0
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "timeout": timeout,
        "errors": errors,
        "json_err": json_err,
        "pass_rate": pass_rate,
    }


def create_styled_bar_chart(labels, values, colors, title=""):
    """Create a premium-styled Plotly bar chart."""
    import plotly.graph_objects as go

    fig = go.Figure(data=[
        go.Bar(
            x=labels,
            y=values,
            marker_color=colors,
            marker_cornerradius=8,
            marker_line=dict(width=0),
            text=values,
            textposition='outside',
            textfont=dict(
                family="Inter, sans-serif",
                size=12,
                color="#c0c0d8",
                weight=600,
            ),
            hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>',
        )
    ])
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", color="#6a6a88", size=12),
        margin=dict(l=16, r=16, t=24, b=36),
        height=280,
        xaxis=dict(
            color="#6a6a88",
            gridcolor="rgba(255,255,255,0.03)",
            showgrid=False,
            tickfont=dict(size=11, weight=600),
        ),
        yaxis=dict(
            color="#6a6a88",
            gridcolor="rgba(255,255,255,0.03)",
            showgrid=True,
            tickfont=dict(size=10),
            zeroline=False,
        ),
        bargap=0.4,
        hoverlabel=dict(
            bgcolor="#1a1a3e",
            bordercolor="rgba(102,126,234,0.3)",
            font=dict(family="Inter, sans-serif", color="#e0e0f0", size=12),
        ),
    )
    return fig


def render_results_table(df):
    """Render results table with colored status badges via HTML."""
    cols = ['test_id', 'title', 'type', 'status', 'reason']
    available_cols = [c for c in cols if c in df.columns]

    header_labels = {
        'test_id': 'ID',
        'title': 'Test Case',
        'type': 'Type',
        'status': 'Status',
        'reason': 'Reason',
    }
    header_cells = "".join(
        "<th>{}</th>".format(header_labels.get(c, c)) for c in available_cols
    )

    rows_html = ""
    for _, row in df.iterrows():
        cells = ""
        for col in available_cols:
            val = str(row.get(col, ""))
            if col == "status":
                val = status_badge(val)
            elif col == "reason":
                escaped = val.replace('"', '&quot;').replace('<', '&lt;')
                display = (val[:80] + "...") if len(val) > 80 else val
                display = display.replace('<', '&lt;')
                val = '<span class="reason-cell" title="{}">{}</span>'.format(escaped, display)
            elif col == "type":
                val = val.upper() if val else ""
            cells += "<td>{}</td>".format(val)
        rows_html += "<tr>{}</tr>".format(cells)

    st.markdown(
        '<table class="results-table"><thead><tr>{h}</tr></thead><tbody>{r}</tbody></table>'.format(
            h=header_cells, r=rows_html),
        unsafe_allow_html=True
    )


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    user = st.session_state.user
    user_email = getattr(user, 'email', 'User')
    org_name = st.session_state.current_org_name or "Personal"

    user_initial = user_email[0].upper() if user_email else "U"
    st.markdown("""
    <div class="sidebar-user">
        <div style="display:flex;align-items:center;gap:0.65rem;">
            <div style="width:32px;height:32px;border-radius:8px;background:linear-gradient(135deg,var(--accent),var(--accent-2));display:flex;align-items:center;justify-content:center;font-weight:700;font-size:0.8rem;color:#fff;flex-shrink:0;">{initial}</div>
            <div>
                <div class="user-email">{email}</div>
                <div class="user-org">{org}</div>
            </div>
        </div>
    </div>
    """.format(initial=user_initial, email=user_email, org=org_name), unsafe_allow_html=True)

    # Org switcher
    st.markdown('<div class="sidebar-label">Workspace</div>', unsafe_allow_html=True)
    orgs = st.session_state.user_orgs
    if orgs:
        org_names = [o["name"] for o in orgs]
        current_idx = next(
            (i for i, o in enumerate(orgs) if o["id"] == st.session_state.current_org_id),
            0,
        )
        selected = st.selectbox("Workspace", org_names, index=current_idx, key="org_select", label_visibility="collapsed")
        selected_org = orgs[org_names.index(selected)]
        if selected_org["id"] != st.session_state.current_org_id:
            st.session_state.current_org_id = selected_org["id"]
            st.session_state.current_org_name = selected_org["name"]
            st.rerun()
    else:
        st.info("No organization found.")

    st.markdown('<div class="sidebar-label">Test Coverage</div>', unsafe_allow_html=True)
    coverage = st.selectbox("Coverage", ["basic", "standard", "comprehensive"], key="coverage_select", label_visibility="collapsed")

    # Status
    st.markdown('<div class="sidebar-label">Quick Stats</div>', unsafe_allow_html=True)
    runs = get_org_test_runs()
    completed_runs = [r for r in runs if r.get("status") == "completed"]
    c1, c2 = st.columns(2)
    c1.metric("Runs", len(runs))
    c2.metric("Completed", len(completed_runs))

    st.divider()
    if st.button("Sign Out", use_container_width=True):
        sign_out()
        st.rerun()


# ─── Tabs ────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["Generate Tests", "Execute", "Results", "Export"])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: Generate Tests
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-header">Test Case Generation</div>', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col1:
        url = st.text_input("Website URL", value="https://example.com",
                            help="Leave empty for BRD-only mode",
                            placeholder="https://your-website.com")
    with col2:
        mode = st.selectbox("Mode", ["Hybrid (Web+BRD)", "Web Only", "BRD Only"])

    deep_crawl_enabled = st.checkbox("Enable Deep Crawl", value=False,
                                     help="Crawl multiple pages instead of just the homepage. Supports login-protected sites.")

    if deep_crawl_enabled:
        crawl_col1, crawl_col2 = st.columns(2)
        with crawl_col1:
            max_pages = st.slider("Max Pages", min_value=1, max_value=50, value=20)
        with crawl_col2:
            max_depth = st.slider("Max Depth", min_value=1, max_value=3, value=2)

        with st.expander("Login Required?"):
            login_url = st.text_input("Login Page URL", placeholder="https://your-site.com/login",
                                      help="Leave empty if no login is needed")
            login_username = st.text_input("Username / Email", placeholder="user@example.com")
            login_password = st.text_input("Password", type="password")

    brd_file = st.file_uploader("Upload BRD / Requirements Document", type=['pdf', 'txt', 'docx'],
                                help="Upload PDF, TXT, or DOCX for requirements-based tests")
    instructions = st.text_area("Custom Instructions (optional)",
                                placeholder="e.g., Focus on login flows, test all navigation links, ignore payment pages",
                                height=80)

    if st.button("Generate Tests", type="primary", use_container_width=True):
        try:
            source = None
            extracted = None

            # Handle BRD
            if brd_file:
                if brd_file.name.endswith('.pdf'):
                    import pypdf
                    reader = pypdf.PdfReader(brd_file)
                    brd_text = "".join(page.extract_text() for page in reader.pages if page.extract_text())
                elif brd_file.name.endswith('.docx'):
                    from docx import Document
                    doc = Document(brd_file)
                    brd_text = "\n".join([p.text for p in doc.paragraphs])
                else:
                    brd_text = brd_file.read().decode('utf-8')

                source = {"brd_content": brd_text[:-1]}
                st.success("Extracted {} chars from BRD".format(len(brd_text)))

            # Handle website
            site_map = None
            if url and mode != "BRD Only":
                url = url if url.startswith(('http://', 'https://')) else "https://" + url

                if deep_crawl_enabled:
                    crawl_login_url = login_url.strip() if login_url.strip() else None
                    crawl_username = login_username.strip() if login_username.strip() else None
                    crawl_password = login_password if login_password else None

                    with st.status("Deep crawling website...", expanded=True) as status:
                        st.write("Starting crawl of {}".format(url))

                        crawl_result = crawl_website(
                            start_url=url,
                            max_pages=max_pages,
                            max_depth=max_depth,
                            login_url=crawl_login_url,
                            login_username=crawl_username,
                            login_password=crawl_password,
                        )

                        if crawl_result.errors:
                            for err in crawl_result.errors[:5]:
                                st.warning(err)
                        if crawl_login_url and crawl_result.login_success:
                            st.write("Login successful")
                        elif crawl_login_url:
                            st.warning("Login may have failed — crawl continued without auth")

                        status.update(label="Crawled {} pages".format(len(crawl_result.pages)), state="complete")

                    site_map = crawl_result.site_map
                    with st.spinner("Aggregating crawl data..."):
                        aggregated_html = aggregate_crawl_data(crawl_result.pages)
                    with st.spinner("Analyzing page structure..."):
                        extracted = extract_website_intelligence(aggregated_html, url)
                else:
                    with st.spinner("Scraping website..."):
                        html = scrape_website(url)
                    with st.spinner("Analyzing page structure..."):
                        extracted = extract_website_intelligence(html, url)

            # Dummy extracted for BRD-only mode
            if extracted is None:
                extracted = ExtractedWebsiteData(
                    url="", title="BRD Mode", description="",
                    forms=[], buttons=[], features={},
                    text_summary="", dom_structure="{}", errors=[]
                )

            # Generate tests
            with st.spinner("Generating test cases with AI..."):
                tests = generate_test_cases(
                    source=source,
                    instruction=instructions or "",
                    extracted=extracted,
                    coverage=coverage,
                    site_map=site_map,
                )

            # Save to Supabase
            client = get_authenticated_client()
            run_response = client.table("test_runs").insert({
                "org_id": st.session_state.current_org_id,
                "user_id": str(st.session_state.user.id),
                "url": url if url and mode != "BRD Only" else None,
                "mode": mode,
                "coverage": coverage,
                "tests_json": tests,
                "status": "pending",
            }).execute()

            run_id = run_response.data[0]["id"]
            st.session_state.current_run_id = run_id

            # Also write locally for subprocess
            with open("tests.json", "w", encoding='utf-8') as f:
                json.dump(tests, f, ensure_ascii=False, indent=2)

            sources_used = []
            if extracted.url:
                sources_used.append("Web")
            if source:
                sources_used.append("BRD")

            if len(tests) == 0:
                st.warning("No test cases were generated. The website may be too minimal. Try a different URL or add a BRD document.")
            else:
                st.session_state.tests_generated = True
                st.success("Generated {} test cases (Run #{})  |  Sources: {}".format(
                    len(tests), run_id, ', '.join(sources_used) if sources_used else "BRD Only"))

        except Exception as e:
            st.error("Generation failed: {}".format(str(e)))
            st.exception(e)

    # Show test metrics if tests were generated
    if st.session_state.tests_generated and os.path.exists("tests.json"):
        with open("tests.json", "r") as f:
            tests = json.load(f)

        pos = sum(1 for t in tests if t.get("type") == "positive")
        neg = sum(1 for t in tests if t.get("type") == "negative")
        edge = sum(1 for t in tests if t.get("type") == "edge")

        st.markdown(stat_cards_html([
            (len(tests), "Total Tests", "stat-purple"),
            (pos, "Positive", "stat-green"),
            (neg, "Negative", "stat-red"),
            (edge, "Edge Cases", "stat-amber"),
        ]), unsafe_allow_html=True)

        st.markdown('<div class="section-header">Generated Test Cases</div>', unsafe_allow_html=True)
        for tc in tests[:5]:
            with st.expander("TC{:02d} - {} ({})".format(tc['id'], tc['title'], tc['type'].upper())):
                st.markdown("**Expected:** {}".format(tc['expected_result']))
                st.markdown("**Steps:**")
                for i, step in enumerate(tc["steps"], 1):
                    st.markdown("{}. {}".format(i, step))


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: Execute Tests
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-header">Test Execution</div>', unsafe_allow_html=True)

    # Auto-refresh every 3 seconds while process is running
    if st.session_state.process_running:
        try:
            from streamlit_autorefresh import st_autorefresh
            st_autorefresh(interval=3000, limit=None, key="exec_autorefresh")
        except ImportError:
            st.info("Install `streamlit-autorefresh` for auto-updates, or click below.")
            if st.button("Refresh", key="manual_refresh"):
                st.rerun()

    org_runs = get_org_test_runs()
    pending_runs = [r for r in org_runs if r.get("status") in ("pending", "running", "completed")]

    if not pending_runs:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-svg">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="80" height="80">
                    <defs><linearGradient id="esg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#667eea"/><stop offset="100%" stop-color="#764ba2"/></linearGradient></defs>
                    <circle cx="50" cy="50" r="28" stroke="url(#esg)" stroke-width="3" fill="none" opacity="0.6"/>
                    <line x1="70" y1="70" x2="95" y2="95" stroke="url(#esg)" stroke-width="4" stroke-linecap="round" opacity="0.6"/>
                </svg>
            </div>
            <p class="empty-title">No test runs available</p>
            <p class="empty-hint">Generate tests first in the Generate tab</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        selected_run = st.selectbox(
            "Select Test Run",
            options=pending_runs,
            format_func=lambda r: "Run #{} - {} ({}) - {}".format(
                r['id'],
                r.get('url') or 'BRD Only',
                r['status'],
                r['created_at'][:16],
            ),
            key="exec_run_select",
        )

        col1, col2 = st.columns([4, 1])

        def safe_run_agent_sync(run_data):
            """Validate and launch browsing_agent as subprocess."""
            try:
                tests = run_data["tests_json"]
                if isinstance(tests, str):
                    tests = json.loads(tests)

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
                st.success("{} tests validated".format(len(tests)))

                # Write tests locally for the subprocess
                with open("tests.json", "w", encoding='utf-8') as f:
                    json.dump(tests, f, ensure_ascii=False, indent=2)

                # Spawn subprocess with multi-tenancy env vars
                env = os.environ.copy()
                env['PYTHONPATH'] = os.getcwd()
                env['PYTHONIOENCODING'] = 'utf-8'
                env['PYTHONUNBUFFERED'] = '1'
                env['MARCUS_RUN_ID'] = str(run_data['id'])
                env['MARCUS_USER_ID'] = str(st.session_state.user.id)
                env['MARCUS_ORG_ID'] = str(st.session_state.current_org_id)
                service_key = os.getenv('SUPABASE_SERVICE_KEY', '')
                if service_key:
                    env['SUPABASE_SERVICE_KEY'] = service_key

                log_file = open("agent_output.log", "w", encoding="utf-8")
                process = subprocess.Popen(
                    [sys.executable, "-m", "browsing_agent"],
                    env=env,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=os.getcwd()
                )

                st.session_state.test_process = process
                st.session_state.log_file = log_file
                st.session_state.process_running = True
                st.session_state.process_just_completed = False
                st.session_state.start_time = time.time()
                st.session_state.current_run_id = run_data['id']
                st.success("Execution started (Run #{})".format(run_data['id']))

            except jsonschema.exceptions.ValidationError as e:
                st.error("Validation failed: {}".format(str(e)[:200]))
            except FileNotFoundError:
                st.error("browsing_agent.py not found in the project directory.")
            except Exception as e:
                st.error("Failed to start: {}".format(str(e)))

        with col1:
            if st.button("Start Execution", type="primary", use_container_width=True,
                         disabled=st.session_state.process_running):
                safe_run_agent_sync(selected_run)
                st.rerun()

        with col2:
            if st.session_state.process_running:
                if st.button("Stop", type="secondary", use_container_width=True):
                    st.session_state.test_process.terminate()
                    if hasattr(st.session_state, 'log_file') and st.session_state.log_file:
                        st.session_state.log_file.close()
                        st.session_state.log_file = None
                    st.session_state.process_running = False
                    st.rerun()

        # ─── Live monitoring ──────────────────────────────────────────────────
        if st.session_state.process_running:
            process = st.session_state.test_process
            return_code = process.poll()
            uptime = time.time() - st.session_state.start_time

            st.markdown('<div class="monitor-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-header" style="margin-top:0;border:none;padding-bottom:0.3rem;">Live Monitor &nbsp;<span class="badge badge-running">RUNNING</span></div>', unsafe_allow_html=True)

            # Read enriched progress data
            prog_data = {}
            if os.path.exists("progress.json"):
                try:
                    with open("progress.json", "r", encoding='utf-8') as f:
                        prog_data = json.load(f)
                except Exception:
                    pass

            current_done = prog_data.get("current", 0)
            total_tests = prog_data.get("total", "?")
            current_test = prog_data.get("current_test_title", "...")
            test_elapsed = prog_data.get("test_elapsed_seconds")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Status", "RUNNING" if return_code is None else "DONE")
            c2.metric("Progress", "{}/{}".format(current_done, total_tests))
            c3.metric("Current Test", (current_test[:28] + "..") if current_test and len(current_test) > 30 else (current_test or "..."))
            c4.metric("Elapsed", "{:.0f}s".format(uptime))

            # Progress bar
            if isinstance(total_tests, int) and total_tests > 0:
                bar_text = "{}/{} completed".format(current_done, total_tests)
                if current_test and current_test != "...":
                    bar_text += " | Current: {}".format(current_test[:40])
                if test_elapsed is not None:
                    bar_text += " ({:.0f}s)".format(test_elapsed)
                st.progress(current_done / total_tests, text=bar_text)

            st.markdown('</div>', unsafe_allow_html=True)

            # Check if process finished
            if return_code is not None:
                if hasattr(st.session_state, 'log_file') and st.session_state.log_file:
                    st.session_state.log_file.close()
                    st.session_state.log_file = None
                st.session_state.process_running = False
                st.session_state.process_just_completed = True
                st.session_state.last_return_code = return_code
                st.rerun()

        # ─── Completion banner (persists after process ends) ──────────────────
        if st.session_state.process_just_completed:
            rc = st.session_state.last_return_code

            summary_text = ""
            if os.path.exists("progress.json"):
                try:
                    with open("progress.json", "r", encoding='utf-8') as f:
                        prog_final = json.load(f)
                    if prog_final.get("status") == "completed" and isinstance(prog_final.get("result"), dict):
                        p = prog_final["result"].get("passed", 0)
                        f_count = prog_final["result"].get("failed", 0)
                        t = prog_final["result"].get("total", 0)
                        summary_text = " — {}/{} passed, {} failed".format(p, t, f_count)
                except Exception:
                    pass

            if rc == 0:
                st.success("Execution completed successfully{}. View results in the Results tab.".format(summary_text))
            else:
                st.warning("Execution finished with exit code {}{}".format(rc, summary_text))

            if st.button("Dismiss", key="dismiss_completion"):
                st.session_state.process_just_completed = False
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: Results Dashboard
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="section-header">Results Dashboard</div>', unsafe_allow_html=True)

    org_runs = get_org_test_runs()
    completed_runs = [r for r in org_runs if r.get("status") == "completed"]

    if not completed_runs:
        # Fallback: check local file for in-progress results
        if os.path.exists("test_results.json"):
            st.info("Showing results from current local execution")
            try:
                with open("test_results.json", "r", encoding='utf-8') as f:
                    results = json.load(f)
                df = pd.DataFrame(results)
                if not df.empty:
                    b = compute_status_breakdown(df)

                    cards = [
                        (b["total"], "Total Tests", "stat-purple"),
                        (b["passed"], "Passed", "stat-green"),
                        (b["failed"], "Failed", "stat-red"),
                    ]
                    if b["timeout"] > 0:
                        cards.append((b["timeout"], "Timeout", "stat-amber"))
                    if b["errors"] + b["json_err"] > 0:
                        cards.append((b["errors"] + b["json_err"], "Errors", "stat-amber"))
                    cards.append(("{:.0f}%".format(b["pass_rate"]), "Pass Rate", "stat-blue"))
                    st.markdown(stat_cards_html(cards), unsafe_allow_html=True)

                    render_results_table(df)
            except Exception as e:
                st.error("Cannot parse local results: {}".format(e))
        else:
            st.markdown("""
            <div class="empty-state">
                <div class="empty-svg">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="80" height="80">
                        <defs><linearGradient id="ecg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#667eea"/><stop offset="100%" stop-color="#764ba2"/></linearGradient></defs>
                        <rect x="20" y="70" width="16" height="30" rx="3" fill="url(#ecg)" opacity="0.3"/>
                        <rect x="42" y="45" width="16" height="55" rx="3" fill="url(#ecg)" opacity="0.45"/>
                        <rect x="64" y="55" width="16" height="45" rx="3" fill="url(#ecg)" opacity="0.6"/>
                        <rect x="86" y="30" width="16" height="70" rx="3" fill="url(#ecg)" opacity="0.4"/>
                    </svg>
                </div>
                <p class="empty-title">No test results yet</p>
                <p class="empty-hint">Run tests first in the Execute tab to see results here</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        selected_result_run = st.selectbox(
            "Select Run",
            options=completed_runs,
            format_func=lambda r: "Run #{} - {} - {}".format(
                r['id'],
                r.get('url') or 'BRD Only',
                r['created_at'][:16],
            ),
            key="results_run_select",
        )

        results = get_run_results(selected_result_run["id"])

        if not results:
            st.info("No results found for this run.")
        else:
            df = pd.DataFrame(results)
            b = compute_status_breakdown(df)

            cards = [
                (b["total"], "Total Tests", "stat-purple"),
                (b["passed"], "Passed", "stat-green"),
                (b["failed"], "Failed", "stat-red"),
            ]
            if b["timeout"] > 0:
                cards.append((b["timeout"], "Timeout", "stat-amber"))
            if b["errors"] + b["json_err"] > 0:
                cards.append((b["errors"] + b["json_err"], "Errors", "stat-amber"))
            cards.append(("{:.0f}%".format(b["pass_rate"]), "Pass Rate", "stat-blue"))
            st.markdown(stat_cards_html(cards), unsafe_allow_html=True)

            # Charts
            STATUS_COLORS = {
                "PASS": "#34d399", "FAIL": "#f87171", "ERROR": "#fbbf24",
                "TIMEOUT": "#fbbf24", "JSON_ERROR": "#fbbf24", "NO_JSON": "#fbbf24",
                "RUNNING": "#60a5fa", "PENDING": "#9090aa",
            }
            TYPE_COLORS = {
                "positive": "#34d399", "negative": "#f87171", "edge": "#fbbf24",
            }

            col1, col2 = st.columns(2)
            with col1:
                st.markdown('<div class="section-header">By Status</div>', unsafe_allow_html=True)
                status_counts = df['status'].value_counts()
                fig = create_styled_bar_chart(
                    labels=status_counts.index.tolist(),
                    values=status_counts.values.tolist(),
                    colors=[STATUS_COLORS.get(s, "#808098") for s in status_counts.index],
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            with col2:
                if 'type' in df.columns:
                    st.markdown('<div class="section-header">By Type</div>', unsafe_allow_html=True)
                    type_counts = df['type'].value_counts()
                    fig = create_styled_bar_chart(
                        labels=type_counts.index.tolist(),
                        values=type_counts.values.tolist(),
                        colors=[TYPE_COLORS.get(t, "#808098") for t in type_counts.index],
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            # Detailed table with status badges
            st.markdown('<div class="section-header">Test Details</div>', unsafe_allow_html=True)
            render_results_table(df)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: Export & Share
# ═══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown('<div class="section-header">Export Results</div>', unsafe_allow_html=True)

    org_runs = get_org_test_runs()
    completed_runs = [r for r in org_runs if r.get("status") == "completed"]

    if not completed_runs:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-svg">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" width="80" height="80">
                    <defs><linearGradient id="eeg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#667eea"/><stop offset="100%" stop-color="#764ba2"/></linearGradient></defs>
                    <rect x="30" y="25" width="60" height="75" rx="6" stroke="url(#eeg)" stroke-width="2.5" fill="none" opacity="0.4"/>
                    <line x1="60" y1="58" x2="60" y2="82" stroke="url(#eeg)" stroke-width="2.5" stroke-linecap="round" opacity="0.5"/>
                    <polyline points="50,72 60,82 70,72" stroke="url(#eeg)" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" opacity="0.5"/>
                </svg>
            </div>
            <p class="empty-title">No completed runs to export</p>
            <p class="empty-hint">Complete a test run first to export results</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        selected_export_run = st.selectbox(
            "Select Run to Export",
            options=completed_runs,
            format_func=lambda r: "Run #{} - {} - {}".format(
                r['id'],
                r.get('url') or 'BRD Only',
                r['created_at'][:16],
            ),
            key="export_run_select",
        )

        results = get_run_results(selected_export_run["id"])

        if not results:
            st.info("No results for this run.")
        else:
            df = pd.DataFrame(results)

            csv = df.to_csv(index=False)
            json_str = json.dumps(results, indent=2)

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    "Download CSV",
                    csv,
                    "test_results_run_{}.csv".format(selected_export_run['id']),
                    "text/csv",
                    use_container_width=True,
                )
            with col2:
                st.download_button(
                    "Download JSON",
                    json_str,
                    "test_results_run_{}.json".format(selected_export_run['id']),
                    "application/json",
                    use_container_width=True,
                )

            # Summary report with proper breakdown
            b = compute_status_breakdown(df)

            report_lines = [
                "<p><strong>Run</strong> <span style='color:var(--text-1);'>#{}</span></p>".format(selected_export_run['id']),
                "<p><strong>URL</strong> <span style='color:var(--text-1);'>{}</span></p>".format(selected_export_run.get('url') or 'BRD Only'),
                "<p><strong>Total Tests</strong> <span style='color:var(--text-1);'>{}</span></p>".format(b["total"]),
                "<p><strong>Passed</strong> <span style='color:var(--pass);'>{} ({:.1f}%)</span></p>".format(b["passed"], b["pass_rate"]),
                "<p><strong>Failed</strong> <span style='color:var(--fail);'>{}</span></p>".format(b["failed"]),
            ]
            if b["timeout"] > 0:
                report_lines.append("<p><strong>Timeout</strong> <span style='color:var(--amber);'>{}</span></p>".format(b["timeout"]))
            if b["errors"] > 0:
                report_lines.append("<p><strong>Errors</strong> <span style='color:var(--amber);'>{}</span></p>".format(b["errors"]))
            if b["json_err"] > 0:
                report_lines.append("<p><strong>Parse Issues</strong> <span style='color:var(--amber);'>{}</span></p>".format(b["json_err"]))
            report_lines.append("<p><strong>Generated</strong> <span style='color:var(--text-3);'>{}</span></p>".format(
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

            st.markdown("""
            <div class="report-card">
                <h3>Test Report Summary</h3>
                {}
            </div>
            """.format("\n".join(report_lines)), unsafe_allow_html=True)
