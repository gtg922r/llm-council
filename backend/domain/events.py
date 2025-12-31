from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from .models import Stage1Result, Stage2Result, Stage3Result

class DomainEvent(BaseModel):
    type: str

class Stage1Start(DomainEvent):
    type: str = "stage1_start"
    total: int

class Stage1Progress(DomainEvent):
    type: str = "stage1_progress"
    completed: int
    total: int

class Stage1Complete(DomainEvent):
    type: str = "stage1_complete"
    data: List[Stage1Result]

class Stage2Start(DomainEvent):
    type: str = "stage2_start"
    total: int

class Stage2Progress(DomainEvent):
    type: str = "stage2_progress"
    completed: int
    total: int

class Stage2Complete(DomainEvent):
    type: str = "stage2_complete"
    data: List[Stage2Result]
    metadata: Dict[str, Any]

class Stage3Start(DomainEvent):
    type: str = "stage3_start"

class Stage3Complete(DomainEvent):
    type: str = "stage3_complete"
    data: Stage3Result

class TitleComplete(DomainEvent):
    type: str = "title_complete"
    data: Dict[str, str]

class CouncilComplete(DomainEvent):
    type: str = "complete"

class CouncilError(DomainEvent):
    type: str = "error"
    message: str
