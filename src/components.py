def create_metric_card(icon, value, label, trend=None, color="#667eea"):
    """Create a styled metric card with icon, value, label, and optional trend"""
    trend_html = ""
    if trend:
        trend_class = "trend-up" if "\u2191" in trend else "trend-down" if "\u2193" in trend else "trend-neutral"
        trend_html = f'<div class="metric-trend {trend_class}">{trend}</div>'

    return f"""
    <div class="metric-card" style="border-top-color: {color};">
        <div class="metric-icon">{icon}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-label">{label}</div>
        {trend_html}
    </div>
    """


def pct_trend(early_val, late_val):
    """Calculate percentage trend between two period values."""
    if early_val and early_val > 0:
        pct = (late_val - early_val) / early_val * 100
        arrow = "\u2191" if pct > 0 else "\u2193" if pct < 0 else "\u2192"
        return f"{arrow} {abs(pct):.0f}% vs earlier period"
    return " "
