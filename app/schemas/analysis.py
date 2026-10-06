from enum import StrEnum

from pydantic import BaseModel, Field


class IssueCategory(StrEnum):
    ACCESS = "access"
    NETWORK = "network"
    HARDWARE = "hardware"
    SOFTWARE = "software"
    EMAIL = "email"
    SECURITY = "security"
    OTHER = "other"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ITIssueAnalysis(BaseModel):
    category: IssueCategory
    summary: str = Field(min_length=3, max_length=500)
    severity: Severity
    probable_causes: list[str] = Field(min_length=1, max_length=10)
    troubleshooting_steps: list[str] = Field(min_length=1, max_length=15)
    recommended_action: str = Field(min_length=3, max_length=1000)
    escalation_required: bool


class AnalyzeRequest(BaseModel):
    issue: str = Field(min_length=5, max_length=5000)

