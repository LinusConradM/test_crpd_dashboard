CUSTOM_STYLE = """
    <style>
        /* Import Fonts — Inter + IBM Plex Mono */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500;600;700&display=swap');
        /* Material Symbols Outlined — for dashboard section icons */
        @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@24,400,0,0&display=swap');

        /* Capitalize all Plotly chart titles */
        .js-plotly-plot .gtitle {
            text-transform: capitalize !important;
        }

        /* Hide Streamlit default elements */
        /* Note: header hiding and block-container padding are managed by nav.py */
        footer {visibility: hidden;}

        /* Expander styling — Stich: ghost border fallback for interactivity */
        [data-testid="stExpander"] > details {
            border: 1px solid rgba(194, 198, 212, 0.5) !important;
            border-radius: 0.75rem !important;
            background: #ffffff !important;
            box-shadow: 0 4px 24px rgba(100, 116, 145, 0.06) !important;
        }
        [data-testid="stExpander"] > details > summary {
            background: #F2F4F8 !important;
            color: #003F87 !important;
            border-radius: 0.75rem !important;
            padding: 10px 16px !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
        }
        [data-testid="stExpander"] > details > summary * {
            font-weight: 700 !important;
            color: #003F87 !important;
        }

        /* WCAG 2.2 §2.4.11 Focus Appearance — visible keyboard focus on expander */
        [data-testid="stExpander"] > details > summary:focus-visible {
            outline: 3px solid #003F87 !important;
            outline-offset: 2px !important;
            border-radius: 4px !important;
        }

        /* Spinning globe animation on expander title */
        @keyframes globe-spin {
            0%   { content: "🌍  "; }
            33%  { content: "🌎  "; }
            66%  { content: "🌏  "; }
            100% { content: "🌍  "; }
        }
        [data-testid="stExpander"] details summary p::before {
            content: "🌍  ";
            animation: globe-spin 3s steps(1) infinite;
        }
        @media (prefers-reduced-motion: reduce) {
            [data-testid="stExpander"] details summary p::before {
                animation: none;
                content: "🌍  ";
            }
        }

        /* Apply Global Font & Background — Stich surface */
        .stApp, body {
            font-family: 'Inter', Arial, sans-serif;
            background-color: #F7F9FD !important;
        }

        /* Protect Streamlit internal Material Icons from being globally overridden */
        .material-symbols-rounded, .stIcon {
            font-family: 'Material Symbols Rounded', 'Material Icons' !important;
        }

        /* Dashboard section icons — Material Symbols Outlined */
        .material-symbols-outlined {
            font-family: 'Material Symbols Outlined' !important;
            font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
            font-size: 1.15em;
            vertical-align: middle;
            line-height: 1;
            display: inline-block;
            user-select: none;
        }

        /* Enhanced text sizing */
        .stApp p {
            font-size: 1.05rem;
            line-height: 1.6;
        }

        /* Benchmark Hero Styling — Stich: Inter 800, no border on badge */
        .hero-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(0, 63, 135, 0.08);
            border: none;
            border-radius: 50px;
            padding: 0.35rem 0.85rem;
            font-size: 0.875rem;
            font-weight: 600;
            color: #003F87;
            letter-spacing: 0.04em;
            margin: 0 auto 1.5rem;
            width: fit-content;
        }

        .hero-badge .dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: #003F87;
            animation: pulse 2s infinite;
        }

        .hero-title {
            font-family: 'Inter', Arial, sans-serif;
            font-size: clamp(2.6rem, 5.5vw, 4.5rem);
            font-weight: 800;
            line-height: 1.07;
            letter-spacing: -0.04em;
            color: #191C1F;
            margin-bottom: 1.4rem;
            text-align: center;
        }

        .hero-title .gradient-word {
            background: linear-gradient(90deg, #003F87 0%, #0056B3 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .hero-sub {
            font-size: clamp(1rem, 1.8vw, 1.15rem);
            color: #424752;
            line-height: 1.65;
            margin-bottom: 2.2rem;
            max-width: 600px;
            margin-left: auto;
            margin-right: auto;
            text-align: center;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.85); }
        }

        /* Tab styling — Stich: tonal surface, gradient active */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #F2F4F8;
            padding: 10px 20px;
            border-radius: 0.75rem;
        }

        .stTabs [data-baseweb="tab-list"] button {
            font-size: 1.1rem;
            font-weight: 500;
            color: #424752;
            background-color: transparent;
            border-radius: 0.5rem;
            padding: 12px 24px;
        }

        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
            background: linear-gradient(135deg, #003F87, #0056B3);
            color: white;
        }

        .stTabs [data-baseweb="tab-list"] button:hover {
            background-color: #ECEEF2;
        }

        /* Metric card styling — Stich: no border, diffused shadow */
        .metric-card {
            background: white;
            padding: 1.5rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 24px rgba(100, 116, 145, 0.06);
            text-align: center;
            margin-bottom: 10px;
            min-height: 130px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }

        .metric-icon {
            font-size: 1.15rem;
            margin-bottom: 0.6rem;
            opacity: 0.7;
        }

        .metric-value {
            font-family: 'Inter', sans-serif !important;
            font-size: clamp(1.4rem, 2.5vw, 2.2rem);
            font-weight: 800;
            color: #191C1F;
            line-height: 1;
            margin-bottom: 0.45rem;
        }

        .metric-label {
            font-family: 'Inter', sans-serif;
            font-size: 0.875rem;
            color: #424752;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        .metric-trend {
            font-size: 0.875rem;
            font-weight: 600;
            margin-top: 8px;
            padding-top: 0;
            border-top: none;
            background: #F2F4F8;
            border-radius: 0.5rem;
            padding: 6px 8px;
            width: 100%;
        }

        .trend-up { color: #2e7d32; }
        .trend-down { color: #BA1A1A; }
        .trend-neutral { color: #7a5200; }
        .trend-neutral-info { color: #424752; }

        /* Info boxes — Stich: no border-left, tonal bg, diffused shadow */
        .info-box {
            background: white;
            padding: 20px;
            border-radius: 0.75rem;
            border-left: none;
            box-shadow: 0 4px 24px rgba(100, 116, 145, 0.06);
            margin: 20px 0;
            min-height: 400px;
        }

        .info-box h4 {
            color: #003F87;
            margin-top: 0;
        }

        /* About tab boxes */
        .about-info-box {
            background: white;
            padding: 20px;
            border-radius: 0.75rem;
            border-left: none;
            box-shadow: 0 4px 24px rgba(100, 116, 145, 0.06);
            margin: 20px 0;
            min-height: 230px;
        }

        /* Insights section — Stich: tonal bg instead of border-left */
        .insights-section {
            background: #F2F4F8;
            padding: 30px;
            border-radius: 0.75rem;
            border-left: none;
            box-shadow: none;
            margin: 20px 0;
        }

        .insight-item {
            margin-bottom: 15px;
            line-height: 1.8;
        }

        .insight-item strong {
            color: #003F87;
        }

        /* Section headers */
        h3 {
            font-size: 1.5rem;
            margin-top: 2rem;
            color: #003F87;
        }

        /* Two-column layouts */
        .two-col-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }

        /* Finding stat highlights — Stich: no divider lines */
        .owid-finding-stat {
            text-align: center;
            padding: 1.2rem 0;
        }
        .owid-finding-stat-value {
            font-family: 'Inter', sans-serif;
            font-size: clamp(1.8rem, 3vw, 2.5rem);
            font-weight: 800;
            color: #003F87;
            line-height: 1;
        }
        .owid-finding-stat-label {
            font-family: 'Inter', sans-serif;
            font-size: 0.875rem;
            color: #424752;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-top: 0.3rem;
        }
        .owid-finding-stat-trend {
            font-size: 0.875rem;
            font-weight: 600;
            margin-top: 0.4rem;
            color: #424752;
        }
        .owid-finding-number {
            font-family: 'Inter', sans-serif;
            font-size: 0.875rem;
            font-weight: 700;
            color: #003F87;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 0.4rem;
            opacity: 0.7;
        }
        .owid-finding-stats-row {
            display: flex;
            gap: 1.5rem;
            justify-content: center;
            flex-wrap: wrap;
        }
        .owid-finding-stats-row > div:not(:last-child) {
            border-right: none;
            padding-right: 1.5rem;
        }
        /* ── Dataframe table styling ── */
        [data-testid="stDataFrame"] {
            border: 1px solid #e2e6ed;
            border-radius: 0.75rem;
            overflow: hidden;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }
        [data-testid="stDataFrame"] table th,
        [data-testid="stDataFrame"] [role="columnheader"] {
            font-weight: 700 !important;
            color: #000000 !important;
            font-size: 0.85rem !important;
            letter-spacing: 0.02em !important;
            background: #f4f6f9 !important;
        }
        [data-testid="stDataFrame"] table td,
        [data-testid="stDataFrame"] [role="gridcell"] {
            font-size: 0.88rem !important;
            font-weight: 700 !important;
            color: #000000 !important;
        }
        /* ── st.table styling: bold black text ── */
        [data-testid="stTable"] table {
            border-collapse: collapse;
            width: 100%;
            border: 1px solid #e2e6ed;
            border-radius: 0.75rem;
            overflow: hidden;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        }
        [data-testid="stTable"] table th {
            font-weight: 700 !important;
            color: #000000 !important;
            font-size: 0.88rem !important;
            background: #f4f6f9 !important;
            letter-spacing: 0.02em !important;
            padding: 10px 14px !important;
            border-bottom: 2px solid #d8dce5 !important;
        }
        [data-testid="stTable"] table td {
            font-weight: 600 !important;
            color: #000000 !important;
            font-size: 0.88rem !important;
            padding: 10px 14px !important;
            border-bottom: 1px solid #eef0f4 !important;
        }

        /* ── WCAG 2.5.8 Touch Target: multiselect hidden input ≥ 24×24px ── */
        [data-testid="stMultiSelect"] input[role="combobox"] {
            min-width: 24px !important;
            min-height: 24px !important;
            width: 24px !important;
        }
    </style>
"""
