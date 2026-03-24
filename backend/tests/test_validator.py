import numpy as np
import pandas as pd
from app.agents.validator import ks_test, apply_differential_privacy
from app.schemas import VariableSpec

class TestKSTest:
    def test_matching_distribution_passes(self):
        """Data drawn from the correct distribution should pass KS test."""
        spec = VariableSpec(distribution="normal", mean=0, std=1)
        data = np.random.default_rng(42).normal(0, 1, 1000)
        result = ks_test(data, spec)
        assert result.passed is True
        assert result.p_value > 0.05

    def test_wrong_distribution_fails(self):
        """Data from wrong distribution should fail KS test."""
        spec = VariableSpec(distribution="normal", mean=100, std=1)
        data = np.random.default_rng(42).normal(0, 1, 1000)
        result = ks_test(data, spec)
        assert result.passed is False

class TestDP:
    def test_noise_applied(self):
        """DP should change the data."""
        rng = np.random.default_rng(42)
        df = pd.DataFrame({"x": rng.normal(0, 1, 100)})
        original = df["x"].copy()
        noised = apply_differential_privacy(df, ["x"], epsilon=1.0, rng=rng)
        assert not np.allclose(original.values, noised["x"].values)

    def test_higher_epsilon_less_noise(self):
        """Higher epsilon → less noise (more utility)."""
        rng1 = np.random.default_rng(42)
        rng2 = np.random.default_rng(42)
        df = pd.DataFrame({"x": np.random.default_rng(0).normal(0, 1, 1000)})
        noised_low = apply_differential_privacy(df.copy(), ["x"], epsilon=0.1, rng=rng1)
        noised_high = apply_differential_privacy(df.copy(), ["x"], epsilon=10.0, rng=rng2)
        noise_low = np.abs(df["x"].values - noised_low["x"].values).mean()
        noise_high = np.abs(df["x"].values - noised_high["x"].values).mean()
        assert noise_low > noise_high