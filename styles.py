"""
Centralized CSS for Marcus Intelligence.
Premium agency-quality styling — raw HTML/CSS, no Python-driven layout.
"""

# ── Font preload + Design tokens ─────────────────────────────────────────────

CSS_TOKENS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

:root {
    /* ── Core palette ────────────────────────── */
    --bg-0: #080618;
    --bg-1: #0f0c29;
    --bg-2: #151336;
    --bg-3: #1a1a3e;
    --bg-4: #24243e;

    --accent: #667eea;
    --accent-2: #764ba2;
    --accent-3: #f77062;

    --text-0: #f0f0ff;
    --text-1: #e0e0f0;
    --text-2: #c0c0d8;
    --text-3: #9090aa;
    --text-4: #6a6a88;
    --text-5: #4a4a68;

    --pass: #34d399;
    --fail: #f87171;
    --amber: #fbbf24;
    --blue: #60a5fa;

    /* ── Glass ────────────────────────────────── */
    --glass-1: rgba(255,255,255,0.02);
    --glass-2: rgba(255,255,255,0.04);
    --glass-3: rgba(255,255,255,0.06);
    --glass-4: rgba(255,255,255,0.08);
    --glass-5: rgba(255,255,255,0.12);

    --border-1: rgba(255,255,255,0.04);
    --border-2: rgba(255,255,255,0.07);
    --border-3: rgba(255,255,255,0.12);
    --border-4: rgba(255,255,255,0.18);

    /* ── Shadows ──────────────────────────────── */
    --shadow-sm: 0 2px 8px rgba(0,0,0,0.15);
    --shadow-md: 0 4px 16px rgba(0,0,0,0.2);
    --shadow-lg: 0 8px 32px rgba(0,0,0,0.3);
    --shadow-xl: 0 16px 48px rgba(0,0,0,0.4);
    --shadow-accent: 0 4px 20px rgba(102,126,234,0.2);
    --shadow-accent-lg: 0 8px 32px rgba(102,126,234,0.3);

    /* ── Spacing ──────────────────────────────── */
    --radius-xs: 6px;
    --radius-sm: 8px;
    --radius-md: 12px;
    --radius-lg: 16px;
    --radius-xl: 20px;
    --radius-2xl: 24px;

    /* ── Motion ───────────────────────────────── */
    --ease-out: cubic-bezier(0.16, 1, 0.3, 1);
    --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
    --duration: 0.25s;
    --duration-slow: 0.4s;

    --font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, sans-serif;
}
"""

# ── Base / Reset / Global ─────────────────────────────────────────────────────

CSS_BASE = """
/* ── Force font everywhere ───────────────── */
html, body, [class*="css"], [data-testid],
.stMarkdown, button, input, textarea, select,
[data-baseweb], label, p, h1, h2, h3, h4, span, div, a, li, td, th {
    font-family: var(--font) !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
}

/* ── Typography scale ────────────────────── */
h1 {
    font-size: 2rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.035em !important;
    line-height: 1.15 !important;
    color: var(--text-0) !important;
}
h2 {
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.025em !important;
    line-height: 1.3 !important;
    color: var(--text-1) !important;
}
h3 {
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
    color: var(--text-1) !important;
}
p, li, td, th, label, span {
    line-height: 1.6;
}

/* ── Brand selection color ───────────────── */
::selection {
    background: rgba(102,126,234,0.3);
    color: var(--text-0);
}

