# Product Requirements Document: Tracelight Synthetic Financial Data Generator

## 1. Executive Summary

**Product**: A containerized microservice that generates mathematically sound, privacy-compliant synthetic financial test data — enabling Tracelight's enterprise clients to instantly validate PoCs without triggering InfoSec/data-privacy compliance protocols.

**The Problem**: Tracelight's CTO (Aleksander Misztal) has publicly stated that enterprise security approval processes create a 3-6 month dead zone in the sales cycle. Clients cannot share real portfolio data with external vendors pre-contract, yet need realistic test data to evaluate Tracelight's in-Excel AI engine.

**The Solution**: A "sidecar" API that sits entirely outside Excel. An LLM Profiler Agent translates natural-language financial scenarios into rigorous statistical specifications, a deterministic math engine generates correlated synthetic time-series via Cholesky decomposition and parametric sampling, and a Differential Privacy validator certifies the output is non-reversible. Output is CSV/JSON — never `.xlsx`.

### The IP Boundary (DMZ Rule)

| We DO | We DO NOT |
|-------|-----------|
| Generate synthetic CSV/JSON test data | Touch, read, write, or manipulate `.xlsx` files |
| Use LLM to interpret financial scenarios into statistical params | Use LLM to generate formulas or spreadsheet logic |
| Output data that can be *imported into* Excel models | Operate within the spreadsheet layer in any way |
| Validate statistical properties of generated data | Replicate Tracelight's in-Excel AI, error-checking, or formula generation |

---

## 2. System Architecture & Data Flow

```
┌──────────────────────────────────────────────────────────┐
│                    STREAMLIT FRONTEND                     │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ NL Scenario│  │ Distribution │  │ Preview + Export  │ │
│  │ Input      │──│ Tuning Panel │──│ (table, charts)   │ │
│  └────────────┘  └──────────────┘  └──────────────────┘ │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP (port 8501 → 8000)
┌────────────────────────▼─────────────────────────────────┐
│                   FASTAPI BACKEND (port 8000)             │
│                                                           │
│  POST /api/v1/generate                                    │
│  GET  /api/v1/download/{job_id}                           │
│  GET  /api/v1/templates (preset scenarios)                │
│  GET  /health                                             │
│                                                           │
│  ┌─────────────────── PIPELINE ────────────────────────┐ │
│  │                                                     │ │
│  │  ┌──────────────┐    ┌────────────────────────┐     │ │
│  │  │ 1. PROFILER  │    │ LLM Agent (Gemini/GPT) │     │ │
│  │  │    AGENT     │◄───│ Jinja2 prompt template  │     │ │
│  │  │              │    │ → structured JSON output │     │ │
│  │  └──────┬───────┘    └────────────────────────┘     │ │
│  │         │ StatisticalProfile (validated JSON)        │ │
│  │         ▼                                           │ │
│  │  ┌──────────────┐                                   │ │
│  │  │ 2. GENERATOR │  NumPy + SciPy                    │ │
│  │  │    ENGINE    │  Cholesky decomposition            │ │
│  │  │              │  Gaussian copula                    │ │
│  │  └──────┬───────┘                                   │ │
│  │         │ Raw DataFrame                              │ │
│  │         ▼                                           │ │
│  │  ┌──────────────┐                                   │ │
│  │  │ 3. VALIDATOR │  KS-tests, correlation RMSE       │ │
│  │  │    AGENT     │  Differential Privacy (Laplace)    │ │
│  │  └──────┬───────┘                                   │ │
│  │         │ Validated + DP-noised DataFrame            │ │
│  │         ▼                                           │ │
│  │  ┌──────────────┐                                   │ │
│  │  │ 4. FORMATTER │  CSV / JSON export                │ │
│  │  │    AGENT     │  Statistical summary report        │ │
│  │  └──────────────┘                                   │ │
│  └─────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

**Docker Compose**: Two services (`backend`, `frontend`) on a shared network. Backend stores generated files in a Docker volume.

---

## 3. Agentic Workflow Detail

### Agent 1: LLM Profiler Agent

**Role**: Translate natural-language financial scenarios into a deterministic `StatisticalProfile` JSON schema.

**How it works**:
1. User submits a natural-language prompt (e.g., *"Distressed PE LBO — mid-market European industrials, high leverage, declining EBITDA margins"*)
2. A Jinja2 template (`profile_suggest.j2`) wraps the user input with system instructions constraining the LLM to output **only** valid JSON matching our Pydantic schema
3. The LLM reasons through the scenario and outputs: asset class, variable names, distribution types + params, a correlation matrix, time horizon, and frequency
4. Pydantic validates the response. If validation fails, one retry with error feedback.

**Why LLM here**: Financial professionals think in narratives, not distribution parameters. The LLM bridges "distressed European industrial" → `{"ebitda_margin": {"type": "beta", "alpha": 2, "beta": 5}, ...}`. This is reasoning, not data generation.

**Why Jinja2**: Deterministic prompt construction. No string concatenation injection risk. Template is version-controlled and auditable.

### Agent 2: Deterministic Generator Engine

**Role**: Pure math. Zero LLM involvement.

**Algorithm**:

1. **Correlation matrix validation**: Check positive semi-definiteness. If not PSD, apply nearest-PSD correction via Higham's alternating projections algorithm.

2. **Cholesky decomposition**: Decompose the validated correlation matrix `Σ = L·Lᵀ` where `L` is lower-triangular.

3. **Uncorrelated sampling**: For each variable, draw `N × T` samples from its specified marginal distribution using `scipy.stats` (normal, lognormal, beta, uniform, etc.).

4. **Correlation injection via Gaussian copula**: Transform uncorrelated samples to uniform via their CDF (probability integral transform), convert to standard normal, apply the Cholesky factor `L`, convert back to uniform via normal CDF, then invert through each variable's inverse CDF. This preserves the exact marginal distributions while imposing the target correlation structure.

5. **Temporal structure**: For time-series variables, apply an AR(1) process with calibrated autocorrelation to introduce realistic serial dependence within each entity.

**Key references (sourced via Nia MCP)**:
- `ActurialCapital/synthetica` — Python library for synthetic time-series with configurable stochastic models (GBM, Merton Jump Diffusion, Heston). We adopt their API patterns for our generator interface.
- `RomainBRSHedging/Multi-Assets-Option-Pricing` — Clean Cholesky-based correlated simulation reference.
- Gaussian Copula methodology from QuantX Research for preserving arbitrary marginals under correlation constraints.

### Agent 3: Differential Privacy Validator

**Role**: Statistical validation + privacy certification.

**Validation steps**:
1. **Kolmogorov-Smirnov test**: For each variable, test the generated distribution against the target. Report p-values. Flag if any p < 0.05.
2. **Correlation RMSE**: Compare the empirical correlation matrix of the generated data against the target. Report Frobenius norm error.
3. **Differential Privacy**: Apply calibrated Laplace noise to each column: `noise ~ Laplace(0, Δf/ε)` where `Δf` is the sensitivity (computed from the column range) and `ε` is the user-specified privacy budget. This provides (ε, 0)-differential privacy.
4. **Post-DP re-validation**: Re-run KS tests after noise injection to confirm distributions still hold within tolerance.

**Key references (sourced via Nia MCP)**:
- `hazy/dpart` — Framework for differentially private synthetic data generation. We adopt their sensitivity calibration approach.
- `Kacimyou/Synthetic_Differentially_Private_Generator` — Reference implementation for Laplace mechanism on tabular financial data.
- `diffix/syndiffix` — Alternative DP mechanism for comparison benchmarking.

### Agent 4: Format Exporter

**Role**: Serialize validated DataFrame to CSV or JSON. Generate a human-readable statistical summary report (optionally LLM-narrated). **Never outputs `.xlsx`.**

---

## 4. API Schema

### `POST /api/v1/generate`

**Request Body**:
```json
{
  "scenario": {
    "natural_language": "Distressed PE LBO, mid-market European industrials, high leverage, declining margins",
    "use_llm_profiler": true
  },
  "profile_override": {
    "asset_class": "private_equity_lbo",
    "num_entities": 50,
    "time_horizon_years": 5,
    "frequency": "quarterly",
    "variables": {
      "revenue": {"distribution": "lognormal", "mu": 18.0, "sigma": 0.4},
      "ebitda_margin": {"distribution": "beta", "alpha": 2, "beta": 5},
      "leverage_ratio": {"distribution": "normal", "mean": 6.5, "std": 1.2},
      "interest_rate": {"distribution": "lognormal", "mu": 0.06, "sigma": 0.015},
      "capex_pct_revenue": {"distribution": "uniform", "low": 0.03, "high": 0.08}
    },
    "correlations": [
      ["revenue", "ebitda_margin", 0.55],
      ["leverage_ratio", "interest_rate", 0.40],
      ["ebitda_margin", "leverage_ratio", -0.35]
    ],
    "temporal": {
      "autocorrelation": 0.7
    }
  },
  "privacy": {
    "enabled": true,
    "epsilon": 1.0
  },
  "output_format": "csv",
  "seed": 42
}
```

**Notes**:
- If `scenario.use_llm_profiler` is `true`, the LLM generates the profile from `scenario.natural_language`. Any fields in `profile_override` then override specific LLM-generated params (giving the user fine-grained control).
- If `use_llm_profiler` is `false`, `profile_override` must be fully specified.

**Response** (`200 OK`):
```json
{
  "job_id": "a1b2c3d4-...",
  "status": "completed",
  "download_url": "/api/v1/download/a1b2c3d4-...",
  "profile_used": {
    "asset_class": "private_equity_lbo",
    "num_entities": 50,
    "time_horizon_years": 5,
    "frequency": "quarterly",
    "variables": { "...": "..." },
    "correlations": "..."
  },
  "validation_report": {
    "row_count": 1000,
    "ks_tests": {
      "revenue": {"statistic": 0.018, "p_value": 0.87, "passed": true},
      "ebitda_margin": {"statistic": 0.022, "p_value": 0.74, "passed": true}
    },
    "correlation_rmse": 0.013,
    "dp_applied": true,
    "dp_epsilon": 1.0,
    "post_dp_ks_all_passed": true
  },
  "generated_at": "2026-03-24T14:30:00Z"
}
```

### `GET /api/v1/download/{job_id}`
Returns the generated CSV/JSON file as a streaming download.

### `GET /api/v1/templates`
Returns preset scenario templates (e.g., "PE LBO", "VC Portfolio", "Real Estate DCF") for the Streamlit dropdown.

---

## 5. Project Structure

```
tracelight/
├── docker-compose.yml
├── PRD.md                          # This document
├── CONTEXT.MD                      # Strategic context & target company profile
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app, routes, CORS
│   │   ├── config.py               # Settings (LLM API key, model, DP defaults)
│   │   ├── schemas.py              # Pydantic: GenerateRequest, GenerateResponse, StatisticalProfile
│   │   ├── pipeline.py             # Orchestrator: profiler → generator → validator → formatter
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── profiler.py         # LLM Profiler Agent (Jinja2 + LLM call)
│   │   │   ├── generator.py        # Deterministic engine (Cholesky, copula, AR(1))
│   │   │   ├── validator.py        # KS-tests + DP Laplace mechanism
│   │   │   └── formatter.py        # CSV/JSON serialization
│   │   ├── prompts/
│   │   │   └── profile_suggest.j2  # Jinja2 LLM prompt template
│   │   └── templates.py            # Preset scenario templates
├── frontend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py                      # Streamlit UI
└── .env.example                    # LLM API key placeholder
```

---

## 6. Tech Stack & Dependencies

### Backend
| Package | Purpose |
|---------|---------|
| `fastapi` + `uvicorn` | API framework |
| `pydantic` v2 | Request/response validation |
| `numpy` | Matrix ops, Cholesky, sampling |
| `scipy` | Statistical distributions, KS-tests, nearest-PSD |
| `pandas` | DataFrame ops, CSV export |
| `jinja2` | LLM prompt templates |
| `google-genai` | Google Gemini SDK (primary LLM provider) |
| `httpx` | Async OpenAI API calls (secondary provider) |
| `python-dotenv` | Env config |

### Frontend
| Package | Purpose |
|---------|---------|
| `streamlit` | Demo UI |
| `plotly` | Interactive distribution/correlation charts |
| `requests` | Backend API calls |
| `pandas` | Data display |

---

## 7. Streamlit Frontend Spec

**Page flow**:
1. **Scenario Input**: Text area for natural-language description OR dropdown of preset templates. Toggle for "Use LLM Profiler".
2. **Distribution Tuning Panel**: After LLM profiler returns, display the generated profile as editable form fields (sliders for distribution params, editable correlation matrix heatmap). User can override any parameter.
3. **Generate**: Button triggers `/api/v1/generate`. Shows spinner.
4. **Results Dashboard**:
   - Data preview table (first 20 rows)
   - Per-variable distribution plot (histogram + fitted PDF overlay)
   - Correlation heatmap (target vs. actual side-by-side)
   - Validation report card (KS test results, DP certification status)
   - Download button (CSV/JSON)

---

## 8. Verification Plan

1. `docker-compose up --build` — both containers start cleanly
2. `GET /health` returns `200`
3. `POST /api/v1/generate` with a fully-specified `profile_override` (no LLM) → valid CSV with correct row count
4. `POST /api/v1/generate` with `use_llm_profiler: true` → LLM returns valid profile, data generates correctly
5. Statistical check: generated data passes KS-tests (p > 0.05) for all variables
6. Correlation check: empirical correlation matrix RMSE < 0.05 vs. target
7. DP check: with `epsilon: 1.0`, verify noise is applied and post-DP distributions remain reasonable
8. Streamlit at `localhost:8501`: full flow works end-to-end with visual charts

---

---

## 9. Phase 1: Implementation Spec

> This section is the self-contained implementation spec. It contains everything needed to build the MVP — every file, every model, every function, every Dockerfile. The LLM provider is **Gemini 3.1 Pro Preview** (default) with **GPT-5.2** as a switchable alternative.

### 9.1 Files to Create

```
tracelight/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── schemas.py
│   │   ├── pipeline.py
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── profiler.py
│   │   │   ├── generator.py
│   │   │   ├── validator.py
│   │   │   └── formatter.py
│   │   ├── prompts/
│   │   │   └── profile_suggest.j2
│   │   └── templates.py
├── frontend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py
```

### 9.2 `backend/app/schemas.py` — Pydantic Models

All Pydantic v2 `BaseModel`:

```python
from pydantic import BaseModel, Field
from typing import Literal

