from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FrozenModel(BaseModel):
    # Attribute docstrings become the field descriptions of the JSON Schema.
    model_config = ConfigDict(extra="forbid", frozen=True, use_attribute_docstrings=True)
