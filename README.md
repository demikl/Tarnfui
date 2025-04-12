# 🚪Tarnfui 🌠

Kubernetes cost and carbon energy saver that selectively shutdown workloads during non-working hours on staging clusters

The project name Tarnfui comes from [tarn fui](https://www.elfdict.com/wt/520573), an entity created by Tolkien that is described as "The Door of the Night".

## Installation

```bash
uv sync
```

## Utilisation

```bash
python -m tarnfui
```

## Tests

```bash
pytest
```

## Architecture

### Sequence Diagram

The following diagram illustrates the operational workflow of Tarnfui:

```mermaid
sequenceDiagram
    participant CLI as CLI (main)
    participant S as Scheduler
    participant K as KubernetesController
    participant R as DeploymentResource
    participant A as Kubernetes API

    Note over CLI: Application start
    CLI->>CLI: Parse arguments
    CLI->>CLI: Setup logging
    CLI->>CLI: Create TarnfuiConfig
    CLI->>S: Create Scheduler
    
    alt Reconcile once
        CLI->>S: reconcile()
    else Run continuously
        CLI->>S: run_reconciliation_loop()
    end
    
    Note over S: Time-based trigger
    S->>S: Check if should_be_active()
    
    alt Active hours (daytime on workdays)
        S->>K: start_resources()
        K->>R: start_resources()
        R->>R: Get deployments at zero replicas
        loop For each deployment
            R->>R: Get original replicas
            alt Has saved state
                R->>A: Scale deployment to saved replicas
                R->>A: Create 'Started' event
            end
        end
    else Inactive hours (nights and weekends)
        S->>K: stop_resources()
        K->>R: stop_resources()
        R->>R: Get all deployments
        loop For each deployment with replicas > 0
            R->>R: Save current replicas
            R->>A: Scale deployment to zero
            R->>A: Create 'Stopped' event
        end
    end
```

### Class Diagram

This diagram shows the core classes and their relationships in Tarnfui:

```mermaid
classDiagram
    class CLI {
        +parse_args()
        +setup_logging()
        +main()
    }
    
    class Scheduler {
        -TarnfuiConfig config
        -KubernetesClient kubernetes_client
        +reconcile()
        +should_be_active()
        +run_reconciliation_loop()
    }
    
    class TarnfuiConfig {
        +str shutdown_time
        +str startup_time
        +list~Weekday~ active_days
        +str timezone
        +int reconciliation_interval
        +str namespace
        +from_env()
    }
    
    class Weekday {
        <<enumeration>>
        MON
        TUE
        WED
        THU
        FRI
        SAT
        SUN
        +to_integer()
        +from_integer()
    }
    
    class KubernetesClient {
        +KubernetesController controller
        +stop_deployments()
        +start_deployments()
        +save_deployment_state()
        +get_original_replicas()
        +scale_deployment()
    }
    
    class KubernetesController {
        +KubernetesConnection connection
        +dict~str, KubernetesResource~ resources
        +stop_resources()
        +start_resources()
    }
    
    class KubernetesResource {
        <<abstract>>
        +KubernetesConnection connection
        +str namespace
        +get_resources()
        +get_resource()
        +scale()
        +stop_resources()
        +start_resources()
    }
    
    class DeploymentResource {
        +get_replicas()
        +set_replicas()
        +get_resource_key()
    }
    
    CLI --> Scheduler : creates
    CLI --> TarnfuiConfig : creates
    Scheduler --> TarnfuiConfig
    Scheduler --> KubernetesClient
    TarnfuiConfig --> Weekday
    KubernetesClient --> KubernetesController
    KubernetesController --> KubernetesResource
    KubernetesResource <|-- DeploymentResource
```

## Using the Helm Chart

The Helm chart for Tarnfui is published to the GitHub Pages of this repository. To use the chart, follow these steps:

1. Add the Helm repository:

   ```bash
   helm repo add tarnfui https://<your-github-username>.github.io/Tarnfui
   helm repo update
   ```

2. Install the chart:

   ```bash
   helm install tarnfui tarnfui/tarnfui --namespace <your-namespace>
   ```

3. Customize the installation by providing your own `values.yaml` file:

   ```bash
   helm install tarnfui tarnfui/tarnfui --namespace <your-namespace> -f values.yaml
   ```

## Releasing the Project

To release a new version of Tarnfui:

1. Ensure all changes are committed and pushed to the `main` branch.
2. Create a new Git tag following semantic versioning (e.g., `v1.2.3`):

   ```bash
   git tag v1.2.3
   git push origin v1.2.3
   ```

3. The GitHub Actions workflow will automatically:
   - Build and publish a Docker image to GitHub Container Registry (GHCR).
   - Package and publish the Helm chart to the GitHub Pages of this repository.

4. Verify the release by checking the Docker image and Helm chart availability.