class VariableSpec(BaseModel):
    distribution: Literal["normal", "lognormal", "beta", "uniform", "exponential"]
    mean: float | None = None
    std: float | None = None
    mu: float | None = None
    sigma: float | None = None
    alpha: float | None = None
    beta: float | None = None
    low: float | None = None
    high: float | None = None
    rate: float | None = None

class StatisticalProfile(BaseModel):
    asset_class: str
    num_entities: int = Field(ge=1, le=10000)
    time_horizon_years: int = Field(ge=1, le=30)
    frequency: Literal["monthly", "quarterly", "annual"]
    variables: dict[str, VariableSpec]
    correlations: list[tuple[str, str, float]]
    temporal: dict = Field(default_factory=lambda: {"autocorrelation": 0.0})

class ScenarioInput(BaseModel):
    natural_language: str = ""
    use_llm_profiler: bool = False

class PrivacyConfig(BaseModel):
    enabled: bool = False
    epsilon: float = Field(default=1.0, gt=0)

class GenerateRequest(BaseModel):
    scenario: ScenarioInput = ScenarioInput()
    profile_override: StatisticalProfile | None = None
    privacy: PrivacyConfig = PrivacyConfig()
    output_format: Literal["csv", "json"] = "csv"
    seed: int | None = None

class KSTestResult(BaseModel):
    statistic: float
    p_value: float
    passed: bool

class ValidationReport(BaseModel):
    row_count: int
    ks_tests: dict[str, KSTestResult]
    correlation_rmse: float
    dp_applied: bool
    dp_epsilon: float | None = None
    post_dp_ks_all_passed: bool | None = None

class GenerateResponse(BaseModel):
    job_id: str
    status: str
    download_url: str
    profile_used: StatisticalProfile
    validation_report: ValidationReport
    generated_at: str
```

### 9.3 `backend/app/config.py` — Settings

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    llm_provider: str = "google"                    # "google" or "openai"
    llm_api_key: str = ""
    llm_model: str = "gemini-3.1-pro-preview"       # or "gpt-5.2-chat-latest"
    llm_base_url: str = "https://api.openai.com/v1" # only used for openai provider
    default_dp_epsilon: float = 1.0
    max_entities: int = 10000
    output_dir: str = "/tmp/synth_output"

    class Config:
        env_file = ".env"
```

### 9.4 `backend/app/agents/profiler.py` — LLM Profiler Agent

**What it does**: Takes `scenario.natural_language`, sends it to the LLM via the Jinja2-templated prompt, returns a validated `StatisticalProfile`.

**Implementation**:
1. Load `prompts/profile_suggest.j2` with Jinja2
2. Render the template with `{"user_scenario": scenario.natural_language}`
3. Call the LLM (provider-specific, see below)
4. Parse the JSON response into `StatisticalProfile` via Pydantic
5. If Pydantic validation fails, retry once — include the validation error in a follow-up prompt
6. If still fails, raise `HTTPException(422, "LLM produced invalid profile")`

**Dual-provider LLM call**:
```python
if settings.llm_provider == "google":
    # Google GenAI SDK — native, handles auth/retries/parsing
    from google import genai
    client = genai.Client(api_key=settings.llm_api_key)
    response = client.models.generate_content(
        model=settings.llm_model,  # "gemini-3.1-pro-preview"
        contents=rendered_prompt,
        config={"response_mime_type": "application/json", "temperature": 0.2},
    )
    raw_json = response.text

elif settings.llm_provider == "openai":
    # httpx — standard OpenAI chat completions
    async with httpx.AsyncClient() as http_client:
        resp = await http_client.post(
            f"{settings.llm_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json={
                "model": settings.llm_model,  # "gpt-5.2-chat-latest"
                "messages": [{"role": "user", "content": rendered_prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            },
            timeout=30.0,
        )
    raw_json = resp.json()["choices"][0]["message"]["content"]
```