/* ── Custom scrollbar ────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.08);
    border-radius: 10px;
}
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.14); }

/* ── Main container ──────────────────────── */
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse 80% 60% at 50% 0%, rgba(102,126,234,0.06) 0%, transparent 60%),
        linear-gradient(180deg, var(--bg-1) 0%, var(--bg-0) 100%);
}
/* Noise texture overlay */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.02'/%3E%3C/svg%3E");
    background-repeat: repeat;
    background-size: 256px 256px;
    pointer-events: none;
    z-index: 0;
    opacity: 0.5;
}
"""

# ── Header ────────────────────────────────────────────────────────────────────

CSS_HEADER = """
.app-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.8rem 0 0.15rem 0;
    animation: fadeInUp 0.5s var(--ease-out);
}
.app-header h1 {
    font-size: 2.2rem !important;
    font-weight: 900 !important;
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-2) 60%, var(--accent-3) 100%);
    background-size: 200% 200%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0;
    letter-spacing: -0.04em;
}
.app-subtitle {
    color: var(--text-4);
    font-size: 0.85rem;
    font-weight: 400;
    margin: 0 0 1.2rem 0;
    letter-spacing: 0.04em;
    animation: fadeIn 0.6s var(--ease-out) 0.15s backwards;
}
.app-subtitle b, .app-subtitle strong {
    color: var(--text-3);
    font-weight: 500;
}
"""

# ── Sidebar ───────────────────────────────────────────────────────────────────

CSS_SIDEBAR = """
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(15,12,41,0.97) 0%, rgba(8,6,24,0.99) 100%);
    border-right: 1px solid var(--border-1);
}
/* Accent line on right edge */
[data-testid="stSidebar"]::after {
    content: '';
    position: absolute;
    top: 0;
    right: -1px;
    width: 1px;
    height: 100%;
    background: linear-gradient(180deg,
        var(--accent) 0%,
        var(--accent-2) 50%,
        transparent 100%);
    opacity: 0.35;
}
[data-testid="stSidebar"] [data-testid="stMarkdown"] p,
[data-testid="stSidebar"] [data-testid="stMarkdown"] span,
[data-testid="stSidebar"] label {
    color: var(--text-2) !important;
    font-size: 0.82rem;
}

/* ── User card ────────────────────────── */
.sidebar-user {
    background: linear-gradient(135deg, rgba(102,126,234,0.1), rgba(118,75,162,0.06));
    border: 1px solid rgba(102,126,234,0.15);
    border-radius: var(--radius-md);
    padding: 0.85rem 1rem;
    margin-bottom: 1.2rem;
    backdrop-filter: blur(16px);
    transition: all var(--duration) var(--ease-out);
    animation: slideInLeft 0.4s var(--ease-out);
    position: relative;
    overflow: hidden;
}
.sidebar-user::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(102,126,234,0.3), transparent);
}
.sidebar-user:hover {
    border-color: rgba(102,126,234,0.3);
    background: linear-gradient(135deg, rgba(102,126,234,0.14), rgba(118,75,162,0.1));
    transform: translateY(-1px);
    box-shadow: var(--shadow-accent);
}
.sidebar-user .user-email {
    color: var(--text-0);
    font-weight: 600;
    font-size: 0.84rem;
    letter-spacing: -0.01em;
}
.sidebar-user .user-org {
    color: var(--text-3);
    font-size: 0.72rem;
    margin-top: 3px;
    font-weight: 500;
}

/* ── Sidebar section labels ───────────── */
.sidebar-label {
    color: var(--text-5);
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.8px;
    margin: 1.8rem 0 0.5rem 0;
    padding-bottom: 0.35rem;
    border-bottom: 1px solid var(--border-1);
}

