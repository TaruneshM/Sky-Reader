# Sky Reader Evaluation Analysis Package

def __getattr__(name: str):
    if name == "ComparativeAnalyzer":
        from backend.evaluation.analysis.comparator import ComparativeAnalyzer
        return ComparativeAnalyzer
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["ComparativeAnalyzer"]
