"""요청·응답 스키마.

경계에서 막는다. 잘못된 정책 값이 안으로 들어오면 조용히 다른 기준으로 판정하게 된다.
"""
from typing import List, Optional

from pydantic import BaseModel, Field


class Answer(BaseModel):
    questionNo: int
    value: Optional[float] = None      # None = "해당사항 없음" → 결측 센티널로 바뀐다


class Policy(BaseModel):
    """판정 정책은 설정(cb_config_v1)이 소유한다. **기본값을 두지 않는다**(FR-009c)."""
    tauConf: float = Field(gt=0.0, lt=1.0)
    tauDens: float = Field(lt=0.0)
    decisionWeights: List[float] = Field(min_length=5, max_length=5)
    contributionMinThreshold: float = Field(ge=0.0)


class PredictRequest(BaseModel):
    answers: List[Answer]
    policy: Policy


class Contribution(BaseModel):
    feature: str
    value: float
    contrib: float
    isMinor: bool


class PredictResponse(BaseModel):
    modelVersion: str
    questionSetVersion: str
    proba: List[float]
    decided: bool
    internalLabel: Optional[int]
    maxProba: float
    rarity: float
    undecidableReason: Optional[str]
    contributions: Optional[List[Contribution]]
