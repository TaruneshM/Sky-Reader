import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from backend.evaluation.result_models import EvaluationResult, RunSummary
except ImportError:
    from evaluation.result_models import EvaluationResult, RunSummary

logger = logging.getLogger(__name__)


class ResultStore:
    """
    Manages structured storage and retrieval of benchmark execution results.
    Persists incremental records into JSONL files under run-specific subdirectories.
    """

    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_run_dir(self, run_id: str) -> Path:
        run_dir = self.base_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def save_result(self, result: EvaluationResult) -> Path:
        """
        Appends an individual EvaluationResult record to results.jsonl immediately.
        Guarantees that partial or interrupted runs are preserved on disk.
        """
        run_dir = self._get_run_dir(result.run_id)
        results_file = run_dir / "results.jsonl"

        # Sanitize any accidental sensitive fields in metadata before serializing
        data = result.model_dump()
        if "execution_metadata" in data and isinstance(data["execution_metadata"], dict):
            for k in list(data["execution_metadata"].keys()):
                if "key" in k.lower() or "secret" in k.lower() or "token" in k.lower():
                    del data["execution_metadata"][k]

        with open(results_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")

        return results_file

    def save_summary(self, summary: RunSummary) -> Path:
        """
        Saves the top-level run summary metadata to summary.json.
        """
        run_dir = self._get_run_dir(summary.run_id)
        summary_file = run_dir / "summary.json"

        clean_config = dict(summary.config)
        for k in list(clean_config.keys()):
            if "key" in k.lower() or "secret" in k.lower() or "token" in k.lower():
                clean_config[k] = "[REDACTED]"

        data = summary.model_dump()
        data["config"] = clean_config

        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return summary_file

    def load_results(self, run_id: str) -> List[EvaluationResult]:
        """Loads all execution records from a specific run."""
        results_file = self.base_dir / run_id / "results.jsonl"
        if not results_file.exists():
            return []

        results = []
        with open(results_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    results.append(EvaluationResult.model_validate(json.loads(line)))
        return results

    def load_summary(self, run_id: str) -> Optional[RunSummary]:
        """Loads summary metadata for a run if present."""
        summary_file = self.base_dir / run_id / "summary.json"
        if not summary_file.exists():
            return None
        with open(summary_file, "r", encoding="utf-8") as f:
            return RunSummary.model_validate(json.load(f))

    def list_runs(self) -> List[Dict[str, Any]]:
        """Lists all existing evaluation run directories and their status."""
        runs = []
        if not self.base_dir.exists():
            return runs

        for d in sorted(self.base_dir.iterdir(), reverse=True):
            if d.is_dir():
                summary = self.load_summary(d.name)
                results_file = d / "results.jsonl"
                record_count = 0
                if results_file.exists():
                    with open(results_file, "r", encoding="utf-8") as f:
                        record_count = sum(1 for line in f if line.strip())

                runs.append({
                    "run_id": d.name,
                    "record_count": record_count,
                    "summary": summary.model_dump() if summary else None,
                    "path": str(d),
                })
        return runs
