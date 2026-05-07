from __future__ import annotations

import base64
import io
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from PIL import Image

try:
    px.defaults.template = "plotly_white"
except Exception:
    pass

from app_services import (
    build_recommendations,
    compute_feature_importance,
    load_or_build_dataset,
    prepare_dataset_for_app,
    resolve_paths,
    run_profile_prediction,
    summarize_population,
    train_models,
)
from unstructured_mvp import (
    build_unstructured_summary,
    compute_theme_signals,
    compute_top_terms,
    extract_unstructured_corpus,
)

NAV_OPTIONS = ["Global Dashboard", "AI Simulation", "Recommendations", "Unstructured Sources"]
MODE_OPTIONS = ["Quick mode", "Reliable mode"]
LOGO_CANDIDATES = [
    "assets/c__Users_pavel_AppData_Roaming_Cursor_User_workspaceStorage_cc6017c0bd644b985b9a3d1576f4282a_images_CACEIS_logo2-d1220268-7aa3-41d5-b61b-3659687fa7c5.png",
    "assets/logo_caceis.png",
    "assets/caceis_logo.png",
    "assets/CACEIS_logo.png",
    "assets/c__Users_pavel_AppData_Roaming_Cursor_User_workspaceStorage_cc6017c0bd644b985b9a3d1576f4282a_images_CACEIS_logo-94d17097-4faa-43f4-a43b-0bcb59962d3c.png",
    "C:/Users/pavel/.cursor/projects/c-Users-pavel-Downloads-CACEIS-Alberthon-alberthon-caceis/assets/c__Users_pavel_AppData_Roaming_Cursor_User_workspaceStorage_cc6017c0bd644b985b9a3d1576f4282a_images_CACEIS_logo-94d17097-4faa-43f4-a43b-0bcb59962d3c.png",
]

PAGE_STYLE = """
<style>
    :root {
        --caceis-blue: #223a63;
        --caceis-red: #cf123f;
        --caceis-line: #d9dfe7;
        --caceis-muted: #5e6f86;
    }
    [data-testid="stHeader"] { display: none; }
    [data-testid="stToolbar"] { display: none; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    html, body, [class*="css"] {
        font-family: Arial, "Helvetica Neue", sans-serif;
        background: #ffffff !important;
        color: var(--caceis-blue);
        font-weight: 400 !important;
    }
    .block-container {
        max-width: 1320px;
        padding-top: 0.5rem;
        padding-bottom: 2rem;
    }
    [data-testid="stHorizontalBlock"] {
        align-items: center;
    }
    div[data-testid="stDecoration"] { background: #ffffff; }
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stImageToolbar"] { display: none !important; }

    .top-separator { border-top: 1px solid var(--caceis-line); margin: 0.5rem 0 0.8rem 0; }
    .section-separator { border-top: 1px solid var(--caceis-line); margin: 1rem 0; }
    .panel-title {
        color: var(--caceis-red);
        text-transform: uppercase;
        letter-spacing: 0.02em;
        font-weight: 500;
        font-size: 2rem;
        margin-bottom: 0.25rem;
    }
    .subtitle { color: var(--caceis-muted); font-size: 0.92rem; }
    .caption-line { color: var(--caceis-muted); font-size: 0.86rem; margin: 0.35rem 0; }

    div[data-testid="stMetric"] label {
        color: var(--caceis-muted) !important;
        font-weight: 400 !important;
    }

    div[data-baseweb="select"] * {
        border-radius: 2px !important;
        border-color: #b9c4d4 !important;
        border-width: 1px !important;
    }
    .stMultiSelect [data-baseweb="select"] {
        border: 1px solid #b9c4d4 !important;
        border-radius: 2px !important;
        background: #fff !important;
    }
    .stButton > button {
        min-height: 56px;
        border-radius: 2px !important;
        border: 1px solid #c9d2df !important;
        background: #fff !important;
        color: #223a63 !important;
        font-weight: 500 !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        font-size: 0.95rem !important;
        line-height: 1.1 !important;
        text-align: center !important;
    }
    .stButton > button[kind="primary"] {
        border-color: #cf123f !important;
        color: #cf123f !important;
        background: #fff !important;
    }
    .logo-shell {
        border: 1px solid #d9dfe7;
        border-radius: 2px;
        background: #fff;
        padding: 4px 8px;
        display: inline-flex;
    }
    .logo-shell img {
        display: block;
    }
    .mode-info {
        display: inline-flex;
        justify-content: center;
        align-items: center;
        width: 28px;
        height: 28px;
        border: 1px solid #c9d2df;
        border-radius: 999px;
        color: #223a63;
        font-weight: 700;
        font-size: 0.9rem;
    }
    .mode-stack .stButton > button {
        min-height: 44px !important;
    }
    [data-testid="stSpinner"] {
        position: fixed !important;
        top: 50% !important;
        left: 50% !important;
        transform: translate(-50%, -50%) !important;
        z-index: 1002 !important;
        background: #ffffff !important;
        border: 1px solid #d9dfe7 !important;
        border-radius: 10px !important;
        padding: 18px 22px !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.15) !important;
    }
    body:has([data-testid="stSpinner"])::before {
        content: "";
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.35);
        z-index: 1001;
    }
</style>
"""