/* ── Sign Out hover — red accent ──────── */
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:last-of-type:hover {
    border-color: rgba(248,113,113,0.25) !important;
    color: var(--fail) !important;
    background: rgba(248,113,113,0.06) !important;
}
"""

# ── Tabs ──────────────────────────────────────────────────────────────────────

CSS_TABS = """
[data-baseweb="tab-list"] {
    gap: 0;
    background: var(--glass-1);
    border-radius: var(--radius-md) var(--radius-md) 0 0;
    border-bottom: 1px solid var(--border-2);
    padding: 0 0.25rem;
    backdrop-filter: blur(12px);
    position: relative;
}
[data-baseweb="tab"] {
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    color: var(--text-4) !important;
    padding: 0.75rem 1.4rem !important;
    transition: all var(--duration) var(--ease-out);
    border-bottom: 2px solid transparent;
    letter-spacing: 0.01em;
    position: relative;
}
[data-baseweb="tab"]:hover {
    color: var(--text-2) !important;
    background: rgba(102,126,234,0.04);
}
[data-baseweb="tab"][aria-selected="true"] {
    color: var(--text-0) !important;
    border-bottom: 2px solid var(--accent) !important;
    background: rgba(102,126,234,0.06);
}
/* Hide default highlight bar — we use border-bottom instead */
[data-baseweb="tab-highlight"] {
    display: none !important;
}
/* Tab panel content area */
[data-baseweb="tab-panel"] {
    padding-top: 0.5rem !important;
}
"""

# ── Stat cards ────────────────────────────────────────────────────────────────

CSS_STAT_CARDS = """
.stat-row {
    display: flex;
    gap: 0.65rem;
    margin: 0.75rem 0 1.5rem 0;
    flex-wrap: wrap;
}
.stat-card {
    flex: 1;
    min-width: 95px;
    border-radius: var(--radius-md);
    padding: 1rem 1.1rem;
    border: 1px solid var(--border-1);
    backdrop-filter: blur(16px);
    transition: all var(--duration) var(--ease-out);
    position: relative;
    overflow: hidden;
}
/* Subtle top-edge glow */
.stat-card::before {
    content: '';
    position: absolute;
    top: 0; left: 20%; right: 20%;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent);
}
.stat-card:hover {
    transform: translateY(-3px);
    border-color: var(--border-3);
    box-shadow: var(--shadow-lg);
}
.stat-card .stat-value {
    font-size: 1.65rem;
    font-weight: 800;
    line-height: 1.15;
    letter-spacing: -0.03em;
}
.stat-card .stat-label {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    opacity: 0.6;
    margin-top: 3px;
}

