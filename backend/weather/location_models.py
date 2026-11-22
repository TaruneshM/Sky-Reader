"""Location contracts. Schema validation checks shape, not provenance authenticity."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class ResolutionProvenance(FrozenModel):
    provider: Literal["open_meteo"] = "open_meteo"
    method: Literal["standalone", "geographic_hint", "provider_spelling_match"]
    reference_name: Name | None = None

    @model_validator(mode="after")
    def check_reference(self):
        if (self.method == "geographic_hint") != (self.reference_name is not None):
            raise ValueError("Only a geographically resolved location requires a reference.")
        return self


class ConfirmedLocation(FrozenModel):
    status: Literal["RESOLVED"] = "RESOLVED"
    name: Name
    country: str | None = None
    country_code: str | None = None
    region: str | None = None
    latitude: float = Field(ge=-90, le=90, strict=True)
    longitude: float = Field(ge=-180, le=180, strict=True)
    # The provider can omit timezone or ID even for a resolved place.
    timezone: str | None = None
    provider_id: int | None = None
    qualifiers: tuple[Name, ...] = ()
    provenance: ResolutionProvenance

    def as_legacy_place(self) -> dict:
        return {
            "name": self.name, "latitude": self.latitude, "longitude": self.longitude,
            "country": self.country, "country_code": self.country_code,
            "admin1": self.region, "timezone": self.timezone,
        }


class CandidateSummary(FrozenModel):
    provider_id: int | None = None
    name: Name
    country: str | None = None
    region: str | None = None
    district: str | None = None


class Resolved(FrozenModel):
    status: Literal["RESOLVED"] = "RESOLVED"
    query: Name
    location: ConfirmedLocation


class Ambiguous(FrozenModel):
    status: Literal["AMBIGUOUS"] = "AMBIGUOUS"
    query: Name
    candidates: tuple[CandidateSummary, ...] = Field(min_length=2)
    missing_qualifiers: tuple[Name, ...] = Field(default=("region", "country"), min_length=1)


class NotFound(FrozenModel):
    status: Literal["NOT_FOUND"] = "NOT_FOUND"
    query: str
    reason: Literal["invalid_query", "no_candidates", "no_matching_candidates"]


class ProviderUnavailable(FrozenModel):
    status: Literal["PROVIDER_UNAVAILABLE"] = "PROVIDER_UNAVAILABLE"
    query: str
    reason: Literal["timeout", "network_error", "provider_http_error", "invalid_response"]
    retriable: bool


LocationResolution = Annotated[
    Resolved | Ambiguous | NotFound | ProviderUnavailable, Field(discriminator="status")
]