### 9.5 `backend/app/prompts/profile_suggest.j2` — Jinja2 Template

```jinja2
You are a quantitative finance expert. Given a natural-language description of a financial scenario, output a JSON object that precisely defines the statistical parameters needed to generate realistic synthetic data for that scenario.

## User Scenario
{{ user_scenario }}

## Output Requirements
Return ONLY valid JSON matching this exact schema (no markdown, no explanation):

{
  "asset_class": "<string: e.g. private_equity_lbo, venture_capital, real_estate_dcf, corporate_ma>",
  "num_entities": <int: number of simulated entities/companies, 10-500>,
  "time_horizon_years": <int: 1-30>,
  "frequency": "<monthly|quarterly|annual>",
  "variables": {
    "<variable_name>": {
      "distribution": "<normal|lognormal|beta|uniform|exponential>",
      <distribution-specific params: mean/std for normal, mu/sigma for lognormal, alpha/beta for beta, low/high for uniform, rate for exponential>
    }
  },
  "correlations": [
    ["<var_a>", "<var_b>", <float between -1 and 1>]
  ],
  "temporal": {
    "autocorrelation": <float 0-0.95: serial dependence strength>
  }
}

## Rules
- Choose distributions that reflect real-world financial properties (e.g., revenue is lognormal, margins are beta-distributed between 0 and 1, interest rates are lognormal with small mu)
- Correlations must be economically sensible (e.g., revenue and EBITDA margin are positively correlated; leverage and interest expense are positively correlated)
- Include 4-8 variables that are essential for the described scenario
- All correlation values must be between -1 and 1
- Variable names must use snake_case
```

### 9.6 `backend/app/agents/generator.py` — Deterministic Math Engine

**Zero LLM. Pure NumPy/SciPy.**

```python
import numpy as np
import pandas as pd
from scipy import stats
from scipy.linalg import cholesky
from app.schemas import VariableSpec, StatisticalProfile

def nearest_psd(matrix: np.ndarray) -> np.ndarray:
    """Higham's nearest positive semi-definite matrix (alternating projections)."""
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
    """Build a full correlation matrix from pairwise specs. Diagonal = 1."""
    n = len(var_names)
    idx = {name: i for i, name in enumerate(var_names)}
    C = np.eye(n)
    for var_a, var_b, rho in correlations:
        i, j = idx[var_a], idx[var_b]
        C[i, j] = rho
        C[j, i] = rho
    if not is_psd(C):
        C = nearest_psd(C)
    return C

def get_scipy_distribution(spec: VariableSpec):
    """Map a VariableSpec to a scipy.stats frozen distribution."""
    match spec.distribution:
        case "normal":
            return stats.norm(loc=spec.mean, scale=spec.std)
        case "lognormal":
            return stats.lognorm(s=spec.sigma, scale=np.exp(spec.mu))
        case "beta":
            return stats.beta(a=spec.alpha, b=spec.beta)
        case "uniform":
            return stats.uniform(loc=spec.low, scale=spec.high - spec.low)
        case "exponential":
            return stats.expon(scale=1.0 / spec.rate)

def generate(profile: StatisticalProfile, seed: int | None = None) -> tuple[pd.DataFrame, np.ndarray]:
    """
    Main generation function. Returns (DataFrame, correlation_matrix).

    1. Build + validate correlation matrix
    2. Cholesky decompose
    3. For each entity: draw correlated samples via Gaussian copula
    4. Apply AR(1) temporal structure
    5. Return DataFrame
    """
    rng = np.random.default_rng(seed)
    var_names = list(profile.variables.keys())
    n_vars = len(var_names)
    n_entities = profile.num_entities
    freq_map = {"monthly": 12, "quarterly": 4, "annual": 1}
    n_periods = profile.time_horizon_years * freq_map[profile.frequency]

    # Step 1-2: Correlation matrix + Cholesky
    corr_matrix = build_correlation_matrix(var_names, profile.correlations)
    L = cholesky(corr_matrix, lower=True)

    # Step 3: Gaussian copula
    distributions = {name: get_scipy_distribution(spec) for name, spec in profile.variables.items()}

    all_rows = []
    for entity_id in range(n_entities):
        # Draw independent standard normals
        Z = rng.standard_normal((n_periods, n_vars))
        # Correlate via Cholesky
        Z_corr = Z @ L.T
        # Transform to uniform via normal CDF
        U = stats.norm.cdf(Z_corr)
        # Transform to target marginals via inverse CDF
        samples = np.column_stack([
            distributions[name].ppf(U[:, i])
            for i, name in enumerate(var_names)
        ])

        # Step 4: AR(1) temporal dependence
        rho = profile.temporal.get("autocorrelation", 0.0)
        if rho > 0:
            for col in range(n_vars):
                for t in range(1, n_periods):
                    samples[t, col] = rho * samples[t-1, col] + (1 - rho) * samples[t, col]

        # Build rows
        for t in range(n_periods):
            row = {"entity_id": entity_id, "period": t}
            for i, name in enumerate(var_names):
                row[name] = samples[t, i]
            all_rows.append(row)

    return pd.DataFrame(all_rows), corr_matrix
```

### 9.7 `backend/app/agents/validator.py` — DP Validator

```python
import numpy as np
import pandas as pd
from scipy import stats
from app.schemas import VariableSpec, StatisticalProfile, PrivacyConfig, KSTestResult, ValidationReport
from app.agents.generator import get_scipy_distribution

def ks_test(data: np.ndarray, spec: VariableSpec) -> KSTestResult:
    """Run KS test for a single variable against its target distribution."""
    dist = get_scipy_distribution(spec)
    statistic, p_value = stats.kstest(data, dist.cdf)
    return KSTestResult(statistic=round(statistic, 4), p_value=round(p_value, 4), passed=p_value > 0.05)

def correlation_rmse(data: pd.DataFrame, var_names: list[str], target_corr: np.ndarray) -> float:
    """Frobenius norm between empirical and target correlation matrices, normalized."""
    empirical = data[var_names].corr().values
    diff = empirical - target_corr
    return float(round(np.sqrt(np.mean(diff**2)), 4))

def apply_differential_privacy(data: pd.DataFrame, var_names: list[str], epsilon: float, rng) -> pd.DataFrame:
    """
    Apply Laplace mechanism to each numeric column.
    sensitivity = column range (max - min) for bounded data.
    noise ~ Laplace(0, sensitivity / epsilon)
    """
    df = data.copy()
    for col in var_names:
        col_range = df[col].max() - df[col].min()
        sensitivity = col_range
        scale = sensitivity / epsilon
        noise = rng.laplace(0, scale, size=len(df))
        df[col] = df[col] + noise
    return df

def validate(
    data: pd.DataFrame,
    profile: StatisticalProfile,
    corr_matrix: np.ndarray,
    privacy_config: PrivacyConfig,
    seed: int | None = None,
) -> tuple[pd.DataFrame, ValidationReport]:
    """Full validation + optional DP. Returns (possibly noised df, report)."""
    rng = np.random.default_rng(seed)
    var_names = list(profile.variables.keys())

    # KS tests pre-DP
    ks_results = {}
    for name, spec in profile.variables.items():
        ks_results[name] = ks_test(data[name].values, spec)

    # Correlation RMSE
    corr_err = correlation_rmse(data, var_names, corr_matrix)

    # DP
    dp_applied = privacy_config.enabled
    post_dp_passed = None
    if dp_applied:
        data = apply_differential_privacy(data, var_names, privacy_config.epsilon, rng)
        post_dp_results = {
            name: ks_test(data[name].values, spec)
            for name, spec in profile.variables.items()
        }
        post_dp_passed = all(r.passed for r in post_dp_results.values())

    report = ValidationReport(
        row_count=len(data),
        ks_tests=ks_results,
        correlation_rmse=corr_err,
        dp_applied=dp_applied,
        dp_epsilon=privacy_config.epsilon if dp_applied else None,
        post_dp_ks_all_passed=post_dp_passed,
    )
    return data, report
```

### 9.8 `backend/app/agents/formatter.py` — Export Agent

```python
import pandas as pd

def export(df: pd.DataFrame, output_format: str, job_id: str, output_dir: str) -> str:
    """Write to disk, return file path. NEVER writes .xlsx."""
    ext = output_format  # "csv" or "json"
    path = f"{output_dir}/{job_id}.{ext}"
    if output_format == "csv":
        df.to_csv(path, index=False)
    else:
        df.to_json(path, orient="records", indent=2)
    return path
```

### 9.9 `backend/app/pipeline.py` — Orchestrator

