from .job_manager import JobType

DEFAULT_TEMPLATES = {
    "complete_generation": {
        "name": "Complete Data Generation Pipeline",
        "steps": [
            {"name": "seed_generation", "job_type": JobType.SEED_GENERATION, "depends_on": []},
            {"name": "synthetic_generation", "job_type": JobType.SYNTHETIC_GENERATION, "depends_on": ["seed_generation"]},
            {"name": "evaluation", "job_type": JobType.DATA_EVALUATION, "depends_on": ["synthetic_generation"]}
        ]
    },
    "quick_generation": {
        "name": "Quick Synthetic Generation",
        "steps": [
            {"name": "seed_generation", "job_type": JobType.SEED_GENERATION, "depends_on": []},
            {"name": "synthetic_generation", "job_type": JobType.SYNTHETIC_GENERATION, "depends_on": ["seed_generation"]}
        ]
    },
    "evaluation_only": {
        "name": "Data Quality Evaluation",
        "steps": [{"name": "evaluation", "job_type": JobType.DATA_EVALUATION, "depends_on": []}]
    }
}
