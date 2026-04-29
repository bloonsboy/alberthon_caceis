# CACEIS - Human Capital Value

<<<<<<< HEAD
Ce projet regroupe la pipeline d'estimation de la **valeur humaine au travail** pour CACEIS, ainsi qu'un notebook séparé d'analyse statistique du dataset final.
=======
Ce projet regroupe la pipeline d'estimation de la **valeur humaine au travail** pour le cas CACEIS / Alberthon, ainsi qu'un notebook séparé d'analyse statistique du dataset final.
>>>>>>> 59b7bda (Add CACEIS HCV pipeline, stats notebook, and provided data)

## Objectif

L'objectif est de :
- nettoyer et intégrer les différentes sources CACEIS
- construire un dataset analytique salarié
- calculer un score `HCV` (Human Capital Value)
- produire des KPI, graphiques et premières lectures métier
- proposer une première lecture prédictive du score et du segment HCV

## Structure du projet

- [caceis_hcv_pipeline.ipynb](./caceis_hcv_pipeline.ipynb)
  Notebook principal : pipeline, score HCV, KPI, visualisations, modèle et exports.

- [caceis_hcv_stats.ipynb](./caceis_hcv_stats.ipynb)
  Notebook complémentaire : statistiques descriptives sur le dataset final déjà construit.

- [human_capital_pipeline.py](./human_capital_pipeline.py)
  Module Python contenant la logique technique :
  chargement des sources, nettoyage, agrégations, construction du dataframe final, calcul du score, modèle et exports.

- [build_stats_notebook.py](./build_stats_notebook.py)
  Script utilitaire pour régénérer le notebook statistique.

- [outputs_hcv_notebook/caceis_hcv_dataset.csv](./outputs_hcv_notebook/caceis_hcv_dataset.csv)
  Dataset final exporté.

- [outputs_hcv_notebook/caceis_hcv_metadata.json](./outputs_hcv_notebook/caceis_hcv_metadata.json)
  Métadonnées d'exécution, formule et synthèse.

## Sources utilisées

Les données proviennent principalement du dossier :
- `caceis-data-provided/Sujet Alberthon`

Les grandes familles mobilisées sont :
- RH master
- performance
- EAE
- formation
- quick reviews / cold reviews
- absentéisme
- contextes France / Luxembourg
- benchmark compensation France / Luxembourg

## Logique méthodologique

Le score `HCV` repose sur 6 briques :
- `Q_qualification`
- `B_behavioural`
- `R_rarity`
- `E_engagement`
- `attrition_risk`
- `succession_score`

Le score final combine :
- qualification
- comportement
- rareté marché
- engagement
- risque d'attrition
- potentiel de succession

## Traitement des valeurs manquantes

Le notebook principal compare plusieurs approches pour les variables de formation manquantes :
- `Observé uniquement`
  suppression des lignes incomplètes sur les variables formation

- `Médiane imputée`
  remplacement des valeurs manquantes par la médiane

- `KNN imputée`
  imputation par voisins proches (`KNNImputer`)

La version principale actuelle du notebook utilise l'approche :
- `KNN imputée`

## Contenu du notebook principal

Le notebook [caceis_hcv_pipeline.ipynb](./caceis_hcv_pipeline.ipynb) contient :
- hypothèses de mapping méthodologique
- traçabilité des sources
- construction de la base RH de référence
- agrégats analytiques
- construction du dataframe final
- calcul du score HCV
- KPI business
- graphiques Plotly
- modèle d'estimation du HCV et du segment
- exemple de scoring d'un nouvel employé
- exports finaux

## Contenu du notebook statistique

Le notebook [caceis_hcv_stats.ipynb](./caceis_hcv_stats.ipynb) contient :
- vue d'ensemble du dataset final
- KPI descriptifs
- répartition des niveaux de diplôme par pays
- HCV moyen par pays et par diplôme
- segments HCV par pays
- comparaison des composantes du score par pays
- lectures complémentaires par contrat et par rôle

## Exécution

Depuis le dossier du projet :

```bash
jupyter notebook
```

Ordre recommandé :
1. ouvrir `caceis_hcv_pipeline.ipynb`
2. exécuter le notebook de haut en bas
3. vérifier les exports dans `outputs_hcv_notebook/`
4. ouvrir ensuite `caceis_hcv_stats.ipynb` pour la lecture descriptive

## Points d'attention

- les comparaisons entre pays doivent être interprétées avec prudence, car la couverture de certaines variables diffère selon les pays
- la France et le Luxembourg disposent d'un benchmark marché plus riche que plusieurs autres pays
- le score HCV reste un score composite construit à partir de proxies
- les importances du modèle reflètent la structure du score construit, pas une causalité directe

## Fichiers de contexte utiles

- [Caceis - Alberthon.pdf](./Caceis%20-%20Alberthon.pdf)
- [20260416 - Alberthon Kickoff.pdf](./20260416%20-%20Alberthon%20Kickoff.pdf)
- [DOCUMENT_ANALYSE_FICHIERS_COMPLET.md](./DOCUMENT_ANALYSE_FICHIERS_COMPLET.md)

## Résultat attendu

Le projet fournit :
- une pipeline défendable méthodologiquement
- un dataset final exploitable
- des KPI business lisibles
- des visualisations pour la restitution
- une base d'analyse pour la soutenance et la réflexion IA