```python
import uuid
from datetime import datetime, timezone
from app.schemas import GenerateRequest, GenerateResponse
from app.config import Settings
from app.agents import profiler, generator, validator, formatter

async def run_pipeline(request: GenerateRequest, settings: Settings) -> GenerateResponse:
    """
    1. If use_llm_profiler → call profiler agent → get StatisticalProfile
    2. If profile_override provided → merge/override
    3. Call generator engine → raw DataFrame
    4. Call validator → validated (+ possibly DP-noised) DataFrame + report
    5. Call formatter → write file
    6. Return GenerateResponse
    """
    job_id = str(uuid.uuid4())

    # Step 1-2: Resolve profile
    if request.scenario.use_llm_profiler:
        profile = await profiler.generate_profile(request.scenario.natural_language, settings)
        # If override fields provided, deep-merge them on top
        if request.profile_override:
            override_data = request.profile_override.model_dump(exclude_unset=True)
            profile_data = profile.model_dump()
            profile_data.update(override_data)
            profile = type(profile)(**profile_data)
    elif request.profile_override:
        profile = request.profile_override
    else:
        from fastapi import HTTPException
        raise HTTPException(422, "Either use_llm_profiler or profile_override must be provided")

    # Step 3: Generate
    data, corr_matrix = generator.generate(profile, seed=request.seed)

    # Step 4: Validate + DP
    data, report = validator.validate(data, profile, corr_matrix, request.privacy, seed=request.seed)

    # Step 5: Export
    formatter.export(data, request.output_format, job_id, settings.output_dir)

    # Step 6: Response
    return GenerateResponse(
        job_id=job_id,
        status="completed",
        download_url=f"/api/v1/download/{job_id}",
        profile_used=profile,
        validation_report=report,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
```

### 9.10 `backend/app/main.py` — FastAPI App

| Method | Path | Handler |
|--------|------|---------|
| `POST` | `/api/v1/generate` | Calls `run_pipeline`, returns `GenerateResponse` |
| `GET` | `/api/v1/download/{job_id}` | `FileResponse` from `output_dir/{job_id}.*` |
| `GET` | `/api/v1/templates` | Returns list from `templates.py` |
| `GET` | `/health` | Returns `{"status": "ok"}` |

- Add CORS middleware allowing `*` origins (demo only)
- Create `output_dir` on startup if it doesn't exist
- Instantiate `Settings()` as a module-level singleton or use FastAPI dependency injection

### 9.11 `backend/app/templates.py` — Presets

Return a list of dicts, each with `name`, `description`, and a full `StatisticalProfile` dict. Include at least:

1. **PE LBO** — revenue (lognormal), ebitda_margin (beta), leverage_ratio (normal), interest_rate (lognormal), capex_pct (uniform). Correlations: revenue↔ebitda +0.55, leverage↔interest +0.4, ebitda↔leverage -0.35.

2. **VC Portfolio** — burn_rate (lognormal), monthly_revenue (lognormal), runway_months (normal), headcount (normal), ltv_cac_ratio (beta). Low correlations.

3. **Real Estate DCF** — noi (lognormal), cap_rate (beta), vacancy_rate (beta), rent_growth (normal), interest_rate (lognormal). noi↔cap_rate -0.3, vacancy↔rent_growth -0.5.

### 9.12 `frontend/app.py` — Streamlit UI

**Layout**:
```python
st.set_page_config(page_title="Synthetic Data Generator", layout="wide")
st.title("Tracelight Synthetic Data Generator")
```

**Sidebar**:
- Dropdown: "Select a preset" (populated from `GET /api/v1/templates`) + "Custom" option
- Toggle: "Use LLM Profiler"
- If LLM toggle on: text area for natural-language scenario
- Number inputs: num_entities, time_horizon_years
- Selectbox: frequency
- Toggle + slider: DP enabled, epsilon
- Radio: output format (CSV/JSON)

**Main area** (after generation):
- `st.dataframe()` — first 20 rows
- Two columns:
  - Left: `plotly` histograms per variable (use `st.plotly_chart`)
  - Right: `plotly` heatmap of correlation matrix (target vs actual side by side)
- Expander: "Validation Report" — show KS test table, correlation RMSE, DP status
- `st.download_button` — download the file

**API calls**: Use `requests.post("http://backend:8000/api/v1/generate", json=payload)` (Docker network name).

### 9.13 Docker

**`backend/Dockerfile`**:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`frontend/Dockerfile`**:
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**`docker-compose.yml`**:
```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - synth_output:/tmp/synth_output

  frontend:
    build: ./frontend
    ports:
      - "8501:8501"
    depends_on:
      - backend

volumes:
  synth_output:
```

**`.env.example`**:
```
LLM_PROVIDER=google
LLM_API_KEY=your-gemini-api-key-here
LLM_MODEL=gemini-3.1-pro-preview

# To switch to OpenAI GPT-5.2, uncomment below and comment above:
# LLM_PROVIDER=openai
# LLM_API_KEY=sk-your-key-here
# LLM_MODEL=gpt-5.2-chat-latest
# LLM_BASE_URL=https://api.openai.com/v1
```

### 9.14 `backend/requirements.txt`
```
fastapi>=0.115
uvicorn[standard]>=0.30
pydantic>=2.0
pydantic-settings>=2.0
numpy>=1.26
scipy>=1.12
pandas>=2.2
jinja2>=3.1
google-genai>=1.0
httpx>=0.27
python-dotenv>=1.0
```

### 9.15 `frontend/requirements.txt`
```
streamlit>=1.38
plotly>=5.22
requests>=2.31
pandas>=2.2
```

### 9.16 Acceptance Criteria

- [ ] `docker-compose up --build` starts both services without errors
- [ ] `GET localhost:8000/health` returns `{"status": "ok"}`
- [ ] `POST localhost:8000/api/v1/generate` with a full `profile_override` (no LLM) returns valid CSV
- [ ] `GET localhost:8000/api/v1/templates` returns 3 presets
- [ ] Streamlit at `localhost:8501` renders the full UI flow
- [ ] Generated data has correct row count (`num_entities × periods`)
- [ ] KS tests pass (p > 0.05) in the validation report
- [ ] Correlation RMSE < 0.05
- [ ] With DP enabled, noise is visibly applied and report reflects it
- [ ] **No `.xlsx` files are created anywhere in the codebase**
- [ ] All LLM calls go through the Jinja2 template only
- [ ] Generator engine uses zero LLM calls

### 9.17 Scope Boundaries

**Phase 1 includes**:
- Fully working FastAPI backend with all 4 agents
- Streamlit frontend with end-to-end flow
- Docker containerization
- LLM Profiler: Gemini 3.1 Pro Preview (default) / GPT-5.2 (switchable)
- Deterministic generation engine with Gaussian copula + Cholesky
- DP Laplace mechanism with KS-test validation
- CSV/JSON output only

**Explicitly deferred to future phases**:
- Advanced generative models (TimeGAN, VAE)
- Authentication / multi-tenancy
- Persistent job storage (currently in-memory)

---
---

## 10. Phase 2: Post-Excel Narrative Deliverable Engine

> **Workflow II from CONTEXT.MD.** This phase adds a second microservice pipeline that ingests structured financial data (JSON/CSV from Phase 1 or exported Tracelight model outputs) plus qualitative source documents, and generates audit-ready Investment Committee memorandums (Word) and executive presentations (PowerPoint).

### 10.1 The Problem

After a financial model is built in Tracelight's Excel engine, analysts spend 48-72 hours manually:
1. Extracting quantitative outputs from the spreadsheet
2. Pasting data into charts
3. Drafting 15-50 page IC memos in Word
4. Building executive PowerPoint decks

This is the **post-Excel bottleneck** — Tracelight perfected the center of the workflow, but the final mile remains entirely manual.

### 10.2 IP Boundary (DMZ Rule — Phase 2 Addendum)

| We DO | We DO NOT |
|-------|-----------|
| Ingest **exported** financial data (CSV/JSON) as a structured payload | Read from or write to `.xlsx` files |
| Ingest qualitative source documents (PDF, DOCX, TXT) for context | Parse Excel formulas, cell references, or spreadsheet logic |
| Generate `.docx` (Word) and `.pptx` (PowerPoint) deliverables | Modify or interact with Tracelight's in-Excel AI |
| Use LLM for narrative drafting with citation enforcement | Use LLM to generate financial models or formulas |
| Produce audit trails linking every claim to source data | Replicate any Tracelight core functionality |

### 10.3 Architecture — Phase 2 Addition

