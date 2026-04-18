"""
Statistical analysis utilities for A/B testing.

This module provides classes for performing statistical analysis
on A/B test results, including hypothesis testing, confidence intervals,
and Bayesian analysis.
"""

import logging
from typing import Any, Dict, List

import numpy as np
import scipy.stats as stats

logger = logging.getLogger(__name__)


class StatisticalTest:
    """
    Base class for statistical tests.

    This class provides a common interface for all statistical tests
    in the A/B testing framework.
    """

    def __init__(self) -> None:
        self.results = {}

    def run(self, control: np.ndarray, treatment: np.ndarray, **kwargs) -> Dict:
        """
        Run the statistical test.

        Parameters
        ----------
        control : array-like
            Control group data.
        treatment : array-like
            Treatment group data.
        **kwargs : dict
            Additional arguments for the test.

        Returns
        -------
        results : dict
            Test results.
        """
        raise NotImplementedError("Subclasses must implement this method")

    def get_results(self) -> Dict:
        """
        Get the test results.

        Returns
        -------
        results : dict
            Test results.
        """
        return self.results

    def is_significant(self, alpha: float = 0.05) -> bool:
        """
        Check if the test result is statistically significant.

        Parameters
        ----------
        alpha : float, default=0.05
            Significance level.

        Returns
        -------
        is_significant : bool
            Whether the test result is statistically significant.
        """
        if "p_value" not in self.results:
            raise ValueError("Test has not been run yet")
        return self.results["p_value"] < alpha


class TTest(StatisticalTest):
    """
    Student's t-test for comparing means.

    This class provides methods for performing t-tests
    on A/B test results.
    """

    def run(
        self,
        control: np.ndarray,
        treatment: np.ndarray,
        equal_var: bool = False,
        alternative: str = "two-sided",
    ) -> Dict:
        """
        Run a t-test.

        Parameters
        ----------
        control : array-like
            Control group data.
        treatment : array-like
            Treatment group data.
        equal_var : bool, default=False
            Whether to assume equal variances.
            If False, performs Welch's t-test.
        alternative : str, default="two-sided"
            Alternative hypothesis. Options: "two-sided", "less", "greater".

        Returns
        -------
        results : dict
            Test results.
        """
        control = np.asarray(control, dtype=float)
        treatment = np.asarray(treatment, dtype=float)
        control = control[~np.isnan(control)]
        treatment = treatment[~np.isnan(treatment)]
        control_n = len(control)
        treatment_n = len(treatment)
        if control_n < 2 or treatment_n < 2:
            raise ValueError("Both groups must have at least two observations")
        control_mean = float(np.mean(control))
        treatment_mean = float(np.mean(treatment))
        control_std = float(np.std(control, ddof=1))
        treatment_std = float(np.std(treatment, ddof=1))
        t_stat, p_value = stats.ttest_ind(
            treatment, control, equal_var=equal_var, alternative=alternative
        )
        if equal_var:
            pooled_var = (
                (control_n - 1) * control_std**2 + (treatment_n - 1) * treatment_std**2
            ) / (control_n + treatment_n - 2)
            pooled_std = float(np.sqrt(pooled_var))
            cohens_d = (treatment_mean - control_mean) / pooled_std
            se = pooled_std * np.sqrt(1.0 / control_n + 1.0 / treatment_n)
            df = control_n + treatment_n - 2
        else:
            cohens_d = (treatment_mean - control_mean) / np.sqrt(
                (control_std**2 + treatment_std**2) / 2.0
            )
            se = np.sqrt(control_std**2 / control_n + treatment_std**2 / treatment_n)
            num = (control_std**2 / control_n + treatment_std**2 / treatment_n) ** 2
            den = (control_std**4 / (control_n**2 * (control_n - 1))) + (
                treatment_std**4 / (treatment_n**2 * (treatment_n - 1))
            )
            df = num / den
        if alternative == "two-sided":
            ci_lower, ci_upper = stats.t.interval(
                0.95, df, loc=treatment_mean - control_mean, scale=se
            )
        elif alternative == "less":
            ci_lower = -np.inf
            ci_upper = (treatment_mean - control_mean) + stats.t.ppf(0.95, df) * se
        elif alternative == "greater":
            ci_lower = (treatment_mean - control_mean) + stats.t.ppf(0.05, df) * se
            ci_upper = np.inf
        self.results = {
            "test": "t-test",
            "equal_var": equal_var,
            "alternative": alternative,
            "control_mean": control_mean,
            "treatment_mean": treatment_mean,
            "control_std": control_std,
            "treatment_std": treatment_std,
            "control_n": control_n,
            "treatment_n": treatment_n,
            "t_statistic": t_stat,
            "p_value": p_value,
            "cohens_d": cohens_d,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "relative_difference": (
                (treatment_mean - control_mean) / control_mean
                if control_mean != 0
                else np.nan
            ),
        }
        return self.results