.stat-purple { background: linear-gradient(135deg, rgba(102,126,234,0.1), rgba(118,75,162,0.06)); }
.stat-purple .stat-value { color: #a78bfa; }
.stat-purple .stat-label { color: #a78bfa; }
.stat-green  { background: linear-gradient(135deg, rgba(52,211,153,0.1), rgba(52,211,153,0.04)); }
.stat-green  .stat-value { color: var(--pass); }
.stat-green  .stat-label { color: var(--pass); }
.stat-red    { background: linear-gradient(135deg, rgba(248,113,113,0.1), rgba(248,113,113,0.04)); }
.stat-red    .stat-value { color: var(--fail); }
.stat-red    .stat-label { color: var(--fail); }
.stat-blue   { background: linear-gradient(135deg, rgba(96,165,250,0.1), rgba(96,165,250,0.04)); }
.stat-blue   .stat-value { color: var(--blue); }
.stat-blue   .stat-label { color: var(--blue); }
.stat-amber  { background: linear-gradient(135deg, rgba(251,191,36,0.1), rgba(251,191,36,0.04)); }
.stat-amber  .stat-value { color: var(--amber); }
.stat-amber  .stat-label { color: var(--amber); }
"""

# ── Status badges ─────────────────────────────────────────────────────────────

CSS_BADGES = """
.badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    border: 1px solid transparent;
}
.badge::before {
    content: '';
    display: inline-block;
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: currentColor;
    opacity: 0.7;
}
.badge-pass {
    background: rgba(52,211,153,0.1);
    color: var(--pass);
    border-color: rgba(52,211,153,0.15);
}
.badge-fail {
    background: rgba(248,113,113,0.1);
    color: var(--fail);
    border-color: rgba(248,113,113,0.15);
}
.badge-error {
    background: rgba(251,191,36,0.1);
    color: var(--amber);
    border-color: rgba(251,191,36,0.15);
}
.badge-running {
    background: rgba(96,165,250,0.1);
    color: var(--blue);
    border-color: rgba(96,165,250,0.15);
    animation: pulse 2s ease-in-out infinite;
}
.badge-running::before {
    animation: pulse 1.5s ease-in-out infinite;
}
.badge-pending {
    background: rgba(144,144,170,0.08);
    color: var(--text-3);
    border-color: rgba(144,144,170,0.1);
}
"""

# ── Section headers ───────────────────────────────────────────────────────────

CSS_SECTION_HEADERS = """
.section-header {
    color: var(--text-1);
    font-size: 1rem;
    font-weight: 700;
    margin: 1.8rem 0 0.8rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border-1);
    letter-spacing: -0.01em;
    animation: fadeInUp 0.35s var(--ease-out);
    position: relative;
}
.section-header::after {
    content: '';
    position: absolute;
    bottom: -1px;
    left: 0;
    width: 40px;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), transparent);
    border-radius: 2px;
}
"""

# ── Empty states ──────────────────────────────────────────────────────────────

CSS_EMPTY_STATES = """
.empty-state {
    text-align: center;
    padding: 4rem 1.5rem;
    color: var(--text-3);
    animation: fadeIn 0.5s var(--ease-out);
}
.empty-state .empty-svg {
    margin-bottom: 1.2rem;
    filter: drop-shadow(0 4px 16px rgba(102,126,234,0.15));
    opacity: 0.7;
}
.empty-state .empty-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text-2);
    margin: 0 0 0.4rem 0;
    letter-spacing: -0.01em;
}
.empty-state p {
    font-size: 0.88rem;
    margin: 0.2rem 0;
}
.empty-state .empty-hint {
    font-size: 0.78rem;
    color: var(--text-5);
    margin-top: 0.6rem;
}
"""

# ── Cards (test case, monitor, report) ────────────────────────────────────────

CSS_CARDS = """
/* ── Test case card ───────────────── */
.tc-card {
    background: var(--glass-2);
    border: 1px solid var(--border-1);
    border-radius: var(--radius-md);
    padding: 1rem 1.2rem;
    margin-bottom: 0.6rem;
    backdrop-filter: blur(16px);
    transition: all var(--duration) var(--ease-out);
}
.tc-card:hover {
    border-color: var(--border-3);
    background: var(--glass-3);
    box-shadow: var(--shadow-sm);
}
.tc-card .tc-title {
    color: var(--text-1);
    font-weight: 700;
    font-size: 0.88rem;
    letter-spacing: -0.01em;
}
.tc-card .tc-meta {
    color: var(--text-4);
    font-size: 0.76rem;
    margin-top: 3px;
}

/* ── Monitor card ─────────────────── */
.monitor-card {
    background: linear-gradient(135deg, rgba(96,165,250,0.04), rgba(102,126,234,0.03));
    border: 1px solid rgba(96,165,250,0.12);
    border-radius: var(--radius-lg);
    padding: 1.3rem 1.5rem;
    margin: 0.75rem 0;
    backdrop-filter: blur(16px);
    position: relative;
    overflow: hidden;
    box-shadow: var(--shadow-md);
}
/* Animated top bar */
.monitor-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--blue), var(--accent-2), var(--accent));
    background-size: 300% 100%;
    animation: shimmer-gradient 3s linear infinite;
}

