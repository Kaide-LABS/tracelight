import numpy as np
from scipy import stats
from app.agents.generator import (
    build_correlation_matrix, nearest_psd, is_psd,
    get_scipy_distribution, generate
)
from app.schemas import VariableSpec, StatisticalProfile

class TestCorrelationMatrix:
    def test_identity_with_no_correlations(self):
        """No correlations → identity matrix."""
        C = build_correlation_matrix(["a", "b", "c"], [])
        assert np.allclose(C, np.eye(3))

    def test_symmetric(self):
        """Correlation matrix must be symmetric."""
        C = build_correlation_matrix(["a", "b"], [("a", "b", 0.5)])
        assert np.allclose(C, C.T)

    def test_diagonal_ones(self):
        """Diagonal must be 1."""
        C = build_correlation_matrix(["a", "b", "c"], [("a", "b", 0.5), ("b", "c", -0.3)])
        assert np.allclose(np.diag(C), 1.0)

    def test_psd_correction(self):
        """Invalid correlation matrix should be corrected to PSD."""
        # Intentionally invalid: |rho| sum > 1 for some triplets
        C = build_correlation_matrix(
            ["a", "b", "c"],
            [("a", "b", 0.9), ("b", "c", 0.9), ("a", "c", -0.9)]
        )
        assert is_psd(C)

class TestNearestPSD:
    def test_already_psd(self):
        """PSD matrix should be returned unchanged (or nearly)."""
        M = np.eye(3)
        result = nearest_psd(M)
        assert np.allclose(result, M, atol=1e-8)

    def test_non_psd_corrected(self):
        """Non-PSD matrix should be corrected."""
        M = np.array([[1, 0.9, 0.9], [0.9, 1, -0.9], [0.9, -0.9, 1]])
        result = nearest_psd(M)
        assert is_psd(result)

class TestDistributionMapping:
    def test_normal(self):
        spec = VariableSpec(distribution="normal", mean=10, std=2)
        dist = get_scipy_distribution(spec)
        assert abs(dist.mean() - 10) < 0.01

    def test_beta_bounded(self):
        """Beta distribution should produce values in [0, 1]."""
        spec = VariableSpec(distribution="beta", alpha=2, beta=5)
        dist = get_scipy_distribution(spec)
        samples = dist.rvs(size=10000)
        assert samples.min() >= 0 and samples.max() <= 1

    def test_lognormal_positive(self):
        """Lognormal should produce only positive values."""
        spec = VariableSpec(distribution="lognormal", mu=1.0, sigma=0.5)
        dist = get_scipy_distribution(spec)
        samples = dist.rvs(size=10000)
        assert samples.min() > 0

class TestGenerate:
    def _make_profile(self, n_entities=10, n_years=2, freq="quarterly"):
        return StatisticalProfile(
            asset_class="test",
            num_entities=n_entities,
            time_horizon_years=n_years,
            frequency=freq,
            variables={
                "revenue": VariableSpec(distribution="lognormal", mu=18.0, sigma=0.4),
                "margin": VariableSpec(distribution="beta", alpha=5, beta=2),
            },
            correlations=[("revenue", "margin", 0.5)],
            temporal={"autocorrelation": 0.0},
        )

    def test_output_shape(self):
        """Row count = n_entities × n_periods."""
        profile = self._make_profile(n_entities=10, n_years=2, freq="quarterly")
        df, _ = generate(profile, seed=42)
        assert len(df) == 10 * 8  # 10 entities × (2 years × 4 quarters)

    def test_deterministic_with_seed(self):
        """Same seed → same output."""
        profile = self._make_profile()
        df1, _ = generate(profile, seed=42)
        df2, _ = generate(profile, seed=42)
        assert df1.equals(df2)

    def test_different_seeds(self):
        """Different seeds → different output."""
        profile = self._make_profile()
        df1, _ = generate(profile, seed=42)
        df2, _ = generate(profile, seed=99)
        assert not df1.equals(df2)

    def test_correlations_preserved(self):
        """Empirical correlation should approximate target."""
        profile = self._make_profile(n_entities=500)
        df, corr_matrix = generate(profile, seed=42)
        empirical_corr = df[["revenue", "margin"]].corr().values[0, 1]
        assert abs(empirical_corr - 0.5) < 0.1  # within 0.1 of target