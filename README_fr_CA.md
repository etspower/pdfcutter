# pdfcutter

[English](README.md) | [简体中文](README_zh.md) | [Français (Canada)](README_fr_CA.md)

Une application de bureau locale pour diviser les fichiers PDF d'apprentissage des langues numérisés en fonction de leur table des matières (TOC).

`pdfcutter` utilise l'OCR avancé (en ligne/hors ligne) et des modèles de langage étendus (LLM) dotés de capacités de vision pour lire la table des matières à partir des pages PDF, extraire automatiquement les titres de chapitres et les numéros de page, puis découper le PDF original en plusieurs fichiers de chapitres individuels.

## Caractéristiques
- **Modes de reconnaissance flexibles :**
  - **OCR en ligne (ocr.space) :** Rapide, prend en charge plus de 20 langues et plusieurs moteurs OCR.
  - **OCR hors ligne (Docling) :** Conversion de documents locale de haute précision avec analyse de la mise en page. Aucune clé API requise.
- **Extraction assistée par IA :** Utilise des modèles de vision (via OpenRouter/NVIDIA) ou une extraction structurée basée sur du texte à partir des résultats OCR.
- **Révision et édition :** Visualisez la table des matières extraite dans un tableau structuré. Corrigez les erreurs, ajoutez ou supprimez des entrées et laissez l'application recalculer les correspondances réelles des pages PDF.
- **Division et téléchargement :** Générez des fichiers PDF individuels pour chaque chapitre et téléchargez-les tous dans une archive ZIP.
- **Interface graphique de bureau native :** Construite avec Flet pour une expérience de bureau fluide.

## Prérequis

- **Python 3.10+**
- **Poppler :** Requis pour l'extraction d'images `pymupdf` et `pdf2image` (si vous utilisez des flux de travail basés sur les images).
- **Clé API OCR.space (Optionnel) :** Si vous souhaitez utiliser le mode de reconnaissance en ligne. Obtenez une clé gratuite sur [ocr.space](https://ocr.space/ocrapi).

## Installation

1. Cloner le dépôt :
    ```bash
    git clone https://github.com/etspower/pdfcutter.git
    cd pdfcutter
    ```

2. Installer les dépendances :
    ```bash
    pip install -r requirements.txt
    ```
    *Note : L'installation de `docling` pour l'OCR hors ligne téléchargera environ 500 Mo de modèles lors de la première exécution.*

3. Configurer les variables d'environnement :
    ```bash
    cp .env.example .env
    ```
    Modifiez le fichier `.env` pour inclure votre `OCR_SPACE_API_KEY` ou vos identifiants LLM.

## Exécution de l'application

Lancez l'application de bureau :
```bash
python gui.py
```

## Fonctionnement

1. **Étape 1 : Configuration et téléversement :** Sélectionnez votre PDF et spécifiez la plage de pages de la table des matières. Choisissez entre la reconnaissance **En ligne (ocr.space)** ou **Hors ligne (Docling)**.
2. **Étape 2 : Aperçu et exécution :** Visualisez les pages de la table des matières et cliquez sur **Run OCR Extraction**. L'application extrait le texte des images et utilise optionnellement un LLM pour le structurer en JSON.
3. **Étape 3 : Révision et édition :** L'application calcule un décalage basé sur le premier numéro de page arabe identifié. Vous pouvez ajuster manuellement les titres, les niveaux ou les pages de début du PDF ici.
4. **Étape 4 : Exécution de la division :** Vérifiez le plan de division et cliquez sur **Split PDF & Save**.

## Architecture
- **Interface graphique (`gui.py`)** : Interface de bureau basée sur Flet.
- **Clients OCR (`src/ocr_client.py`, `src/docling_client.py`)** : Intégration avec ocr.space (en ligne) et Docling (hors ligne).
- **Client LLM (`src/llm_client.py`)** : Extraction de données structurées utilisant des invites LLM de vision ou de texte pur.
- **Utilitaires PDF (`src/pdf_utils.py`)** : Rendu et division de PDF utilisant `PyMuPDF` et `pypdf`.
- **Modules logiques (`src/toc_extract.py`, `src/split_logic.py`)** : Validation des données et calculs de décalage de page.

## Licence
MIT