/* ── Report card ──────────────────── */
.report-card {
    background: var(--glass-2);
    border: 1px solid var(--border-2);
    border-radius: var(--radius-lg);
    padding: 1.6rem 1.8rem;
    margin-top: 1rem;
    backdrop-filter: blur(16px);
    transition: all var(--duration) var(--ease-out);
    position: relative;
}
.report-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border-3), transparent);
}
.report-card:hover {
    border-color: var(--border-3);
    box-shadow: var(--shadow-md);
}
.report-card h3 {
    color: var(--text-0);
    margin: 0 0 0.85rem 0;
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: -0.01em;
}
.report-card p {
    color: var(--text-2);
    margin: 0.35rem 0;
    font-size: 0.85rem;
}
.report-card strong {
    color: var(--text-3);
    font-weight: 600;
}
"""

# ── Results table ─────────────────────────────────────────────────────────────

CSS_TABLES = """
.results-table {
    width: 100%;
    border-collapse: separate;
    border-spacing: 0;
    font-size: 0.82rem;
    margin-top: 0.5rem;
    background: var(--glass-1);
    border-radius: var(--radius-md);
    overflow: hidden;
    border: 1px solid var(--border-1);
}
.results-table th {
    padding: 0.7rem 0.85rem;
    text-align: left;
    color: var(--text-4);
    font-weight: 700;
    font-size: 0.68rem;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    background: var(--glass-2);
    border-bottom: 1px solid var(--border-2);
    position: sticky;
    top: 0;
    z-index: 1;
}
.results-table td {
    padding: 0.6rem 0.85rem;
    color: var(--text-2);
    border-bottom: 1px solid var(--border-1);
    transition: all var(--duration) var(--ease-out);
}
.results-table tbody tr {
    animation: fadeInUp 0.3s var(--ease-out) backwards;
}
.results-table tbody tr:nth-child(1)  { animation-delay: 0.02s; }
.results-table tbody tr:nth-child(2)  { animation-delay: 0.04s; }
.results-table tbody tr:nth-child(3)  { animation-delay: 0.06s; }
.results-table tbody tr:nth-child(4)  { animation-delay: 0.08s; }
.results-table tbody tr:nth-child(5)  { animation-delay: 0.1s;  }
.results-table tbody tr:nth-child(6)  { animation-delay: 0.12s; }
.results-table tbody tr:nth-child(7)  { animation-delay: 0.14s; }
.results-table tbody tr:nth-child(8)  { animation-delay: 0.16s; }
.results-table tbody tr:nth-child(9)  { animation-delay: 0.18s; }
.results-table tbody tr:nth-child(10) { animation-delay: 0.2s;  }
.results-table tr:hover td {
    background: var(--glass-3);
}
.results-table .reason-cell {
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text-3);
    font-size: 0.78rem;
}
/* Last row no border */
.results-table tbody tr:last-child td {
    border-bottom: none;
}
"""

# ── Metrics ───────────────────────────────────────────────────────────────────

CSS_METRICS = """
[data-testid="stMetric"] {
    background: var(--glass-2);
    border: 1px solid var(--border-1);
    border-radius: var(--radius-md);
    padding: 0.85rem 1rem;
    backdrop-filter: blur(16px);
    transition: all var(--duration) var(--ease-out);
}
[data-testid="stMetric"]:hover {
    border-color: var(--border-3);
    box-shadow: var(--shadow-sm);
}
[data-testid="stMetricLabel"] {
    color: var(--text-4) !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
[data-testid="stMetricValue"] {
    color: var(--text-0) !important;
    font-weight: 800 !important;
}
"""

# ── Component overrides ──────────────────────────────────────────────────────

CSS_COMPONENT_OVERRIDES = """
/* ── Text inputs ─────────────────────── */
[data-testid="stTextInput"] input {
    background: var(--glass-2) !important;
    border: 1px solid var(--border-2) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-1) !important;
    font-size: 0.85rem !important;
    padding: 0.6rem 0.8rem !important;
    transition: all var(--duration) var(--ease-out);
}
[data-testid="stTextInput"] input::placeholder { color: var(--text-5) !important; }
[data-testid="stTextInput"] input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(102,126,234,0.12), var(--shadow-sm) !important;
    background: var(--glass-3) !important;
}
[data-testid="stTextInput"] label {
    color: var(--text-3) !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
}

