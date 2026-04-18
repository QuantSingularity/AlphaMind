from typing import Any, Dict, List, Tuple

import numpy as np
import QuantLib as ql


class CVAcalculator:
    """
    Calculates Credit Valuation Adjustment (CVA) for a portfolio of trades,
    assuming a constant hazard rate for the counterparty.
    """

    def __init__(
        self, portfolio: List[Dict[str, Any]], default_probs: Dict[str, float]
    ) -> None:
        """
        Initializes the calculator.

        Args:
            portfolio: A list of trade dictionaries. Each dict is expected
                       to have an "exposure_profile" key, which is a
                       tuple of (dates_list, exposures_list).
            default_probs: A dictionary containing counterparty default
                           parameters, expecting "hazard_rate" (float)
                           and "recovery_rate" (float).
        """
        self.portfolio = portfolio
        self.default_probs = default_probs
        self.hazard_rate: float = self.default_probs["hazard_rate"]
        self.recovery_rate: float = self.default_probs["recovery_rate"]
        self.lgd: float = 1.0 - self.recovery_rate

    def _survival_probability(self, t: float) -> float:
        """Calculates survival probability S(t) = exp(-hazard_rate * t)."""
        if t <= 0.0:
            return 1.0
        return np.exp(-self.hazard_rate * t)

    def calculate_cva(self, discount_curve: ql.YieldTermStructure) -> float:
        """
        Calculates the total CVA for the portfolio.

        The CVA is calculated as the sum of discounted expected losses:
        CVA = Σ [ LGD * EPE(t_i) * DF(t_i) * PD(t_{i-1}, t_i) ]

        where:
        - LGD = Loss Given Default (1 - recovery_rate)
        - EPE(t_i) = Expected Positive Exposure at time t_i
        - DF(t_i) = Discount Factor at time t_i
        - PD(t_{i-1}, t_i) = Marginal default probability between t_{i-1} and t_i
                           = S(t_{i-1}) - S(t_i)

        Args:
            discount_curve: A QuantLib discount curve object used
                            for discounting and time calculation.

        Returns:
            The total CVA of the portfolio.
        """
        total_cva = 0.0
        for trade in self.portfolio:
            trade_cva = 0.0
            if "exposure_profile" not in trade:
                continue
            exposure_profile: Tuple[list, list] = trade["exposure_profile"]
            dates, exposures = exposure_profile
            if not dates:
                continue
            t_prev = 0.0
            surv_prob_prev = 1.0
            for date, exposure in zip(dates, exposures):
                t = discount_curve.timeFromReference(date)
                if t <= t_prev:
                    continue
                surv_prob_t = self._survival_probability(t)
                marginal_pd = surv_prob_prev - surv_prob_t
                df = discount_curve.discount(t)
                cva_contribution = self.lgd * exposure * df * marginal_pd
                trade_cva += cva_contribution
                t_prev = t
                surv_prob_prev = surv_prob_t
            total_cva += trade_cva
        return total_cva
