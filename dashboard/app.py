import os
from datetime import UTC, datetime

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
API_BASE = f"{BACKEND_URL}/api/v1"

st.set_page_config(page_title="AI Code Review Dashboard", page_icon="AI", layout="wide")

st.markdown(
    """
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&display=swap');
      html, body, [class*="css"]  {
          font-family: 'Space Grotesk', sans-serif;
      }
      .hero {
          padding: 1rem 1.4rem;
          border-radius: 18px;
          background: linear-gradient(120deg, #0f766e 0%, #155e75 60%, #1d4ed8 100%);
          color: #f8fafc;
          box-shadow: 0 14px 30px rgba(15, 118, 110, 0.25);
          margin-bottom: 1rem;
      }
      .hero h1 {
          margin: 0;
          font-size: 2rem;
      }
      .hero p {
          margin: 0.3rem 0 0 0;
          opacity: 0.9;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>AI Code Review Command Center</h1>
      <p>Multi-model intelligence with consensus scoring, semantic cache, and CI-ready reports.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Connection")
    st.write(f"Backend: {BACKEND_URL}")
    st.subheader("Auth (optional)")
    auth_mode = st.selectbox("Auth header", options=["None", "X-API-Key", "Bearer JWT"], index=0)
    auth_value = st.text_input("Auth value", value="", type="password")
    st.caption("If your backend has `AUTH_MODE` enabled, set the matching header here.")

    def _auth_headers() -> dict[str, str]:
        if not auth_value:
            return {}
        if auth_mode == "X-API-Key":
            return {"X-API-Key": auth_value}
        if auth_mode == "Bearer JWT":
            return {"Authorization": f"Bearer {auth_value}"}
        return {}

    if st.button("Check Health"):
        try:
            response = requests.get(f"{API_BASE}/health", timeout=8)
            response.raise_for_status()
            st.success(response.json())
        except Exception as exc:
            st.error(f"Health check failed: {exc}")

live_tab, history_tab, system_tab = st.tabs(["Live Review", "Review History", "System Metrics"])

with live_tab:
    st.subheader("Run New Code Review")
    col1, col2 = st.columns([1, 1])

    with col1:
        user_id = st.text_input("User ID", value="dashboard-user")
        repository = st.text_input("Repository", value="example/repo")
        file_path = st.text_input("File Path", value="src/main.py")
        language = st.selectbox(
            "Language",
            options=["python", "javascript", "typescript", "go", "java"],
        )
        focus = st.multiselect(
            "Focus Areas",
            options=["security", "performance", "maintainability", "style", "testing"],
            default=["security", "performance", "maintainability"],
        )

    with col2:
        code = st.text_area(
            "Code",
            value="def add(a, b):\n    return a + b\n",
            height=240,
        )
        diff = st.text_area("Optional Diff", value="", height=150)

    if st.button("Analyze Code", type="primary"):
        payload = {
            "user_id": user_id,
            "repository": repository,
            "file_path": file_path,
            "language": language,
            "code": code,
            "diff": diff or None,
            "focus": focus,
            "metadata": {
                "source": "streamlit",
                "timestamp": datetime.now(UTC).isoformat(),
            },
        }
        try:
            response = requests.post(
                f"{API_BASE}/reviews",
                json=payload,
                headers=_auth_headers(),
                timeout=300,
            )
            response.raise_for_status()
            data = response.json()

            score_col, cache_col, latency_col = st.columns(3)
            score_col.metric("Consensus Score", f"{data['consensus_score']}/10")
            cache_col.metric("Cache Hit", "Yes" if data.get("cache_hit") else "No")
            latency_col.metric("Latency", f"{data.get('processing_ms', 0)} ms")

            st.write("### Summary")
            st.info(data.get("summary", "No summary returned."))

            findings = data.get("findings", [])
            st.write("### Findings")
            if findings:
                findings_df = pd.DataFrame(findings)
                st.dataframe(findings_df, use_container_width=True)
            else:
                st.success("No findings returned.")

            st.write("### Refactoring Suggestions")
            for suggestion in data.get("refactoring_suggestions", []):
                st.write(f"- {suggestion}")

            st.write("### Test Recommendations")
            for rec in data.get("test_recommendations", []):
                st.write(f"- {rec}")

            if data.get("html_report"):
                with st.expander("HTML Report Preview", expanded=False):
                    st.components.v1.html(data["html_report"], height=500, scrolling=True)

        except Exception as exc:
            st.error(f"Review failed: {exc}")

with history_tab:
    st.subheader("Recent Reviews")
    history_user = st.text_input("Filter by User ID (optional)", value="")
    if st.button("Load History"):
        params = {"limit": 100, "offset": 0}
        if history_user:
            params["user_id"] = history_user

        try:
            response = requests.get(
                f"{API_BASE}/reviews/history",
                params=params,
                headers=_auth_headers(),
                timeout=20,
            )
            response.raise_for_status()
            records = response.json()
            if not records:
                st.warning("No review history found.")
            else:
                df = pd.DataFrame(records)
                st.dataframe(df, use_container_width=True)

                chart = px.histogram(
                    df,
                    x="overall_score",
                    nbins=20,
                    title="Consensus Score Distribution",
                    color_discrete_sequence=["#0f766e"],
                )
                st.plotly_chart(chart, use_container_width=True)

                trend = px.line(
                    df.sort_values("created_at"),
                    x="created_at",
                    y="overall_score",
                    markers=True,
                    title="Score Trend",
                )
                st.plotly_chart(trend, use_container_width=True)
        except Exception as exc:
            st.error(f"Failed to load history: {exc}")

with system_tab:
    st.subheader("System Status")
    try:
        health = requests.get(f"{API_BASE}/health", timeout=8).json()
        col1, col2, col3 = st.columns(3)
        col1.metric("Environment", health.get("environment", "unknown"))
        col2.metric("Redis", "UP" if health.get("redis") else "DOWN")
        col3.metric("Database", "UP" if health.get("database") else "DOWN")
        st.json(health)
    except Exception as exc:
        st.error(f"Unable to fetch system status: {exc}")
