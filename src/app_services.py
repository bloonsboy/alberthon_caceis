from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from human_capital_pipeline import (
    FILES,
    MODEL_FEATURES_CAT,
    MODEL_FEATURES_NUM,
    apply_training_missing_strategy,
    build_analysis_df,
    build_base_snapshot,
    build_employee_aggregates,
    build_feature_importance,
    build_summary,
    compute_hcv_scores,
    load_sources,
    map_contract,
    map_education,
    minmax,
    score_new_employee,
    train_hcv_models,
)


@dataclass(frozen=True)
class AppPaths:
    project_root: Path
    data_root: Path
    outputs_dir: Path
    dataset_csv: Path


def resolve_paths(project_root: Path | None = None) -> AppPaths:
    # project root is one level above `src/` when called from code in `src/`
    root = (project_root or Path(__file__).resolve().parent.parent).resolve()
    # data should be placed by the user in the `data/` folder at project root
    data_root = root / "data"
    outputs_dir = root / "data" / "outputs_hcv_notebook"
    dataset_csv = outputs_dir / "caceis_hcv_dataset.csv"
    return AppPaths(
        project_root=root,
        data_root=data_root,
        outputs_dir=outputs_dir,
        dataset_csv=dataset_csv,
    )


def _build_from_raw(paths: AppPaths) -> pd.DataFrame:
    sources = load_sources(paths.data_root)
    base = build_base_snapshot(
        master=sources["master"],
        mobility_fr_raw=sources["mobility_fr_raw"],
        absence_fr_context_raw=sources["absence_fr_context_raw"],
        absence_lu_context=sources["absence_lu_context"],
        compensation_file=paths.data_root
        / "Finance"
        / "AlbertSchool_CACEIS_PL-FTE_22-25_Sent.xlsx",
    )
    aggregates = build_employee_aggregates(
        perf=sources["perf"],
        eae=sources["eae"],
        eae_working=sources["eae_working"],
        train_records=sources["train_records"],
        quick=sources["quick"],
        cold=sources["cold"],
        abs_df=sources["abs_df"],
    )
    merged = build_analysis_df(base, *aggregates)
    merged = apply_training_missing_strategy(merged, strategy="knn")
    return compute_hcv_scores(merged)