/* ── Text areas ──────────────────────── */
[data-testid="stTextArea"] textarea {
    background: var(--glass-2) !important;
    border: 1px solid var(--border-2) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-1) !important;
    font-size: 0.85rem !important;
    transition: all var(--duration) var(--ease-out);
}
[data-testid="stTextArea"] textarea::placeholder { color: var(--text-5) !important; }
[data-testid="stTextArea"] textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(102,126,234,0.12), var(--shadow-sm) !important;
    background: var(--glass-3) !important;
}
[data-testid="stTextArea"] label {
    color: var(--text-3) !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
}

/* ── Select boxes ────────────────────── */
[data-testid="stSelectbox"] > div > div {
    background: var(--glass-2) !important;
    border: 1px solid var(--border-2) !important;
    border-radius: var(--radius-sm) !important;
    transition: all var(--duration) var(--ease-out);
}
[data-testid="stSelectbox"] > div > div:hover {
    border-color: var(--border-4) !important;
}
[data-testid="stSelectbox"] label {
    color: var(--text-3) !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
}

/* ── Primary buttons ─────────────────── */
[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, var(--accent), var(--accent-2)) !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 700 !important;
    font-size: 0.84rem !important;
    letter-spacing: 0.02em;
    transition: all var(--duration) var(--ease-out);
    box-shadow: var(--shadow-accent);
    position: relative;
    overflow: hidden;
}
[data-testid="stBaseButton-primary"]::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent);
    transform: translateX(-100%);
    transition: transform 0.6s ease;
}
[data-testid="stBaseButton-primary"]:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-accent-lg) !important;
}
[data-testid="stBaseButton-primary"]:hover::after {
    transform: translateX(100%);
}
[data-testid="stBaseButton-primary"]:active {
    transform: translateY(0);
    box-shadow: var(--shadow-sm) !important;
}

/* ── Secondary buttons ───────────────── */
[data-testid="stBaseButton-secondary"] {
    background: var(--glass-2) !important;
    border: 1px solid var(--border-2) !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: 0.84rem !important;
    color: var(--text-2) !important;
    transition: all var(--duration) var(--ease-out);
}
[data-testid="stBaseButton-secondary"]:hover {
    border-color: var(--border-4) !important;
    background: var(--glass-4) !important;
    color: var(--text-0) !important;
    box-shadow: var(--shadow-sm);
}

/* ── File uploader ───────────────────── */
[data-testid="stFileUploader"] {
    border: 1.5px dashed var(--border-2) !important;
    border-radius: var(--radius-md) !important;
    transition: all var(--duration) var(--ease-out);
    padding: 0.75rem;
    background: var(--glass-1);
}
[data-testid="stFileUploader"]:hover {
    border-color: rgba(102,126,234,0.25) !important;
    background: var(--glass-2);
}
[data-testid="stFileUploader"] label {
    color: var(--text-3) !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
}

/* ── Expanders ───────────────────────── */
[data-testid="stExpander"] {
    background: var(--glass-2) !important;
    border: 1px solid var(--border-1) !important;
    border-radius: var(--radius-md) !important;
    transition: all var(--duration) var(--ease-out);
    overflow: hidden;
}
[data-testid="stExpander"]:hover {
    border-color: var(--border-3) !important;
    box-shadow: var(--shadow-sm);
}
[data-testid="stExpander"] summary {
    font-weight: 600 !important;
    font-size: 0.84rem !important;
}

/* ── Progress bar ────────────────────── */
[data-testid="stProgress"] > div > div {
    background: rgba(255,255,255,0.04) !important;
    border-radius: 10px !important;
    overflow: hidden;
    height: 8px !important;
}
[data-testid="stProgress"] > div > div > div {
    background: linear-gradient(90deg, var(--accent), var(--accent-2), var(--blue)) !important;
    background-size: 200% 100%;
    border-radius: 10px !important;
    position: relative;
    overflow: hidden;
    animation: shimmer-gradient 2s linear infinite;
}
[data-testid="stProgress"] > div > div > div::after {
    content: '';
    position: absolute;
    top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
    animation: shimmer 1.5s linear infinite;
}

