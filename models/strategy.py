# mna_automation/models/strategy.py

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class WebSearchCriteria(BaseModel):
    """Criteria for Web Search Agent"""

    target_keywords: List[str] = Field(default_factory=list)
    revenue_range: Optional[Dict[str, float]] = Field(default_factory=dict)
    location_preferences: List[str] = Field(default_factory=list)
    excluded_terms: List[str] = Field(default_factory=list)
    priority_metrics: List[str] = Field(default_factory=list)


class DataExtractionRequirements(BaseModel):
    """Requirements for Data Collection Agent"""

    required_financials: List[str] = Field(default_factory=list)
    time_period: str = "TTM"  # Trailing Twelve Months by default
    key_metrics: List[str] = Field(default_factory=list)
    comparison_factors: List[str] = Field(default_factory=list)


class ValuationParameters(BaseModel):
    """Parameters for Valuation Agent"""

    preferred_methods: List[str] = Field(default_factory=list)
    synergy_factors: List[str] = Field(default_factory=list)
    risk_factors: List[str] = Field(default_factory=list)
    target_metrics: Dict[str, float] = Field(default_factory=dict)


class TargetCriteria(BaseModel):
    revenue_range: Optional[Dict[str, float]] = Field(default_factory=dict)
    industry: Optional[str] = None
    geography: List[str] = Field(default_factory=list)
    technologies: Optional[List[str]] = Field(default_factory=list)
    talents: Optional[List[str]] = Field(default_factory=list)
    other_criteria: Optional[Dict[str, str]] = Field(default_factory=dict)


class SuccessMetrics(BaseModel):
    financial: List[str] = Field(default_factory=list)
    operational: List[str] = Field(default_factory=list)
    strategic: List[str] = Field(default_factory=list)
    timeline: Dict[str, str] = Field(default_factory=dict)


class StrategyModel(BaseModel):
    primary_goal: Optional[str] = None
    secondary_goals: List[str] = Field(default_factory=list)
    buyer_type: Optional[str] = None  # "financial" or "strategic"
    acquisition_type: Optional[str] = None  # "horizontal" or "vertical"
    target_criteria: TargetCriteria = Field(default_factory=TargetCriteria)
    success_metrics: SuccessMetrics = Field(default_factory=SuccessMetrics)
    risk_considerations: List[str] = Field(default_factory=list)
    implementation_timeline: Dict[str, str] = Field(default_factory=dict)
    web_search_criteria: WebSearchCriteria = Field(default_factory=WebSearchCriteria)
    data_requirements: DataExtractionRequirements = Field(
        default_factory=DataExtractionRequirements
    )
    valuation_parameters: ValuationParameters = Field(
        default_factory=ValuationParameters
    )
    next_steps: Dict[str, List[str]] = Field(default_factory=dict)

    def formatted_output(self) -> str:
        """Format strategy for human-readable output"""
        return f"""
        Acquisition Strategy Summary:
        
        1. Strategic Goals:
           - Primary: {self.primary_goal or 'Not yet defined'}
           - Secondary: {', '.join(self.secondary_goals) if self.secondary_goals else 'None specified'}
        
        2. Acquisition Type:
           - Buyer Type: {self.buyer_type or 'To be determined'}
           - Structure: {self.acquisition_type or 'To be determined'}
        
        3. Target Criteria:
           - Industry: {self.target_criteria.industry or 'Not yet specified'}
           - Geography: {', '.join(self.target_criteria.geography) if self.target_criteria.geography else 'Not specified'}
           - Revenue Range: {self.target_criteria.revenue_range if self.target_criteria.revenue_range else 'Not specified'}
        
        4. Success Metrics:
           - Financial: {', '.join(self.success_metrics.financial) if self.success_metrics.financial else 'Not yet defined'}
           - Operational: {', '.join(self.success_metrics.operational) if self.success_metrics.operational else 'Not yet defined'}
           - Strategic: {', '.join(self.success_metrics.strategic) if self.success_metrics.strategic else 'Not yet defined'}
        
        5. Implementation Timeline:
           {self._format_timeline()}
        
        6. Risk Considerations:
           {self._format_risks()}
        
        7. Next Steps:
           {self._format_next_steps()}
        """

    def _format_timeline(self) -> str:
        if not self.implementation_timeline:
            return "           Not yet defined"
        return "\n           ".join(
            [f"{k}: {v}" for k, v in self.implementation_timeline.items()]
        )

    def _format_risks(self) -> str:
        if not self.risk_considerations:
            return "           No risks identified yet"
        return "\n           ".join([f"- {risk}" for risk in self.risk_considerations])

    def _format_next_steps(self) -> str:
        if not self.next_steps:
            return "           Next steps not yet defined"
        return "\n           ".join(
            [
                f"{k}:\n              - {', '.join(v)}"
                for k, v in self.next_steps.items()
            ]
        )
