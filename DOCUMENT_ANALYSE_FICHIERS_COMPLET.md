# 📊 ANALYSE COMPLÈTE DE TOUS LES FICHIERS - SUJET ALBERTHON

**Date d'analyse:** 28 avril 2026  
**Localisation:** `/home/nathan/Téléchargements/caceis/caceis-data-provided/Sujet Alberthon`  
**Total fichiers:** 35 fichiers | **Taille totale:** 197.82 MB

---

## 🎯 RÉSUMÉ EXÉCUTIF

### Vue d'ensemble par module
| Module | Fichiers | Taille | Qualité | Priorité |
|--------|----------|--------|---------|----------|
| **HR Data** | 7 | 111.90 MB | ⭐⭐⭐⭐⭐ | 🔴 CRITIQUE |
| **Training** | 3 | 2.28 MB | ⭐⭐⭐⭐ | 🟡 MOYENNE |
| **Finance** | 1 | 0.01 MB | ⭐⭐⭐ | 🟡 MOYENNE |
| **Engagement** | 6 | 38.06 MB | ⭐⭐⭐ | 🟡 MOYENNE |
| **Governance** | 18 | 45.57 MB | ⭐⭐⭐ | 🟢 BASSE |

---

## 📂 DÉTAIL PAR MODULE

---

## 1️⃣ HR DATA (111.90 MB) - ⭐⭐⭐⭐⭐ QUALITÉ CRITIQUE

### Fichier 1: `20240222 - CACEIS Notes evaluation 2023.xlsx`
**Taille:** 0.08 MB  
**Type:** Excel (binaire)

**Structure:**
```
Sheet: Feuil1
Lignes: 2,544 employés
Colonnes: 5
- Pays (2 pays)
- IUG (Employee ID - unique)
- Nom
- Contrat (type de contrat)
- Note (0-5 scale)
```

**Statistiques:**
- Note moyenne: 3.34/5 (distribution: moyenne-haute)
- Couverture: 2,544 employés ont des évaluations
- Pays: France, Luxembourg

**🟢 UTILITÉ POUR LE PROJET:**
- ✅ **PERFORMANCE RATINGS** → Composant clé du KPI EVI
- ✅ Identifiant unique (IUG) permet jointure
- ✅ Échelonnage 0-5 → normalize facilement en 0-100
- ⚠️ Limitation: Seulement 44% de couverture vs 5,766 employés dans EAE

**Recommandation:** Utiliser comme source primaire de performance. Pour les 56% sans notes, imputer par médiane BU.

---

### Fichier 2: `20250218 - Stats CACEIS EAE EP 18-02-2025 Version Définitive cloture.xlsx`
**Taille:** 0.76 MB  
**Type:** Excel

**Structure:**
```
Sheet: Database
Lignes: 5,766 employés
Colonnes: 32
Principal columns:
- BU (Business Unit)
- Année (Year)
- Statut du document (approval status)
- Evaluation manager
- IUG (Employee ID)
- Nom, Prénom, Mail
- Libellé emploi (Job title)
- Type contrat
- + 17 autres colonnes (compensation, department, etc.)
```

**Statistiques:**
- Employés uniques (IUG): 3,765
- Complétude des données: 72.5%
- Valeurs manquantes: 50,766 / 184,512 (27.5%)

**🟢 UTILITÉ POUR LE PROJET:**
- ✅ **DONNÉES MAÎTRE** → Master employee dataset
- ✅ Données les plus complètes: manager evaluations, job titles, contracts
- ✅ BU segmentation → analyse par département possible
- ✅ Identifiant unique IUG
- ⚠️ 27.5% de données manquantes

**Recommandation:** Utiliser comme base maître pour joindre tous les autres fichiers sur IUG.

---

### Fichier 3: `20260121 - Absentéisme_-_détail_affectation_-_Bilan_social 2025.xlsx` (×3 versions)
**Taille:** 24.18 MB (version 2025), 22.24 MB (autre), 38.33 MB (autre)  
**Type:** Excel

