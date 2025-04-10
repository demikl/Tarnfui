"""Command-line interface for Tarnfui.

This module serves as the entrypoint for the Tarnfui application.
"""
import argparse
import logging
import sys

from tarnfui.config import TarnfuiConfig, Weekday
from tarnfui.kubernetes import KubernetesClient
from tarnfui.scheduler import Scheduler


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration.

    Args:
        verbose: Whether to enable verbose logging.
    """
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    logging.basicConfig(
        level=log_level,
        format=log_format,
        stream=sys.stdout
    )


def parse_args(args: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        args: Command-line arguments to parse. If None, sys.argv will be used.

    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        prog="tarnfui",
        description=(
            "Kubernetes cost and carbon energy saver that selectively shutdown workloads during non-working hours."
        )
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--namespace",
        help="Specific namespace to manage (overrides TARNFUI_NAMESPACE)"
    )

    parser.add_argument(
        "--startup-time",
        help="Time to start deployments (HH:MM format, overrides TARNFUI_STARTUP_TIME)"
    )

    parser.add_argument(
        "--shutdown-time",
        help="Time to stop deployments (HH:MM format, overrides TARNFUI_SHUTDOWN_TIME)"
    )

    parser.add_argument(
        "--active-days",
        help="Comma-separated list of active days (mon,tue,wed,thu,fri,sat,sun format, overrides TARNFUI_ACTIVE_DAYS)"
    )

    parser.add_argument(
        "--timezone",
        help="Timezone for time calculations (e.g. 'Europe/Paris', overrides TARNFUI_TIMEZONE)"
    )

    parser.add_argument(
        "--interval",
        type=int,
        help="Reconciliation interval in seconds (overrides TARNFUI_RECONCILIATION_INTERVAL)"
    )

    parser.add_argument(
        "--reconcile-once",
        action="store_true",
        help="Run reconciliation once and exit"
    )

    return parser.parse_args(args)


def main(args: list[str] | None = None) -> int:
    """Main entry point for the Tarnfui application.

    Args:
        args: Command-line arguments. If None, sys.argv will be used.

    Returns:
        Exit code.
    """
    try:
        parsed_args = parse_args(args)
        setup_logging(parsed_args.verbose)
        logger = logging.getLogger(__name__)
        logger.info("Starting Tarnfui")

        # Create config from environment variables
        config = TarnfuiConfig.from_env()

        # Override with command-line arguments
        if parsed_args.namespace:
            config.namespace = parsed_args.namespace
        if parsed_args.startup_time:
            config.startup_time = parsed_args.startup_time
        if parsed_args.shutdown_time:
            config.shutdown_time = parsed_args.shutdown_time
        if parsed_args.timezone:
            config.timezone = parsed_args.timezone

        # Revalidate startup and shutdown times with the updated timezone
        config.startup_time = TarnfuiConfig.validate_time_format(
            config.startup_time, {"timezone": config.timezone}, "startup_time"
        )
        config.shutdown_time = TarnfuiConfig.validate_time_format(
            config.shutdown_time, {
                "timezone": config.timezone}, "shutdown_time"
        )

        if parsed_args.active_days:
            try:
                days = [Weekday(day.strip().lower())
                        for day in parsed_args.active_days.split(",")]
                config.active_days = days
            except ValueError as e:
                logger.error(f"Invalid active days format: {e}")
                return 1
        if parsed_args.interval:
            config.reconciliation_interval = parsed_args.interval

        logger.info(f"Configuration: startup={config.startup_time}, shutdown={config.shutdown_time}, "
                    f"timezone={config.timezone}, "
                    f"active_days={[day.value for day in config.active_days]}, "
                    f"interval={config.reconciliation_interval}s, "
                    f"namespace={config.namespace or 'all'}")

        # Create Kubernetes client
        k8s_client = KubernetesClient(namespace=config.namespace)

        # Create scheduler
        scheduler = Scheduler(config=config, kubernetes_client=k8s_client)

        if parsed_args.reconcile_once:
            logger.info("Running reconciliation once")
            scheduler.reconcile()
        else:
            logger.info("Running continuous reconciliation")
            scheduler.run_reconciliation_loop()

    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Interrupted by user")
    except ValueError as e:
        logging.getLogger(__name__).error(f"Configuration error: {e}")
        return 1
    except Exception as e:
        logging.getLogger(__name__).error(f"An unexpected error occurred: {e}")
        return 1

    logging.getLogger(__name__).info("Tarnfui exiting")
    return 0


if __name__ == "__main__":
    sys.exit(main())
