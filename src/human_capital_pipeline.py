import json
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.impute import KNNImputer, SimpleImputer
from sklearn.metrics import accuracy_score, mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

warnings.filterwarnings("ignore")

REFERENCE_DATE = pd.Timestamp("2026-04-28")
FILES = {
    "master": ("HR Data/Data.xlsx", "Sheet1"),
    "perf": ("HR Data/20240222 - CACEIS Notes evaluation 2023.xlsx", None),
    "eae": ("HR Data/20250218 - Stats CACEIS EAE EP 18-02-2025 Version Définitive cloture.xlsx", "Database"),
    "eae_working": ("HR Data/2025 - Stats CACEIS EAE EP fichier de travail - Vretraitement.xlsx", "Database"),
    "abs_df": ("HR Data/20260121 - Absentéisme_-_détail_affectation_-_Bilan_social 2025.xlsx", None),
    "train_records": ("Training/Training_Records_Unnamed.xlsx", None),
    "quick": ("Training/Quick_Review_Unnamed.xlsx", None),
    "cold": ("Training/Cold_Review_Unnamed.xlsx", None),
    "mobility_fr_raw": ("HR Data/Data.xlsx", "taux mob_TO FR"),
    "absence_fr_context_raw": ("HR Data/Data.xlsx", "Absentéisme FR"),
    "absence_lu_context": ("HR Data/Data.xlsx", "Abssentéisme Luxembourg"),
}
SOURCE_OVERVIEW = {
    "master": ("HR master", "id_employee"),
    "perf": ("Performance ratings", "iug"),
    "eae": ("EAE definitive", "iug"),
    "eae_working": ("EAE working", "iug"),
    "abs_df": ("Absenteeism", "employee_code"),
    "train_records": ("Training records", "employee_code"),
    "quick": ("Quick review", "matricule"),
    "cold": ("Cold review", "matricule"),
    "absence_lu_context": ("Lux absence context", "login"),
}
MODEL_FEATURES_NUM = [
    "tenure_caceis_years", "tenure_position_years", "performance_rating", "training_intensity_score",
    "training_completion_rate", "absence_days", "absence_rate", "education_score",
    "contract_seniority", "role_scarcity_score", "certification_rate",
]
MODEL_FEATURES_CAT = ["country", "contract_type", "degree_level", "role", "entity", "bu"]
EXPORT_COLS = [
    "employee_id", "country", "entity", "bu", "contract_type", "degree_level", "role",
    "tenure_caceis_years", "tenure_position_years", "performance_rating", "training_hours",
    "training_events", "absence_days", "benchmark_fixed_salary", "benchmark_variable_salary",
    "benchmark_total_comp", "di_inclusion_score", "di_participation_rate", "taux_mobilite",
    "taux_turnover", "taux_abs", "lu_absence_hours_per_login", "Q_qualification", "B_behavioural",
    "R_rarity", "E_engagement", "attrition_risk", "succession_score", "HCV", "HCV_segment",
]
TEXT_SCORES = {
    "tout à fait d'accord": 1.0, "oui, tout à fait": 1.0, "oui": 1.0, "plutôt d'accord": 0.75,
    "oui, en partie": 0.65, "en partie": 0.5, "mitigé": 0.5, "plutôt pas d'accord": 0.25,
    "non": 0.0, "pas du tout d'accord": 0.0,
}
EDUCATION_MAP = {"phd": 1.0, "doctor": 1.0, "master": 0.95, "bachelor": 0.75, "bac_5": 0.95, "bac_4": 0.85, "bac_3": 0.70, "bac_2": 0.55, "bac": 0.40}
CONTRACT_MAP = {"executive": 1.0, "cadre": 0.95, "manager": 0.95, "permanent": 0.80, "cdi": 0.80, "fixed": 0.55, "cdd": 0.55, "intern": 0.30, "stage": 0.30, "apprentice": 0.35, "altern": 0.35}
COMPONENT_LABELS = {
    "Q": "0.45 education + 0.40 performance + 0.15 certifications",
    "B": "0.20 completion + 0.45 presence + 0.35 mobility_context",
    "R": "0.50 role_scarcity + 0.35 market_benchmark + 0.15 contract_seniority",
    "E": "0.20 sentiment + 0.45 inclusion + 0.35 participation",
    "attrition": "0.35 low_tenure + 0.30 absence + 0.35 turnover_context",
    "succession": "0.45 tenure_position + 0.55 learning_depth",
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.columns = out.columns.astype(str).str.strip().str.lower().str.replace(r"[^0-9a-zA-Z]+", "_", regex=True).str.strip("_")
    return out


def clean_id(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().replace({"nan": np.nan, "None": np.nan, "": np.nan})


def parse_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", dayfirst=True)


def _num(s, fill=None):
    s = pd.to_numeric(s, errors="coerce")
    return s.fillna(fill) if fill is not None else s


def minmax(series: pd.Series, lower_q: float = 0.01, upper_q: float = 0.99) -> pd.Series:
    s = _num(series)
    if not s.notna().any():
        return pd.Series(np.nan, index=series.index)
    lo, hi = s.quantile(lower_q), s.quantile(upper_q)
    return pd.Series(0.5, index=series.index) if pd.isna(lo) or pd.isna(hi) or hi <= lo else ((s.clip(lo, hi) - lo) / (hi - lo)).clip(0, 1)


def _safe_map(value, mapping, default):
    if pd.isna(value):
        return default
    text = str(value).strip().lower()
    return next((score for key, score in mapping.items() if key in text), default)


def map_likert_text(value):
    return _safe_map(value, TEXT_SCORES, np.nan)


def map_education(value):
    return _safe_map(value, EDUCATION_MAP, 0.45 if pd.isna(value) else 0.50)


def map_contract(value):
    return _safe_map(value, CONTRACT_MAP, 0.60)


def mode_or_na(series: pd.Series):
    s = series.dropna().astype(str)
    return s.mode().iat[0] if not s.empty else np.nan


def normalize_role(value):
    return np.nan if pd.isna(value) else re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9]+", " ", str(value).upper().strip())).strip()


def describe_source(df: pd.DataFrame, name: str, id_col=None):
    out = {"source": name, "rows": int(len(df)), "columns": int(df.shape[1])}
    if id_col in df.columns:
        out["unique_ids"] = int(df[id_col].nunique(dropna=True))
    return out


def load_sources(data_dir: Path) -> dict[str, pd.DataFrame]:
    out = {}
    for name, (rel_path, sheet) in FILES.items():
        kwargs = {"sheet_name": sheet} if sheet else {}
        if name in {"mobility_fr_raw", "absence_fr_context_raw"}:
            kwargs["header"] = None
        frame = pd.read_excel(Path(data_dir) / rel_path, **kwargs)
        out[name] = frame if name in {"mobility_fr_raw", "absence_fr_context_raw"} else normalize_columns(frame)
    return out


def summarize_loaded_sources(sources: dict[str, pd.DataFrame]) -> pd.DataFrame:
    return pd.DataFrame([describe_source(sources[k], *SOURCE_OVERVIEW[k]) for k in SOURCE_OVERVIEW])


def parse_compensation_block(excel_path: Path, sheet_name: str, country: str, year_col_start: int = 12) -> pd.DataFrame:
    cols = ["role_benchmark", "benchmark_headcount", "benchmark_fixed_salary", "benchmark_variable_salary"]
    block = pd.read_excel(excel_path, sheet_name=sheet_name, header=None).iloc[4:, [year_col_start + i for i in range(4)]].copy()
    block.columns = cols
    block = block[block["role_benchmark"].notna()].copy()
    block[cols[1:]] = block[cols[1:]].apply(_num)
    block["country"], block["role_norm"] = country, block["role_benchmark"].map(normalize_role)
    block["benchmark_total_comp"] = block["benchmark_fixed_salary"].fillna(0) + block["benchmark_variable_salary"].fillna(0)
    return block.dropna(subset=["role_norm"]).drop_duplicates(["country", "role_norm"])


def nearest_period_lookup(base_df: pd.DataFrame, context_df: pd.DataFrame, period_col: str, keys: list[str], value_cols: list[str]) -> pd.DataFrame:
    merged = pd.merge_asof(
        base_df.sort_values(keys + ["period"]),
        context_df.sort_values(keys + [period_col]),
        left_on="period", right_on=period_col, by=keys, direction="backward",
    )
    return merged[["employee_id"] + value_cols]


def _latest_snapshot(master: pd.DataFrame) -> pd.DataFrame:
    master = master.copy()
    for c in ["period", "date_entry_caceis", "date_entry_poste"]:
        master[c] = parse_date(master[c])
    master["employee_id"] = clean_id(master["id_employee"])
    base = master.sort_values(["employee_id", "period"]).groupby("employee_id", as_index=False).tail(1).copy()
    base["tenure_caceis_years"] = ((REFERENCE_DATE - base["date_entry_caceis"]).dt.days / 365.25).clip(lower=0)
    base["tenure_position_years"] = ((REFERENCE_DATE - base["date_entry_poste"]).dt.days / 365.25).clip(lower=0)
    return base.assign(
        country=base["country_group_label_en"], contract_type=base["contract_group_label_en"],
        degree_level=base["degree_level_group_label_en"], role=base["poste_label_local"],
        entity=base["entity_label_local"], entry_reason=base["reason_entry_group_label_en"],
        snapshot_year=base["period"].dt.year,
    )


def _prepare_mobility_context(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.iloc[5:, :8].copy()
    df.columns = ["period", "effectif_moyen_cdi", "mobilite_groupe", "mobilite_interne", "taux_mob_externe", "taux_mob_interne", "taux_mobilite", "taux_turnover"]
    df["period"] = pd.to_datetime(df["period"], errors="coerce")
    df[["taux_mob_externe", "taux_mob_interne", "taux_mobilite", "taux_turnover"]] = df[["taux_mob_externe", "taux_mob_interne", "taux_mobilite", "taux_turnover"]].apply(_num)
    return df.dropna(subset=["period"]).assign(country="France")


def _prepare_absence_fr_context(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.iloc[3:, :12].copy()
    df.columns = ["period_abs", "period_tdb", "taux_abs", "absence_non_autorisee", "autres_motifs", "accident", "legal_conventionnel", "autre_legal_conventionnel", "familial", "maladie", "maternite_paternite", "total_abs"]
    df["period"] = pd.to_datetime(df["period_abs"], errors="coerce")
    df[["taux_abs", "maladie", "maternite_paternite", "total_abs"]] = df[["taux_abs", "maladie", "maternite_paternite", "total_abs"]].apply(_num)
    return df.dropna(subset=["period"]).assign(country="France")


def _prepare_absence_lu_context(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    for col in ["maladie_a_certif", "maladie_s_certif", "cns_a_certif", "cns_s_certif"]:
        df[col] = _num(df[col], 0)
    df["period"] = pd.to_datetime(df["p_riode"].astype(str) + "01", format="%Y%m%d", errors="coerce")
    df["lu_absence_hours"] = df[["maladie_a_certif", "maladie_s_certif", "cns_a_certif", "cns_s_certif"]].sum(axis=1)
    df = df.groupby("period", as_index=False).agg(lu_absence_hours=("lu_absence_hours", "sum"), lu_population=("login", "nunique"))
    df["lu_absence_hours_per_login"] = df["lu_absence_hours"] / df["lu_population"].replace(0, np.nan)
    return df.assign(country="Luxembourg")


def build_base_snapshot(master: pd.DataFrame, mobility_fr_raw: pd.DataFrame, absence_fr_context_raw: pd.DataFrame, absence_lu_context: pd.DataFrame, compensation_file: Path) -> pd.DataFrame:
    base = _latest_snapshot(master).merge(pd.DataFrame([{"country": "France", "di_inclusion_score": 0.70, "di_participation_rate": 0.26}, {"country": "Luxembourg", "di_inclusion_score": 0.64, "di_participation_rate": 0.25}]), on="country", how="left")
    mobility_fr, abs_fr, abs_lu = _prepare_mobility_context(mobility_fr_raw), _prepare_absence_fr_context(absence_fr_context_raw), _prepare_absence_lu_context(absence_lu_context)
    join_specs = [
        ("France", mobility_fr, ["taux_mob_externe", "taux_mob_interne", "taux_mobilite", "taux_turnover"]),
        ("France", abs_fr, ["taux_abs", "maladie", "maternite_paternite"]),
        ("Luxembourg", abs_lu, ["lu_absence_hours_per_login"]),
    ]
    for country, ctx, values in join_specs:
        lookup = nearest_period_lookup(base.loc[base["country"].eq(country), ["employee_id", "period", "country"]], ctx, "period", ["country"], values)
        base = base.merge(lookup, on="employee_id", how="left")
    comp = pd.concat([parse_compensation_block(compensation_file, "Compensation Data FR", "France"), parse_compensation_block(compensation_file, "Compensation Data LU", "Luxembourg")], ignore_index=True)
    base["role_norm"] = base["role"].map(normalize_role)
    return base.merge(comp[["country", "role_norm", "benchmark_headcount", "benchmark_fixed_salary", "benchmark_variable_salary", "benchmark_total_comp"]], on=["country", "role_norm"], how="left")


def prepare_eae_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if "note_de_performance" not in frame.columns:
        return pd.DataFrame(columns=["employee_id", "eae_performance_rating", "eae_records", "bu", "eae_job_label"])
    frame = frame.copy()
    frame["employee_id"], frame["note_de_performance"] = clean_id(frame["iug"]), _num(frame["note_de_performance"])
    job_label_col = next((c for c in frame.columns if "emploi" in c), None)
    agg = {"eae_performance_rating": ("note_de_performance", "mean"), "eae_records": ("note_de_performance", "count")}
    if "bu" in frame.columns:
        agg["bu"] = ("bu", mode_or_na)
    if job_label_col:
        agg["eae_job_label"] = (job_label_col, mode_or_na)
    return frame.groupby("employee_id", as_index=False).agg(**agg)


def _agg_reviews(frame: pd.DataFrame, id_col: str, status_col: str, completion_col: str, extra: dict, rename: dict) -> pd.DataFrame:
    frame = frame.copy()
    frame["employee_id"] = clean_id(frame[id_col])
    frame["status_clean"] = frame.get(status_col, pd.Series(index=frame.index)).astype(str).str.lower()
    frame[completion_col] = frame["status_clean"].str.contains("compl", na=False).astype(float)
    for col, values in extra.items():
        frame[col] = values
    return frame.groupby("employee_id", as_index=False).agg(**rename)


def build_employee_aggregates(perf: pd.DataFrame, eae: pd.DataFrame, eae_working: pd.DataFrame, train_records: pd.DataFrame, quick: pd.DataFrame, cold: pd.DataFrame, abs_df: pd.DataFrame):
    perf = perf.copy()
    perf["employee_id"], perf["note"] = clean_id(perf["iug"]), _num(perf["note"])
    perf_agg = perf.groupby("employee_id", as_index=False).agg(performance_rating=("note", "mean"), performance_records=("note", "count"))

    eae_agg = pd.concat([prepare_eae_frame(eae), prepare_eae_frame(eae_working)], ignore_index=True)
    eae_agg = eae_agg.sort_values(["employee_id", "eae_records"], ascending=[True, False]).drop_duplicates("employee_id", keep="first") if not eae_agg.empty else pd.DataFrame(columns=["employee_id"])

    train = train_records.copy()
    train["employee_id"], train["total_training_hours"], train["attended_courses"] = clean_id(train["employee_code"]), _num(train["total_training_hours"]), _num(train["attended_courses"])
    train["certification_flag"] = train.get("certifications", pd.Series(index=train.index)).astype(str).str.lower().map({"yes": 1, "oui": 1, "no": 0, "non": 0})
    train["status_clean"] = train.get("status", pd.Series(index=train.index)).astype(str).str.lower()
    train["completed_flag"], train["cancelled_flag"] = train["status_clean"].str.contains("réalis|realis|compl", na=False).astype(float), train["status_clean"].str.contains("annul", na=False).astype(float)
    train_agg = train.groupby("employee_id", as_index=False).agg(
        training_events=("employee_id", "size"), training_hours=("total_training_hours", "sum"), training_courses_sum=("attended_courses", "sum"),
        certification_rate=("certification_flag", "mean"), training_completion_rate=("completed_flag", "mean"), training_cancel_rate=("cancelled_flag", "mean"),
    )

    quick_agg = _agg_reviews(
        quick, "matricule", "statut", "quick_completed_flag",
        {
            "note_generale": _num(quick.get("note_generale")),
            "recommend_score": quick.get("je_recommanderais_cette_formation_a_un_collegue", pd.Series(index=quick.index)).map(map_likert_text),
        },
        {
            "quick_reviews": ("employee_id", "size"),
            "quick_rating_avg": ("note_generale", "mean"),
            "quick_recommend_avg": ("recommend_score", "mean"),
            "quick_completion_rate": ("quick_completed_flag", "mean"),
        },
    )

    cold = cold.copy()
    cold["employee_id"] = clean_id(cold["matricule"])
    cold["status_clean"] = cold.get("status", pd.Series(index=cold.index)).astype(str).str.lower()
    cold["cold_completed_flag"] = cold["status_clean"].str.contains("compl", na=False).astype(float)
    questions = [c for c in cold.columns if any(k in c for k in [
        "considerez_vous_que_cette_formation", "la_formation_a_t_elle_repondu_a_vos_attentes_initiales",
        "estimez_vous_que_la_formation_etait_en_adequation", "recommanderiez_vous_ce_stage_a_une_personne_exercant_le_meme_metier_que_vous",
        "utilisez_vous_les_connaissances_acquises_lors_de_la_formation",
    ])]
    for col in questions:
        cold[f"{col}_score"] = cold[col].map(map_likert_text)
    cold["cold_sentiment_row"] = cold[[c for c in cold.columns if c.endswith("_score")]].mean(axis=1)
    cold_agg = cold.groupby("employee_id", as_index=False).agg(cold_reviews=("employee_id", "size"), cold_sentiment_avg=("cold_sentiment_row", "mean"), cold_completion_rate=("cold_completed_flag", "mean"))

    abs_df = abs_df.copy()
    abs_df["employee_id"], abs_df["date_absence"] = clean_id(abs_df["employee_code"]), parse_date(abs_df["date_absence"])
    jours_ouvres = next((c for c in abs_df.columns if "jours_ouvr" in c and "absence" in c and "ables" not in c), None)
    jours_ouvrables = next((c for c in abs_df.columns if "jours_ouvrables_absence" in c), None)
    abs_df["absence_days"] = pd.concat([_num(abs_df.get(jours_ouvres, 0), 0), _num(abs_df.get(jours_ouvrables, 0), 0)], axis=1).max(axis=1)
    abs_agg = abs_df.groupby("employee_id", as_index=False).agg(absence_events=("employee_id", "size"), absence_days=("absence_days", "sum"))
    return perf_agg, eae_agg, train_agg, quick_agg, cold_agg, abs_agg


def build_analysis_df(base_snapshot: pd.DataFrame, perf_agg: pd.DataFrame, eae_agg: pd.DataFrame, train_agg: pd.DataFrame, quick_agg: pd.DataFrame, cold_agg: pd.DataFrame, abs_agg: pd.DataFrame) -> pd.DataFrame:
    df = base_snapshot.copy()
    for part in [perf_agg, eae_agg, train_agg, quick_agg, cold_agg, abs_agg]:
        df = df.merge(part, on="employee_id", how="left")
    df["performance_rating"] = df[["performance_rating", "eae_performance_rating"]].mean(axis=1, skipna=True).fillna(df["performance_rating"].median())
    for col in ["training_hours", "training_events", "training_courses_sum", "certification_rate", "absence_days", "absence_events"]:
        df[col] = _num(df.get(col))
    df["training_hours"] = df["training_hours"].clip(lower=0)
    df["training_info_available"] = df["training_hours"].notna()
    df["training_completion_rate"] = df["training_completion_rate"].fillna(df["quick_completion_rate"]).fillna(df["cold_completion_rate"])
    df["training_sentiment_score"] = (df[["quick_rating_avg"]].mean(axis=1) / 5.0).fillna(df["quick_recommend_avg"]).fillna(df["cold_sentiment_avg"])
    df["training_hours_viz"], df["absence_days"], df["absence_events"] = df["training_hours"].fillna(0) + 0.1, df["absence_days"].fillna(0), df["absence_events"].fillna(0)
    df["absence_rate"] = (df["absence_days"] / 220).clip(0, 1)
    df["presence_index"] = 1 - df["absence_rate"]
    df["training_intensity"] = (df["training_hours"] / (df["tenure_caceis_years"].replace(0, np.nan) + 1)).replace([np.inf, -np.inf], np.nan)
    context_cols = ["benchmark_fixed_salary", "benchmark_variable_salary", "benchmark_total_comp", "di_inclusion_score", "di_participation_rate", "taux_mobilite", "taux_turnover", "taux_abs", "lu_absence_hours_per_login"]
    for col in context_cols:
        df[col] = _num(df.get(col))
    df["context_mobility_score"] = minmax(df["taux_mobilite"]).fillna(0.5)
    df["context_turnover_risk"] = minmax(df["taux_turnover"]).fillna(0.5)
    df["context_absence_stress"] = minmax(df[["taux_abs", "lu_absence_hours_per_login"]].max(axis=1, skipna=True)).fillna(0.5)
    df["context_inclusion_score"] = df["di_inclusion_score"].fillna(df["di_inclusion_score"].median())
    df["context_participation_score"] = df["di_participation_rate"].fillna(df["di_participation_rate"].median())
    df["context_engagement_signal"] = (0.45 * df["context_inclusion_score"] + 0.25 * df["context_participation_score"] + 0.15 * df["context_mobility_score"] + 0.15 * (1 - df["context_absence_stress"])).clip(0, 1)
    return df


def apply_training_missing_strategy(df: pd.DataFrame, strategy: str = "median") -> pd.DataFrame:
    out = df.copy()
    training_cols = ["training_hours", "training_events", "training_courses_sum", "certification_rate", "training_completion_rate", "training_sentiment_score", "training_intensity"]
    if strategy == "drop":
        out = out.dropna(subset=training_cols).copy()
    elif strategy == "median":
        for col in training_cols:
            out[col] = _num(out[col]).fillna(_num(out[col]).median())
    elif strategy == "knn":
        base_cols = ["tenure_caceis_years", "tenure_position_years", "performance_rating", "absence_days", "benchmark_total_comp", "taux_mobilite", "taux_turnover", "di_inclusion_score", "di_participation_rate"]
        imputer_cols = [c for c in base_cols + training_cols if c in out.columns]
        imputed = pd.DataFrame(KNNImputer(n_neighbors=5, weights="distance").fit_transform(out[imputer_cols].apply(_num)), columns=imputer_cols, index=out.index)
        out[training_cols] = imputed[training_cols]
    else:
        raise ValueError("strategy must be 'drop', 'median' or 'knn'")
    out["training_hours"] = out["training_hours"].clip(lower=0)
    out["training_hours_viz"] = out["training_hours"].fillna(0) + 0.1
    out["training_intensity"] = (out["training_hours"] / (out["tenure_caceis_years"].replace(0, np.nan) + 1)).replace([np.inf, -np.inf], np.nan)
    if strategy in {"median", "knn"}:
        out["training_intensity"] = out["training_intensity"].fillna(_num(out["training_intensity"]).median())
        for col in ["training_completion_rate", "training_sentiment_score", "certification_rate"]:
            out[col] = out[col].clip(0, 1)
        out["training_events"] = out["training_events"].clip(lower=0)
    return out


def _score_training_intensity(df: pd.DataFrame, tenure_caceis_years: float, training_hours: float) -> float:
    raw = max(training_hours, 0) / (max(tenure_caceis_years, 0) + 1)
    ref = _num(df["training_intensity_log"])
    lo, hi = ref.quantile(0.01), ref.quantile(0.99)
    if pd.isna(lo) or pd.isna(hi) or hi <= lo:
        return 0.5
    return float(np.clip((np.clip(np.log1p(raw), lo, hi) - lo) / (hi - lo), 0, 1))


def compute_hcv_scores(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["education_score"], df["contract_seniority"] = df["degree_level"].map(map_education), df["contract_type"].map(map_contract)
    df["performance_score"], df["tenure_position_score"], df["tenure_caceis_score"] = (df["performance_rating"] / 5.0).clip(0, 1).fillna(0.5), minmax(df["tenure_position_years"]), minmax(df["tenure_caceis_years"])
    df["training_intensity_log"] = np.log1p(df["training_intensity"].clip(lower=0))
    df["training_intensity_score"], df["presence_score"], df["certification_score"] = minmax(df["training_intensity_log"]), df["presence_index"].clip(0, 1).fillna(1), df["certification_rate"].clip(0, 1).fillna(0)
    role_share = df["role"].fillna("Unknown").map(df["role"].fillna("Unknown").value_counts() / len(df))
    df["role_scarcity_score"], df["benchmark_comp_score"] = minmax((1 / role_share.replace(0, np.nan))).fillna(0.5), minmax(df["benchmark_total_comp"]).fillna(df["contract_seniority"])
    signals = {
        "completion_signal": df["training_completion_rate"].clip(0, 1).fillna(0),
        "sentiment_signal": df["training_sentiment_score"].clip(0, 1).fillna(0.5),
        "learning_depth_signal": df["training_intensity_score"].clip(0, 1).fillna(0),
        "mobility_signal": df["context_mobility_score"].clip(0, 1).fillna(0.5),
        "inclusion_signal": df["context_inclusion_score"].clip(0, 1).fillna(0.5),
        "participation_signal": df["context_participation_score"].clip(0, 1).fillna(0.5),
        "absence_signal": (1 - df["presence_score"]).clip(0, 1).fillna(0),
    }
    for k, v in signals.items():
        df[k] = v
    df["Q_qualification"] = (0.45 * df["education_score"] + 0.40 * df["performance_score"] + 0.15 * df["certification_score"]).clip(0, 1)
    df["B_behavioural"] = (0.20 * df["completion_signal"] + 0.45 * df["presence_score"] + 0.35 * df["mobility_signal"]).clip(0, 1)
    df["R_rarity"] = (0.50 * df["role_scarcity_score"] + 0.35 * df["benchmark_comp_score"] + 0.15 * df["contract_seniority"]).clip(0, 1)
    df["E_engagement"] = (0.20 * df["sentiment_signal"] + 0.45 * df["inclusion_signal"] + 0.35 * df["participation_signal"]).clip(0, 1)
    df["attrition_risk"] = (0.35 * (1 - df["tenure_caceis_score"]) + 0.30 * df["absence_signal"] + 0.35 * df["context_turnover_risk"]).clip(0, 1)
    df["succession_score"] = (0.45 * df["tenure_position_score"] + 0.55 * df["learning_depth_signal"]).clip(0, 1)
    df["hcv_raw"] = ((0.45 * df["Q_qualification"] + 0.25 * df["B_behavioural"] + 0.30 * df["R_rarity"]) * (0.70 + 0.60 * df["E_engagement"]) * (1 - 0.70 * df["attrition_risk"]) + 0.60 * df["succession_score"])
    df["HCV"] = (100 * minmax(df["hcv_raw"])).clip(0, 100)
    for col in ["Q_qualification", "B_behavioural", "R_rarity", "E_engagement", "attrition_risk", "succession_score", "HCV"]:
        df[col] = df[col].fillna(df[col].median())
    q1, q2, q3 = df["HCV"].quantile([0.25, 0.50, 0.75])
    df["HCV_segment"] = df["HCV"].map(lambda s: "Elite" if s >= q3 else "High" if s >= q2 else "Medium" if s >= q1 else "Development Potential")
    return df


def build_summary(df: pd.DataFrame) -> dict:
    return {
        "employees": int(df["employee_id"].nunique()), "countries": int(df["country"].nunique(dropna=True)), "roles": int(df["role"].nunique(dropna=True)),
        "avg_hcv": round(df["HCV"].mean(), 2), "median_hcv": round(df["HCV"].median(), 2), "avg_attrition_risk": round(df["attrition_risk"].mean(), 3),
        "avg_training_hours": round(df["training_hours"].mean(), 2), "comp_benchmark_coverage": round(df["benchmark_total_comp"].notna().mean(), 3),
        "context_inclusion_coverage": round(df["di_inclusion_score"].notna().mean(), 3), "context_mobility_coverage": round(df["taux_mobilite"].notna().mean(), 3),
        "context_absence_coverage": round(df[["taux_abs", "lu_absence_hours_per_login"]].notna().any(axis=1).mean(), 3),
        "performance_coverage": round(df["performance_rating"].notna().mean(), 3), "absence_coverage": round((df["absence_events"] > 0).mean(), 3),
        "training_coverage": round((df["training_events"] > 0).mean(), 3),
    }


def build_core_kpis(df: pd.DataFrame) -> pd.DataFrame:
    high_elite = df["HCV_segment"].isin(["High", "Elite"])
    rows = [
        ("HCV median", round(df["HCV"].median(), 2), "Niveau typique de valeur humaine dans l'organisation."),
        ("Part High + Elite", round(100 * high_elite.mean(), 1), "Poids des profils les plus créateurs de valeur."),
        ("Talents critiques à risque", round(100 * (high_elite & df["attrition_risk"].gt(0.50)).mean(), 1), "Part des profils à forte valeur déjà exposés au risque de départ."),
        ("Engagement moyen (E)", round(df["E_engagement"].mean(), 3), "Mesure la qualité du lien entre capital humain et engagement."),
        ("Rareté moyenne (R)", round(df["R_rarity"].mean(), 3), "Indique à quel point les profils sont difficiles à remplacer sur le marché."),
    ]
    return pd.DataFrame(rows, columns=["kpi", "value", "why_it_matters"])


def compare_training_strategies(df_raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for strategy, label in [("drop", "Observé uniquement"), ("median", "Médiane imputée"), ("knn", "KNN imputée")]:
        scored = compute_hcv_scores(apply_training_missing_strategy(df_raw, strategy))
        rows.append({
            "strategie": label, "population": int(scored["employee_id"].nunique()), "hcv_median": round(scored["HCV"].median(), 2),
            "hcv_mean": round(scored["HCV"].mean(), 2), "part_high_elite_pct": round(100 * scored["HCV_segment"].isin(["High", "Elite"]).mean(), 1),
            "engagement_mean": round(scored["E_engagement"].mean(), 3), "training_hours_median": round(scored["training_hours"].median(), 2),
        })
    return pd.DataFrame(rows)


def build_segment_kpis(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("HCV_segment", as_index=False).agg(
        employees=("employee_id", "count"), avg_hcv=("HCV", "mean"), avg_q=("Q_qualification", "mean"),
        avg_b=("B_behavioural", "mean"), avg_r=("R_rarity", "mean"), avg_e=("E_engagement", "mean"),
        avg_attrition=("attrition_risk", "mean"), avg_tenure=("tenure_caceis_years", "mean"),
        avg_training_hours=("training_hours", "mean"),
    ).sort_values("avg_hcv", ascending=False)


def train_hcv_models(df: pd.DataFrame) -> dict:
    model_df = df[MODEL_FEATURES_NUM + MODEL_FEATURES_CAT + ["HCV", "HCV_segment"]].dropna(subset=["HCV", "HCV_segment"]).copy()
    X, y_reg, y_clf = model_df[MODEL_FEATURES_NUM + MODEL_FEATURES_CAT], model_df["HCV"], model_df["HCV_segment"]
    preprocessor = ColumnTransformer([
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), MODEL_FEATURES_NUM),
        ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), MODEL_FEATURES_CAT),
    ])
    X_train, X_test, y_reg_train, y_reg_test = train_test_split(X, y_reg, test_size=0.2, random_state=42)
    _, _, y_clf_train, y_clf_test = train_test_split(X, y_clf, test_size=0.2, random_state=42)
    reg_model = Pipeline([("preprocessor", preprocessor), ("model", RandomForestRegressor(n_estimators=250, max_depth=12, random_state=42, n_jobs=-1))])
    clf_model = Pipeline([("preprocessor", preprocessor), ("model", RandomForestClassifier(n_estimators=250, max_depth=12, random_state=42, n_jobs=-1))])
    reg_model.fit(X_train, y_reg_train)
    clf_model.fit(X_train, y_clf_train)
    reg_pred, clf_pred = reg_model.predict(X_test), clf_model.predict(X_test)
    return {
        "reg_model": reg_model,
        "clf_model": clf_model,
        "model_metrics": pd.DataFrame([
            {"model": "HCV regressor", "r2": r2_score(y_reg_test, reg_pred), "rmse": mean_squared_error(y_reg_test, reg_pred) ** 0.5, "mae": mean_absolute_error(y_reg_test, reg_pred)},
            {"model": "HCV segment classifier", "accuracy": accuracy_score(y_clf_test, clf_pred)},
        ]),
    }


def feature_family(name: str) -> str:
    for prefix, label in [
        ("num__tenure", "Anciennete"), ("num__training", "Formation"), ("num__absence", "Absenteisme"), ("num__performance", "Performance"),
        ("num__benchmark", "Marche / contrat"), ("num__contract", "Marche / contrat"), ("num__role_scarcity", "Capital humain"),
        ("num__education", "Capital humain"), ("num__certification", "Capital humain"), ("cat__country", "Pays"), ("cat__entity", "Entite"),
        ("cat__role", "Role"), ("cat__degree_level", "Diplome"), ("cat__contract_type", "Type de contrat"), ("cat__bu", "BU"),
    ]:
        if name.startswith(prefix):
            return label
    return "Autres"


def build_feature_importance(reg_model: Pipeline) -> tuple[pd.DataFrame, pd.DataFrame]:
    importance = pd.DataFrame({"feature": reg_model.named_steps["preprocessor"].get_feature_names_out(), "importance": reg_model.named_steps["model"].feature_importances_}).sort_values("importance", ascending=False)
    importance["family"] = importance["feature"].map(feature_family)
    return importance, importance.groupby("family", as_index=False)["importance"].sum().sort_values("importance", ascending=False)


def score_new_employee(df: pd.DataFrame, reg_model: Pipeline, clf_model: Pipeline, tenure_caceis_years, tenure_position_years, performance_rating, training_hours, training_events, training_completion_rate, training_sentiment_score, absence_days, certification_rate=0, country=None, contract_type=None, degree_level=None, role=None, entity=None, bu=None) -> pd.Series:
    defaults = {k: (df[k].mode().iat[0] if k != "bu" or ("bu" in df.columns and df["bu"].notna().any()) else np.nan) for k in ["country", "contract_type", "degree_level", "role", "entity", "bu"]}
    chosen_role = role or defaults["role"]
    role_score = df.loc[df["role"].eq(chosen_role), "role_scarcity_score"].median()
    row = pd.DataFrame([{
        "tenure_caceis_years": tenure_caceis_years, "tenure_position_years": tenure_position_years, "performance_rating": performance_rating,
        "training_intensity_score": _score_training_intensity(df, tenure_caceis_years, training_hours), "training_completion_rate": training_completion_rate,
        "absence_days": absence_days, "absence_rate": min(absence_days / 220, 1), "education_score": map_education(degree_level or defaults["degree_level"]),
        "contract_seniority": map_contract(contract_type or defaults["contract_type"]), "role_scarcity_score": role_score if pd.notna(role_score) else df["role_scarcity_score"].median(),
        "certification_rate": certification_rate, "country": country or defaults["country"], "contract_type": contract_type or defaults["contract_type"],
        "degree_level": degree_level or defaults["degree_level"], "role": chosen_role, "entity": entity or defaults["entity"], "bu": bu or defaults["bu"],
    }])
    return pd.Series({"predicted_hcv": round(float(reg_model.predict(row)[0]), 2), "predicted_segment": clf_model.predict(row)[0]})


def export_outputs(df: pd.DataFrame, output_dir: Path, summary: dict) -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    dataset_path, metadata_path = output_dir / "caceis_hcv_dataset.csv", output_dir / "caceis_hcv_metadata.json"
    df[EXPORT_COLS].copy().to_csv(dataset_path, index=False)
    metadata = {
        "execution_date": str(pd.Timestamp.now()), "reference_date": str(REFERENCE_DATE.date()), "population_size": int(df["employee_id"].nunique()),
        "hcv_formula": "(0.45*Q + 0.25*B + 0.30*R) * (0.70 + 0.60*E) * (1 - 0.70*attrition_risk) + 0.60*succession_score",
        "components": COMPONENT_LABELS, "summary": summary, "segment_distribution": df["HCV_segment"].value_counts().to_dict(),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return dataset_path, metadata_path
