"""Synthetic data configuration for the Momentum Life Claims demo.

All values are demo defaults from the requirements package (04_SYNTHETIC_DATA.md).
Deterministic: the same SEED reproduces the same dataset, including the three
seeded demo scenarios (DS1-DS3) which must exist with known claim numbers.
"""

SEED = 20260706

# Volume of synthetic estate.
N_POLICIES = 5_000
CLAIMS_PER_100_POLICIES = 12            # ~600 claims
NTU_RATE = 0.18                         # share of pre-lodge claims that stall (Not Taken Up)

# Distributions.
CLAIM_TYPE_MIX = {
    "death": 0.45,
    "disability": 0.25,
    "critical_illness": 0.20,
    "income": 0.10,
}
STATE_MIX = {
    "initiated": 0.12,
    "lodged": 0.10,
    "in_assessment": 0.30,
    "decided": 0.33,
    "paid": 0.15,
}
DECISION_MIX = {"pay": 0.72, "decline": 0.13, "refer": 0.15}

# South African context.
REGION = "eu-west-1"                     # residency-compliant deploy region (af-south-1 is not a Databricks region)
PROVINCES = [
    "Gauteng", "Western Cape", "KwaZulu-Natal",
    "Eastern Cape", "Free State", "Limpopo",
]
PROVINCE_WEIGHTS = [0.30, 0.20, 0.18, 0.12, 0.10, 0.10]

BENEFIT_TYPES = ["death", "disability", "critical_illness", "income_protection"]
OCCUPATIONS = [
    "Clerk", "Teacher", "Accountant", "Nurse", "Boilermaker", "Electrician",
    "Miner", "Driver", "Manager", "Engineer", "Farmer", "Security Officer",
    "Sales Representative", "Administrator", "Technician",
]
BROKERS = [
    "Momentum Consult", "PSG Wealth", "Alexforbes", "Liberty Advisers",
    "Independent Broker Network", "NMG Benefits", "Direct",
]
DOC_TYPES = [
    "death_certificate", "op_form", "specialist_medical_report",
    "ID", "bank_letter", "claim_form",
]

# Requirement templates per claim type: (code, description).
REQUIREMENTS_BY_TYPE = {
    "death": [
        ("REQ-DEATH-CERT", "Death certificate"),
        ("REQ-OP-FORM", "Ombudsman / claim (OP) form"),
        ("REQ-MED-CONSENT", "Medical-aid consent"),
        ("REQ-ID", "Certified ID of deceased"),
        ("REQ-BANK", "Bank verification letter"),
    ],
    "disability": [
        ("REQ-SPECIALIST", "Specialist medical report"),
        ("REQ-OCC-CONFIRM", "Occupation confirmation"),
        ("REQ-OP-FORM", "Claim (OP) form"),
        ("REQ-ID", "Certified ID"),
        ("REQ-BANK", "Bank verification letter"),
    ],
    "critical_illness": [
        ("REQ-SPECIALIST", "Specialist medical report"),
        ("REQ-DIAGNOSIS", "Confirmed diagnosis report"),
        ("REQ-OP-FORM", "Claim (OP) form"),
        ("REQ-ID", "Certified ID"),
    ],
    "income": [
        ("REQ-INCOME-PROOF", "Proof of income"),
        ("REQ-SPECIALIST", "Medical / functional report"),
        ("REQ-OP-FORM", "Claim (OP) form"),
        ("REQ-ID", "Certified ID"),
    ],
}

# Third-party verification sources.
TP_SOURCES = ["VPD", "other_insurer", "bank", "identity"]

# The three seeded demo scenarios — must exist with these exact claim numbers.
SEEDED_SCENARIOS = ["CLM-DEATH-CLEAN", "CLM-DISAB-DISCREP", "CLM-SUSPECT-FRAUD"]

# Physical layout. The spec asks for catalog `momentum_claims_demo` with
# schemas bronze/silver/gold/ai/ops. The demo workspace's metastore has Default
# Storage with no storage root, so CREATE CATALOG is unavailable; we co-locate
# as schemas `momentum_claims_<layer>` inside the existing managed catalog
# (same pattern as the Investec demo on this workspace). Override CATALOG for a
# workspace where a dedicated `momentum_claims_demo` catalog can be created.
CATALOG = "elexon_app_for_settlement_acc_catalog"
SCHEMAS = {
    "bronze": "momentum_claims_bronze",
    "silver": "momentum_claims_silver",
    "gold": "momentum_claims_gold",
    "ai": "momentum_claims_ai",
    "ops": "momentum_claims_ops",
}


def fq(layer: str, table: str, catalog: str | None = None) -> str:
    """Fully-qualified table name for a medallion layer."""
    cat = catalog or CATALOG
    return f"{cat}.{SCHEMAS[layer]}.{table}"