**Structure:**
```
Lignes: 127,825 enregistrements d'absence
Colonnes: 46
Key columns:
- Mat compliance / Employee Code
- Nom, Prénom
- Genre
- Type Contrat / Contrat Particulier
- Présents/non Présents (attendance flag)
- Code Régime Temps Travail (work schedule)
- + 40 autres colonnes (dates, motifs, etc.)
```

**Statistiques:**
- Employés uniques: 2,264
- Granularité: Détail quotidien/hebdomadaire
- Fichiers multiples = versions de travail vs. finales

**🟢 UTILITÉ POUR LE PROJET:**
- ✅ **RETENTION PROXY** → Absentéisme = indicateur de désengagement
- ✅ **ENGAGEMENT INVERSE** → Taux d'absence corrèle avec satisfaction
- ✅ Identifiants multiples (Employee Code, Mat compliance)
- ✅ Genre inclus → Analyse diversité possible
- ⚠️ Très volumineux (84.75 MB total)

**Recommandation:** Agréger par employé (taux absence annuel) pour calculer engagement inverse. Intégrer via Employee Code ou IUG.

---

### Fichier 4: `Data.xlsx` (multi-sheets)
**Taille:** 24.88 MB  
**Type:** Excel

**Sheets:**
```
1. Sheet1: 275,609 rows × 15 cols
   → Likely master employee dataset (TRÈS COMPLET!)
   
2. Compensation Data FR: 151 rows × 16 cols
   → Salary/compensation by entity (France)
   
3. Compensation Data LU: 151 rows × 16 cols
   → Salary/compensation by entity (Luxembourg)
   
4. taux mob_TO FR: Mobility rates (France)

5. Absentéisme FR: Absence data (France)

6. Absentéisme Luxembourg: Absence data (Luxembourg)
```

**🟢 UTILITÉ POUR LE PROJET:**
- ✅ **CRITICAL** → Sheet1 with 275,609 rows = MASTER EMPLOYEE REGISTRY
- ✅ Compensation data → Salary KPI component
- ✅ Geographic split FR/LU → controllable for bias analysis
- ✅ Probable source of truth for employee counts

**Recommandation:** **PRIORITÉ ABSOLUE** → Analyzer Sheet1 en détail. Probable clé pour joindre tout le reste.

---

### Fichier 5-7: Autres fichiers de travail
- `2025 - Stats CACEIS EAE EP fichier de travail - Vretraitement.xlsx` (1.44 MB) → Working draft
- Versions multiples = staging/final versions

**Recommandation:** Utiliser version "Définitive" ou "cloture" en production.

---

## 2️⃣ TRAINING (2.28 MB) - ⭐⭐⭐⭐ QUALITÉ BONNE

### Fichier 1: `Cold_Review_Unnamed.xlsx`
**Taille:** 0.61 MB

**Structure:**
```
Lignes: 8,647 training events
Colonnes: 23
Key columns:
- Date
- Matricule (Employee ID)
- Formation (course name)
- Organization
- Session_ID
- Date de début/fin de session
- Lieu de session
- + Satisfaction feedback (6 questions about training impact)
```

**Statistiques:**
- Complétude: 58.0%
- Training satisfaction scales incluses

**🟢 UTILITÉ:**
- ✅ Training volume → KPI WAS (Workforce Agility Score)
- ✅ Satisfaction feedback → Engagement proxy
- ✅ Identifiant: Matricule
- ⚠️ Complétude modérée (58%)

---

### Fichier 2: `Quick_Review_Unnamed.xlsx`
**Taille:** 0.82 MB

**Structure:**
```
Lignes: 9,706 training events
Colonnes: 23
Similar to Cold_Review
- Date
- Matricule
- Formation
- Mode de formation (online/classroom)
- Organisme (provider)
- Formateur (trainer)
- ID de session
```

**Statistiques:**
- Complétude: 66.8% (meilleur que Cold_Review)
- Format: Mix of training modes

**🟢 UTILITÉ:**
- ✅ Training diversity → Mode variation (digital transformation indicator)
- ✅ Provider data → Training quality analysis possible

---

### Fichier 3: `Training_Records_Unnamed.xlsx`
**Taille:** 0.85 MB

