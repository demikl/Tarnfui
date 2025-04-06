# Cahier des charges Tarnfui

Il s'agit d'un programme prévu pour être exécuté dans un pod Kubernetes, et qui s'occupera de stopper les pods du cluster dans lequel il s'exécute pendant les heures non ouvrées (nuit et week-end). Le matin, il redémarrera les déploiements en rétablissant le nombre de réplicas initial.

Codé en Python avec typing, dépendances gérées avec "uv" et lint + formattage avec "ruff".

## Découpage du projet en étapes (TDD)

### Phase 1: Initialisation et configuration

1. **Configuration du projet et environnement de développement**
   - Mise en place de la structure du projet (src/tarnfui, tests, etc.)
   - Configuration de pyproject.toml avec uv et dépendances
   - Configuration de l'environnement dev container pour VSCode
   - Premiers tests unitaires pour valider la configuration

2. **Client Kubernetes**
   - Tests unitaires pour l'interaction avec l'API Kubernetes
   - Implémentation d'une classe client pour l'API Kubernetes
   - Tests d'intégration avec un cluster de test (minikube ou kind)

### Phase 2: Fonctionnalités principales

1. **Détection des horaires ouvrés/non-ouvrés**
   - Tests unitaires pour la détection des horaires
   - Implémentation de la logique de détection (nuit vs jour, jours ouvrés vs weekend)
   - Tests paramétrés avec différents fuseaux horaires et configurations

2. **Sauvegarde de l'état des déploiements**
   - Tests unitaires pour la sauvegarde de l'état (nombre de réplicas)
   - Implémentation du stockage persistant des états
   - Tests d'intégration pour vérifier la persistance

3. **Arrêt des pods**
   - Tests unitaires pour la logique d'arrêt (mise à 0 des réplicas)
   - Implémentation de la fonctionnalité d'arrêt
   - Tests de robustesse avec divers scénarios d'erreur

4. **Redémarrage des déploiements**
   - Tests unitaires pour la logique de restauration
   - Implémentation de la fonctionnalité de restauration des réplicas
   - Tests pour vérifier le bon fonctionnement de la restauration

### Phase 3: Orchestration et scheduling

1. **Planificateur de tâches**
   - Tests unitaires pour le planificateur
   - Implémentation d'un scheduler pour exécuter les arrêts/démarrages
   - Tests d'intégration pour vérifier l'exécution aux horaires définis

2. **Configuration paramétrable**
   - Tests unitaires pour le système de configuration
   - Implémentation d'un système de configuration (env vars, fichier config, etc.)
   - Tests d'intégration avec différentes configurations

### Phase 4: Déploiement et monitoring

1. **Logging et métriques**
   - Tests unitaires pour le système de logs
   - Implémentation d'un système de logs et métriques
   - Tests d'intégration pour vérifier la collecte de métriques

2. **Packaging et déploiement**
   - Création du Dockerfile et tests
   - Création des charts Helm
   - Configuration de la CI/CD avec GitHub Actions

3. **Documentation**
   - Complétion du README
   - Documentation technique
   - Documentation des procédures opérationnelles

## Améliorations potentielles

- Interface web pour visualiser l'état des pods et planifications
- Notification des événements (arrêt/démarrage) via webhooks
- Support pour des règles plus complexes (jours fériés, horaires spécifiques par namespace)
- Intégration avec des solutions de monitoring (Prometheus, Grafana)
- Optimisation des performances pour les grands clusters

## À faire

- [ ] Initialiser la structure du projet
- [ ] Configurer les outils de développement
- [ ] Implémenter le client Kubernetes
- [ ] Implémenter la détection des horaires
- [ ] Implémenter la sauvegarde/restauration des états
- [ ] Implémenter l'arrêt/démarrage des pods
- [ ] Mettre en place le planificateur
- [ ] Configurer le déploiement et la CI/CD
