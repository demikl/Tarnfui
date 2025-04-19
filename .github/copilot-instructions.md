# Copilot Instructions

## Project Structure

- **Source Code**: All Python source code is located in `/src/tarnfui/`. Execute it with
  "uv run tarnfui".
- **Helm Chart**: The Helm chart is located in `/chart/tarnfui/`. Ensure that it is
  updated when features are added or removed from the project.
- **Tests**: All tests are located in `/tests/`. Execute them with this terminal
  command: "source .venv/bin/activate && pytest"
- **Overview**: the `/README.md` should accuratly reflect the code architecture through
  its Mermaid diagrams.

## GitHub Actions

- All GitHub Actions workflows are located in `/.github/workflows/`.
- Ensure that workflows are updated to reflect any changes or new features in the project.

## Language and Tone

- All files must be written in **English**.
- Use a **professional tone** that is clear and understandable for readers whose native language is not English.

## Additional Guidelines

- Refer to the requirements document located at `/DEVBOOK.md` for implementation progress updates. This file will serve as a development journal and project progress tracker.
- Use an emoji-based system to track the status of tasks:
  - ✅ Completed
  - 🟡 In Progress
  - ❌ Not Started
- Update `DEVBOOK.md` regularly to reflect the current state of the project.
- Update `DEVBOOK.md` regularly to rephrase whatever text I may add to this file, so that it conforms to the requirements defined in the section "Language and Tone" above.
- **Testing**: Unit tests are required for every feature.
- **Performance**: Write memory-efficient code, especially when handling a large number of objects or resources.
- Ensure the Helm chart is updated to include any new environment variables, CLI arguments, commands, or options added to the project.
