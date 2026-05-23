import os
import uuid
import asyncio
from typing import Dict, Any
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load dotenv BEFORE importing LangGraph/OpenAI components
env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

from backend.agent.graph import build_graph
from backend.agent.state import ScraperState
from backend.agent.tools import BrowserManager
from backend.agent.nodes import active_browsers

app = FastAPI(title="Self-Correcting OSINT Scraper")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

job_states: Dict[str, dict] = {}
graph = build_graph()

class ScrapeRequest(BaseModel):
    url: str
    objective: str

async def run_scraper_job(job_id: str, request: ScrapeRequest):
    # Initialize Browser
    browser = BrowserManager()
    await browser.initialize()
    active_browsers[job_id] = browser

    initial_state = ScraperState(
        job_id=job_id,
        url=request.url,
        objective=request.objective,
        steps=[],
        current_step_index=0,
        history=[],
        scraped_data=None,
        html_snapshot="",
        error_message=None,
        retry_count=0,
        max_retries=3,
        status="running",
        accumulated_texts=[],
        failed_steps=[]
    )
    
    job_states[job_id] = initial_state
    
    try:
        # We use astream to capture intermediate states
        async for output in graph.astream(initial_state):
            # output is a dict like {'plan_node': {...state updates...}}
            for node_name, state_update in output.items():
                print(f"[{job_id}] Update from {node_name}: {state_update.get('status', 'running')}")
                job_states[job_id].update(state_update)
                
    except Exception as e:
        print(f"[{job_id}] Graph execution error: {e}")
        job_states[job_id]["status"] = "failed"
        job_states[job_id]["error_message"] = str(e)
    finally:
        await browser.cleanup()
        if job_id in active_browsers:
            del active_browsers[job_id]

@app.post("/api/scrape")
async def start_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not set.")
        
    job_id = str(uuid.uuid4())
    background_tasks.add_task(run_scraper_job, job_id, request)
    return {"job_id": job_id, "status": "started"}

@app.get("/api/scrape/{job_id}")
async def get_job_status(job_id: str):
    if job_id not in job_states:
        raise HTTPException(status_code=404, detail="Job not found")
        
    state = job_states[job_id]
    # Filter out html_snapshot to avoid huge payloads
    filtered_state = {k: v for k, v in state.items() if k != "html_snapshot"}
    return filtered_state

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