class MannWhitneyU(StatisticalTest):
    """
    Mann-Whitney U test for comparing distributions.

    This class provides methods for performing Mann-Whitney U tests
    on A/B test results.
    """

    def run(
        self,
        control: np.ndarray,
        treatment: np.ndarray,
        alternative: str = "two-sided",
        use_continuity: bool = True,
    ) -> Dict:
        """
        Run a Mann-Whitney U test.

        Parameters
        ----------
        control : array-like
            Control group data.
        treatment : array-like
            Treatment group data.
        alternative : str, default="two-sided"
            Alternative hypothesis. Options: "two-sided", "less", "greater".
        use_continuity : bool, default=True
            Whether to use continuity correction.

        Returns
        -------
        results : dict
            Test results.
        """
        control = np.asarray(control, dtype=float)
        treatment = np.asarray(treatment, dtype=float)
        control = control[~np.isnan(control)]
        treatment = treatment[~np.isnan(treatment)]
        control_n = len(control)
        treatment_n = len(treatment)
        if control_n < 1 or treatment_n < 1:
            raise ValueError("Both groups must have at least one observation")
        control_median = float(np.median(control))
        treatment_median = float(np.median(treatment))
        u_stat, p_value = stats.mannwhitneyu(
            treatment, control, alternative=alternative, use_continuity=use_continuity
        )
        z_score = (
            stats.norm.ppf(1 - p_value / 2)
            if alternative == "two-sided"
            else stats.norm.ppf(1 - p_value)
        )
        effect_size_r = z_score / np.sqrt(control_n + treatment_n)
        self.results = {
            "test": "mann-whitney-u",
            "alternative": alternative,
            "use_continuity": use_continuity,
            "control_median": control_median,
            "treatment_median": treatment_median,
            "control_n": control_n,
            "treatment_n": treatment_n,
            "u_statistic": u_stat,
            "p_value": p_value,
            "effect_size_r": effect_size_r,
            "relative_difference": (
                (treatment_median - control_median) / control_median
                if control_median != 0
                else np.nan
            ),
        }
        return self.results


class BayesianABTest(StatisticalTest):
    """
    Bayesian A/B test for comparing distributions.

    This class provides methods for performing Bayesian A/B tests
    on A/B test results.
    """

    def run(
        self,
        control: np.ndarray,
        treatment: np.ndarray,
        prior_alpha: float = 1.0,
        prior_beta: float = 1.0,
        n_samples: int = 10000,
    ) -> Dict:
        """
        Run a Bayesian A/B test.

        Parameters
        ----------
        control : array-like
            Control group data.
        treatment : array-like
            Treatment group data.
        prior_alpha : float, default=1.0
            Alpha parameter for the prior distribution.
        prior_beta : float, default=1.0
            Beta parameter for the prior distribution.
        n_samples : int, default=10000
            Number of samples to draw from the posterior distribution.

        Returns
        -------
        results : dict
            Test results.
        """
        control = np.asarray(control, dtype=float)
        treatment = np.asarray(treatment, dtype=float)
        control = control[~np.isnan(control)]
        treatment = treatment[~np.isnan(treatment)]
        control_n = len(control)
        treatment_n = len(treatment)
        if control_n < 1 or treatment_n < 1:
            raise ValueError("Both groups must have at least one observation")
        control_mean = float(np.mean(control))
        treatment_mean = float(np.mean(treatment))
        control_std = float(np.std(control, ddof=1))
        treatment_std = float(np.std(treatment, ddof=1))
        if set(np.unique(control)).issubset({0.0, 1.0}) and set(
            np.unique(treatment)
        ).issubset({0.0, 1.0}):
            control_successes = np.sum(control)
            treatment_successes = np.sum(treatment)
            control_alpha = prior_alpha + control_successes
            control_beta = prior_beta + control_n - control_successes
            treatment_alpha = prior_alpha + treatment_successes
            treatment_beta = prior_beta + treatment_n - treatment_successes
            control_samples = np.random.beta(control_alpha, control_beta, n_samples)
            treatment_samples = np.random.beta(
                treatment_alpha, treatment_beta, n_samples
            )
            prob_improvement = np.mean(treatment_samples > control_samples)
            expected_improvement = np.mean(treatment_samples - control_samples)
            diff_samples = treatment_samples - control_samples
            ci_lower = np.percentile(diff_samples, 2.5)
            ci_upper = np.percentile(diff_samples, 97.5)
            self.results = {
                "test": "bayesian-ab-test",
                "model": "beta-binomial",
                "control_mean": control_mean,
                "treatment_mean": treatment_mean,
                "control_n": control_n,
                "treatment_n": treatment_n,
                "control_successes": control_successes,
                "treatment_successes": treatment_successes,
                "control_alpha": control_alpha,
                "control_beta": control_beta,
                "treatment_alpha": treatment_alpha,
                "treatment_beta": treatment_beta,
                "prob_improvement": prob_improvement,
                "expected_improvement": expected_improvement,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "relative_improvement": (
                    expected_improvement / control_mean if control_mean != 0 else np.nan
                ),
            }
        else:
            control_mean_posterior = control_mean
            control_std_posterior = control_std / np.sqrt(control_n)
            treatment_mean_posterior = treatment_mean
            treatment_std_posterior = treatment_std / np.sqrt(treatment_n)
            control_samples = np.random.normal(
                control_mean_posterior, control_std_posterior, n_samples
            )
            treatment_samples = np.random.normal(
                treatment_mean_posterior, treatment_std_posterior, n_samples
            )
            prob_improvement = np.mean(treatment_samples > control_samples)
            expected_improvement = np.mean(treatment_samples - control_samples)
            diff_samples = treatment_samples - control_samples
            ci_lower = np.percentile(diff_samples, 2.5)
            ci_upper = np.percentile(diff_samples, 97.5)
            self.results = {
                "test": "bayesian-ab-test",
                "model": "normal",
                "control_mean": control_mean,
                "treatment_mean": treatment_mean,
                "control_std": control_std,
                "treatment_std": treatment_std,
                "control_n": control_n,
                "treatment_n": treatment_n,
                "prob_improvement": prob_improvement,
                "expected_improvement": expected_improvement,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "relative_improvement": (
                    expected_improvement / control_mean if control_mean != 0 else np.nan
                ),
            }
        return self.results

    def is_significant(self, threshold: float = 0.95) -> bool:
        """
        Check if the test result is practically significant.

        Parameters
        ----------
        threshold : float, default=0.95
            Probability threshold for significance.

        Returns
        -------
        is_significant : bool
            Whether the test result is practically significant.
        """
        if "prob_improvement" not in self.results:
            raise ValueError("Test has not been run yet")
        return self.results["prob_improvement"] > threshold


