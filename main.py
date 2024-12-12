# mna_automation/main.py

import os
import sys
from pathlib import Path

from colorama import Fore, Style, init

from agents.strategy_agent.agent import StrategyAgent
from models.strategy import StrategyModel
from utils.logger import get_logger, setup_logging


def print_welcome():
    print(
        f"\n{Style.BRIGHT}{Fore.CYAN}=== M&A Strategy Development Assistant ==={Style.RESET_ALL}"
    )
    print(
        f"\n{Fore.YELLOW}This assistant will help you develop an M&A strategy through natural conversation."
        f"\nJust describe your goals and requirements, and I'll guide you through the process.{Style.RESET_ALL}"
    )
    print(f"\n{Fore.YELLOW}Commands:{Style.RESET_ALL}")
    print("- Type 'exit' or 'quit' to end the conversation")
    print("- Press Ctrl+C to interrupt the process")
    print(f"\n{Fore.GREEN}Let's begin...{Style.RESET_ALL}\n")
    print("=" * 50 + "\n")


def ensure_output_directory():
    """Create output directory if it doesn't exist"""
    output_dir = Path("outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def main():
    """Main execution flow for M&A strategy development"""
    init()

    setup_logging()
    logger = get_logger(__name__)

    try:
        logger.info("Starting M&A Strategy Development Process")
        output_dir = ensure_output_directory()
        strategy_agent = StrategyAgent()
        logger.info("Strategy Agent initialized")
        print_welcome()

        strategy: StrategyModel = strategy_agent.run()

        if strategy:
            logger.info("Strategy development completed successfully")
            strategy_path = output_dir / "strategy.md"

            print(
                f"\n{Fore.CYAN}Strategy document has been generated!{Style.RESET_ALL}"
            )
            print(f"You can find it at: {strategy_path.absolute()}\n")
            print(f"{Fore.CYAN}=== Strategy Overview ==={Style.RESET_ALL}")
            print(
                f"{Fore.YELLOW}Primary Goal:{Style.RESET_ALL} {strategy.primary_goal}"
            )
            if strategy.target_criteria.industry:
                print(
                    f"{Fore.YELLOW}Target Industry:{Style.RESET_ALL} {strategy.target_criteria.industry}"
                )
            print("\nFull details are available in the generated markdown file.")
        else:
            logger.warning("Strategy development was not completed")
            print(
                f"\n{Fore.YELLOW}Strategy development was not completed. "
                f"No output file has been generated.{Style.RESET_ALL}"
            )
            sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        print(f"\n{Fore.YELLOW}Process interrupted by user{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        logger.error("Critical error in M&A strategy development", exc_info=True)
        print(f"\n{Fore.RED}An error occurred: {str(e)}{Style.RESET_ALL}")
        raise
    finally:
        print(
            f"\n{Fore.GREEN}Thank you for using the M&A Strategy Development Assistant{Style.RESET_ALL}"
        )
        logger.info("M&A Strategy Development Process completed")


if __name__ == "__main__":
    main()
