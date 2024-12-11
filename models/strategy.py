# mna_automation/models/strategy.py

from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class TargetCriteria(BaseModel):
    """Core criteria for potential acquisition targets"""

    revenue_range: Optional[Dict[str, float]] = Field(default_factory=dict)
    industry: Optional[str] = None
    geography: List[str] = Field(default_factory=list)
    key_requirements: Optional[List[str]] = Field(default_factory=list)


class SuccessMetrics(BaseModel):
    """Metrics to measure acquisition success"""

    primary: List[str] = Field(default_factory=list)
    timeline: Dict[str, str] = Field(default_factory=dict)


class StrategyModel(BaseModel):
    """M&A Strategy Model"""

    primary_goal: Optional[str] = None
    secondary_goals: List[str] = Field(default_factory=list)
    buyer_type: Optional[str] = None  # "financial" or "strategic"
    acquisition_type: Optional[str] = None  # "horizontal" or "vertical"
    target_criteria: TargetCriteria = Field(default_factory=TargetCriteria)
    success_metrics: SuccessMetrics = Field(default_factory=SuccessMetrics)
    risk_considerations: List[str] = Field(default_factory=list)
    implementation_timeline: Dict[str, str] = Field(default_factory=dict)

    def to_markdown(self) -> str:
        """Convert strategy to markdown format"""
        return f"""# M&A Strategy Report

## Executive Summary
Primary Goal: {self.primary_goal or 'Not defined'}
{f'Secondary Goals: {", ".join(self.secondary_goals)}' if self.secondary_goals else ''}

## Acquisition Overview
- Type: {self.acquisition_type or 'To be determined'} acquisition
- Buyer Classification: {self.buyer_type or 'To be determined'} buyer

## Target Criteria
- Industry: {self.target_criteria.industry or 'Not specified'}
- Geography: {', '.join(self.target_criteria.geography) if self.target_criteria.geography else 'Not specified'}
- Revenue Range: {self.target_criteria.revenue_range if self.target_criteria.revenue_range else 'Not specified'}
- Key Requirements: {', '.join(self.target_criteria.key_requirements) if self.target_criteria.key_requirements else 'None specified'}

## Success Metrics
{self._format_metrics_md()}

## Risk Analysis
{self._format_risks_md()}

## Implementation Timeline
{self._format_timeline_md()}
"""

    def _format_metrics_md(self) -> str:
        if not self.success_metrics.primary:
            return "No specific metrics defined"
        return "\n".join([f"- {metric}" for metric in self.success_metrics.primary])

    def _format_risks_md(self) -> str:
        if not self.risk_considerations:
            return "No risks identified"
        return "\n".join([f"- {risk}" for risk in self.risk_considerations])

    def _format_timeline_md(self) -> str:
        if not self.implementation_timeline:
            return "Timeline not yet defined"
        return "\n".join(
            [f"- {k}: {v}" for k, v in self.implementation_timeline.items()]
        )

    def save_to_file(self, directory: str = "output") -> None:
        """Save strategy to markdown file"""
        output_dir = Path(directory)
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / "strategy.md"
        output_path.write_text(self.to_markdown())
