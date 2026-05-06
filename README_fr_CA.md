# pdfcutter

[English](README.md) | [简体中文](README_zh.md) | [Français (Canada)](README_fr_CA.md)

Une application de bureau locale pour diviser les fichiers PDF d'apprentissage des langues numérisés en fonction de leur table des matières (TOC).

`pdfcutter` utilise l'OCR avancé (en ligne/hors ligne) pour lire la table des matières à partir des pages PDF, extraire automatiquement les titres de chapitres et les numéros de page, puis découper le PDF original en plusieurs fichiers de chapitres individuels.

## Caractéristiques
- **Modes de reconnaissance flexibles :**
  - **OCR en ligne (LlamaParse) :** Analyse avancée de documents utilisant LlamaCloud, extrêmement précis pour les tables complexes.
  - **OCR hors ligne (Docling) :** Conversion de documents locale de haute précision avec analyse de la mise en page. Aucune clé API requise.
- **Extraction automatisée :** Extrait le texte des résultats OCR et le transforme en un format de tableau structuré éditable.
- **Révision et édition :** Visualisez la table des matières extraite dans un tableau structuré. Corrigez les erreurs, ajoutez ou supprimez des entrées et laissez l'application recalculer les correspondances réelles des pages PDF.
- **Contrôle du décalage de page :** Ajustez facilement la correspondance entre les numéros de page imprimés et les pages PDF réelles grâce à un décalage global (avec boutons +/-).
- **Aperçu des pages en direct :** Prévisualisez n'importe quelle page du PDF instantanément dans le tableau de correspondance pour vérifier l'exactitude avant le découpage.
- **Division et téléchargement :** Générez des fichiers PDF individuels pour chaque chapitre et téléchargez-les tous dans une archive ZIP.
- **Interface graphique de bureau native :** Construite avec Flet pour une expérience de bureau fluide.

## Prérequis

- **Python 3.10+**
- **Poppler :** Requis pour l'extraction d'images.
- **Clé API LlamaParse (Optionnel) :** Si vous souhaitez utiliser le mode de reconnaissance en ligne. Obtenez une clé gratuite sur [LlamaCloud](https://cloud.llamaindex.ai).

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
    Modifiez le fichier `.env` pour inclure votre `LLAMAPARSE_API_KEY`.

## Exécution de l'application

Lancez l'application de bureau :
```bash
python gui.py
```

## Fonctionnement

1. **Étape 1 : Configuration et téléversement :** Sélectionnez votre PDF et spécifiez la plage de pages de la table des matières. Choisissez entre la reconnaissance **En ligne (LlamaParse)** ou **Hors ligne (Docling)**.
2. **Étape 2 : Aperçu et exécution :** Visualisez les pages de la table des matières et cliquez sur **Run OCR Extraction**. L'application extrait le texte et le structure en une liste modifiable.
3. **Étape 3 : Révision et édition :** L'application calcule un décalage initial. Vous pouvez ajuster manuellement ce **Décalage Global** à l'aide des boutons +/- et utiliser le **bouton d'aperçu** (icône d'œil) sur chaque ligne pour vérifier la correspondance en temps réel.
4. **Étape 4 : Exécution de la division :** Vérifiez le plan de division et cliquez sur **Split PDF & Save**.

## Architecture
- **Interface graphique (`gui.py`)** : Interface de bureau basée sur Flet.
- **Clients OCR (`src/ocr_client.py`, `src/docling_client.py`)** : Intégration avec LlamaParse (en ligne) et Docling (hors ligne).
- **Utilitaires PDF (`src/pdf_utils.py`)** : Rendu et division de PDF utilisant `PyMuPDF` et `pypdf`.
- **Modules logiques (`src/toc_extract.py`, `src/split_logic.py`)** : Validation des données et calculs de décalage de page.

## Crédits & Remerciements
Ce projet repose sur les incroyables projets open-source suivants :
- [Docling](https://docling-project.github.io/docling/) - Pour un OCR local et une conversion de documents puissants.
- [LlamaParse](https://github.com/run-llama/llama_parse) - Pour des capacités d'analyse de documents en ligne de pointe.
- [Flet](https://flet.dev/) - Pour permettre la création de superbes applications de bureau avec Python.
- [PyMuPDF](https://pymupdf.readthedocs.io/) & [pypdf](https://pypdf.readthedocs.io/) - Pour la manipulation et le rendu des PDF.

## Licence
MIT