```
┌──────────────────────────────────────────────────────────────┐
│                    STREAMLIT FRONTEND (extended)              │
│  ┌──────────────┐  ┌────────────────┐  ┌──────────────────┐ │
│  │ Phase 1:     │  │ Phase 2:       │  │ Phase 2:         │ │
│  │ Synth Data   │  │ Upload Sources │  │ Preview + Export  │ │
│  │ Generator    │  │ + Config Memo  │  │ (DOCX/PPTX)      │ │
│  └──────────────┘  └───────┬────────┘  └──────────────────┘ │
└────────────────────────────┼─────────────────────────────────┘
                             │ HTTP (port 8501 → 8000)
┌────────────────────────────▼─────────────────────────────────┐
│              FASTAPI BACKEND (port 8000 — extended)           │
│                                                               │
│  Phase 1 routes (unchanged):                                  │
│    POST /api/v1/generate                                      │
│    GET  /api/v1/download/{job_id}                             │
│    GET  /api/v1/templates                                     │
│                                                               │
│  Phase 2 routes (new):                                        │
│    POST /api/v2/memo/generate                                 │
│    POST /api/v2/memo/upload-sources                           │
│    GET  /api/v2/memo/download/{job_id}                        │
│    GET  /api/v2/memo/status/{job_id}                          │
│                                                               │
│  ┌──────────── PHASE 2 PIPELINE ───────────────────────────┐ │
│  │                                                         │ │
│  │  ┌─────────────────┐                                    │ │
│  │  │ 1. CONTEXT       │  PDF/DOCX/TXT ingestion           │ │
│  │  │    HARVESTER     │  Semantic chunking + embedding     │ │
│  │  │    AGENT         │  → ChromaDB vector store           │ │
│  │  └────────┬─────────┘                                   │ │
│  │           │ Indexed vector store                         │ │
│  │           ▼                                             │ │
│  │  ┌─────────────────┐                                    │ │
│  │  │ 2. QUANTITATIVE  │  Ingest CSV/JSON financial data    │ │
│  │  │    EXTRACTION    │  Deterministic metric extraction    │ │
│  │  │    AGENT         │  Source-tagged JSON payload         │ │
│  │  └────────┬─────────┘                                   │ │
│  │           │ CitedMetrics (every number has a source tag) │ │
│  │           ▼                                             │ │
│  │  ┌─────────────────┐                                    │ │
│  │  │ 3. NARRATIVE     │  LLM drafts memo section-by-sec   │ │
│  │  │    DRAFTING      │  Citation-enforced RAG             │ │
│  │  │    AGENT         │  Pyramid Principle structure       │ │
│  │  └────────┬─────────┘                                   │ │
│  │           │ SectionDraft[] with inline citations         │ │
│  │           ▼                                             │ │
│  │  ┌─────────────────┐                                    │ │
│  │  │ 4. CITATION &    │  Verify every claim has source     │ │
│  │  │    FORMATTING    │  Inject into DOCX/PPTX templates   │ │
│  │  │    AGENT         │  Generate audit trail appendix     │ │
│  │  └─────────────────┘                                   │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 10.4 New Files to Create

```
backend/
├── app/
│   ├── schemas_v2.py                    # Phase 2 Pydantic models
│   ├── pipeline_v2.py                   # Phase 2 orchestrator
│   ├── agents/
│   │   ├── context_harvester.py         # PDF/DOCX ingestion + vector store
│   │   ├── quant_extractor.py           # Financial data extraction + source tagging
│   │   ├── narrative_drafter.py         # Citation-enforced LLM narrative generation
│   │   └── citation_formatter.py        # Audit trail + DOCX/PPTX rendering
│   ├── prompts/
│   │   ├── memo_section.j2             # Per-section drafting prompt
│   │   └── executive_summary.j2        # Top-level summary prompt
│   └── templates_v2/
│       ├── ic_memo_template.docx       # Word template with Jinja2 placeholders
│       └── exec_deck_template.pptx     # PowerPoint template
```

### 10.5 `backend/app/schemas_v2.py` — Phase 2 Pydantic Models

```python
from pydantic import BaseModel, Field
from typing import Literal

class SourceDocument(BaseModel):
    """A qualitative source document uploaded by the user."""
    filename: str
    doc_type: Literal["cim", "management_presentation", "expert_call", "market_report", "other"]
    description: str = ""

class FinancialMetric(BaseModel):
    """A single extracted metric with mandatory source attribution."""
    name: str                               # e.g. "base_case_irr"
    value: float | str
    unit: str = ""                          # e.g. "%", "$M", "x"
    scenario: Literal["base", "upside", "downside"] = "base"
    source_tag: str                         # e.g. "model_export:row_42:irr" or "cim:page_12"

class CitedMetrics(BaseModel):
    """All extracted financial metrics, each source-tagged."""
    company_name: str
    deal_type: str                          # e.g. "LBO", "Growth Equity", "M&A"
    currency: str = "USD"
    metrics: list[FinancialMetric]

class MemoSection(BaseModel):
    """One section of the IC memo."""
    section_id: str                         # e.g. "executive_summary", "investment_thesis"
    title: str
    content: str                            # Markdown with inline citations [source_tag]
    citations: list[str]                    # List of source_tags referenced
    confidence: float = Field(ge=0, le=1)   # LLM's confidence in the section
    needs_review: bool = False              # Flagged if confidence < threshold

class MemoConfig(BaseModel):
    """User configuration for memo generation."""
    memo_type: Literal["ic_memo", "exec_deck", "both"] = "both"
    firm_name: str = ""
    sections: list[str] = Field(default_factory=lambda: [
        "executive_summary",
        "investment_thesis",
        "market_analysis",
        "financial_projections",
        "deal_structure",
        "risk_mitigation",
    ])
    tone: Literal["formal", "concise", "technical"] = "formal"
    max_pages: int = Field(default=30, ge=5, le=50)
    confidence_threshold: float = Field(default=0.7, ge=0, le=1)

class MemoGenerateRequest(BaseModel):
    """Request body for POST /api/v2/memo/generate."""
    session_id: str                         # From prior upload-sources call
    financial_data_job_id: str | None = None # Optional: pull from Phase 1 output
    financial_data_inline: CitedMetrics | None = None  # Or provide directly
    config: MemoConfig = MemoConfig()

class MemoGenerateResponse(BaseModel):
    job_id: str
    status: Literal["processing", "completed", "failed"]
    sections: list[MemoSection] | None = None
    download_urls: dict[str, str] = {}      # {"docx": "/api/v2/memo/download/xxx?fmt=docx", ...}
    audit_trail_url: str | None = None
    generated_at: str
```

### 10.6 Agent 1: Context Harvester Agent

**Role**: Ingest qualitative source documents, chunk them semantically, embed them into a per-session vector store for RAG retrieval.

**Implementation**:
1. Accept uploaded files via `POST /api/v2/memo/upload-sources` (PDF, DOCX, TXT)
2. Extract text:
   - PDF → `pymupdf` (fitz) for text extraction + table detection
   - DOCX → `python-docx` for paragraph extraction
   - TXT → direct read
3. Semantic chunking: split into ~500-token chunks with 50-token overlap, preserving paragraph boundaries
4. Embed chunks using a lightweight local model (`sentence-transformers/all-MiniLM-L6-v2`) — no external API call needed
5. Store in **ChromaDB** (ephemeral, per-session collection) with metadata: `{source_filename, page_number, chunk_index}`
6. Return a `session_id` for downstream agents to query

**Why ChromaDB**: Lightweight, runs in-process (no separate service), perfect for a demo. Ephemeral collections clean up automatically.

**Why local embeddings**: Avoids external API latency/cost for document ingestion. MiniLM-L6-v2 is 80MB and runs in ~10ms per chunk on CPU.

**Key references (sourced via Nia MCP)**:
- `huseink/docx-dynamic-generation` — FastAPI + python-docx-template integration pattern
- Citation-Enforced RAG for Fiscal Document Intelligence (arXiv:2603.14170) — source-first ingestion with span-level traceability

### 10.7 Agent 2: Quantitative Extraction Agent

**Role**: Deterministic. Zero LLM. Extract and source-tag every financial metric from the input data.

**Implementation**:
1. If `financial_data_job_id` is provided: load the CSV/JSON from Phase 1's output directory
2. If `financial_data_inline` is provided: use directly
3. For each metric in the data:
   - Compute summary statistics (mean, median, P10/P90 across entities)
   - Compute scenario-specific metrics (base/upside/downside if multiple seeds)
   - Tag every number with a deterministic `source_tag`: `"model_export:{column}:{aggregation}"` (e.g., `"model_export:ebitda_margin:p50"`)
4. Output: `CitedMetrics` object — every single number has a provenance tag

**Critical rule**: This agent never generates numbers. It only extracts, aggregates, and tags. Every metric in the output must be traceable to a specific column and aggregation of the input data.

### 10.8 Agent 3: Narrative Drafting Agent

**Role**: LLM-powered, section-by-section IC memo drafting with **mandatory citation enforcement**.

**Implementation (per section)**:
1. Load section-specific Jinja2 template (`memo_section.j2`)
2. Retrieve top-K relevant chunks from ChromaDB via semantic search on the section topic
3. Inject retrieved chunks + `CitedMetrics` for the relevant section into the prompt
4. LLM generates the section narrative with **inline citations**: every factual claim must reference a `[source_tag]`
5. **Post-generation validation**: parse the output for citation tags, verify each tag exists in the `CitedMetrics` or ChromaDB metadata. If a claim has no citation, flag `needs_review = True`
6. Assign `confidence` score: `(cited_claims / total_claims)`. If below `confidence_threshold`, route to human review.

**Citation enforcement approach** (adapted from arXiv:2603.14170):
- **Source-first**: the prompt includes only retrieved evidence — LLM is explicitly instructed: *"Do not include any claim that cannot be supported by the provided data. If insufficient evidence, write: [INSUFFICIENT DATA — REQUIRES ANALYST INPUT]"*
- **Post-validation**: regex scan for `[source_tag]` patterns, cross-reference against known tags
- **Abstention**: sections with <70% citation coverage are flagged, not silently included

**Pyramid Principle**: Each section opens with the conclusion/recommendation, followed by supporting arguments grouped logically. This is enforced via the Jinja2 template structure.

### 10.9 Agent 4: Citation & Formatting Agent

**Role**: Render the validated narrative into professional `.docx` and `.pptx` files using templates, and generate an audit trail appendix.

**Implementation**:
1. **Word generation** (`python-docx-template` / `docxtpl`):
   - Load `ic_memo_template.docx` — a pre-styled Word template with Jinja2 tags (`{{ executive_summary }}`, `{{ investment_thesis }}`, etc.)
   - Inject section content, converting inline `[source_tag]` references to Word footnotes or endnotes
   - Inject charts as images (pre-rendered by `plotly` → PNG)
   - Generate audit trail appendix: table mapping every `[source_tag]` → source document, page, metric value

2. **PowerPoint generation** (`python-pptx`):
   - Load `exec_deck_template.pptx` — branded slide master
   - Slide 1: Title + deal summary
   - Slide 2: Investment thesis (3-4 bullets from exec summary)
   - Slides 3-5: Key financial metrics as charts (plotly → PNG → inserted)
   - Slide 6: Risk matrix
   - Slide 7: Recommendation

3. **Audit trail JSON**: machine-readable mapping of every generated claim to its source

**Key references (sourced via Nia MCP)**:
- `docxtpl` / `python-docx-template` — Jinja2-powered Word generation
- `molodsom/docx-generator` — DOCX/PDF generation from templates via Jinja2
- `python-pptx` — programmatic PowerPoint generation
- `icip-cas/PPTAgent` — agentic framework for reflective slide generation

### 10.10 `backend/app/prompts/memo_section.j2` — Section Drafting Template

```jinja2
You are a senior investment analyst at a top-tier private equity firm drafting an Investment Committee memorandum. You write in a formal, precise style following the McKinsey Pyramid Principle: lead with the conclusion, then provide supporting evidence.