st.set_page_config(page_title="CACEIS HCV", layout="wide", initial_sidebar_state="collapsed")
st.markdown(PAGE_STYLE, unsafe_allow_html=True)


def _existing_logo_path() -> str | None:
    for candidate in LOGO_CANDIDATES:
        if Path(candidate).exists():
            return candidate
    return None


@st.cache_data(show_spinner=False)
def _load_logo_bytes(path: str) -> bytes:
    # Convert near-black background pixels to transparent for clean white header rendering.
    img = Image.open(path).convert("RGBA")
    px_data = img.load()
    width, height = img.size
    for y in range(height):
        for x in range(width):
            r, g, b, a = px_data[x, y]
            if r < 26 and g < 26 and b < 26:
                px_data[x, y] = (255, 255, 255, 0)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def _render_logo_static(path: str, width: int = 170) -> None:
    logo_bytes = _load_logo_bytes(path)
    encoded = base64.b64encode(logo_bytes).decode("utf-8")
    st.markdown(
        f"<div class='logo-shell'><img src='data:image/png;base64,{encoded}' width='{width}' /></div>",
        unsafe_allow_html=True,
    )


def _confirm_reliable_dialog() -> None:
    @st.dialog("Switch to Reliable mode?")
    def _dialog() -> None:
        st.write(
            "You are about to re-scan Excel sources. This increases data fidelity but can significantly increase loading time."
        )
        c1, c2 = st.columns(2)
        if c1.button("Continue", type="primary", use_container_width=True):
            st.session_state["reliable_confirmed"] = True
            st.session_state["selected_mode"] = "Reliable mode"
            st.rerun()
        if c2.button("Cancel", use_container_width=True):
            st.session_state["selected_mode"] = "Quick mode"
            st.session_state["reliable_confirmed"] = False
            st.rerun()

    _dialog()


@st.cache_data(show_spinner=False)
def compute_models_bundle(df: pd.DataFrame) -> dict:
    try:
        return {"ok": True, "models": train_models(df), "error": None}
    except Exception as exc:
        return {"ok": False, "models": None, "error": str(exc)}


@st.cache_data(show_spinner=False)
def get_unstructured_df(data_root: str) -> pd.DataFrame:
    return extract_unstructured_corpus(Path(data_root))


def render_filters(df: pd.DataFrame) -> pd.DataFrame:
    st.markdown("#### Filters")
    c1, c2, c3 = st.columns(3)
    countries = c1.multiselect("Country", sorted(df["country"].dropna().astype(str).unique().tolist()))
    contracts = c2.multiselect("Contract type", sorted(df["contract_type"].dropna().astype(str).unique().tolist()))
    roles = c3.multiselect("Role", sorted(df["role"].dropna().astype(str).unique().tolist()))

    filtered = df.copy()
    if countries:
        filtered = filtered[filtered["country"].isin(countries)]
    if contracts:
        filtered = filtered[filtered["contract_type"].isin(contracts)]
    if roles:
        filtered = filtered[filtered["role"].isin(roles)]
    return filtered


def _dynamic_title(page: str, df: pd.DataFrame) -> str:
    countries = sorted(df["country"].dropna().astype(str).unique().tolist()) if "country" in df.columns else []
    suffix = f" - {countries[0].upper()}" if len(countries) == 1 else ""
    return f"{page.upper()}{suffix}"


