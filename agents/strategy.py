# agents/strategy.py

from pathlib import Path
from typing import Dict, List, Optional

import yaml
from crewai import Agent, Task
from pydantic import BaseModel, Field, field_validator


class CompanyProfile(BaseModel):
    industry: Optional[str] = None
    size: Optional[str] = None
    core_business: Optional[str] = None
    growth_stage: Optional[str] = None
    current_markets: Optional[List[str]] = None
    annual_revenue: Optional[str] = None
    employees: Optional[str] = None

    @field_validator("size")
    @classmethod
    def validate_size(cls, v):
        if v is None:
            return v
        valid_sizes = ["startup", "sme", "enterprise"]
        if v.lower() not in valid_sizes:
            raise ValueError(f"Size must be one of {valid_sizes}")
        return v.lower()

    @field_validator("growth_stage")
    @classmethod
    def validate_growth_stage(cls, v):
        if v is None:
            return v
        valid_stages = ["early", "growth", "mature", "decline"]
        if v.lower() not in valid_stages:
            raise ValueError(f"Growth stage must be one of {valid_stages}")
        return v.lower()


class AcquisitionObjectives(BaseModel):
    primary_objective: Optional[str] = None
    secondary_objectives: Optional[List[str]] = None
    target_timeline: Optional[str] = None
    budget_range: Optional[str] = None

    @field_validator("secondary_objectives")
    @classmethod
    def validate_secondary_objectives(cls, v):
        if v is None:
            return []
        return [obj.strip() for obj in v if obj.strip()]


class TargetCriteria(BaseModel):
    revenue_range: Optional[str] = None
    regions: Optional[List[str]] = None
    key_capabilities: Optional[List[str]] = None
    customer_focus: Optional[str] = None
    preferred_deal_type: Optional[str] = None

    @field_validator("regions", "key_capabilities")
    @classmethod
    def validate_lists(cls, v):
        if v is None:
            return []
        return [item.strip() for item in v if item.strip()]


class StrategyContext(BaseModel):
    company_profile: CompanyProfile
    objectives: AcquisitionObjectives
    target_criteria: TargetCriteria


