Mon cahier des charges est là : #file:CDC.md : tu le mettras à jour en fonction de l'avancement des implémentations, et tu pourras ajouter des items pour ce qu'il reste à faire ou les améliorations potentielles.

# Prompt pour GitHub Copilot : Initialisation d'un projet Python moderne

## Objectif

Générer la structure de base et les fichiers de configuration initiaux pour un nouveau projet Python. Ce projet met l'accent sur une gestion moderne des dépendances, un outillage de qualité de code, le développement conteneurisé, le déploiement via Docker/Helm/Kubernetes, l'automatisation CI/CD avec GitHub Actions, des tests unitaires systématiques et une attention particulière à l'efficacité mémoire.

## Spécifications Techniques

1. **Langage :** Python (dernière version stable ou spécifier si besoin, ex: 3.13+)
2. **Gestion des Dépendances :** Utiliser `uv` pour l'installation et la gestion des dépendances.
    * Générer un fichier `pyproject.toml` initial configuré pour `uv`.
    * Inclure `ruff` comme dépendance de développement.
    * Inclure `pytest` comme dépendance de développement pour les tests.
    * Ajouter des placeholders pour les dépendances de production.
3. **Qualité du Code (Linting & Formatage) :** Utiliser `ruff` pour le formatage et le linting.
    * Configurer `ruff` dans `pyproject.toml` avec des règles de base raisonnables (ex: activer les règles par défaut, isort, flake8).
    * Configurer `ruff format`.
4. **Environnement de Développement :** VS Code Dev Container.
    * Créer un répertoire `.devcontainer`.
    * Générer un fichier `.devcontainer/devcontainer.json` configuré pour Python, utilisant une image de base appropriée (ex: `mcr.microsoft.com/devcontainers/python:3.13`).
    * Configurer `devcontainer.json` pour installer `uv` et `ruff` automatiquement.
    * Inclure les extensions VS Code recommandées (ex: `ms-python.python`, `ms-azuretools.vscode-docker`, `charliermarsh.ruff`).
    * Configurer les `postCreateCommand` ou `postAttachCommand` si nécessaire pour installer les dépendances avec `uv sync` via le `pyproject.toml`.
    * Générer un fichier `.devcontainer/Dockerfile` basique si des personnalisations de l'image de dev sont nécessaires (sinon, l'image de base peut suffire).
5. **Structure du Projet :**
    * Utiliser une structure de type `src/tarnfui/` pour le code source.
    * Créer un répertoire `tests/` pour les tests unitaires.
    * Inclure un `.gitignore` adapté aux projets Python et aux fichiers de l'environnement (VSCode, etc.).
    * Créer un `README.md` basique avec des sections pour l'installation, l'utilisation, les tests et le déploiement.
6. **Packaging & Déploiement :**
    * **Docker :** Générer un `Dockerfile` multi-étages optimisé pour la production.
        * Utiliser une image de base Python slim.
        * Copier uniquement les dépendances nécessaires et le code source.
        * Exécuter l'application avec un utilisateur non-root.
        * Tenir compte de l'installation des dépendances via `uv`.
    * **Helm :** Créer une structure de chart Helm basique dans un répertoire `charts/tarnfui/`.
        * `Chart.yaml`
        * `values.yaml` (avec des placeholders pour l'image, le tag, les replicas, les ressources, etc.)
        * `templates/deployment.yaml` (utilisant les valeurs de `values.yaml`)
        * `templates/service.yaml` (basique)
        * `templates/_helpers.tpl` (si nécessaire)
        * `.helmignore`
7. **Automatisation (CI/CD) :** GitHub Actions.
    * Créer un répertoire `.github/workflows`.
    * Générer un workflow (`ci.yaml`) qui se déclenche sur `push` (branches `main`/`master`) et `pull_request`. Ce workflow doit :
        * Checkout le code.
        * Setup Python.
        * Installer `uv`.
        * Installer les dépendances (`uv sync --dev`).
        * Lancer `ruff check .` et `ruff format --check .`.
        * Lancer les tests unitaires avec `pytest`.
    * Générer un workflow (`cd.yaml`) qui se déclenche sur `push` sur la branche `main` (après le succès de CI). Ce workflow doit (avec placeholders pour les secrets/registries) :
        * Build l'image Docker de production.
        * Tag l'image Docker (ex: avec le SHA du commit).
        * Push l'image Docker vers un registry (ex: GitHub Container Registry - GHCR).
        * Mettre à jour et publier la chart Helm sur un dépôt public
8. **Tests :**
    * Exiger des tests unitaires pour chaque fonctionnalité.
    * Générer un exemple simple de fichier de test dans `tests/` (ex: `tests/test_example.py`) utilisant `pytest`, qui teste une fonction d'exemple.
    * Créer un fichier source d'exemple correspondant (ex: `src/tarnfui/example.py`).
9. **Performance (Consommation Mémoire) :**
    * Le code devra être écrit en gardant à l'esprit l'efficacité mémoire, surtout lors du traitement potentiel d'un grand nombre d'objets/ressources.
    * Ajouter un commentaire dans le `README.md` ou dans un fichier `CONTRIBUTING.md` (à créer) mentionnant cette contrainte et suggérant l'utilisation de générateurs, d'itérateurs, de vues mémoire (`memoryview`), ou de bibliothèques comme `psutil` ou des profileurs mémoire si nécessaire.
