import argparse

__version__ = "0.1.3"
__description__ = (
    "Kubernetes cost and carbon energy saver that selectively shutdown workloads during non-working hours "
    "on staging clusters"
)


def main():
    from . import __description__, __version__

    parser = argparse.ArgumentParser(description="Tarnfui CLI")
    parser.add_argument("--version", action="store_true", help="Show the version and description of Tarnfui")

    args = parser.parse_args()

    if args.version:
        print(f"Tarnfui version {__version__}: {__description__}")
    else:
        print("hello this is tarnfui")