class MultipleTestingCorrection:
    """
    Multiple testing correction for controlling false discovery rate.

    This class provides methods for correcting p-values when
    performing multiple statistical tests.
    """

    @staticmethod
    def bonferroni(p_values: List[float]) -> List[float]:
        """
        Apply Bonferroni correction to p-values.

        Parameters
        ----------
        p_values : list
            List of p-values to correct.

        Returns
        -------
        corrected_p_values : list
            Corrected p-values.
        """
        n_tests = len(p_values)
        return [min(p * n_tests, 1.0) for p in p_values]

    @staticmethod
    def benjamini_hochberg(p_values: List[float]) -> List[float]:
        """
        Apply Benjamini-Hochberg correction to p-values.

        Parameters
        ----------
        p_values : list
            List of p-values to correct.

        Returns
        -------
        corrected_p_values : list
            Corrected p-values.
        """
        n_tests = len(p_values)
        sorted_indices = np.argsort(p_values)
        sorted_p_values = [p_values[i] for i in sorted_indices]
        corrected_sorted_p_values: List[Any] = []
        for i, p in enumerate(sorted_p_values):
            corrected_p = p * n_tests / (i + 1)
            corrected_sorted_p_values.append(min(corrected_p, 1.0))
        for i in range(n_tests - 2, -1, -1):
            corrected_sorted_p_values[i] = min(
                corrected_sorted_p_values[i], corrected_sorted_p_values[i + 1]
            )
        corrected_p_values: List[float] = [0.0] * n_tests
        for i, idx in enumerate(sorted_indices):
            corrected_p_values[idx] = corrected_sorted_p_values[i]
        return corrected_p_values

    @staticmethod
    def holm(p_values: List[float]) -> List[float]:
        """
        Apply Holm-Bonferroni correction to p-values.

        Parameters
        ----------
        p_values : list
            List of p-values to correct.

        Returns
        -------
        corrected_p_values : list
            Corrected p-values.
        """
        n_tests = len(p_values)
        sorted_indices = np.argsort(p_values)
        sorted_p_values = [p_values[i] for i in sorted_indices]
        corrected_sorted_p_values: List[Any] = []
        for i, p in enumerate(sorted_p_values):
            corrected_p = p * (n_tests - i)
            corrected_sorted_p_values.append(min(corrected_p, 1.0))
        for i in range(n_tests - 2, -1, -1):
            corrected_sorted_p_values[i] = max(
                corrected_sorted_p_values[i], corrected_sorted_p_values[i + 1]
            )
        corrected_p_values: List[float] = [0.0] * n_tests
        for i, idx in enumerate(sorted_indices):
            corrected_p_values[idx] = corrected_sorted_p_values[i]
        return corrected_p_values