/* ── Download buttons ────────────────── */
[data-testid="stDownloadButton"] button {
    background: var(--glass-2) !important;
    border: 1px solid var(--border-2) !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    font-size: 0.82rem !important;
    transition: all var(--duration) var(--ease-out);
    color: var(--text-2) !important;
}
[data-testid="stDownloadButton"] button:hover {
    border-color: rgba(102,126,234,0.25) !important;
    background: rgba(102,126,234,0.06) !important;
    color: var(--text-0) !important;
    box-shadow: var(--shadow-sm);
    transform: translateY(-1px);
}

/* ── Alerts ──────────────────────────── */
[data-testid="stAlert"] {
    border-radius: var(--radius-sm) !important;
    backdrop-filter: blur(12px);
    border: 1px solid var(--border-2) !important;
    border-left: 3px solid var(--accent) !important;
    font-size: 0.84rem;
}

/* ── Dividers ────────────────────────── */
hr {
    border-color: var(--border-1) !important;
    opacity: 0.6;
}

/* ── Spinner ─────────────────────────── */
[data-testid="stSpinner"] {
    color: var(--accent) !important;
}
"""

# ── Animations ────────────────────────────────────────────────────────────────

CSS_ANIMATIONS = """
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(16px); }
    to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
    from { opacity: 0; }
    to   { opacity: 1; }
}
@keyframes slideInLeft {
    from { opacity: 0; transform: translateX(-16px); }
    to   { opacity: 1; transform: translateX(0); }
}
@keyframes scaleIn {
    from { opacity: 0; transform: scale(0.92); }
    to   { opacity: 1; transform: scale(1); }
}
@keyframes shimmer {
    from { transform: translateX(-100%); }
    to   { transform: translateX(100%); }
}
@keyframes shimmer-gradient {
    0%   { background-position: 0% 50%; }
    100% { background-position: 300% 50%; }
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%      { opacity: 0.4; }
}
@keyframes gradientShift {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
@keyframes float {
    0%, 100% { transform: translateY(0px); }
    50%      { transform: translateY(-6px); }
}

/* ── Staggered stat card entrance ───── */
.stat-row .stat-card {
    animation: scaleIn 0.35s var(--ease-spring) backwards;
}
.stat-row .stat-card:nth-child(1) { animation-delay: 0.04s; }
.stat-row .stat-card:nth-child(2) { animation-delay: 0.08s; }
.stat-row .stat-card:nth-child(3) { animation-delay: 0.12s; }
.stat-row .stat-card:nth-child(4) { animation-delay: 0.16s; }
.stat-row .stat-card:nth-child(5) { animation-delay: 0.20s; }
.stat-row .stat-card:nth-child(6) { animation-delay: 0.24s; }
"""

# ── Charts (Plotly container) ─────────────────────────────────────────────────

CSS_CHARTS = """
[data-testid="stPlotlyChart"] {
    border-radius: var(--radius-md);
    overflow: hidden;
    background: var(--glass-1);
    border: 1px solid var(--border-1);
    padding: 0.5rem;
}
"""

# ── Login-specific ────────────────────────────────────────────────────────────

CSS_LOGIN = """
/* ── Animated gradient background ──── */
[data-testid="stAppViewContainer"] {
    background:
        radial-gradient(ellipse 80% 50% at 50% 0%, rgba(102,126,234,0.08) 0%, transparent 60%),
        radial-gradient(ellipse 60% 40% at 80% 100%, rgba(118,75,162,0.06) 0%, transparent 60%),
        linear-gradient(135deg, var(--bg-0) 0%, var(--bg-1) 30%, var(--bg-2) 60%, var(--bg-4) 100%);
    background-size: 200% 200%, 200% 200%, 100% 100%;
    animation: gradientShift 20s ease infinite;
}
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.02'/%3E%3C/svg%3E");
    background-repeat: repeat;
    background-size: 256px 256px;
    pointer-events: none;
    z-index: 0;
    opacity: 0.4;
}