## Section: {{ section_title }}

## Financial Data (Source-Tagged)
{% for metric in relevant_metrics %}
- {{ metric.name }}: {{ metric.value }}{{ metric.unit }} [{{ metric.source_tag }}] ({{ metric.scenario }} case)
{% endfor %}

## Qualitative Context (Retrieved from Source Documents)
{% for chunk in retrieved_chunks %}
---
Source: {{ chunk.metadata.source_filename }}, Page {{ chunk.metadata.page_number }}
Content: {{ chunk.text }}
---
{% endfor %}

## Instructions
1. Draft the "{{ section_title }}" section of the IC memo.
2. **MANDATORY**: Every factual claim or number MUST include an inline citation in the format [source_tag]. Use the exact source_tags provided above.
3. If you cannot support a claim from the provided data, write: [INSUFFICIENT DATA — REQUIRES ANALYST INPUT]
4. Structure: Lead with the key takeaway for this section, then provide 2-4 supporting arguments.
5. Use precise financial language. No hedging unless the data warrants it.
6. Target length: {{ target_words }} words.

Return the section as markdown text with inline [source_tag] citations.
```

### 10.11 `backend/app/prompts/executive_summary.j2`

```jinja2
You are drafting the Executive Summary for an Investment Committee memorandum. This is the most critical section — senior partners will read this first and may read nothing else.

## Deal Overview
- Company: {{ company_name }}
- Deal Type: {{ deal_type }}
- Firm: {{ firm_name }}

## Key Metrics
{% for metric in key_metrics %}
- {{ metric.name }}: {{ metric.value }}{{ metric.unit }} [{{ metric.source_tag }}]
{% endfor %}

## Section Summaries
{% for section in section_summaries %}
### {{ section.title }}
{{ section.summary }}
{% endfor %}

## Instructions
1. Write a 300-500 word executive summary following the Pyramid Principle.
2. Open with the investment recommendation (proceed / pass / conditional proceed).
3. Cite the 3-5 most critical metrics with their [source_tag].
4. Highlight the top 2 risks and mitigants.
5. Every number must have a [source_tag] citation.
```

### 10.12 API Routes — Phase 2

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| `POST` | `/api/v2/memo/upload-sources` | Accepts multipart file upload | Ingests PDFs/DOCX/TXT, chunks, embeds, returns `session_id` |
| `POST` | `/api/v2/memo/generate` | Accepts `MemoGenerateRequest` | Kicks off async pipeline, returns `job_id` immediately |
| `GET` | `/api/v2/memo/status/{job_id}` | Poll for completion | Returns current status + sections as they complete |
| `GET` | `/api/v2/memo/download/{job_id}` | Query param `fmt=docx\|pptx\|json` | Downloads the generated deliverable |

**Note**: Phase 2 pipeline runs **async via BackgroundTasks** (incorporating Gemini's feedback from Phase 1). The generate endpoint returns immediately with a `job_id`; the frontend polls `/status/`.

### 10.13 Streamlit Frontend Extension

**New tab**: "Deliverable Engine" (alongside existing "Synthetic Data Generator")

**Flow**:
1. **Upload Sources**: Multi-file uploader for CIM, management decks, expert call transcripts (PDF/DOCX/TXT). Shows upload progress + chunking status.
2. **Financial Data**: Either "Pull from Phase 1 job" (dropdown of recent job IDs) or "Upload CSV/JSON directly"
3. **Configure Memo**:
   - Firm name input
   - Memo type: IC Memo / Exec Deck / Both
   - Section checkboxes (all checked by default)
   - Tone selector
   - Confidence threshold slider (default 0.7)
4. **Generate**: Button → shows progress bar polling `/status/`
5. **Review Dashboard**:
   - Section-by-section preview (markdown rendered)
   - Sections flagged `needs_review` highlighted in amber with "[INSUFFICIENT DATA]" markers visible
   - Citation sidebar: click any `[source_tag]` to see the source chunk
   - Audit trail table: expandable
6. **Download**: Buttons for `.docx`, `.pptx`, and audit trail JSON

### 10.14 New Dependencies — Phase 2

**Backend additions to `requirements.txt`**:
```
docxtpl>=0.18                # Word generation from Jinja2 templates
python-pptx>=1.0             # PowerPoint generation
chromadb>=0.5                # In-process vector store
sentence-transformers>=3.0   # Local embedding model (all-MiniLM-L6-v2)
pymupdf>=1.24                # PDF text extraction
plotly>=5.22                  # Chart rendering to PNG for doc insertion
kaleido>=0.2                  # Plotly static image export
```

### 10.15 Docker Updates

**`docker-compose.yml`** — no new services needed. ChromaDB runs in-process within the backend container. The only change is the backend Dockerfile needs to handle the larger image (sentence-transformers model download).

**`backend/Dockerfile` addition**:
```dockerfile
# Pre-download the embedding model at build time to avoid runtime latency
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

### 10.16 Acceptance Criteria — Phase 2

- [ ] `POST /api/v2/memo/upload-sources` accepts PDF/DOCX/TXT, returns `session_id`
- [ ] `POST /api/v2/memo/generate` returns `job_id` immediately (async)
- [ ] `GET /api/v2/memo/status/{job_id}` shows progress, eventually `completed`
- [ ] Generated IC memo has all 6 default sections
- [ ] **Every factual claim in the memo has an inline `[source_tag]` citation**
- [ ] Sections with confidence < 0.7 are flagged `needs_review: true`
- [ ] Claims without sufficient evidence show `[INSUFFICIENT DATA — REQUIRES ANALYST INPUT]`
- [ ] `GET /api/v2/memo/download/{job_id}?fmt=docx` returns a valid `.docx` file
- [ ] `GET /api/v2/memo/download/{job_id}?fmt=pptx` returns a valid `.pptx` file with charts
- [ ] Audit trail JSON maps every citation to source document + page/row
- [ ] **No `.xlsx` files are created or read anywhere**
- [ ] Streamlit "Deliverable Engine" tab works end-to-end
- [ ] Pipeline can pull financial data from a Phase 1 `job_id` seamlessly

---
---

## 11. Phase 3: InfoSec & Vendor Risk Automation Pipeline

> **Workflow III from CONTEXT.MD.** This phase adds a compliance automation pipeline that ingests inbound security questionnaires (SIG Core/Lite, CAIQ, bespoke), matches questions against Tracelight's internal security knowledge base, and auto-generates responses with confidence scoring and human-in-the-loop routing for low-confidence answers.

### 11.1 The Problem

As a seed-stage startup selling to PE funds, banks, and asset managers, Tracelight faces exhaustive third-party vendor risk assessments:
- **SIG Core**: 800+ questions across 21 risk domains
- **SIG Lite**: ~126 questions for lower-risk engagements
- **CAIQ**: 260+ cloud security control questions
- **Bespoke**: Every bank has its own custom questionnaire

The CTO and engineering team — former Jane Street engineers — are currently hand-completing these. Hundreds of hours drained from product development to copy-paste answers into procurement spreadsheets.

### 11.2 IP Boundary (DMZ Rule — Phase 3 Addendum)

