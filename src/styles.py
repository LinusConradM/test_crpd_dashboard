CUSTOM_STYLE = """
    <style>
        /* Hide Streamlit default elements */
        .block-container{padding-top:1.2rem;}
        header {visibility: hidden;}
        footer {visibility: hidden;}

        /* Enhanced text sizing */
        .stApp p {
            font-size: 1.05rem;
            line-height: 1.6;
        }

        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #3d5161;
            padding: 10px 20px;
            border-radius: 8px 8px 0 0;
        }

        .stTabs [data-baseweb="tab-list"] button {
            font-size: 1.1rem;
            font-weight: 500;
            color: white;
            background-color: transparent;
            border-radius: 6px 6px 0 0;
            padding: 12px 24px;
        }

        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
            background-color: #26a69a;
            color: white;
        }

        .stTabs [data-baseweb="tab-list"] button:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }

        /* Metric card styling */
        .metric-card {
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
            border-top: 4px solid;
            margin-bottom: 10px;
            min-height: 200px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }

        .metric-icon {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }

        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #1f1f1f;
            margin: 10px 0;
        }

        .metric-label {
            font-size: 0.9rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .metric-trend {
            font-size: 0.85rem;
            font-weight: 500;
            margin-top: 8px;
            min-height: 20px;
        }

        .trend-up { color: #2e7d32; }
        .trend-down { color: #c62828; }
        .trend-neutral { color: #f57c00; }

        /* Info boxes */
        .info-box {
            background: rgba(61, 81, 97, 0.08);
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #3d5161;
            margin: 20px 0;
            min-height: 400px;
        }

        .info-box h4 {
            color: #3d5161;
            margin-top: 0;
        }
        /* About tab boxes - smaller min-height */

        .about-info-box {
            background: rgba(61, 81, 97, 0.08);
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #3d5161;
            margin: 20px 0;
            min-height: 230px;  /* Smaller than the 360px we use elsewhere */
        }

        /* Insights section */
        .insights-section {
            background: #f8f9fa;
            padding: 30px;
            border-radius: 8px;
            border-left: 4px solid #3d5161;
            margin: 20px 0;
        }

        .insight-item {
            margin-bottom: 15px;
            line-height: 1.8;
        }

        .insight-item strong {
            color: #1f1f1f;
        }

        /* Section headers */
        h3 {
            font-size: 1.5rem;
            margin-top: 2rem;
            color: #1f1f1f;
        }

        /* Two-column layouts */
        .two-col-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin: 20px 0;
        }
    </style>
"""
