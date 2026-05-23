from typing import TypedDict, List, Dict, Any, Optional

class ScraperState(TypedDict):
    job_id: str
    url: str
    objective: str
    steps: List[Dict[str, Any]]
    current_step_index: int
    history: List[Dict[str, Any]]
    scraped_data: Any
    html_snapshot: str
    error_message: Optional[str]
    retry_count: int
    max_retries: int
    status: str # 'running', 'correcting', 'done', 'failed'
    accumulated_texts: List[Dict[str, str]] # [{'url': str, 'text': str}]
    failed_steps: List[Dict[str, Any]] # List of steps that failed execution