| We DO | We DO NOT |
|-------|-----------|
| Parse inbound questionnaires (CSV, DOCX, PDF, JSON) | Read or write `.xlsx` questionnaire files |
| Match questions against an indexed security knowledge base | Access Tracelight's production infrastructure or codebase |
| Generate draft responses with confidence scores | Make claims about security controls not in the knowledge base |
| Route low-confidence answers to human reviewers | Auto-submit responses without human approval |
| Export completed questionnaires as CSV/DOCX/JSON | Touch any financial modeling or in-Excel functionality |

### 11.3 Architecture — Phase 3 Addition

```
┌──────────────────────────────────────────────────────────────┐
│                 STREAMLIT FRONTEND (extended)                  │
│  ┌────────────┐  ┌────────────────┐  ┌─────────────────────┐ │
│  │ Phase 1:   │  │ Phase 2:       │  │ Phase 3:            │ │
│  │ Synth Data │  │ Deliverables   │  │ Compliance Engine   │ │
│  └────────────┘  └────────────────┘  └──────────┬──────────┘ │
└─────────────────────────────────────────────────┼────────────┘
                                                  │ HTTP
┌─────────────────────────────────────────────────▼────────────┐
│               FASTAPI BACKEND (port 8000 — extended)          │
│                                                               │
│  Phase 3 routes (new):                                        │
│    POST /api/v3/compliance/upload-kb                           │
│    POST /api/v3/compliance/upload-questionnaire                │
│    POST /api/v3/compliance/generate                            │
│    GET  /api/v3/compliance/status/{job_id}                     │
│    PATCH /api/v3/compliance/review/{job_id}/{question_id}      │
│    GET  /api/v3/compliance/download/{job_id}                   │
│                                                               │
│  ┌──────────── PHASE 3 PIPELINE ───────────────────────────┐ │
│  │                                                         │ │
│  │  ┌─────────────────┐                                    │ │
│  │  │ 1. INTAKE &      │  Parse questionnaire format        │ │
│  │  │    PARSING       │  Normalize to QuestionItem[]        │ │
│  │  │    AGENT         │  Detect framework (SIG/CAIQ/custom) │ │
│  │  └────────┬─────────┘                                   │ │
│  │           │ QuestionItem[] (normalized)                   │ │
│  │           ▼                                             │ │
│  │  ┌─────────────────┐                                    │ │
│  │  │ 2. KNOWLEDGE     │  Semantic search against KB         │ │
│  │  │    RETRIEVAL     │  Retrieve top-K policy matches      │ │
│  │  │    AGENT         │  Per question                       │ │
│  │  └────────┬─────────┘                                   │ │
│  │           │ QuestionItem + RetrievedEvidence[]            │ │
│  │           ▼                                             │ │
│  │  ┌─────────────────┐                                    │ │
│  │  │ 3. RESPONSE      │  LLM drafts answer per question    │ │
│  │  │    DRAFTING      │  Citation-enforced (reuses Phase 2  │ │
│  │  │    AGENT         │  pattern). Confidence scored.       │ │
│  │  └────────┬─────────┘                                   │ │
│  │           │ DraftResponse[] with confidence scores        │ │
│  │           ▼                                             │ │
│  │  ┌─────────────────┐                                    │ │
│  │  │ 4. ROUTING &     │  High confidence → auto-approved    │ │
│  │  │    EXPORT        │  Low confidence → flagged for human │ │
│  │  │    AGENT         │  Export to CSV/DOCX/JSON             │ │
│  │  └─────────────────┘                                   │ │
│  └─────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 11.4 New Files to Create

```
backend/
├── app/
│   ├── schemas_v3.py                    # Phase 3 Pydantic models
│   ├── pipeline_v3.py                   # Phase 3 orchestrator
│   ├── agents/
│   │   ├── intake_parser.py             # Questionnaire format detection + normalization
│   │   ├── kb_retriever.py              # Knowledge base indexing + semantic retrieval
│   │   ├── response_drafter.py          # LLM response generation with citation enforcement
│   │   └── routing_exporter.py          # Confidence routing + export to CSV/DOCX/JSON
│   ├── prompts/
│   │   └── compliance_response.j2       # Per-question response prompt
```

### 11.5 `backend/app/schemas_v3.py` — Phase 3 Pydantic Models

```python
from pydantic import BaseModel, Field
from typing import Literal

class QuestionItem(BaseModel):
    """A single normalized question from any questionnaire format."""
    question_id: str                        # e.g., "SIG_A.1.1" or "CAIQ_AIS-01" or "Q42"
    domain: str = ""                        # e.g., "Access Control", "Encryption", "Business Resiliency"
    question_text: str
    response_type: Literal["boolean", "narrative", "multiple_choice", "evidence_upload"] = "narrative"
    options: list[str] = []                 # For multiple_choice
    framework: str = ""                     # "sig_core", "sig_lite", "caiq", "custom"

class KBDocument(BaseModel):
    """A security policy or evidence document in the knowledge base."""
    filename: str
    doc_type: Literal["soc2_report", "pentest_summary", "incident_response_plan",
                       "security_policy", "prior_questionnaire", "architecture_doc", "other"]
    description: str = ""

class RetrievedEvidence(BaseModel):
    """A chunk retrieved from the KB matching a specific question."""
    text: str
    source_filename: str
    page_number: int = 0
    similarity_score: float

class DraftResponse(BaseModel):
    """A generated response for a single question."""
    question_id: str
    question_text: str
    domain: str
    response_text: str
    response_type: Literal["boolean", "narrative", "multiple_choice"] = "narrative"
    boolean_value: bool | None = None       # For boolean questions
    citations: list[str]                    # Source tags
    confidence: float = Field(ge=0, le=1)
    status: Literal["auto_approved", "needs_review", "human_overridden"] = "needs_review"
    reviewer_notes: str = ""

class ComplianceConfig(BaseModel):
    """User configuration for questionnaire processing."""
    confidence_threshold: float = Field(default=0.8, ge=0, le=1)
    auto_approve_above: float = Field(default=0.9, ge=0, le=1)
    company_name: str = "Tracelight"
    default_tone: Literal["formal", "concise", "technical"] = "formal"

class ComplianceGenerateRequest(BaseModel):
    """Request body for POST /api/v3/compliance/generate."""
    kb_session_id: str                      # From prior upload-kb call
    questionnaire_session_id: str           # From prior upload-questionnaire call
    config: ComplianceConfig = ComplianceConfig()

class ComplianceGenerateResponse(BaseModel):
    job_id: str
    status: Literal["processing", "completed", "failed"]
    total_questions: int = 0
    auto_approved: int = 0
    needs_review: int = 0
    responses: list[DraftResponse] | None = None
    download_urls: dict[str, str] = {}
    generated_at: str

class ReviewUpdate(BaseModel):
    """PATCH body for human review of a single question."""
    response_text: str | None = None        # Override the generated response
    boolean_value: bool | None = None
    status: Literal["auto_approved", "human_overridden"] = "human_overridden"
    reviewer_notes: str = ""
```

### 11.6 Agent 1: Intake & Parsing Agent

**Role**: Detect questionnaire format, parse questions into normalized `QuestionItem[]`.

**Implementation**:
1. Accept uploaded questionnaire via `POST /api/v3/compliance/upload-questionnaire` (CSV, DOCX, PDF, JSON)
2. **Format detection**:
   - CSV: look for column headers matching known patterns (`Question`, `Control ID`, `Response`, `Domain`)
   - DOCX/PDF: extract text, use regex to detect SIG domain headers (e.g., `"A. Enterprise Risk Management"`, `"B. Security Policy"`) or CAIQ control IDs (`AIS-01`, `BCR-01`)
   - JSON: parse directly if structured
3. **Framework identification**: classify as `sig_core`, `sig_lite`, `caiq`, or `custom` based on control ID patterns and question count
4. **Normalization**: map every question to a `QuestionItem` with:
   - Deterministic `question_id` from the source (e.g., SIG control ID, row number)
   - `response_type` inferred from question phrasing ("Do you..." → boolean, "Describe..." → narrative)
   - `domain` extracted from section headers

**Key design**: This agent is **zero LLM** — pure regex/heuristic parsing. Questionnaire formats are rigid and well-structured; LLM parsing would be overkill and non-deterministic.

### 11.7 Agent 2: Knowledge Retrieval Agent

**Role**: Index Tracelight's security documentation into a persistent ChromaDB collection, then retrieve top-K relevant chunks per question.

**Implementation**:
1. `POST /api/v3/compliance/upload-kb` accepts security docs (SOC 2 reports, pentest summaries, prior completed questionnaires, security policies, architecture docs)
2. Reuses the **same chunking + embedding pipeline from Phase 2's Context Harvester** (`sentence-transformers/all-MiniLM-L6-v2` + ChromaDB)
3. KB collection is persisted across sessions (unlike Phase 2's ephemeral per-session collections) — the KB is Tracelight's "trust center" and should accumulate over time
4. For each `QuestionItem`, embed the `question_text` and retrieve top-5 chunks with similarity scores
5. If the top chunk's similarity score < 0.3, flag the question as "no KB coverage"

**Reuse from Phase 2**: `ContextHarvester._chunk_text()` and the embedding pipeline are identical. Factor into a shared utility or instantiate `ContextHarvester` with a persistent collection name.

### 11.8 Agent 3: Response Drafting Agent

**Role**: LLM-powered, per-question response generation with citation enforcement.

**Implementation (per question)**:
1. Load `compliance_response.j2` Jinja2 template
2. Inject: `question_text`, `response_type`, `retrieved_evidence[]`, `company_name`, `tone`
3. LLM generates the response:
   - **Boolean**: "Yes" or "No" + brief justification with `[source_tag]`
   - **Narrative**: 50-200 word response citing specific policies/controls
   - **Multiple choice**: selected option + justification
4. **Citation enforcement** (reuses Phase 2 pattern): every claim must reference a `[source_tag]`. Unsubstantiated claims → `[REQUIRES REVIEW]`
5. **Confidence scoring**: `(verified_citations / total_claims)` × `max(similarity_scores)`. Accounts for both citation quality and retrieval relevance.
6. **Provider pattern**: Uses `settings.llm_provider` and `settings.llm_model` — **same dual-provider `_call_llm()` pattern from the fixed `narrative_drafter.py`**. Never hardcode model IDs.

### 11.9 Agent 4: Routing & Export Agent

**Role**: Route responses by confidence, allow human review, export final questionnaire.

**Implementation**:
1. **Auto-routing**:
   - `confidence >= auto_approve_above` (default 0.9) → `status: "auto_approved"`
   - `confidence < confidence_threshold` (default 0.8) → `status: "needs_review"`
   - Between threshold and auto-approve → `status: "needs_review"` (conservative)
2. **Human review** via `PATCH /api/v3/compliance/review/{job_id}/{question_id}`:
   - Reviewer can override `response_text`, `boolean_value`, add `reviewer_notes`
   - Status flips to `"human_overridden"`
3. **Export** via `GET /api/v3/compliance/download/{job_id}?fmt=csv|docx|json`:
   - **CSV**: columns = `question_id, domain, question_text, response, confidence, status, citations`
   - **DOCX**: formatted questionnaire response document grouped by domain, with confidence badges
   - **JSON**: full `DraftResponse[]` array
   - **Never `.xlsx`**

### 11.10 `backend/app/prompts/compliance_response.j2`

```jinja2
You are the Head of Information Security at {{ company_name }}, responding to a third-party vendor risk assessment questionnaire. Your responses must be accurate, {{ tone }}, and grounded exclusively in the provided security documentation.

