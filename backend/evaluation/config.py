import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field

try:
    from backend.evaluation.result_models import FixtureMode
except ImportError:
    from evaluation.result_models import FixtureMode

DEFAULT_RESULTS_DIR = Path(__file__).resolve().parent / "results"
DEFAULT_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")


class EvaluationConfig(BaseModel):
    """
    Configuration options for benchmark evaluation execution.
    """
    dataset_path: Optional[str] = None
    fixtures_path: Optional[str] = None
    results_dir: str = str(DEFAULT_RESULTS_DIR)
    model: str = DEFAULT_MODEL
    api_key: Optional[str] = None
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=300.0)
    max_retries: int = Field(default=2, ge=0, le=5)
    retry_backoff_seconds: float = Field(default=2.0, ge=0.0, le=30.0)
    max_iterations: int = Field(default=10, ge=1, le=20)
    fixture_mode: FixtureMode = FixtureMode.SYNTHETIC_FIXTURE
    concurrency: int = Field(default=1, ge=1, le=5, description="Concurrent tasks (conservative default 1).")
    dry_run: bool = Field(default=False, description="Validate configuration and plan without executing models.")
    selected_systems: Optional[List[str]] = Field(default=None, description="Subset of systems: baseline_llm, tool_using_agent, sky_reader_full.")
    selected_categories: Optional[List[str]] = Field(default=None, description="Subset of category names to evaluate.")
    selected_ids: Optional[List[str]] = Field(default=None, description="Specific test case IDs to run.")
    max_cases: Optional[int] = Field(default=None, ge=1, description="Maximum test cases to process.")
