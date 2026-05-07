# CACEIS - Human Capital Value

Ce dépôt contient la pipeline et les artefacts pour l'analyse _Human Capital Value (HCV)_ réalisée pour CACEIS.

Important : les notebooks et l'application Streamlit attendent des données locales. Créez et placez vos fichiers de données dans le dossier `data/` (voir section « Structure »).

**Nouveau rangement**

Le projet a été réorganisé pour être plus lisible :

- `docs/` : documentation et PDF (présentation, supports de réunion)
- `src/` : code Python (scripts et modules)
- `notebooks/` : notebooks Jupyter pour la présentation et l'analyse
- `data/` : dossier de données (vide par défaut — à remplir localement)

Les fichiers originaux ont été déplacés vers ces dossiers :

- PDFs → `docs/`
- `.py` → `src/`
- `.ipynb` → `notebooks/`
- exports (ancien `outputs_hcv_notebook/`) → `data/outputs_hcv_notebook/`

Le fichier de documentation d'analyse détaillée `DOCUMENT_ANALYSE_FICHIERS_COMPLET.md` a été supprimé conformément à la demande.

## Instructions d'utilisation

- Placer vos jeux de données locaux dans `data/` avant d'exécuter les notebooks ou `streamlit`.
- Les notebooks et `app_streamlit.py` chargent les données depuis des chemins relatifs `data/` — adaptez les chemins si nécessaire.

Exemples rapides :

Jupyter:

```bash
jupyter notebook
```

Streamlit (depuis la racine du projet) :

```bash
pip install -r requirements_app.txt
streamlit run src/app_streamlit.py
```

## Points pratiques

- `data/` est ignoré par Git (voir `.gitignore`). Ne poussez pas de données sensibles.
- Le dossier `data/` contient un sous-dossier `outputs_hcv_notebook/` où sont stockés les CSV/JSON d'export.

## Besoin d'aide

Si tu veux, je peux :

- vérifier et adapter les chemins d'import dans les notebooks (`notebooks/`) et dans `src/app_streamlit.py` pour utiliser `data/` directement;
- ajouter un petit script `src/00_setup_data.py` qui vérifie la présence des fichiers attendus et affiche des messages d'erreur clairs.

---

Fait : réorganisation initiale des fichiers et ajout d'un squelette `data/` (à remplir localement).
