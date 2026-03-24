import numpy as np
import pandas as pd
from scipy import stats
from scipy.linalg import cholesky
from app.schemas import VariableSpec, StatisticalProfile

def nearest_psd(matrix: np.ndarray) -> np.ndarray:
    """Higham's nearest positive semi-definite matrix."""
    B = (matrix + matrix.T) / 2
    _, s, V = np.linalg.svd(B)
    H = V.T @ np.diag(np.maximum(s, 0)) @ V
    A2 = (B + H) / 2
    A3 = (A2 + A2.T) / 2
    if is_psd(A3):
        return A3
    spacing = np.spacing(np.linalg.norm(matrix))
    identity = np.eye(matrix.shape[0])
    k = 1
    while not is_psd(A3):
        min_eig = np.min(np.real(np.linalg.eigvals(A3)))
        A3 += identity * (-min_eig * k**2 + spacing)
        k += 1
    return A3

def is_psd(matrix: np.ndarray) -> bool:
    try:
        np.linalg.cholesky(matrix)
        return True
    except np.linalg.LinAlgError:
        return False

def build_correlation_matrix(var_names: list[str], correlations: list[tuple[str, str, float]]) -> np.ndarray:
    n = len(var_names)
    idx = {name: i for i, name in enumerate(var_names)}
    C = np.eye(n)
    for var_a, var_b, rho in correlations:
        if var_a in idx and var_b in idx:
            i, j = idx[var_a], idx[var_b]
            C[i, j] = rho
            C[j, i] = rho
    if not is_psd(C):
        C = nearest_psd(C)
    return C

def get_scipy_distribution(spec: VariableSpec):
    match spec.distribution:
        case "normal":
            return stats.norm(loc=spec.mean or 0.0, scale=spec.std or 1.0)
        case "lognormal":
            return stats.lognorm(s=spec.sigma or 1.0, scale=np.exp(spec.mu or 0.0))
        case "beta":
            return stats.beta(a=spec.alpha or 2.0, b=spec.beta or 2.0)
        case "uniform":
            return stats.uniform(loc=spec.low or 0.0, scale=(spec.high or 1.0) - (spec.low or 0.0))
        case "exponential":
            return stats.expon(scale=1.0 / (spec.rate or 1.0))

def generate(profile: StatisticalProfile, seed: int | None = None) -> tuple[pd.DataFrame, np.ndarray]:
    rng = np.random.default_rng(seed)
    var_names = list(profile.variables.keys())
    n_vars = len(var_names)
    n_entities = profile.num_entities
    freq_map = {"monthly": 12, "quarterly": 4, "annual": 1}
    n_periods = profile.time_horizon_years * freq_map[profile.frequency]

    corr_matrix = build_correlation_matrix(var_names, profile.correlations)
    L = cholesky(corr_matrix, lower=True)

    distributions = {name: get_scipy_distribution(spec) for name, spec in profile.variables.items()}

    # Vectorized Generation
    # 1. Independent standard normals
    Z = rng.standard_normal((n_entities, n_periods, n_vars))
    
    # 2. Apply AR(1) structure on independent standard normals before Cholesky
    rho = profile.temporal.get("autocorrelation", 0.0)
    if rho > 0:
        for t in range(1, n_periods):
            Z[:, t, :] = rho * Z[:, t-1, :] + np.sqrt(1 - rho**2) * Z[:, t, :]
            
    # 3. Correlate via Cholesky factor
    Z_corr = Z @ L.T
    
    # 4. Transform to uniform via normal CDF
    U = stats.norm.cdf(Z_corr)
    
    # 5. Transform to target marginals
    U_2d = U.reshape(-1, n_vars)
    samples_2d = np.empty_like(U_2d)
    
    for i, name in enumerate(var_names):
        samples_2d[:, i] = distributions[name].ppf(U_2d[:, i])
        
    # Build DataFrame
    entity_ids = np.repeat(np.arange(n_entities), n_periods)
    periods = np.tile(np.arange(n_periods), n_entities)
    
    df_data = {
        "entity_id": entity_ids,
        "period": periods
    }
    
    for i, name in enumerate(var_names):
        df_data[name] = samples_2d[:, i]
        
    df = pd.DataFrame(df_data)
    return df, corr_matrix