def render_dashboard(df: pd.DataFrame) -> None:
    st.markdown(f"<div class='panel-title'>{_dynamic_title('Global Dashboard', df)}</div>", unsafe_allow_html=True)
    summary = summarize_population(df)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Population", f"{summary['employees']}")
    k2.metric("Average HCV", f"{summary['avg_hcv']}")
    k3.metric("Average attrition risk", f"{summary['avg_attrition_risk']}")
    k4.metric("Average training hours", f"{summary['avg_training_hours']}")

    left, right = st.columns(2)
    with left:
        seg = df["HCV_segment"].value_counts(dropna=False).rename_axis("segment").reset_index(name="employees")
        fig_seg = px.bar(
            seg,
            x="segment",
            y="employees",
            color="segment",
            title="HCV Segment Distribution",
            color_discrete_sequence=["#223a63", "#cf123f", "#2f7892", "#8aa1bd"],
        )
        st.plotly_chart(fig_seg, use_container_width=True)
    with right:
        fig_scatter = px.scatter(
            df,
            x="training_hours",
            y="HCV",
            color="HCV_segment",
            size="tenure_caceis_years",
            hover_data=["country", "contract_type", "role"],
            title="Training vs HCV (bubble size = CACEIS tenure)",
            color_discrete_sequence=["#223a63", "#cf123f", "#2f7892", "#8aa1bd"],
        )
        st.plotly_chart(fig_scatter, use_container_width=True)


def render_simulation(df: pd.DataFrame, models: dict | None) -> None:
    st.markdown(f"<div class='panel-title'>{_dynamic_title('AI Simulation', df)}</div>", unsafe_allow_html=True)
    if models is None:
        err = st.session_state.get("_model_train_error", "unknown error")
        st.warning("The predictive module is currently unavailable.")
        st.caption(f"Technical details: {err}")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        tenure_caceis = st.slider("CACEIS tenure (years)", 0.0, 25.0, 5.0, 0.5)
        tenure_role = st.slider("Role tenure (years)", 0.0, 20.0, 3.0, 0.5)
        performance = st.slider("Performance rating", 1.0, 5.0, 3.5, 0.1)
    with c2:
        training_hours = st.slider("Annual training hours", 0.0, 120.0, 20.0, 1.0)
        training_events = st.slider("Training events", 0, 20, 4, 1)
        completion = st.slider("Training completion rate", 0.0, 1.0, 0.7, 0.01)
    with c3:
        sentiment = st.slider("Post-training sentiment", 0.0, 1.0, 0.6, 0.01)
        absence_days = st.slider("Absence days", 0.0, 60.0, 5.0, 0.5)
        cert_rate = st.slider("Certification rate", 0.0, 1.0, 0.2, 0.01)

    c4, c5, c6 = st.columns(3)
    country = c4.selectbox("Country", sorted(df["country"].dropna().astype(str).unique().tolist()))
    contract_type = c5.selectbox("Contract type", sorted(df["contract_type"].dropna().astype(str).unique().tolist()))
    degree = c6.selectbox("Degree level", sorted(df["degree_level"].dropna().astype(str).unique().tolist()))
    role = st.selectbox("Role", sorted(df["role"].dropna().astype(str).unique().tolist()))
    entity = st.selectbox("Entity", sorted(df["entity"].dropna().astype(str).unique().tolist()))

    if st.button("Run prediction", type="primary"):
        profile = {
            "tenure_caceis_years": tenure_caceis,
            "tenure_position_years": tenure_role,
            "performance_rating": performance,
            "training_hours": training_hours,
            "training_events": training_events,
            "training_completion_rate": completion,
            "training_sentiment_score": sentiment,
            "absence_days": absence_days,
            "certification_rate": cert_rate,
            "country": country,
            "contract_type": contract_type,
            "degree_level": degree,
            "role": role,
            "entity": entity,
        }
        pred = run_profile_prediction(df, models, profile)
        m1, m2 = st.columns(2)
        m1.metric("Predicted HCV", f"{pred['predicted_hcv']}")
        m2.metric("Predicted segment", f"{pred['predicted_segment']}")

    with st.expander("Global feature importance", expanded=False):
        _, family_importance = compute_feature_importance(models)
        fig = px.bar(
            family_importance,
            x="family",
            y="importance",
            title="Feature importance by variable family",
            color_discrete_sequence=["#223a63"],
        )
        st.plotly_chart(fig, use_container_width=True)


def render_recommendations_page(df: pd.DataFrame) -> None:
    st.markdown(f"<div class='panel-title'>{_dynamic_title('Recommendations', df)}</div>", unsafe_allow_html=True)
    recs = build_recommendations(df)
    st.dataframe(
        recs[["priority", "pillar", "title", "target_population_pct", "kpi_to_track"]],
        use_container_width=True,
        hide_index=True,
    )


