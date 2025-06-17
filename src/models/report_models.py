from pydantic import BaseModel, HttpUrl
from typing import List, Dict, Any, Optional
from enum import Enum

class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class IssueType(str, Enum):
    ARIA = "aria"
    SEMANTIC = "semantic"
    IMAGE = "image"
    MEDIA = "media"
    VISUAL = "visual"
    KEYBOARD = "keyboard"

class AccessibilityIssue(BaseModel):
    type: IssueType
    severity: SeverityLevel
    message: str
    description: str
    element: Optional[str] = None
    line_number: Optional[int] = None
    recommendation: str
    wcag_reference: Optional[str] = None

class CategoryScore(BaseModel):
    category: str
    score: float
    max_score: float = 100.0
    issues_count: int
    passed_checks: int
    total_checks: int

class CheckOptions(BaseModel):
    enable_aria_check: bool = True
    enable_semantic_check: bool = True
    enable_image_check: bool = True
    enable_media_check: bool = True
    enable_visual_check: bool = True
    include_screenshots: bool = False
    wait_time: int = 5

class CheckRequest(BaseModel):
    url: HttpUrl
    options: Optional[CheckOptions] = CheckOptions()

class CheckResult(BaseModel):
    url: str
    total_score: float
    category_scores: Dict[str, CategoryScore]
    issues: List[AccessibilityIssue]
    summary: Dict[str, Any]
    checked_at: str
    check_duration: float