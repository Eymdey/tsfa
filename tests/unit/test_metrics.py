"""Unit tests for ml/postprocessing/metrics.py."""

import math
import pytest

from ml.postprocessing.metrics import mae, rmse, mape, smape, coverage


# ---------------------------------------------------------------------------
# MAE
# ---------------------------------------------------------------------------

class TestMAE:
    def test_perfect_prediction(self):
        assert mae([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0

    def test_known_value(self):
        # |1-2| + |2-2| + |3-4| = 1 + 0 + 1 = 2 → 2/3
        result = mae([1.0, 2.0, 3.0], [2.0, 2.0, 4.0])
        assert abs(result - 2 / 3) < 1e-9

    def test_all_same_error(self):
        result = mae([0.0, 0.0, 0.0], [1.0, 1.0, 1.0])
        assert result == 1.0

    def test_empty(self):
        assert mae([], []) == 0.0

    def test_single_element(self):
        assert mae([5.0], [3.0]) == 2.0

    def test_negative_values(self):
        result = mae([-3.0, -1.0], [-1.0, -3.0])
        assert result == 2.0


# ---------------------------------------------------------------------------
# RMSE
# ---------------------------------------------------------------------------

class TestRMSE:
    def test_perfect_prediction(self):
        assert rmse([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0

    def test_known_value(self):
        # errors: -1, 0, -1 → MSE = (1+0+1)/3 = 2/3 → RMSE = sqrt(2/3)
        result = rmse([1.0, 2.0, 3.0], [2.0, 2.0, 4.0])
        assert abs(result - math.sqrt(2 / 3)) < 1e-9

    def test_single_large_error(self):
        # MSE = 9 → RMSE = 3
        result = rmse([0.0], [3.0])
        assert result == 3.0

    def test_empty(self):
        assert rmse([], []) == 0.0

    def test_rmse_ge_mae(self):
        y_true = [1.0, 2.0, 3.0, 10.0]
        y_pred = [1.5, 2.5, 3.5, 4.0]
        assert rmse(y_true, y_pred) >= mae(y_true, y_pred)


# ---------------------------------------------------------------------------
# MAPE
# ---------------------------------------------------------------------------

class TestMAPE:
    def test_perfect_prediction(self):
        assert mape([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0

    def test_known_value(self):
        # |1-2|/1 + |4-3|/4 = 1 + 0.25 = 1.25 → /2 = 0.625
        result = mape([1.0, 4.0], [2.0, 3.0])
        assert abs(result - 0.625) < 1e-9

    def test_division_by_zero_skipped(self):
        # y_true=0 → skip that pair; only (2, 3) counts → |2-3|/2 = 0.5
        result = mape([0.0, 2.0], [1.0, 3.0])
        assert abs(result - 0.5) < 1e-9

    def test_all_zeros_returns_zero(self):
        result = mape([0.0, 0.0], [1.0, 2.0])
        assert result == 0.0

    def test_empty(self):
        assert mape([], []) == 0.0

    def test_50_percent_error(self):
        # |1-1.5|/1 = 0.5
        result = mape([1.0], [1.5])
        assert abs(result - 0.5) < 1e-9


# ---------------------------------------------------------------------------
# sMAPE
# ---------------------------------------------------------------------------

class TestSMAPE:
    def test_perfect_prediction(self):
        assert smape([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0

    def test_known_value(self):
        # 2*|1-2|/(1+2) = 2/3; 2*|4-3|/(4+3) = 2/7 → mean = (2/3 + 2/7)/2
        expected = (2 / 3 + 2 / 7) / 2
        result = smape([1.0, 4.0], [2.0, 3.0])
        assert abs(result - expected) < 1e-9

    def test_both_zeros_skipped(self):
        # (0, 0) skipped; (2, 3) → 2*1/5 = 0.4
        result = smape([0.0, 2.0], [0.0, 3.0])
        assert abs(result - 0.4) < 1e-9

    def test_all_zeros_returns_zero(self):
        result = smape([0.0, 0.0], [0.0, 0.0])
        assert result == 0.0

    def test_empty(self):
        assert smape([], []) == 0.0

    def test_symmetric(self):
        # sMAPE should be symmetric w.r.t. swap
        r1 = smape([1.0, 2.0], [3.0, 4.0])
        r2 = smape([3.0, 4.0], [1.0, 2.0])
        assert abs(r1 - r2) < 1e-9


# ---------------------------------------------------------------------------
# Coverage
# ---------------------------------------------------------------------------

class TestCoverage:
    def test_full_coverage(self):
        result = coverage([1.0, 2.0, 3.0], [0.0, 1.0, 2.0], [2.0, 3.0, 4.0])
        assert result == 1.0

    def test_zero_coverage(self):
        result = coverage([5.0, 6.0], [0.0, 0.0], [1.0, 1.0])
        assert result == 0.0

    def test_partial_coverage(self):
        # [0,2] covers 1.0 ✓; [3,4] does not cover 2.5 ✗ → 0.5
        result = coverage([1.0, 2.5], [0.0, 3.0], [2.0, 4.0])
        assert result == 0.5

    def test_boundary_inclusive(self):
        # exact boundary should be included
        result = coverage([1.0], [1.0], [1.0])
        assert result == 1.0

    def test_empty(self):
        assert coverage([], [], []) == 0.0

    def test_two_thirds(self):
        y_true = [1.0, 5.0, 3.0]
        lower =  [0.0, 0.0, 2.0]
        upper =  [2.0, 4.0, 4.0]
        # 1.0 in [0,2] ✓; 5.0 not in [0,4] ✗; 3.0 in [2,4] ✓ → 2/3
        result = coverage(y_true, lower, upper)
        assert abs(result - 2 / 3) < 1e-9