class StrategyAgent(BaseModel):
    llm: object = Field(description="LLM instance to use for the agent")
    tools: List = Field(default_factory=list, description="List of tools for the agent")
    agent: Optional[Agent] = Field(default=None, description="CrewAI agent instance")
    config: Optional[Dict] = Field(default=None, description="Agent configuration")

    class Config:
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        self.config = self._load_config()
        self.agent = self._create_agent()

    def _load_config(self) -> Dict:
        config_path = Path(__file__).parent.parent / "config" / "strategy.yaml"
        with open(config_path) as f:
            return yaml.safe_load(f)

    def _create_agent(self) -> Agent:
        return Agent(
            role=self.config["agent"]["role"],
            goal=self.config["agent"]["goal"],
            backstory=self.config["agent"]["backstory"],
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=self.tools,
        )

    def gather_context(self) -> StrategyContext:
        print("\nLet's start by understanding your company and acquisition goals.")

        while True:
            company_profile = self._gather_company_profile_conversational()
            if not company_profile.industry:
                print("\nIndustry information is essential for developing a strategy.")
                continue
            if not company_profile.core_business:
                should_continue = input(
                    "\nIt would help to know your core business. Would you like to provide this information? (y/n): "
                ).lower()
                if should_continue == "y":
                    continue
            break

        while True:
            objectives = self._gather_objectives_conversational()
            if not objectives.primary_objective:
                print(
                    "\nA primary objective is essential for developing an acquisition strategy."
                )
                continue
            break

        while True:
            target_criteria = self._gather_target_criteria_conversational()
            if not any(
                [
                    target_criteria.revenue_range,
                    target_criteria.regions,
                    target_criteria.key_capabilities,
                ]
            ):
                should_continue = input(
                    "\nProviding some target criteria would help develop a better strategy. Would you like to add some criteria? (y/n): "
                ).lower()
                if should_continue == "y":
                    continue
            break

        return StrategyContext(
            company_profile=company_profile,
            objectives=objectives,
            target_criteria=target_criteria,
        )

    def _get_optional_input(
        self, prompt: str, examples: List[str] = None
    ) -> Optional[str]:
        if examples:
            example_str = f" (e.g., {', '.join(examples)})"
        else:
            example_str = ""
        response = input(f"{prompt}{example_str} (press Enter to skip): ").strip()
        return response if response else None

    def _gather_company_profile_conversational(self) -> CompanyProfile:
        print("\nFirst, tell me about your company.")

        while True:
            industry = input("What industry are you in? ").strip()
            if not industry:
                print(
                    "Industry information is required to proceed. Please provide your industry."
                )
                continue
            break

        print(
            f"\nValid company sizes: {', '.join(self.config['input_validation']['company_profile']['size']['valid_options'])}"
        )
        size = self._get_optional_input("How would you categorize your company size?")

        while True:
            core_business = self._get_optional_input(
                "What's your core business or main products?"
            )
            if not core_business:
                print(
                    "\nUnderstanding your core business will help develop a more targeted strategy."
                )
                should_continue = input(
                    "Would you like to provide this information? (y/n): "
                ).lower()
                if should_continue != "y":
                    break
                continue
            break

        if core_business:
            print(
                f"\nValid growth stages: {', '.join(self.config['input_validation']['company_profile']['growth_stage']['valid_options'])}"
            )
            growth_stage = self._get_optional_input(
                "What growth stage is your company in?"
            )
        else:
            growth_stage = None

        current_markets = self._get_optional_input(
            "Which markets do you currently operate in? (comma-separated)"
        )
        annual_revenue = self._get_optional_input("What's your annual revenue?")
        employees = self._get_optional_input("How many employees do you have?")

        return CompanyProfile(
            industry=industry,
            size=size,
            core_business=core_business,
            growth_stage=growth_stage,
            current_markets=current_markets.split(",") if current_markets else None,
            annual_revenue=annual_revenue,
            employees=employees,
        )

    def _gather_objectives_conversational(self) -> AcquisitionObjectives:
        print("\nNow, let's discuss your acquisition objectives.")

        validation_config = self.config["input_validation"].get(
            "acquisition_objectives", {}
        )

        if "primary_objectives" in validation_config:
            print(
                f"\nCommon objectives include: {', '.join(validation_config['primary_objectives'])}"
            )

        primary_objective = input(
            "What's your primary goal for this acquisition? "
        ).strip()

        if primary_objective:
            secondary_objectives = self._get_optional_input(
                "Any secondary objectives? (comma-separated)"
            )

            if "timeline_ranges" in validation_config:
                print(
                    f"\nTypical timelines: {', '.join(validation_config['timeline_ranges'])}"
                )
            target_timeline = self._get_optional_input(
                "What's your target timeline for completion?"
            )

            if "budget_ranges" in validation_config:
                print(
                    f"\nTypical budget ranges: {', '.join(validation_config['budget_ranges']['examples'])}"
                )
            budget_range = self._get_optional_input(
                "Do you have a budget range in mind?"
            )
        else:
            secondary_objectives = target_timeline = budget_range = None

        return AcquisitionObjectives(
            primary_objective=primary_objective,
            secondary_objectives=(
                secondary_objectives.split(",") if secondary_objectives else None
            ),
            target_timeline=target_timeline,
            budget_range=budget_range,
        )

    def _gather_target_criteria_conversational(self) -> TargetCriteria:
        print("\nFinally, let's define what you're looking for in potential targets.")

        revenue_range = self._get_optional_input(
            "What revenue range are you targeting?"
        )

        if revenue_range:
            regions = self._get_optional_input(
                "Which regions are you interested in? (comma-separated)"
            )
            key_capabilities = self._get_optional_input(
                "What capabilities or technologies are you looking for? (comma-separated)"
            )
            customer_focus = self._get_optional_input(
                "What customer segment should the target focus on?"
            )
            preferred_deal_type = self._get_optional_input(
                "Do you have a preferred deal type?"
            )
        else:
            regions = key_capabilities = customer_focus = preferred_deal_type = None

        return TargetCriteria(
            revenue_range=revenue_range,
            regions=regions.split(",") if regions else None,
            key_capabilities=key_capabilities.split(",") if key_capabilities else None,
            customer_focus=customer_focus,
            preferred_deal_type=preferred_deal_type,
        )

    def update_context(
        self, context: StrategyContext, improvements: str
    ) -> StrategyContext:
        print("\nLet's address your requested improvements.")

        # Update company profile if needed
        if any(
            keyword in improvements.lower()
            for keyword in ["company", "industry", "size", "business"]
        ):
            context.company_profile = self._gather_company_profile_conversational()

        # Update objectives if needed
        if any(
            keyword in improvements.lower()
            for keyword in ["objective", "goal", "timeline", "budget"]
        ):
            context.objectives = self._gather_objectives_conversational()

        # Update target criteria if needed
        if any(
            keyword in improvements.lower()
            for keyword in ["target", "criteria", "revenue", "region"]
        ):
            context.target_criteria = self._gather_target_criteria_conversational()

        return context

    def create_strategy_task(self, context: StrategyContext, output_dir: str) -> Task:
        prompt = self._generate_prompt(context)
        return Task(
            description=prompt,
            expected_output=self._generate_expected_output(),
            agent=self.agent,
            output_file=f"{output_dir}/strategy.md",
        )

    def _generate_expected_output(self) -> str:
        """Generate the expected output structure for the strategy document in markdown format."""
        output_structure = self.config["output_structure"]["sections"]
        sections = []

        for section in output_structure:
            if section.get("required", False):
                components = "\n".join(
                    [f"- {comp}" for comp in section["key_components"]]
                )
                sections.append(f"# {section['title']}\n\n{components}")

        return "\n\n".join(sections)

    def _generate_prompt(self, context: StrategyContext) -> str:
        framework = self.config["strategy_framework"]

        # Only include populated fields in the prompt
        company_info = []
        if context.company_profile.industry:
            company_info.append(f"Industry: {context.company_profile.industry}")
        if context.company_profile.size:
            company_info.append(f"Size: {context.company_profile.size}")
        if context.company_profile.core_business:
            company_info.append(
                f"Core Business: {context.company_profile.core_business}"
            )
        if context.company_profile.growth_stage:
            company_info.append(f"Growth Stage: {context.company_profile.growth_stage}")
        if context.company_profile.current_markets:
            company_info.append(
                f"Current Markets: {', '.join(context.company_profile.current_markets)}"
            )
        if context.company_profile.annual_revenue:
            company_info.append(
                f"Annual Revenue: {context.company_profile.annual_revenue}"
            )
        if context.company_profile.employees:
            company_info.append(f"Employees: {context.company_profile.employees}")

        objectives_info = []
        if context.objectives.primary_objective:
            objectives_info.append(f"Primary: {context.objectives.primary_objective}")
        if context.objectives.secondary_objectives:
            objectives_info.append(
                f"Secondary: {', '.join(context.objectives.secondary_objectives)}"
            )
        if context.objectives.target_timeline:
            objectives_info.append(f"Timeline: {context.objectives.target_timeline}")
        if context.objectives.budget_range:
            objectives_info.append(f"Budget Range: {context.objectives.budget_range}")

        target_info = []
        if context.target_criteria.revenue_range:
            target_info.append(
                f"Revenue Range: {context.target_criteria.revenue_range}"
            )
        if context.target_criteria.regions:
            target_info.append(f"Regions: {', '.join(context.target_criteria.regions)}")
        if context.target_criteria.key_capabilities:
            target_info.append(
                f"Key Capabilities: {', '.join(context.target_criteria.key_capabilities)}"
            )
        if context.target_criteria.customer_focus:
            target_info.append(
                f"Customer Focus: {context.target_criteria.customer_focus}"
            )
        if context.target_criteria.preferred_deal_type:
            target_info.append(
                f"Preferred Deal Type: {context.target_criteria.preferred_deal_type}"
            )

        prompt = "Based on the provided information, develop a comprehensive M&A strategy.\n\n"

        if company_info:
            prompt += (
                "Company Profile:\n"
                + "\n".join(f"- {info}" for info in company_info)
                + "\n\n"
            )

        if objectives_info:
            prompt += (
                "Acquisition Objectives:\n"
                + "\n".join(f"- {info}" for info in objectives_info)
                + "\n\n"
            )

        if target_info:
            prompt += (
                "Target Criteria:\n"
                + "\n".join(f"- {info}" for info in target_info)
                + "\n\n"
            )

        prompt += """Analysis Framework:

            1. Market Assessment:
            {}

            2. Synergy Evaluation:
            {}

            3. Risk Analysis:
            {}

            Success Metrics:
            1. Financial:
            {}

            2. Operational:
            {}

            3. Strategic:
            {}

            Develop a clear, actionable strategy document that addresses the provided information 
            and follows the standard M&A strategy framework. Focus on concrete recommendations 
            and specific action items.""".format(
            "\n".join(
                f"   - {item}"
                for item in framework["analysis_components"]["market_assessment"]
            ),
            "\n".join(
                f"   - {item}"
                for item in framework["analysis_components"]["synergy_evaluation"]
            ),
            "\n".join(
                f"   - {item}"
                for item in framework["analysis_components"]["risk_factors"]
            ),
            "\n".join(
                f"   - {item}" for item in framework["success_metrics"]["financial"]
            ),
            "\n".join(
                f"   - {item}" for item in framework["success_metrics"]["operational"]
            ),
            "\n".join(
                f"   - {item}" for item in framework["success_metrics"]["strategic"]
            ),
        )

        return prompt