def prepare_dataset_for_app(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """
    Normalise le DataFrame pour l'UI et pour train_hcv_models.

    Le CSV exporté (`EXPORT_COLS`) ne contient pas les variables ML intermédiaires ;
    on les reconstruit localement sans relire les Excel pour éviter un chargement lent.
    """
    meta: dict[str, Any] = {"dataset_kind": "unknown", "augmented_from_export": False}
    df = df.copy()

    req_models = set(MODEL_FEATURES_NUM + MODEL_FEATURES_CAT + ["HCV", "HCV_segment"])

    def _sanitize_categories(frame: pd.DataFrame) -> pd.DataFrame:
        out = frame
        for col in MODEL_FEATURES_CAT:
            if col not in out.columns:
                out[col] = ""
            out[col] = (
                out[col]
                .fillna("")
                .astype(str)
                .replace({"nan": "", "None": "", "<NA>": ""})
                .str.strip()
            )
        return out

    def _ensure_absence_events(frame: pd.DataFrame) -> pd.DataFrame:
        out = frame
        if "absence_events" not in out.columns:
            ad = pd.to_numeric(out.get("absence_days"), errors="coerce").fillna(0)
            out["absence_events"] = (ad > 0).astype(np.int64)
        return out

    if req_models.issubset(df.columns):
        meta["dataset_kind"] = "pipeline_full"
        df = _ensure_absence_events(df)
        df = _sanitize_categories(df)
        return df, meta

    meta["dataset_kind"] = "export_csv"
    meta["augmented_from_export"] = True

    df = _ensure_absence_events(df)

    th = (
        pd.to_numeric(df.get("training_hours"), errors="coerce").fillna(0).clip(lower=0)
    )
    tc = pd.to_numeric(df.get("tenure_caceis_years"), errors="coerce").fillna(0)
    denom = tc.replace(0, np.nan) + 1
    training_intensity = (th / denom).replace([np.inf, -np.inf], np.nan).fillna(0)
    df["training_intensity_log"] = np.log1p(training_intensity.clip(lower=0))
    df["training_intensity_score"] = minmax(df["training_intensity_log"])

    dl = df.get("degree_level")
    df["education_score"] = (
        dl.map(map_education)
        if dl is not None
        else pd.Series(0.5, index=df.index, dtype=float)
    )
    ct = df.get("contract_type")
    df["contract_seniority"] = (
        ct.map(map_contract)
        if ct is not None
        else pd.Series(0.6, index=df.index, dtype=float)
    )

    adays = pd.to_numeric(df.get("absence_days"), errors="coerce").fillna(0)
    df["absence_rate"] = (adays / 220).clip(0, 1)

    rk = df.get("role")
    role_key = (
        rk.fillna("Unknown").astype(str)
        if rk is not None
        else pd.Series(["Unknown"] * len(df), index=df.index)
    )
    role_share = role_key.map(role_key.value_counts() / max(len(df), 1))
    df["role_scarcity_score"] = minmax((1 / role_share.replace(0, np.nan))).fillna(0.5)

    if "training_completion_rate" not in df.columns:
        df["training_completion_rate"] = 0.65
    else:
        tcr = pd.to_numeric(df["training_completion_rate"], errors="coerce")
        df["training_completion_rate"] = tcr.fillna(0.65).clip(0, 1)

    if "certification_rate" not in df.columns:
        df["certification_rate"] = 0.2
    else:
        df["certification_rate"] = (
            pd.to_numeric(df["certification_rate"], errors="coerce")
            .fillna(0.2)
            .clip(0, 1)
        )

    df = _sanitize_categories(df)
    return df, meta


def load_or_build_dataset(
    force_rebuild: bool = False, project_root: Path | None = None
) -> pd.DataFrame:
    paths = resolve_paths(project_root=project_root)
    if not force_rebuild and paths.dataset_csv.exists():
        return pd.read_csv(paths.dataset_csv)
    return _build_from_raw(paths)


def train_models(df: pd.DataFrame) -> dict[str, Any]:
    return train_hcv_models(df)


def compute_feature_importance(
    models: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    return build_feature_importance(models["reg_model"])


def run_profile_prediction(
    df: pd.DataFrame, models: dict[str, Any], profile: dict[str, Any]
) -> pd.Series:
    defaults = {
        "certification_rate": 0.0,
        "country": None,
        "contract_type": None,
        "degree_level": None,
        "role": None,
        "entity": None,
        "bu": None,
    }
    return score_new_employee(
        df=df,
        reg_model=models["reg_model"],
        clf_model=models["clf_model"],
        **(defaults | profile),
    )


def summarize_population(df: pd.DataFrame) -> dict[str, Any]:
    return build_summary(df)


def build_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "priority",
                "pillar",
                "title",
                "rationale",
                "target_population_pct",
                "kpi_to_track",
            ]
        )
    rows: list[dict[str, Any]] = []
    population = len(df)

    signals = [
        (
            "Q_qualification",
            0.55,
            "Qualification",
            "Renforcer certifications et montée en expertise",
            "Le score Q est faible: prioriser des parcours certifiants et coaching managers sur la performance.",
            "Taux de certification, score Q moyen",
        ),
        (
            "B_behavioural",
            0.55,
            "Behavioural",
            "Augmenter complétion et assiduité formation",
            "Le score B indique une dynamique d'apprentissage irrégulière: sécuriser l'exécution des plans de formation.",
            "Training completion rate, absentéisme",
        ),
        (
            "E_engagement",
            0.55,
            "Engagement",
            "Lancer plan engagement ciblé",
            "Le score E est faible: mener actions de proximité managériale, inclusion et participation aux dispositifs internes.",
            "E moyen, participation D&I",
        ),
        (
            "attrition_risk",
            0.50,
            "Retention",
            "Sécuriser les populations critiques à risque",
            "Le risque d'attrition est élevé: prioriser plans de rétention sur segments High/Elite.",
            "Part High/Elite à risque, turnover contextuel",
        ),
    ]

    for col, threshold, pillar, title, rationale, kpi in signals:
        if col not in df.columns:
            continue
        if col == "attrition_risk":
            impacted = df[col].fillna(0).ge(threshold)
        else:
            impacted = df[col].fillna(1).lt(threshold)
        impacted_share = float(impacted.mean())
        if impacted_share < 0.15:
            continue
        rows.append(
            {
                "priority": (
                    1 if impacted_share >= 0.40 else 2 if impacted_share >= 0.25 else 3
                ),
                "pillar": pillar,
                "title": title,
                "rationale": rationale,
                "target_population_pct": round(100 * impacted_share, 1),
                "kpi_to_track": kpi,
                "target_population_n": int(impacted.sum()),
                "population_n": population,
            }
        )

    if not rows:
        rows.append(
            {
                "priority": 3,
                "pillar": "Monitoring",
                "title": "Maintenir le niveau global et surveiller les signaux faibles",
                "rationale": "Aucun signal critique massif détecté, conserver la trajectoire et suivre les KPI trimestriels.",
                "target_population_pct": 0.0,
                "kpi_to_track": "HCV médian, attrition, engagement",
                "target_population_n": 0,
                "population_n": population,
            }
        )

    recs = (
        pd.DataFrame(rows)
        .sort_values(["priority", "target_population_pct"], ascending=[True, False])
        .reset_index(drop=True)
    )
    return recs


def expected_model_features() -> dict[str, list[str]]:
    return {"numeric": MODEL_FEATURES_NUM, "categorical": MODEL_FEATURES_CAT}


def validate_data_folder(paths: AppPaths) -> dict[str, bool]:
    checks = {}
    for key, (relative, _) in FILES.items():
        checks[key] = (paths.data_root / relative).exists()
    return checks