/* ── Hero ─────────────────────────── */
.login-hero {
    text-align: center;
    padding: 2.5rem 0 0.5rem 0;
    animation: fadeInUp 0.6s var(--ease-out);
}
.login-hero .login-logo {
    margin-bottom: 1.2rem;
    filter: drop-shadow(0 6px 24px rgba(102,126,234,0.25));
    animation: float 4s ease-in-out infinite;
}
.login-hero h1 {
    font-size: 2.8rem !important;
    font-weight: 900 !important;
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-2) 45%, var(--accent-3) 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0.4rem;
    letter-spacing: -0.04em;
}
.login-hero p {
    color: var(--text-3);
    font-size: 1rem;
    margin: 0;
    font-weight: 300;
    letter-spacing: 0.01em;
}
.login-hero .login-tagline {
    color: var(--text-5);
    font-size: 0.8rem;
    margin-top: 0.6rem;
    font-weight: 400;
    letter-spacing: 0.04em;
}

/* ── Login card ──────────────────── */
.login-card {
    background: rgba(255,255,255,0.025);
    border: 1px solid var(--border-2);
    border-radius: var(--radius-2xl);
    padding: 2rem 2rem 1.5rem 2rem;
    backdrop-filter: blur(20px);
    margin-top: 1rem;
    box-shadow: var(--shadow-xl);
    animation: fadeInUp 0.5s var(--ease-out) 0.15s backwards;
    position: relative;
    overflow: hidden;
}
.login-card::before {
    content: '';
    position: absolute;
    top: 0; left: 10%; right: 10%;
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
}
.login-card h3 {
    color: var(--text-1);
    font-size: 1.05rem;
    font-weight: 600;
    margin-bottom: 1rem;
    letter-spacing: -0.01em;
}

.login-card [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid var(--border-2);
    background: transparent;
}
.login-card [data-baseweb="tab"] {
    color: var(--text-4);
    font-weight: 600;
    font-size: 0.88rem;
}
.login-card [data-baseweb="tab"][aria-selected="true"] {
    color: var(--text-0) !important;
}

/* ── Footer ──────────────────────── */
.login-footer {
    text-align: center;
    color: var(--text-5);
    font-size: 0.75rem;
    margin-top: 2.5rem;
    padding-bottom: 2rem;
    animation: fadeIn 0.5s var(--ease-out) 0.6s backwards;
    letter-spacing: 0.03em;
}
"""


# ── Public API ────────────────────────────────────────────────────────────────

def get_app_css() -> str:
    """Return the full CSS for the main application wrapped in <style> tags."""
    sections = [
        CSS_TOKENS,
        CSS_BASE,
        CSS_HEADER,
        CSS_SIDEBAR,
        CSS_TABS,
        CSS_STAT_CARDS,
        CSS_BADGES,
        CSS_SECTION_HEADERS,
        CSS_EMPTY_STATES,
        CSS_CARDS,
        CSS_TABLES,
        CSS_METRICS,
        CSS_COMPONENT_OVERRIDES,
        CSS_ANIMATIONS,
        CSS_CHARTS,
    ]
    return "<style>\n{}\n</style>".format("\n".join(sections))


def get_login_css() -> str:
    """Return the CSS for the login page wrapped in <style> tags."""
    sections = [
        CSS_TOKENS,
        CSS_BASE,
        CSS_LOGIN,
        CSS_TABS,
        CSS_COMPONENT_OVERRIDES,
        CSS_ANIMATIONS,
    ]
    return "<style>\n{}\n</style>".format("\n".join(sections))
