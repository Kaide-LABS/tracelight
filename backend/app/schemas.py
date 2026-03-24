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
