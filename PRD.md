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
- Workflow II (Post-Excel Narrative Deliverable Engine)
- Workflow III (InfoSec/Vendor Risk Automation Pipeline)
- Advanced generative models (TimeGAN, VAE)
- Authentication / multi-tenancy
- Persistent job storage (currently in-memory)