## Question
ID: {{ question_id }}
Domain: {{ domain }}
Question: {{ question_text }}
Response Type: {{ response_type }}
{% if options %}
Options: {{ options | join(", ") }}
{% endif %}

## Evidence from Security Knowledge Base
{% for evidence in retrieved_evidence %}
---
Source: {{ evidence.source_filename }}, Page {{ evidence.page_number }}
Relevance: {{ "%.0f" | format(evidence.similarity_score * 100) }}%
Content: {{ evidence.text }}
---
{% endfor %}

## Instructions
{% if response_type == "boolean" %}
1. Answer "Yes" or "No" based strictly on the evidence above.
2. Follow with a 1-2 sentence justification citing [source_filename:page_X].
3. If the evidence does not clearly support either answer, respond: "Yes" with caveat and add [REQUIRES REVIEW].
{% elif response_type == "narrative" %}
1. Write a 50-200 word response addressing the question directly.
2. Cite specific policies, controls, or evidence using [source_filename:page_X] tags.
3. If evidence is insufficient, write what you can support and append: [REQUIRES REVIEW — INSUFFICIENT KB COVERAGE]
{% elif response_type == "multiple_choice" %}
1. Select the most appropriate option from: {{ options | join(", ") }}
2. Provide a 1-sentence justification with [source_filename:page_X] citation.
{% endif %}
4. Never fabricate controls or policies not present in the evidence.
5. Use precise security terminology appropriate for enterprise procurement.
```

### 11.11 API Routes — Phase 3

| Method | Path | Handler | Description |
|--------|------|---------|-------------|
| `POST` | `/api/v3/compliance/upload-kb` | Multipart file upload | Index security docs into persistent KB collection |
| `POST` | `/api/v3/compliance/upload-questionnaire` | Multipart file upload | Parse + normalize questionnaire, return `questionnaire_session_id` |
| `POST` | `/api/v3/compliance/generate` | `ComplianceGenerateRequest` | Kick off async response generation |
| `GET` | `/api/v3/compliance/status/{job_id}` | Poll for completion | Returns progress + responses as they complete |
| `PATCH` | `/api/v3/compliance/review/{job_id}/{question_id}` | `ReviewUpdate` body | Human override for a single question |
| `GET` | `/api/v3/compliance/download/{job_id}` | Query param `fmt=csv\|docx\|json` | Export completed questionnaire |

### 11.12 Streamlit Frontend Extension

**New tab**: "Compliance Engine" (third tab)

**Flow**:
1. **Upload Knowledge Base**: Multi-file uploader for SOC 2 reports, pentest summaries, security policies, prior questionnaire responses. Shows indexing progress. Persists across sessions.
2. **Upload Questionnaire**: Single file uploader (CSV/DOCX/PDF). Shows detected framework, question count, domain breakdown.
3. **Configure**:
   - Company name (default "Tracelight")
   - Confidence threshold slider (default 0.8)
   - Auto-approve threshold slider (default 0.9)
   - Tone selector
4. **Generate**: Button → progress bar polling `/status/`
5. **Review Dashboard**:
   - Summary cards: total questions, auto-approved (green), needs review (amber), no KB coverage (red)
   - Filterable table: all questions with response preview, confidence bar, status badge
   - Click any "needs review" row → expandable editor:
     - Shows retrieved evidence chunks
     - Editable response text area
     - "Approve" / "Override" buttons → calls PATCH endpoint
   - Domain-level progress bar (e.g., "Access Control: 12/15 approved")
6. **Export**: Buttons for CSV, DOCX, JSON. Only enabled when all questions are approved or overridden.

### 11.13 New Dependencies — Phase 3

No new dependencies beyond Phase 2. Reuses:
- `chromadb` (persistent collection for KB)
- `sentence-transformers` (same embedding model)
- `pymupdf` + `python-docx` (document parsing)
- `docxtpl` (DOCX export)
- LLM via existing `Settings` dual-provider pattern

### 11.14 Docker Updates

None. Phase 3 runs entirely within the existing backend container. The only change is ChromaDB needs a persistent volume for the KB collection:

**`docker-compose.yml` addition**:
```yaml
services:
  backend:
    volumes:
      - synth_output:/tmp/synth_output
      - chroma_data:/tmp/chroma_data    # NEW: persistent KB storage
volumes:
  synth_output:
  chroma_data:                           # NEW
```

And `config.py` needs:
```python
chroma_persist_dir: str = "/tmp/chroma_data"
```

### 11.15 Acceptance Criteria — Phase 3

- [ ] `POST /api/v3/compliance/upload-kb` accepts PDF/DOCX/TXT security docs, indexes into persistent KB
- [ ] `POST /api/v3/compliance/upload-questionnaire` parses CSV/DOCX/PDF, returns normalized question count + detected framework
- [ ] `POST /api/v3/compliance/generate` returns `job_id` immediately (async)
- [ ] Responses are generated for all parsed questions
- [ ] **Every response cites `[source_filename:page_X]` from the KB**
- [ ] Questions with confidence >= 0.9 are auto-approved
- [ ] Questions with confidence < 0.8 are flagged `needs_review`
- [ ] `PATCH /api/v3/compliance/review/{job_id}/{question_id}` allows human override
- [ ] `GET /api/v3/compliance/download/{job_id}?fmt=csv` exports valid CSV with all responses
- [ ] `GET /api/v3/compliance/download/{job_id}?fmt=docx` exports formatted DOCX grouped by domain
- [ ] **No `.xlsx` files are created or read anywhere**
- [ ] Streamlit "Compliance Engine" tab works end-to-end
- [ ] KB persists across Docker restarts (volume-mounted)
- [ ] Intake parser correctly detects SIG Core/Lite, CAIQ, and custom formats
- [ ] Export only enabled when all questions are approved/overridden

### 11.16 Gemini Implementation Notes

> **CRITICAL — Read before implementing. These are recurring mistakes from Phase 1 and Phase 2.**

1. **LLM Model IDs**: The correct models are `gemini-3.1-pro-preview` (Google) and `gpt-5.2-chat-latest` (OpenAI). Do NOT use `gemini-2.5-pro`, `gemini-2.5-flash`, `gpt-4o`, or any other model ID. Always read the model from `settings.llm_model` — never hardcode.

2. **Dual-provider pattern**: Every agent that calls an LLM must support both Google (via `google-genai` SDK) and OpenAI (via `httpx`). Use the `_call_llm()` pattern from `backend/app/agents/narrative_drafter.py` as the reference implementation. Read `settings.llm_provider` to determine which path.

3. **Settings injection**: Always accept `Settings` as a constructor parameter. Never read env vars directly with `os.getenv()`. The `Settings` class from `config.py` handles all env resolution.

4. **DMZ Rule**: No `.xlsx` anywhere. CSV/DOCX/JSON only.

5. **`__pycache__`**: Add `__pycache__/` and `*.pyc` to `.gitignore` before committing.
