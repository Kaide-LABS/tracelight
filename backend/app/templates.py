from app.schemas import StatisticalProfile, VariableSpec

PRESETS = [
    {
        "name": "PE LBO",
        "description": "Private Equity LBO scenario with revenue, margins, and leverage.",
        "profile": StatisticalProfile(
            asset_class="private_equity_lbo",
            num_entities=50,
            time_horizon_years=5,
            frequency="quarterly",
            variables={
                "revenue": VariableSpec(distribution="lognormal", mu=18.0, sigma=0.4),
                "ebitda_margin": VariableSpec(distribution="beta", alpha=2.0, beta=5.0),
                "leverage_ratio": VariableSpec(distribution="normal", mean=6.5, std=1.2),
                "interest_rate": VariableSpec(distribution="lognormal", mu=-2.8, sigma=0.15),
                "capex_pct": VariableSpec(distribution="uniform", low=0.03, high=0.08)
            },
            correlations=[
                ("revenue", "ebitda_margin", 0.55),
                ("leverage_ratio", "interest_rate", 0.40),
                ("ebitda_margin", "leverage_ratio", -0.35)
            ],
            temporal={"autocorrelation": 0.7}
        ).model_dump()
    },
    {
        "name": "VC Portfolio",
        "description": "Venture Capital portfolio with fast burn rates and runway.",
        "profile": StatisticalProfile(
            asset_class="venture_capital",
            num_entities=100,
            time_horizon_years=3,
            frequency="monthly",
            variables={
                "burn_rate": VariableSpec(distribution="lognormal", mu=12.0, sigma=0.5),
                "monthly_revenue": VariableSpec(distribution="lognormal", mu=10.0, sigma=1.0),
                "runway_months": VariableSpec(distribution="normal", mean=18.0, std=6.0),
                "headcount": VariableSpec(distribution="normal", mean=40.0, std=15.0),
                "ltv_cac_ratio": VariableSpec(distribution="beta", alpha=3.0, beta=2.0)
            },
            correlations=[
                ("burn_rate", "headcount", 0.8),
                ("runway_months", "burn_rate", -0.6)
            ],
            temporal={"autocorrelation": 0.5}
        ).model_dump()
    },
    {
        "name": "Real Estate DCF",
        "description": "Real Estate discounted cash flow with NOI and cap rates.",
        "profile": StatisticalProfile(
            asset_class="real_estate_dcf",
            num_entities=20,
            time_horizon_years=10,
            frequency="annual",
            variables={
                "noi": VariableSpec(distribution="lognormal", mu=15.0, sigma=0.3),
                "cap_rate": VariableSpec(distribution="beta", alpha=5.0, beta=95.0),
                "vacancy_rate": VariableSpec(distribution="beta", alpha=2.0, beta=20.0),
                "rent_growth": VariableSpec(distribution="normal", mean=0.03, std=0.01),
                "interest_rate": VariableSpec(distribution="lognormal", mu=-3.0, sigma=0.2)
            },
            correlations=[
                ("noi", "cap_rate", -0.3),
                ("vacancy_rate", "rent_growth", -0.5)
            ],
            temporal={"autocorrelation": 0.8}
        ).model_dump()
    }
]