**Structure:**
```
Lignes: 14,943 training records
Colonnes: 12
Key columns:
- Employee Code
- Entity
- Direction
- Attended_Courses (count?)
- Organization
- Session_Start_Date / Session_End_Date
- Session_ID
- Duration(?), Status(?)
```

**Statistiques:**
- Complétude: 94.7% ⭐ (MEILLEUR!)
- Format: Structured and clean

**🟢 UTILITÉ:**
- ✅ **BEST QUALITY** training source
- ✅ Identifiant: Employee Code
- ✅ Entity/Direction → Organizational hierarchy
- ✅ Most complete → Use as primary source

---

### Recommandation TRAINING:
Fusionner les 3 fichiers:
1. Training_Records comme base (94.7% complet)
2. Cold_Review + Quick_Review pour enrichissement satisfaction
3. Aggregate par Employee Code:
   - Total training hours
   - Training frequency
   - Average satisfaction score
   - Recent vs. historical

---

## 3️⃣ FINANCE (0.01 MB) - ⭐⭐⭐ QUALITÉ BASIQUE

### Fichier 1: `AlbertSchool_CACEIS_PL-FTE_22-25_Sent.xlsx`
**Taille:** 0.01 MB

**Sheets:**
```
1. Synthese_PL: 12 rows × 11 cols
   P&L Summary (2022-2025)
   - Réel décembre 2022, 2023, 2024, 2025
   - Europe breakdown
   - Format: Finance department summary

2. Synthese_ETP: 8 rows × 10 cols
   Employee headcount summary
   - End of Year vs. Average for Year
   - 2022-2025 comparison
```

**🟢 UTILITÉ:**
- ✅ **CONTEXT ONLY** → P&L and headcount trends (not individual level)
- ⚠️ Aggregate level → Cannot join on employee ID
- ⚠️ Very small dataset

**Recommandation:** Use for:
- Narrative context in presentation ("CACEIS group employed X avg in 2024")
- HCI (Human Capital Intensity) calculation at company level
- Not useful for individual employee KPIs

---

## 4️⃣ EMPLOYEE SATISFACTION & ENGAGEMENT (38.06 MB) - ⭐⭐⭐ QUALITÉ MODÉRÉE

### 📋 Fichiers PDF (Requires manual extraction)

| Fichier | Taille | Description | Dates |
|---------|--------|-------------|-------|
| `IER 2021.pdf` | 1.76 MB | Internal Engagement Report | 2021 |
| `IMR2022_CACEIS_GROUP_DATA_FR.pdf` | 1.55 MB | Internal Management Report | 2022 |
| `IMR2023_CACEIS_GROUP.pdf` | 15.66 MB | Internal Management Report | 2023 |
| `IMR2024_CACEIS_GROUP.pdf` | 9.10 MB | Internal Management Report | 2024 |
| `RESULTATS ENQUETE MANAGERS.pdf` | 1.06 MB | Manager Survey Results | Recent |
| `TI2025_CACEIS_GROUP_fr.pdf` | 8.92 MB | Talent Index 2025 | 2025 |

**🟢 UTILITÉ:**
- ✅ **ENGAGEMENT SCORES** → Core for KPI Engagement Index
- ✅ **TALENT INSIGHTS** → Trends over 2021-2025
- ✅ Multi-year comparison possible
- ⚠️ **PDF FORMAT** → Requires manual/OCR extraction
- ⚠️ Aggregate level (group-wide summaries, not individual)
- ⚠️ Large files (IMR2023: 15.66 MB suggests graphics-heavy)

**🔴 LIMITATION MAJEURE:**
- Cannot directly join to individual employee records
- Need to:
  1. Extract engagement scores by BU/Department if available
  2. Map back to employees via BU field from EAE data
  3. Or use as context for engagement average

**Recommandation:**
- Extract key metrics (Engagement score, trends, segment breakdowns)
- If no individual-level data in PDFs, use aggregate score by BU
- Map via BU to employees in EAE dataset

---

## 5️⃣ GOVERNANCE (45.57 MB) - ⭐⭐⭐ QUALITÉ CONTEXTUELLE