def render_unstructured_page(paths_root: str, df: pd.DataFrame) -> None:
    st.markdown(f"<div class='panel-title'>{_dynamic_title('Unstructured Sources', df)}</div>", unsafe_allow_html=True)
    corpus = get_unstructured_df(paths_root)
    summary = build_unstructured_summary(corpus)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Documents", summary["documents"])
    c2.metric("PDF", summary["pdf_files"])
    c3.metric("PPTX", summary["pptx_files"])
    c4.metric("Extractable docs", f"{summary['extractable_docs_pct']}%")

    if corpus.empty:
        st.info("No PDF/PPTX documents found in the configured data folder.")
        return
    themes = compute_theme_signals(corpus)
    terms = compute_top_terms(corpus)
    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            px.bar(themes, x="theme", y="normalized_score", title="Theme signals", color_discrete_sequence=["#223a63"]),
            use_container_width=True,
        )
    with right:
        st.plotly_chart(
            px.bar(terms, x="term", y="count", title="Top terms", color_discrete_sequence=["#cf123f"]),
            use_container_width=True,
        )
    st.dataframe(corpus[["source_type", "file_name", "word_count", "char_count"]], use_container_width=True, hide_index=True)


def main() -> None:
    st.session_state.setdefault("selected_page", NAV_OPTIONS[0])
    st.session_state.setdefault("selected_mode", MODE_OPTIONS[0])
    st.session_state.setdefault("reliable_confirmed", False)

    logo_col, nav_col, mode_col = st.columns([1.0, 4.4, 1.5], vertical_alignment="center")
    with logo_col:
        logo_path = _existing_logo_path()
        if logo_path:
            _render_logo_static(logo_path, width=170)
        else:
            st.markdown("### CACEIS")

    with nav_col:
        nav_cols = st.columns(4, gap="small")
        for idx, option in enumerate(NAV_OPTIONS):
            is_active = st.session_state["selected_page"] == option
            if nav_cols[idx].button(option, use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state["selected_page"] = option
                st.rerun()

    with mode_col:
        m1, m2 = st.columns([4, 1], gap="small")
        with m1:
            st.markdown("<div class='mode-stack'>", unsafe_allow_html=True)
            quick_active = st.session_state["selected_mode"] == "Quick mode"
            if st.button("Quick mode", use_container_width=True, type="primary" if quick_active else "secondary", key="quick_mode_btn"):
                st.session_state["selected_mode"] = "Quick mode"
                st.session_state["reliable_confirmed"] = False
                st.rerun()
            reliable_active = st.session_state["selected_mode"] == "Reliable mode"
            if st.button("Reliable mode", use_container_width=True, type="primary" if reliable_active else "secondary", key="reliable_mode_btn"):
                st.session_state["selected_mode"] = "Reliable mode"
                st.session_state["reliable_confirmed"] = False
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with m2:
            with st.popover("ⓘ", use_container_width=True):
                st.write(
                    "Quick mode is faster: it loads exported CSV data and reconstructs ML features locally. "
                    "Reliable mode rescans Excel sources for higher fidelity and takes longer."
                )

        if st.session_state["selected_mode"] == "Reliable mode" and not st.session_state["reliable_confirmed"]:
            _confirm_reliable_dialog()

    force_rebuild = st.session_state["selected_mode"] == "Reliable mode" and st.session_state["reliable_confirmed"]

    st.markdown("<div class='top-separator'></div>", unsafe_allow_html=True)

    paths = resolve_paths()
    with st.spinner("Loading HR data..."):
        raw_df = load_or_build_dataset(force_rebuild=force_rebuild)
        df, meta = prepare_dataset_for_app(raw_df)

    st.markdown(
        "<div class='caption-line'>"
        + (
            "Reliable mode is active. Full Excel rescan is used for maximum data fidelity."
            if force_rebuild
            else "Quick mode is active. Data is loaded rapidly from CSV with local feature reconstruction."
        )
        + "</div>",
        unsafe_allow_html=True,
    )

    page = st.session_state["selected_page"]
    if page in {"Global Dashboard", "Recommendations"}:
        filtered_df = render_filters(df)
        st.markdown("<div class='section-separator'></div>", unsafe_allow_html=True)
    else:
        filtered_df = df

    models = None
    if page == "AI Simulation":
        with st.spinner("Training AI models..."):
            bundle = compute_models_bundle(df)
        models = bundle["models"] if bundle["ok"] else None
        st.session_state["_model_train_error"] = bundle.get("error")

    if page == "Global Dashboard":
        render_dashboard(filtered_df)
    elif page == "AI Simulation":
        render_simulation(filtered_df, models)
    elif page == "Recommendations":
        render_recommendations_page(filtered_df)
    else:
        render_unstructured_page(str(paths.data_root), filtered_df)


if __name__ == "__main__":
    main()
