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

- Create a virtual environment using `venv`
    ```bash
    python3.11 -m venv mna
    source mna/bin/activate
    ```

- Alternatively, use `mamba` to create the virtual environment
    ```bash
    mamba env create -n mna python=3.11
    maamba activate mna
    ```

- Install the required dependencies
    ```bash
    pip install -r requirements.txt
    ```

## Project Structure
```
mna_automation/
├── README.md
├── requirements.txt
├── main.py
├── config/
│   └── settings.py
├── agents/
│   ├── base_agent.py
│   ├── strategy_agent/
│   ├── web_search_agent/
│   ├── data_collection_agent/
│   ├── valuation_agent/
│   ├── due_diligence_agent/
│   ├── negotiation_agent/
│   └── legal_agent/
├── models/
│   └── strategy.py
│   ... [more models]
└── utils/
    ├── logger.py
    ├── utils.py
    └── web.py
```

## Configuration

TODO

## Usage

Run the main script to start the M&A automation system
```bash
python main.py
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.