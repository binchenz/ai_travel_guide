"""Pydantic v2 models that mirror data/ontology/schemas/*.schema.json."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class BilingualString(BaseModel):
    model_config = ConfigDict(extra="forbid")
    en: str = Field(min_length=1)
    zh: str = Field(min_length=1)


class BilingualList(BaseModel):
    model_config = ConfigDict(extra="forbid")
    en: List[str]
    zh: List[str]


class Period(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start: int
    end: int
    label: BilingualString


class Hall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^hall/[a-z0-9-]+$")
    name: BilingualString
    floor: int = Field(ge=0)
    theme: Optional[BilingualString] = None


class Dynasty(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^dynasty/[a-z0-9-]+$")
    name: BilingualString
    period: Period
    predecessor: Optional[str] = Field(default=None, pattern=r"^dynasty/[a-z0-9-]+$")
    successor:   Optional[str] = Field(default=None, pattern=r"^dynasty/[a-z0-9-]+$")
    shortDesc: Optional[BilingualString] = None


class Person(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^person/[a-z0-9-]+$")
    name: BilingualString
    role: BilingualString
    dynastyId: str = Field(pattern=r"^dynasty/[a-z0-9-]+$")
    shortDesc: Optional[BilingualString] = None


class Dimension(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: float
    unit: str


class Inscriptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    characterCount: int = Field(ge=0)
    significance: Optional[BilingualString] = None


class CulturalContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ritualUse:        Optional[BilingualString] = None
    socialFunction:   Optional[BilingualString] = None
    relatedConcepts:  List[str] = Field(default_factory=list)


class NarrativePoints(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entry:  List[str] = Field(min_length=2)
    deeper: List[str] = Field(min_length=2)
    expert: List[str] = Field(min_length=2)


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^artifact/[a-z0-9-]+$")
    type: str
    name: BilingualString
    imageUrl: Optional[str] = None
    hallId: str = Field(pattern=r"^hall/[a-z0-9-]+$")
    dynastyId: str = Field(pattern=r"^dynasty/[a-z0-9-]+$")
    personIds: List[str] = Field(default_factory=list)
    period: Optional[Period] = None
    dimensions: Dict[str, Dimension] = Field(default_factory=dict)
    material:   List[str] = Field(default_factory=list)
    techniques: List[str] = Field(default_factory=list)
    inscriptions: Optional[Inscriptions] = None
    culturalContext: Optional[CulturalContext] = None
    narrativePoints: Optional[NarrativePoints] = None
    relationships: Dict[str, List[str]] = Field(default_factory=dict)
    quickQuestions: Optional[BilingualList] = None
