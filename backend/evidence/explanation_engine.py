from typing import Any, Dict, List, Optional

try:
    from backend.evidence.evidence_models import (
        ClaimValidationResult,
        EvidenceCollection,
        EvidenceItem,
        EvidenceSourceType,
        ExplanationProof,
        HallucinationReport,
        ValidationStatus,
        WeatherVariable,
    )
except ImportError:
    from evidence.evidence_models import (
        ClaimValidationResult,
        EvidenceCollection,
        EvidenceItem,
        EvidenceSourceType,
        ExplanationProof,
        HallucinationReport,
        ValidationStatus,
        WeatherVariable,
    )


class ExplanationEngine:
    """
    Weather Reasoning & Explainability Engine.
    Synthesizes structured evidence records, analysis provenance, and claim validation audits
    into formal ExplanationProofs and human-readable reasoning chains.
    """

    def __init__(self):
        pass

    def generate_proof(
        self,
        query: str,
        response_text: str,
        evidence: EvidenceCollection,
        report: Optional[HallucinationReport] = None,
        validation_results: Optional[List[ClaimValidationResult]] = None,
    ) -> ExplanationProof:
        """
        Constructs a structured ExplanationProof tracing conclusions to underlying data,
        provenance, and validation results.
        """
        results = validation_results or (report.validation_results if report else [])

        # 1. Gather all supporting evidence items cited in validated claims
        cited_evidence_ids = set()
        for r in results:
            if r.status in (ValidationStatus.SUPPORTED, ValidationStatus.PARTIALLY_SUPPORTED):
                cited_evidence_ids.update(r.supporting_evidence_ids)

        # If no specific citations, include top observed and derived items
        supporting_items: List[EvidenceItem] = []
        if cited_evidence_ids:
            for it in evidence.items:
                if it.id in cited_evidence_ids:
                    supporting_items.append(it)
        else:
            # Fallback to key current and derived items
            supporting_items = [
                it for it in evidence.items
                if it.source_type in (EvidenceSourceType.OBSERVED, EvidenceSourceType.DERIVED)
            ][:8]

        # 2. Extract measurements used (raw numbers and units)
        measurements: List[Dict[str, Any]] = []
        data_sources = set()
        time_periods = set()
        analysis_performed = set()

        for it in supporting_items:
            data_sources.add(it.source_name)
            time_periods.add(it.time_period)
            if it.analysis_method:
                analysis_performed.add(it.analysis_method)

            measurements.append({
                "id": it.id,
                "variable": it.variable.value,
                "value": it.value,
                "unit": it.unit,
                "time_period": it.time_period,
                "source_type": it.source_type.value,
            })

        # Add any derived analysis methods from entire collection if not already captured
        for it in evidence.items:
            if it.source_type == EvidenceSourceType.DERIVED and it.analysis_method:
                analysis_performed.add(it.analysis_method)
            data_sources.add(it.source_name)

        # 3. Determine validation status summary
        total_claims = len(results)
        supported_claims = sum(1 for r in results if r.status == ValidationStatus.SUPPORTED)
        contradicted_claims = sum(1 for r in results if r.status == ValidationStatus.CONTRADICTED)

        if total_claims == 0:
            val_status = "Informational (No testable factual claims)"
            risk = "Low"
        elif contradicted_claims > 0:
            val_status = f"Contradictions Detected ({contradicted_claims}/{total_claims} claims failed)"
            risk = "High"
        elif supported_claims == total_claims:
            val_status = f"100% Grounded ({supported_claims}/{total_claims} claims verified)"
            risk = "Low"
        else:
            val_status = f"Partially Grounded ({supported_claims}/{total_claims} claims strictly verified)"
            risk = "Moderate"

        # 4. Formulate the primary conclusion snippet
        conclusion = response_text.strip().split("\n")[0]
        if len(conclusion) > 160:
            conclusion = conclusion[:157] + "..."

        # 5. Formulate standard meteorological limitations
        limitations = (
            "Numerical weather prediction accuracy naturally degrades beyond 24-48 hours. "
            "Local microclimates, high-altitude terrain shifts, or sudden convective cells may cause localized variances."
        )

        supporting_evidence_data = [
            {
                "id": it.id,
                "variable": it.variable.value,
                "value": it.value,
                "unit": it.unit,
                "source": it.source_name,
                "source_type": it.source_type.value,
                "time_period": it.time_period,
            }
            for it in supporting_items
        ]

        return ExplanationProof(
            query=query,
            conclusion=conclusion,
            supporting_evidence=supporting_evidence_data,
            measurements_used=measurements,
            analysis_performed=sorted(list(analysis_performed)),
            data_sources=sorted(list(data_sources)),
            time_periods=sorted(list(time_periods)),
            claim_validation_status=val_status,
            hallucination_risk=risk,
            limitations_and_uncertainty=limitations,
        )

    def format_markdown_proof(self, proof: ExplanationProof) -> str:
        """Renders an ExplanationProof into an audited Markdown block."""
        lines = [
            "### 🔬 Evidence & Meteorological Reasoning Proof",
            f"**Conclusion:** {proof.conclusion}",
            f"- **Validation Status:** {proof.claim_validation_status}",
            f"- **Hallucination Risk:** {proof.hallucination_risk}",
            "",
            "#### Key Supporting Measurements",
        ]

        if proof.measurements_used:
            lines.append("| Variable | Value | Period | Source |")
            lines.append("|---|---|---|---|")
            for m in proof.measurements_used[:6]:
                unit = m.get("unit") or ""
                lines.append(f"| {m.get('variable')} | {m.get('value')} {unit} | {m.get('time_period')} | {m.get('source_type')} |")
        else:
            lines.append("*No numerical measurements cited.*")

        if proof.analysis_performed:
            lines.append("")
            lines.append("#### Analysis Methods Applied")
            for a in proof.analysis_performed[:5]:
                lines.append(f"- {a}")

        lines.append("")
        lines.append(f"> **Limitations & Uncertainty:** {proof.limitations_and_uncertainty}")

        return "\n".join(lines)