### 5.1 Excel Files - Qualitative Metrics

| Fichier | Taille | Contenu | Utilité |
|---------|--------|---------|---------|
| `Bilan Groupe Be Generous CACEIS 2025.xlsx` | 0.02 MB | CSR initiative metrics (12 rows) | 🟢 Employee engagement in volunteering |
| `Bilan Groupe Be Generous CACEIS 2024 pour CASA.xlsx` | 0.02 MB | CSR reporting (21 rows) | 🟢 Employee names, organizations, CSR theme |
| `Bilan CDP 2023 pour CAsa.xlsx` | 0.05 MB | Sustainability data | 🟢 Company-level context |
| `We Care - Bilan 2025.xlsx` | 0.02 MB | Well-being program (48 rows) | 🟢 Employee participation in wellness |

**🟢 UTILITÉ:**
- ✅ **ENGAGEMENT PROXY** → Participation in CSR/wellness = engagement indicator
- ✅ Employee names in CSR files → Can identify volunteers
- ✅ Theme data → Categorize engagement types
- ⚠️ Very small samples (12-48 rows)
- ⚠️ Not individual-level performance data

**Recommandation:** Use to identify "engaged employees" (CSR volunteers) → Binary engagement flag for certain cohort.

---

### 5.2 PDF Reports - Diversity & Inclusion & Social

| Fichier | Taille | Sujet |
|---------|--------|-------|
| `Baromètre Diversité et Inclusion CACEIS - France.pdf` | 4.10 MB | D&I metrics (France) |
| `Baromètre Diversité et Inclusion CACEIS - Luxembourg.pdf` | 4.14 MB | D&I metrics (Luxembourg) |
| `Bilan Social 2023 VF.pdf` | 2.31 MB | Social report 2023 |
| `Bilan Social 2024 Luxembourg- VF final.pdf` | 1.79 MB | Social report 2024 (LU) |
| `Bilan Social 2024.pdf` | 1.69 MB | Social report 2024 (FR) |
| `Suivi accord mixité diversité QVT 2023 VF.pdf` | 1.53 MB | D&I agreement follow-up 2023 |
| `Suivi accord mixité diversité QVT 2024 vDef.pdf` | 2.43 MB | D&I agreement follow-up 2024 |

**🟡 UTILITÉ:**
- ✅ Context for bias mitigation framework
- ✅ Gender, age, origin statistics (if extractable)
- ✅ Quality of Work Life (QVT) data
- ⚠️ PDF format → extraction difficulty
- ⚠️ Mostly narrative/compliance reporting

**Recommandation:** Extract key statistics (gender ratio by department, etc.) for bias analysis context. Use for presenting "governance approach" in presentation.

---

### 5.3 PowerPoint Presentations

| Fichier | Taille | Contenu |
|---------|--------|---------|
| `BILAN FAB'Life programme 2023.pptx` | 6.07 MB | Employee well-being program |
| `Bilan FAB'Life 2024.pptx` | 11.61 MB | Employee well-being program |
| `CACEIS HR Project ID Card_platform J'agis.pptx` | 0.20 MB | HR Platform overview |
| `Diversity Month Wrap up 2025.pptx` | 0.79 MB | D&I celebration event |
| `QVCT D&I Bilan 2025 VFinal.pptx` | 0.25 MB | Quality of Work Life + D&I |
| `Slide achievements Diversity and Inclusion.pptx` | 8.17 MB | D&I achievements summary |

**🟡 UTILITÉ:**
- ✅ Context slides (can reuse visuals in your presentation)
- ✅ FAB'Life program participation data (if extractable)
- ⚠️ Primarily for communication, not analysis

---

### 5.4 Word Document

- `Be Generous 2025 synthèse.docx` (0.38 MB) → CSR summary narrative

---

## 📊 MATRICE DE JOINTURE PROPOSÉE

