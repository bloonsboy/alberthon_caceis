import json
from pathlib import Path


def md(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": [line + "\n" for line in text.strip("\n").split("\n")]}


def code(text: str, hidden: bool = False) -> dict:
    metadata = {}
    if hidden:
        metadata = {"jupyter": {"source_hidden": True}, "collapsed": True}
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": metadata,
        "outputs": [],
        "source": [line + "\n" for line in text.strip("\n").split("\n")],
    }


cells = [
    md(
        """
        # CACEIS HCV - Statistiques descriptives

        Ce notebook complète la pipeline HCV avec une lecture statistique du dataset final déjà construit.
        L'objectif est d'explorer la population, les répartitions par pays et diplôme, ainsi que les grands patterns RH.
        """
    ),
    md(
        """
        ## Lecture du notebook

        Ce notebook est organisé en 4 temps :
        1. chargement du dataset final
        2. KPI descriptifs
        3. répartitions par pays / diplôme / segment
        4. patterns utiles pour la restitution métier
        """
    ),
    code(
        """
        from pathlib import Path

        import numpy as np
        import pandas as pd
        import plotly.express as px
        import plotly.graph_objects as go
        import plotly.io as pio

        pd.set_option("display.max_columns", 120)
        pd.set_option("display.float_format", lambda x: f"{x:,.3f}")
        pio.renderers.default = "notebook_connected"
        """,
        hidden=True,
    ),
    code(
        """
        BASE_DIR = Path.cwd()
        DATASET_PATH = BASE_DIR / "outputs_hcv_notebook" / "caceis_hcv_dataset.csv"

        df = pd.read_csv(DATASET_PATH)
        print("Dataset :", DATASET_PATH)
        print("Lignes  :", len(df))
        print("Colonnes:", df.shape[1])
        """,
        hidden=True,
    ),
    md("## 1. Vue d'ensemble"),
    code(
        """
        overview = pd.DataFrame(
            {
                "indicateur": [
                    "Population totale",
                    "Nombre de pays",
                    "Nombre d'entités",
                    "Nombre de rôles",
                    "HCV moyen",
                    "HCV médian",
                ],
                "valeur": [
                    int(df["employee_id"].nunique()),
                    int(df["country"].nunique(dropna=True)),
                    int(df["entity"].nunique(dropna=True)),
                    int(df["role"].nunique(dropna=True)),
                    round(df["HCV"].mean(), 2),
                    round(df["HCV"].median(), 2),
                ],
            }
        )
        overview
        """
    ),
    md("## 2. KPI descriptifs"),
    code(
        """
        high_elite = df["HCV_segment"].isin(["High", "Elite"])
        kpis = pd.DataFrame(
            [
                {"KPI": "Part High + Elite", "Valeur": round(100 * high_elite.mean(), 1), "Lecture": "Poids des profils les plus créateurs de valeur."},
                {"KPI": "Part Development Potential", "Valeur": round(100 * df["HCV_segment"].eq("Development Potential").mean(), 1), "Lecture": "Part de la population à développer en priorité."},
                {"KPI": "Ancienneté CACEIS médiane", "Valeur": round(df["tenure_caceis_years"].median(), 2), "Lecture": "Niveau de maturité interne typique."},
                {"KPI": "Heures de formation médianes", "Valeur": round(df["training_hours"].median(), 2), "Lecture": "Investissement formation typique par collaborateur."},
                {"KPI": "Risque d'attrition moyen", "Valeur": round(df["attrition_risk"].mean(), 3), "Lecture": "Pression moyenne de risque sur la population."},
            ]
        )
        kpis
        """
    ),
    md("## 3. Répartition diplôme par pays"),
    code(
        """
        degree_country = (
            df.groupby(["country", "degree_level"], as_index=False)
            .agg(employees=("employee_id", "count"))
        )
        degree_country["share_in_country"] = (
            degree_country["employees"]
            / degree_country.groupby("country")["employees"].transform("sum")
        )
        degree_country.sort_values(["country", "employees"], ascending=[True, False]).head(20)
        """
    ),
    code(
        """
        top_countries = df["country"].value_counts().head(10).index
        heatmap_df = (
            degree_country[degree_country["country"].isin(top_countries)]
            .pivot(index="degree_level", columns="country", values="share_in_country")
            .fillna(0)
        )

        fig = px.imshow(
            heatmap_df,
            text_auto=".0%",
            aspect="auto",
            color_continuous_scale="Blues",
            title="Répartition des niveaux de diplôme par pays (part dans le pays)",
        )
        fig.update_layout(template="plotly_white")
        fig.show()
        print("Lecture: cette heatmap montre la structure de diplôme de chaque pays. Elle aide à voir si un pays concentre surtout des profils très qualifiés, des profils intermédiaires, ou une structure plus mixte.")
        """
    ),
    md("## 4. HCV par pays et par diplôme"),
    code(
        """
        hcv_country_degree = (
            df.groupby(["country", "degree_level"], as_index=False)
            .agg(employees=("employee_id", "count"), avg_hcv=("HCV", "mean"))
            .query("employees >= 15")
        )
        hcv_country_degree.sort_values("avg_hcv", ascending=False).head(20)
        """
    ),
    code(
        """
        focus = hcv_country_degree[hcv_country_degree["country"].isin(top_countries)]
        fig = px.scatter(
            focus,
            x="country",
            y="avg_hcv",
            size="employees",
            color="degree_level",
            title="HCV moyen par pays et niveau de diplôme",
            hover_data=["employees"],
        )
        fig.update_layout(template="plotly_white")
        fig.show()
        print("Lecture: ce graphe montre comment le HCV varie selon le niveau de diplôme à l'intérieur de chaque pays. Il permet de distinguer un effet pays d'un effet qualification.")
        """
    ),
    md("## 5. Segments HCV par pays"),
    code(
        """
        segment_country = (
            df.groupby(["country", "HCV_segment"], as_index=False)
            .agg(employees=("employee_id", "count"))
        )
        segment_country["share_in_country"] = (
            segment_country["employees"]
            / segment_country.groupby("country")["employees"].transform("sum")
        )
        segment_country.head()
        """
    ),
    code(
        """
        fig = px.bar(
            segment_country[segment_country["country"].isin(top_countries)],
            x="country",
            y="share_in_country",
            color="HCV_segment",
            barmode="stack",
            title="Structure des segments HCV par pays",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(template="plotly_white", yaxis_tickformat=".0%")
        fig.show()
        print("Lecture: ce graphe compare la composition des pays par segment HCV. Il permet de voir quels pays concentrent davantage de profils Elite / High ou, au contraire, davantage de Development Potential.")
        """
    ),
    md("## 6. Pays les plus hauts / bas sur les composantes"),
    code(
        """
        component_country = (
            df.groupby("country", as_index=False)
            .agg(
                employees=("employee_id", "count"),
                hcv=("HCV", "mean"),
                q=("Q_qualification", "mean"),
                b=("B_behavioural", "mean"),
                r=("R_rarity", "mean"),
                e=("E_engagement", "mean"),
                attr=("attrition_risk", "mean"),
                succ=("succession_score", "mean"),
            )
            .query("employees >= 30")
            .sort_values("hcv", ascending=False)
        )
        component_country
        """
    ),
    code(
        """
        component_plot = component_country.melt(
            id_vars=["country", "employees"],
            value_vars=["q", "b", "r", "e", "attr", "succ"],
            var_name="component",
            value_name="score",
        )
        fig = px.line(
            component_plot[component_plot["country"].isin(top_countries)],
            x="component",
            y="score",
            color="country",
            markers=True,
            title="Profil des composantes HCV par pays",
        )
        fig.update_layout(template="plotly_white")
        fig.show()
        print("Lecture: cette vue compare le profil des pays sur les briques du score. Elle aide à expliquer pourquoi un pays est plus haut ou plus bas en HCV moyen.")
        """
    ),
    md("## 7. Autres angles utiles"),
    code(
        """
        by_contract = (
            df.groupby("contract_type", as_index=False)
            .agg(employees=("employee_id", "count"), avg_hcv=("HCV", "mean"))
            .query("employees >= 20")
            .sort_values("avg_hcv", ascending=False)
        )
        by_contract
        """
    ),
    code(
        """
        top_roles = (
            df.groupby("role", as_index=False)
            .agg(employees=("employee_id", "count"), avg_hcv=("HCV", "mean"))
            .query("employees >= 20")
            .sort_values("avg_hcv", ascending=False)
            .head(15)
        )
        fig = px.bar(
            top_roles.sort_values("avg_hcv"),
            x="avg_hcv",
            y="role",
            color="employees",
            orientation="h",
            title="Top 15 rôles par HCV moyen",
            color_continuous_scale="Tealgrn",
        )
        fig.update_layout(template="plotly_white")
        fig.show()
        print("Lecture: ce classement identifie les rôles les plus valorisés en moyenne parmi les rôles suffisamment représentés. Il permet de repérer les métiers les plus critiques ou les plus différenciants.")
        """
    ),
    md(
        """
        ## 8. Pistes de lecture métier

        Quelques questions que ce notebook aide à traiter :
        - certains pays ont-ils une structure de diplôme différente ?
        - les écarts de HCV viennent-ils surtout du pays, du diplôme, du contrat ou du rôle ?
        - la structure des segments HCV est-elle homogène selon les zones géographiques ?
        - quelles composantes expliquent le mieux les écarts entre pays ?
        """
    ),
]

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.9"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

output_path = Path(__file__).with_name("caceis_hcv_stats.ipynb")
output_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
print(output_path)
