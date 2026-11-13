"""
deepaft: Python deep accelerated failure time models.

Reproduces Norman et al. (2024) Statistics in Medicine methods and adds
limitation-aware extensions for covariate-dependent censoring and
heteroscedastic residuals.
"""

from deepaft.estimator import DeepAFT, DeepAFTConfig
from deepaft.metrics import amse, harrell_c_index, integrated_brier_score
from deepaft.simulate import scenario_a, scenario_b, scenario_c, scenario_d, scenario_ph

__version__ = "0.1.2"
__all__ = [
    "DeepAFT",
    "DeepAFTConfig",
    "harrell_c_index",
    "amse",
    "integrated_brier_score",
    "scenario_a",
    "scenario_b",
    "scenario_c",
    "scenario_d",
    "scenario_ph",
]
