"""Data Consolidatorilta tulevan JSONin malli. Muokkaa tätä, kun sovitte lopullisen muodon."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InputPayload(BaseModel):
    """Esimerkki:

    {
      "source_id": "site-42",
      "timestamp": "2026-10-17T08:00:00Z",
      "area": "Helsinki",
      "metrics": {"water_pressure_bar": 3.1, "flow_l_min": 0.0, "temperature_c": 19.5}
    }
    """

    model_config = ConfigDict(extra="ignore")

    source_id: str = Field(min_length=1, max_length=200)
    timestamp: datetime | None = None
    area: str | None = Field(default=None, max_length=200)
    metrics: dict[str, float]

    @field_validator("metrics")
    @classmethod
    def _check_metrics(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("metrics ei saa olla tyhjä")
        for name, number in value.items():
            if not name or len(name) > 100:
                raise ValueError(f"virheellinen mittarin nimi: {name!r}")
            if not math.isfinite(number):
                raise ValueError(f"mittarin {name} arvo ei ole äärellinen luku")
        return value

    def epoch(self, now: int) -> int:
        """Aikaleima unix-sekunteina. Puuttuva aikaleima = vastaanottohetki, ilman aikavyöhykettä = UTC."""
        if self.timestamp is None:
            return now
        ts = self.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return int(ts.timestamp())
