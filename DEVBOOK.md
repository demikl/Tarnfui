# Tarnfui Requirements Document

This program is designed to run in a Kubernetes pod and will stop the pods in the cluster where it is running during non-working hours (night and weekends). In the morning, it will restart the deployments by restoring the initial number of replicas.

Written in Python with typing, dependencies managed using "uv," and linting/formatting handled by "ruff."

## Development Journal and Progress Tracker

This file serves as a development journal and project progress tracker. Tasks are tracked using the following emoji-based system:
- ✅ Completed
- 🟡 In Progress
- ❌ Not Started

## Project Breakdown into Phases (TDD)

### Phase 1: Initialization and Configuration

1. **Project and Development Environment Setup**
   - ✅ Set up the project structure (src/tarnfui, tests, etc.)
   - 🟡 Configure pyproject.toml with uv and dependencies
   - ❌ Configure the development container environment for VSCode
   - ❌ Write initial unit tests to validate the configuration

2. **Kubernetes Client**
   - ❌ Write unit tests for interacting with the Kubernetes API
   - ❌ Implement a client class for the Kubernetes API
   - ❌ Perform integration tests with a test cluster (minikube or kind)

### Phase 2: Core Features

1. **Detection of Working/Non-Working Hours**
   - ❌ Write unit tests for time detection logic
   - ❌ Implement logic to detect night vs. day and weekdays vs. weekends
   - ❌ Write parameterized tests for different time zones and configurations

2. **Saving Deployment States**
   - ❌ Write unit tests for saving the state (number of replicas)
   - ❌ Implement persistent storage for deployment states
   - ❌ Perform integration tests to verify persistence

3. **Stopping Pods**
   - ❌ Write unit tests for the logic to stop pods (set replicas to 0)
   - ❌ Implement the stop functionality
   - ❌ Perform robustness tests with various error scenarios

4. **Restarting Deployments**
   - ❌ Write unit tests for the logic to restore replicas
   - ❌ Implement the functionality to restore replicas
   - ❌ Test to ensure proper restoration functionality

### Phase 3: Orchestration and Scheduling

1. **Task Scheduler**
   - ❌ Write unit tests for the scheduler
   - ❌ Implement a scheduler to execute stop/start actions
   - ❌ Perform integration tests to verify execution at defined times

2. **Configurable Settings**
   - ❌ Write unit tests for the configuration system
   - ❌ Implement a configuration system (env vars, config files, etc.)
   - ❌ Perform integration tests with different configurations

### Phase 4: Deployment and Monitoring

1. **Logging and Metrics**
   - ❌ Write unit tests for the logging system
   - ❌ Implement a logging and metrics collection system
   - ❌ Perform integration tests to verify metrics collection

2. **Performance Testing and Memory Optimization**
   - ❌ Perform load tests simulating a large number of resources (namespaces, deployments)
   - ❌ Profile memory usage and optimize critical points
   - ❌ Implement batch or streaming mechanisms to reduce memory footprint
   - ❌ Benchmark performance with different cluster sizes

3. **Packaging and Deployment**
   - ✅ Create and test the Dockerfile
   - ✅ Create Helm charts
   - ✅ Configure CI/CD with GitHub Actions
   - ✅ Set up automated Docker image publication to GHCR
   - ✅ Set up automated Helm chart publication to GitHub Pages

4. **Documentation**
   - 🟡 Complete the README
   - ❌ Write technical documentation
   - ❌ Document operational procedures

## Potential Improvements

- Develop a web interface to visualize pod states and schedules.
- Implement event notifications (stop/start) via webhooks.
- Add support for more complex rules (holidays, specific schedules per namespace).
- Integrate with monitoring solutions (Prometheus, Grafana).
- Optimize performance for large clusters.
- To optimize the management of clusters with a large number of `Deployment` resources scaled to 0, iterate over the pods in the cluster and identify which resource manages their lifecycle (e.g., by inspecting the `.metadata.owner` field). Perform the shutdown via this resource to avoid iterating over a very large number of deployments.

## To Do

- ✅ Set up CI/CD workflows for automated releases.
- ❌ Regularly update this file to reflect progress.
