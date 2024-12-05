# M&A Automation

A sophisticated multi-agent system for automated mergers and acquisitions (M&A) processes.

## Overview

M&A are complex processes that require careful planning, execution, and evaluation. Our system is designed to streamline and automate various aspects of this process, from strategy development to legal compliance. The system consists of multiple specialized agents that work together to facilitate the entire M&A lifecycle. Each agent is designed to handle specific aspects of the M&A process while collaborating with other agents and human experts.

## Installation

- Clone the repository
    ```bash
    git clone https://github.com/AdeptTechSolutions/mna-automation.git
    cd mna-automation
    ```

- Install `uv`
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

- Create a virtual environment
    ```bash
    uv venv --python=3.11
    source .venv/bin/activate
    ```

- Sync up the dependencies
    ```bash
    uv sync
    ```

## Project Structure

```bash
mna/
├── pyproject.toml
├── .env
└── mna/
    ├── __init__.py
    ├── main.py
    ├── crew.py
    ├── tools/
    │   ├── __init__.py
    │   ├── fmp_tools.py          # Financial Markets Platform API tools
    │   ├── valuation_tools.py    # Custom valuation calculation tools
    │   ├── document_tools.py     # Document processing tools
    │   └── research_tools.py     # Web research and data collection tools
    ├── config/
    │   ├── agents.yaml           # Agent configurations
    │   ├── tasks.yaml            # Task definitions
    │   └── settings.yaml         # General settings
    └── agents/
        └── __init__.py           # Agent implementations
```

## Configuration

TODO

## Usage

TODO

## License

This project is licensed under the MIT License. See the LICENSE file for details.