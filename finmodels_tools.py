import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import numpy_financial as npf

from fmp_tools import FMPTools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FinModelError(Exception):
    """Custom exception for financial modeling errors."""

    pass


class FinModelsTools:
    """Financial modeling tools for LBO and IPO analysis."""

    def __init__(self, fmp_api_key: str):
        """Initialize with FMP API key.

        Args:
            fmp_api_key (str): Financial Modeling Prep API key
        """
        self.fmp = FMPTools(fmp_api_key)

    def calculate_lbo_metrics(
        self,
        symbol: str,
        holding_period: int = 5,
        target_irr: float = 0.20,
        debt_ratio: float = 0.7,
        interest_rate: float = 0.08,
        fcf_growth_rate: float = 0.10,
        debt_repayment_pct: float = 0.30,
        exit_multiple: float = 10.0,
        exit_ebitda_growth: float = 0.08,
    ) -> Dict[str, Any]:
        """Calculate LBO analysis metrics."""
        data = self.fmp.get_complete_lbo_data(symbol)
        if not data:
            raise FinModelError(f"Failed to get LBO data for {symbol}")

        try:
            ev = data["capital_structure"]["enterprise_value"]
            ebitda = data["financials"]["income_statement"]["ebitda"][0]
            fcf = data["financials"]["cash_flow"]["free_cash_flow"][0]

            debt = ev * debt_ratio
            equity = ev - debt

            projected_fcf = []
            remaining_debt = debt
            for year in range(holding_period):
                fcf_growth = fcf * (1 + fcf_growth_rate) ** year
                debt_repayment = min(fcf_growth * debt_repayment_pct, remaining_debt)
                remaining_debt -= debt_repayment
                interest_expense = remaining_debt * interest_rate
                free_cash_after_debt = fcf_growth - interest_expense - debt_repayment
                projected_fcf.append(free_cash_after_debt)

            exit_ebitda = ebitda * (1 + exit_ebitda_growth) ** holding_period
            exit_value = exit_ebitda * exit_multiple
            exit_equity = exit_value - remaining_debt

            cash_flows = [-equity] + projected_fcf + [exit_equity]

            try:
                irr = npf.irr(cash_flows)
                if np.isnan(irr):
                    irr = "Unable to calculate (nan)"
                else:
                    irr = float(irr)
            except Exception as e:
                irr = f"Error: {str(e)}"

            moic = exit_equity / equity if equity != 0 else "N/A (division by zero)"

            return {
                "purchase_price": {
                    "enterprise_value": ev,
                    "equity_contribution": equity,
                    "debt_financing": debt,
                    "debt_ratio": debt_ratio,
                },
                "projections": {
                    "projected_fcf": projected_fcf,
                    "exit_value": exit_value,
                    "remaining_debt": remaining_debt,
                },
                "returns": {"irr": irr, "moic": moic, "exit_equity": exit_equity},
            }
        except Exception as e:
            raise FinModelError(f"Error calculating LBO metrics: {str(e)}")

    def calculate_ipo_valuation(
        self, symbol: str, target_float: float = 0.20, price_range_buffer: float = 0.15
    ) -> Dict[str, Any]:
        """Calculate IPO valuation metrics.

        Args:
            symbol (str): Company stock symbol
            target_float (float): Target percentage of shares to float
            price_range_buffer (float): Buffer for price range calculation

        Returns:
            Dict[str, Any]: IPO valuation results
        """

        data = self.fmp.get_complete_ipo_data(symbol)
        if not data:
            raise FinModelError(f"Failed to get IPO data for {symbol}")

        try:
            metrics = data["metrics"]
            peer_data = data["peer_analysis"]

            revenue = metrics["valuation_metrics"]["ev_to_sales"][0] or 0
            ebitda = metrics["valuation_metrics"]["ev_to_ebitda"][0] or 0
            pe_ratio = metrics["valuation_metrics"]["pe_ratio"][0]

            revenue_growth = metrics["growth_metrics"]["revenue_growth"][0]
            ebit_growth = metrics["growth_metrics"]["ebit_growth"][0]

            peer_companies = peer_data["peer_companies"]
            sector_pe = peer_data["sector_multiples"].get(
                metrics["company_profile"]["sector"]
            )
            if sector_pe is None or sector_pe == 0:
                sector_pe = pe_ratio if pe_ratio and pe_ratio != 0 else 15

            ev_revenue = (revenue * sector_pe) if revenue and sector_pe else 0
            ev_ebitda = (ebitda * 10) if ebitda else 0

            if ev_revenue and ev_ebitda:

                if revenue_growth > 0.3:
                    enterprise_value = (ev_revenue * 0.7) + (ev_ebitda * 0.3)
                else:
                    enterprise_value = (ev_revenue * 0.3) + (ev_ebitda * 0.7)
            elif ev_revenue:
                enterprise_value = ev_revenue
            else:
                enterprise_value = ev_ebitda

            debt = metrics["valuation_metrics"]["debt_to_equity"][0]
            equity_value = enterprise_value - debt

            shares_outstanding = equity_value / metrics["company_profile"]["market_cap"]
            float_shares = shares_outstanding * target_float

            base_price = equity_value / shares_outstanding
            price_low = base_price * (1 - price_range_buffer)
            price_high = base_price * (1 + price_range_buffer)

            ev_revenue_multiple = (
                ev_revenue / revenue if revenue and revenue != 0 else "N/A"
            )
            ev_ebitda_multiple = ev_ebitda / ebitda if ebitda and ebitda != 0 else "N/A"

            return {
                "valuation": {
                    "enterprise_value": enterprise_value,
                    "equity_value": equity_value,
                    "ev_revenue_multiple": ev_revenue_multiple,
                    "ev_ebitda_multiple": ev_ebitda_multiple,
                },
                "offering": {
                    "shares_outstanding": shares_outstanding,
                    "float_shares": float_shares,
                    "price_range": {
                        "low": price_low,
                        "base": base_price,
                        "high": price_high,
                    },
                },
                "comparables": {
                    "sector_pe": sector_pe,
                    "peer_companies": peer_companies,
                    "revenue_growth": revenue_growth,
                    "ebit_growth": ebit_growth,
                },
            }
        except Exception as e:
            raise FinModelError(f"Error in IPO valuation: {str(e)}")

    def perform_lbo_sensitivity_analysis(
        self,
        symbol: str,
        fcf_growth_rates: List[float] = [0.05, 0.08, 0.10, 0.12, 0.15],
        exit_multiples: List[float] = [8.0, 10.0, 12.0, 14.0, 16.0],
        interest_rates: List[float] = [0.06, 0.07, 0.08, 0.09, 0.10],
        holding_period: int = 5,
        target_irr: float = 0.20,
        debt_ratio: float = 0.7,
        debt_repayment_pct: float = 0.30,
        exit_ebitda_growth: float = 0.08,
    ) -> Dict[str, Any]:
        """Perform sensitivity analysis for LBO analysis.

        Args:
            symbol (str): Company stock symbol
            fcf_growth_rates (List[float]): Range of FCF growth rates to analyze
            exit_multiples (List[float]): Range of exit multiples to analyze
            interest_rates (List[float]): Range of interest rates to analyze
            holding_period (int): Investment holding period in years
            target_irr (float): Target internal rate of return
            debt_ratio (float): Initial debt to enterprise value ratio
            debt_repayment_pct (float): Debt repayment percentage of FCF
            exit_ebitda_growth (float): Exit EBITDA growth rate

        Returns:
            Dict[str, Any]: Sensitivity analysis results
        """

        data = self.fmp.get_complete_lbo_data(symbol)
        if not data:
            raise FinModelError(f"Failed to get LBO data for {symbol}")

        try:
            ev = data["capital_structure"]["enterprise_value"]
            ebitda = data["financials"]["income_statement"]["ebitda"][0]
            fcf = data["financials"]["cash_flow"]["free_cash_flow"][0]

            results = {
                "fcf_growth_rate": [],
                "exit_multiple": [],
                "interest_rate": [],
                "irr": [],
                "moic": [],
            }

            for growth_rate in fcf_growth_rates:
                for multiple in exit_multiples:
                    for rate in interest_rates:

                        debt = ev * debt_ratio
                        equity = ev - debt

                        projected_fcf = []
                        remaining_debt = debt
                        for year in range(holding_period):

                            fcf_growth = fcf * (1 + growth_rate) ** year

                            debt_repayment = min(
                                fcf_growth * debt_repayment_pct, remaining_debt
                            )
                            remaining_debt -= debt_repayment

                            interest_expense = remaining_debt * rate

                            free_cash_after_debt = (
                                fcf_growth - interest_expense - debt_repayment
                            )
                            available_cash = data["financials"]["balance_sheet"][
                                "cash"
                            ][0]
                            free_cash_after_debt = max(
                                free_cash_after_debt, -available_cash
                            )

                            projected_fcf.append(free_cash_after_debt)

                        exit_ebitda = (
                            ebitda * (1 + exit_ebitda_growth) ** holding_period
                        )
                        exit_value = exit_ebitda * multiple

                        total_investment = equity
                        exit_equity = exit_value - remaining_debt

                        cash_flows = [-total_investment] + projected_fcf + [exit_equity]
                        irr = npf.irr(cash_flows)

                        moic = exit_equity / total_investment

                        results["fcf_growth_rate"].append(growth_rate)
                        results["exit_multiple"].append(multiple)
                        results["interest_rate"].append(rate)
                        results["irr"].append(irr)
                        results["moic"].append(moic)

            return results
        except Exception as e:
            raise FinModelError(f"Error in LBO sensitivity analysis: {str(e)}")

    def perform_ipo_sensitivity_analysis(
        self,
        symbol: str,
        target_floats: List[float] = [0.15, 0.20, 0.25, 0.30, 0.35],
        price_range_buffers: List[float] = [0.10, 0.15, 0.20, 0.25, 0.30],
    ) -> Dict[str, Any]:
        """Perform sensitivity analysis for IPO analysis.

        Args:
            symbol (str): Company stock symbol
            target_floats (List[float]): Range of target float percentages to analyze
            price_range_buffers (List[float]): Range of price range buffers to analyze

        Returns:
            Dict[str, Any]: Sensitivity analysis results
        """

        data = self.fmp.get_complete_ipo_data(symbol)
        if not data:
            raise FinModelError(f"Failed to get IPO data for {symbol}")

        try:
            metrics = data["metrics"]
            peer_data = data["peer_analysis"]

            revenue = metrics["valuation_metrics"]["ev_to_sales"][0] or 0
            ebitda = metrics["valuation_metrics"]["ev_to_ebitda"][0] or 0
            pe_ratio = metrics["valuation_metrics"]["pe_ratio"][0]

            revenue_growth = metrics["growth_metrics"]["revenue_growth"][0]
            ebit_growth = metrics["growth_metrics"]["ebit_growth"][0]

            peer_companies = peer_data["peer_companies"]
            sector_pe = peer_data["sector_multiples"].get(
                metrics["company_profile"]["sector"]
            )
            if sector_pe is None:
                sector_pe = pe_ratio if pe_ratio else 15

            ev_revenue = (revenue * sector_pe) if revenue else 0
            ev_ebitda = (ebitda * 10) if ebitda else 0

            if ev_revenue and ev_ebitda:

                if revenue_growth > 0.3:
                    enterprise_value = (ev_revenue * 0.7) + (ev_ebitda * 0.3)
                else:
                    enterprise_value = (ev_revenue * 0.3) + (ev_ebitda * 0.7)
            elif ev_revenue:
                enterprise_value = ev_revenue
            else:
                enterprise_value = ev_ebitda

            results = {
                "target_float": [],
                "price_range_buffer": [],
                "equity_value": [],
                "price_low": [],
                "price_base": [],
                "price_high": [],
                "float_shares": [],
            }

            for target_float in target_floats:
                for buffer in price_range_buffers:

                    debt = metrics["valuation_metrics"]["debt_to_equity"][0]
                    equity_value = enterprise_value - debt

                    shares_outstanding = (
                        equity_value / metrics["company_profile"]["market_cap"]
                    )
                    float_shares = shares_outstanding * target_float

                    base_price = equity_value / shares_outstanding
                    price_low = base_price * (1 - buffer)
                    price_high = base_price * (1 + buffer)

                    results["target_float"].append(target_float)
                    results["price_range_buffer"].append(buffer)
                    results["equity_value"].append(equity_value)
                    results["price_low"].append(price_low)
                    results["price_base"].append(base_price)
                    results["price_high"].append(price_high)
                    results["float_shares"].append(float_shares)

            return results
        except Exception as e:
            raise FinModelError(f"Error in IPO sensitivity analysis: {str(e)}")
