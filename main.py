# main.py

import os
from pathlib import Path

import dotenv
from crewai import LLM, Crew, Task
from crewai_tools import FileWriterTool

from agents.strategy import StrategyAgent

dotenv.load_dotenv()


def main():
    llm = LLM(
        api_key=os.getenv("GEMINI_API_KEY"),
        model="gemini/gemini-1.5-pro",
    )

    output_dir = "outputs"
    output_dir.mkdir(exist_ok=True)
    file_writer = FileWriterTool(directory=str(output_dir))

    print("\n=== M&A Strategy Development System ===")
    print("Let's develop your acquisition strategy through a conversation.")

    strategy_agent = StrategyAgent(llm=llm, tools=[file_writer])
    context = strategy_agent.gather_context()

    while True:
        strategy_task = strategy_agent.create_strategy_task(
            context, output_dir=output_dir
        )

        print("\nGenerating M&A strategy...")

        crew = Crew(
            agents=[strategy_agent.agent],
            tasks=[strategy_task],
        )

        try:
            result = crew.kickoff()
            if isinstance(result, str):
                file_writer._run(
                    filename="strategy.md",
                    content=result,
                    directory=str(output_dir),
                    overwrite="True",
                )
                print(f"\nStrategy saved to outputs/strategy.md")
            else:
                print("\nStrategy generation completed")

        except Exception as e:
            print(f"\nError generating strategy: {e}")
            print("Let's gather more information to create a better strategy.")
            context = strategy_agent.gather_context()
            continue

        while True:
            improvements = input(
                "\nWhat aspects of the strategy would you like to improve?\n"
                "1. Company information\n"
                "2. Objectives\n"
                "3. Target criteria\n"
                "4. Exit\n"
                "Enter your choice (1-4): "
            ).strip()

            if improvements == "4":
                return
            elif improvements in ["1", "2", "3"]:
                print("\nUpdating strategy based on your feedback...")
                context = strategy_agent.update_context(
                    context,
                    {"1": "company", "2": "objectives", "3": "target"}[improvements],
                )
                break
            else:
                print("Please enter a valid choice (1-4)")


if __name__ == "__main__":
    main()
