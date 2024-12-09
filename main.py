# mna_automation/main.py

import sys

from colorama import Fore, Style, init

from agents.strategy_agent.agent import StrategyAgent
from models.strategy import StrategyModel
from utils.logger import get_logger, setup_logging


def print_welcome():
    print(
        f"\n{Style.BRIGHT}{Fore.CYAN}=== M&A Strategy Development Process ==={Style.RESET_ALL}"
    )
    print(f"{Fore.YELLOW}Commands:{Style.RESET_ALL}")
    print("- Press Ctrl+C to interrupt the process")
    print("- Type 'exit' to end the conversation")
    print(
        f"\n{Fore.GREEN}Let's begin developing your M&A strategy...{Style.RESET_ALL}\n"
    )
    print("=" * 50 + "\n")


def main():
    """Main execution flow for M&A automation"""
    # Initialize colorama
    init()

    # Setup logging
    setup_logging()
    logger = get_logger(__name__)

    try:
        logger.info("Starting M&A Automation Process")

        strategy_agent = StrategyAgent()
        logger.info("Strategy Agent initialized")

        print_welcome()

        strategy: StrategyModel = strategy_agent.run()

        if strategy:
            logger.info("Strategy development completed successfully")
            print(f"\n{Fore.CYAN}=== Final Strategy ==={Style.RESET_ALL}")
            print(strategy.formatted_output())
        else:
            logger.warning("Strategy development was not completed")
            print(
                f"\n{Fore.YELLOW}Strategy development was not completed. Exiting the program.{Style.RESET_ALL}"
            )
            sys.exit(0)  # Exit gracefully

        return strategy

        # TODO: Initialize and run subsequent agents
        # web_search_agent = WebSearchAgent(strategy)
        # data_collection_agent = DataCollectionAgent(strategy)
        # valuation_agent = ValuationAgent(strategy)

    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        print("\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error("Critical error in M&A automation", exc_info=True)
        print(f"\nAn error occurred: {str(e)}")
        raise
    finally:
        print(
            f"\n{Fore.GREEN}Thank you for using the M&A Automation System{Style.RESET_ALL}"
        )
        logger.info("M&A Automation Process completed")


if __name__ == "__main__":
    main()
