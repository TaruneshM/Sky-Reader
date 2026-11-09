import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure backend directory is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.evidence.evidence_models import (
    ClaimValidationResult,
    EvidenceCollection,
    EvidenceItem,
    EvidenceSourceType,
    ValidationStatus,
    WeatherVariable,
)
from backend.evidence.claim_extractor import ClaimExtractor
from backend.evidence.claim_validator import ClaimValidator
from backend.evidence.hallucination_controller import HallucinationController
from backend.evaluation.metrics import (
    calculate_claim_grounding,
    calculate_contradiction_rate,
    calculate_hallucination_rate,
)
from backend.evaluation.benchmark import BENCHMARK_SCENARIOS


def run_ablation_study() -> Dict[str, Any]:
    """
    Evaluates 4 configurations to measure the specific contribution of each component:
    1. Full System
    2. Ablation A: No Hallucination Feedback Loop (leaves hallucinated text as-is)
    3. Ablation B: Zero Tolerance (strict numerical equality only, no domain tolerance)
    4. Ablation C: No Derived Evidence (raw observed measurements only)
    """
    extractor = ClaimExtractor()
    default_validator = ClaimValidator()

    # Zero tolerance validator
    zero_tol_validator = ClaimValidator()
    zero_tol_validator.TOLERANCES = {v: 0.0 for v in zero_tol_validator.TOLERANCES}

    results = {
        "1. Full Sky Reader (Phase 4)": {"grounding": [], "hallucination": [], "trustworthy": []},
        "2. Ablation: No Feedback Loop": {"grounding": [], "hallucination": [], "trustworthy": []},
        "3. Ablation: Zero Tolerance (No margins)": {"grounding": [], "hallucination": [], "trustworthy": []},
        "4. Ablation: No Derived Evidence": {"grounding": [], "hallucination": [], "trustworthy": []},
    }

    controller = HallucinationController(claim_extractor=extractor, claim_validator=default_validator)

    for sc in BENCHMARK_SCENARIOS:
        full_evidence = EvidenceCollection(items=sc["evidence_items"])

        # 1. Full System on Phase 4 text
        c_full = extractor.extract_claims(sc["phase4_response"])
        v_full = default_validator.validate_all(c_full, full_evidence)
        r_full = controller.evaluate_claims(v_full)
        results["1. Full Sky Reader (Phase 4)"]["grounding"].append(calculate_claim_grounding(v_full))
        results["1. Full Sky Reader (Phase 4)"]["hallucination"].append(calculate_hallucination_rate(v_full))
        results["1. Full Sky Reader (Phase 4)"]["trustworthy"].append(1.0 if r_full.is_trustworthy else 0.0)

        # 2. No Feedback Loop: When tested on hallucinated baseline input, no correction occurs
        c_nofb = extractor.extract_claims(sc["baseline_response"])
        v_nofb = default_validator.validate_all(c_nofb, full_evidence)
        r_nofb = controller.evaluate_claims(v_nofb)
        results["2. Ablation: No Feedback Loop"]["grounding"].append(calculate_claim_grounding(v_nofb))
        results["2. Ablation: No Feedback Loop"]["hallucination"].append(calculate_hallucination_rate(v_nofb))
        results["2. Ablation: No Feedback Loop"]["trustworthy"].append(1.0 if r_nofb.is_trustworthy else 0.0)

        # 3. Zero Tolerance on Phase 3 text (which uses rounded numbers like 23°C for 22.5°C)
        c_zt = extractor.extract_claims(sc["phase3_response"])
        v_zt = zero_tol_validator.validate_all(c_zt, full_evidence)
        r_zt = controller.evaluate_claims(v_zt)
        results["3. Ablation: Zero Tolerance (No margins)"]["grounding"].append(calculate_claim_grounding(v_zt))
        results["3. Ablation: Zero Tolerance (No margins)"]["hallucination"].append(calculate_hallucination_rate(v_zt))
        results["3. Ablation: Zero Tolerance (No margins)"]["trustworthy"].append(1.0 if r_zt.is_trustworthy else 0.0)

        # 4. No Derived Evidence (filter out DERIVED items)
        raw_only_items = [it for it in sc["evidence_items"] if it.source_type != EvidenceSourceType.DERIVED]
        raw_evidence = EvidenceCollection(items=raw_only_items)
        c_noderiv = extractor.extract_claims(sc["phase4_response"])
        v_noderiv = default_validator.validate_all(c_noderiv, raw_evidence)
        r_noderiv = controller.evaluate_claims(v_noderiv)
        results["4. Ablation: No Derived Evidence"]["grounding"].append(calculate_claim_grounding(v_noderiv))
        results["4. Ablation: No Derived Evidence"]["hallucination"].append(calculate_hallucination_rate(v_noderiv))
        results["4. Ablation: No Derived Evidence"]["trustworthy"].append(1.0 if r_noderiv.is_trustworthy else 0.0)

    summary = {}
    for name, data in results.items():
        summary[name] = {
            "avg_grounding": round(sum(data["grounding"]) / len(data["grounding"]), 4),
            "avg_hallucination": round(sum(data["hallucination"]) / len(data["hallucination"]), 4),
            "trustworthy_pct": round((sum(data["trustworthy"]) / len(data["trustworthy"])) * 100, 1),
        }
    return summary


def print_ablation_table():
    summary = run_ablation_study()
    print("==========================================================================================")
    print("                        SKY READER PHASE 4 ABLATION STUDY RESULTS                         ")
    print("==========================================================================================")
    print(f"{'Ablation Configuration':<44} | {'Grounding':<10} | {'Halluc. Rate':<12} | {'Trustworthy %':<12}")
    print("-" * 88)
    for name, m in summary.items():
        print(
            f"{name:<44} | "
            f"{m['avg_grounding']*100:>8.1f}% | "
            f"{m['avg_hallucination']*100:>10.1f}% | "
            f"{m['trustworthy_pct']:>10.1f}%"
        )
    print("==========================================================================================")


if __name__ == "__main__":
    print_ablation_table()