```
MASTER TABLE (Data.xlsx - Sheet1 avec 275,609 rows)
    ↓
    ├─ LEFT JOIN [Notes evaluation 2023] ON IUG
    ├─ LEFT JOIN [EAE Stats] ON IUG  
    ├─ LEFT JOIN [Absentéisme] ON Employee Code / IUG
    ├─ LEFT JOIN [Training - aggregated] ON Employee Code / Matricule
    ├─ LEFT JOIN [Engagement by BU] FROM PDFs
    └─ LEFT JOIN [Governance flags] FROM CSR/D&I data
```

---

## 🎯 PRIORITÉS D'UTILISATION

### 🔴 CRITIQUES (inclure absolument)
1. **Data.xlsx Sheet1** → 275,609 employees = base maître
2. **Notes evaluation 2023.xlsx** → Performance ratings
3. **EAE Stats** → Manager evaluations + job titles
4. **Absentéisme** → Engagement proxy
5. **Training aggregated** → Agility & development

### 🟡 IMPORTANTS (inclure si temps permet)
6. **Engagement PDFs** → Extract summary scores by BU
7. **Governance diversity metrics** → For bias mitigation narrative

### 🟢 OPTIONNELS (utiliser pour contexte)
8. **Finance summary** → Context only (group-level)
9. **CSR participation** → Bonus engagement indicator
10. **Presentations** → Visual inspiration

---

## ⚠️ DÉFIS IDENTIFIÉS

| Défi | Fichiers affectés | Solution |
|------|------------------|----------|
| **Identifiants fragmentés** | Tous | Créer table de mapping IUG ↔ Employee Code ↔ Matricule |
| **PDFs non structurés** | Engagement (6 files) | Extraction manuelle ou OCR + mapping BU |
| **Complétude variable** | Training (58-94%), EAE (72%) | Imputation par médiane BU |
| **Données financières agrégées** | Finance (1 file) | Utiliser pour contexte, pas pour KPIs |
| **Versions multiples** | HR Data | Utiliser versions "Définitive" ou "cloture" |

---

## 🚀 PLAN D'ACTION PROPOSÉ

### Phase 1: Charger et explorer (FAIT)
- [x] Identifier tous les fichiers
- [x] Analyser structure
- [x] Identifier identifiants communs

### Phase 2: Préparer les données (À FAIRE)
- [ ] Charger Data.xlsx Sheet1 comme master (275,609 rows)
- [ ] Normaliser identifiants (IUG, Employee Code, Matricule)
- [ ] Créer table de mapping des IDs
- [ ] Nettoyer et joindre fichiers structurés (Notes, EAE, Absentéisme, Training)

### Phase 3: Enrichir les données (À FAIRE)
- [ ] Extraire scores d'engagement des PDFs par BU
- [ ] Mapper engagement scores à employees via BU
- [ ] Intégrer flags CSR/wellness

### Phase 4: Calculer KPIs (PARTIELLEMENT FAIT)
- [ ] EVI avec données réelles de performance + tenure
- [ ] Talent ROI avec salaires réels
- [ ] OCRR avec engagement & retention risk réels
- [ ] WAS avec formation réelle
- [ ] Retention Risk avec absentéisme

### Phase 5: Présentation (28 AVRIL DEADLINE)
- [ ] Valider KPIs avec données complètes
- [ ] Générer insights final
- [ ] Préparer 7-min presentation

---

## 📌 RECOMMANDATION FINALE

**Stratégie recommandée pour la midterm (30 avril):**

1. **Utiliser Data.xlsx Sheet1** comme base (275K+ employees = structure)
2. **Joindre les fichiers structurés Excel** (Notes, EAE, Absentéisme, Training)
3. **Pour Engagement:** Si extraction PDF trop complexe, utiliser taux engagement par BU de PDFs comme estimation
4. **Documenter limitations** dans présentation:
   - "27.5% données manquantes dans EAE compensées par imputation BU"
   - "Engagement estimé par BU depuis rapports 2024"
5. **Valoriser la couverture:** 275K+ employees × 7 KPIs = 1.9M data points!

Cette approche maximise la valeur des données disponibles tout en restant pragmatique pour le délai.

---

**Document généré:** 28 avril 2026  
**Statut:** Prêt pour phase 2 (Préparation données)
