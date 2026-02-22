from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import NDArray


@dataclass
class RegressionFit:
	alpha: float
	betas: dict[str, float]
	r2: float
	residuals: NDArray[np.float64]


def _fit_ols(
	y: NDArray[np.float64],
	x: NDArray[np.float64],
	factor_codes: list[str],
) -> RegressionFit:
	design = np.column_stack([np.ones(len(y), dtype=float), x])
	coefs, *_ = np.linalg.lstsq(design, y, rcond=None)
	fitted = design @ coefs
	residuals = y - fitted

	y_centered = y - float(np.mean(y))
	ss_total = float(np.dot(y_centered, y_centered))
	ss_res = float(np.dot(residuals, residuals))
	r2 = 0.0 if ss_total <= 1e-12 else max(0.0, 1.0 - (ss_res / ss_total))

	return RegressionFit(
		alpha=float(coefs[0]),
		betas={factor_codes[idx]: float(coefs[idx + 1]) for idx in range(len(factor_codes))},
		r2=r2,
		residuals=residuals,
	)


def align_factor_inputs(
	basket_returns: pd.Series,
	factor_returns_df: pd.DataFrame,
) -> pd.DataFrame:
	aligned = pd.concat([basket_returns.rename("basket"), factor_returns_df], axis=1)
	aligned = aligned.dropna(how="any")
	if aligned.empty:
		raise ValueError("No overlapping basket/factor rows")
	return aligned


def rolling_factor_exposures(
	basket_returns: pd.Series,
	factor_returns_df: pd.DataFrame,
	window: int,
) -> pd.DataFrame:
	if window < 20:
		raise ValueError("window must be >= 20")

	aligned = align_factor_inputs(
		basket_returns=basket_returns,
		factor_returns_df=factor_returns_df,
	)
	if len(aligned.index) < window:
		raise ValueError("Not enough aligned observations for selected rolling window")

	factor_codes = list(factor_returns_df.columns)
	rows: list[dict[str, float | object]] = []

	for end_idx in range(window, len(aligned.index) + 1):
		sample = aligned.iloc[end_idx - window : end_idx]
		y = sample["basket"].to_numpy(dtype=float)
		x = sample[factor_codes].to_numpy(dtype=float)
		fit = _fit_ols(y=y, x=x, factor_codes=factor_codes)

		row: dict[str, float | object] = {
			"date": sample.index[-1],
			"alpha": fit.alpha,
			"r2": fit.r2,
		}
		row.update(fit.betas)
		rows.append(row)

	exposures = pd.DataFrame(rows).set_index("date")
	return exposures


def factor_attribution(
	basket_returns: pd.Series,
	factor_returns_df: pd.DataFrame,
) -> dict[str, float]:
	aligned = align_factor_inputs(
		basket_returns=basket_returns,
		factor_returns_df=factor_returns_df,
	)
	factor_codes = list(factor_returns_df.columns)

	y = aligned["basket"].to_numpy(dtype=float)
	x = aligned[factor_codes].to_numpy(dtype=float)
	fit = _fit_ols(y=y, x=x, factor_codes=factor_codes)

	total_basket_return = float(np.sum(y))
	contributions: dict[str, float] = {}

	for idx, code in enumerate(factor_codes):
		factor_component = float(np.sum(x[:, idx] * fit.betas[code]))
		contributions[code] = factor_component

	residual_component = float(np.sum(fit.residuals))
	contributions["IDIO"] = residual_component

	if abs(total_basket_return) <= 1e-12:
		return {name: 0.0 for name in contributions}

	return {name: value / total_basket_return for name, value in contributions.items()}


def regime_map(
	exposures_df: pd.DataFrame,
	factor_to_regime: dict[str, str],
) -> pd.Series:
	factor_columns = [
		column for column in exposures_df.columns if column not in {"alpha", "r2"}
	]
	if not factor_columns:
		raise ValueError("No factor columns available for regime mapping")

	def _pick_regime(row: pd.Series) -> str:
		dominant = max(factor_columns, key=lambda code: abs(float(row[code])))
		return factor_to_regime.get(dominant, "growth")

	return exposures_df.apply(_pick_regime, axis=1).rename("regime")


def factor_correlation_matrix(factor_returns_df: pd.DataFrame) -> pd.DataFrame:
	if factor_returns_df.empty:
		raise ValueError("factor_returns_df is empty")
	aligned = factor_returns_df.dropna(how="any")
	if aligned.empty:
		raise ValueError("No overlapping factor rows")
	return aligned.corr()
