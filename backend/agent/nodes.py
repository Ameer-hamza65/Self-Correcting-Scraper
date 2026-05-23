import os
import json
import re
from typing import Dict, Any, Tuple
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from backend.agent.state import ScraperState
from backend.agent.tools import BrowserManager

def clean_selector(selector: str) -> str:
    if not selector:
        return selector
    # Clean anchor tags with hrefs (e.g. a.link.nav[href='/en/tools']) to simple a[href='/en/tools']
    match = re.search(r'a(?:[.\w\-#]+)?\[href=[\'"]([^\'\"]+)[\'"]\]', selector)
    if match:
        href = match.group(1)
        return f"a[href='{href}']"
    return selector

# Global dictionary to manage browser instances by job_id
active_browsers: Dict[str, BrowserManager] = {}

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, max_retries=1, request_timeout=60)

async def observe_node(state: ScraperState) -> Dict[str, Any]:
    job_id = state['job_id']
    browser = active_browsers.get(job_id)
    if not browser:
        return {"error_message": "Browser not initialized", "status": "failed"}
    
    # Only navigate to the initial URL if we haven't executed any steps yet
    history = state.get('history', [])
    if not history:
        print(f"[{job_id}] Navigating to initial page: {state['url']}")
        success = await browser.navigate(state['url'])
        if not success:
            return {"error_message": f"Failed to navigate to {state['url']}", "status": "failed"}
    else:
        print(f"[{job_id}] Observing page after step execution...")
        
    clean_html = await browser.get_clean_html()
    
    return {
        "html_snapshot": clean_html[:80000],
        "status": "planning"
    }

async def plan_node(state: ScraperState) -> Dict[str, Any]:
    job_id = state['job_id']
    history = state.get('history', [])
    accumulated_texts = state.get('accumulated_texts', [])
    failed_steps = state.get('failed_steps', [])
    
    # Safety guardrail to prevent infinite browsing loops
    if len(history) >= 15:
        print(f"[{job_id}] Max steps limit reached. Forcing synthesis.")
        current_steps = list(state.get('steps', []))
        current_steps.append({"action": "finish_and_synthesize"})
        return {"steps": current_steps, "current_step_index": len(current_steps) - 1, "status": "running"}

    print(f"[{job_id}] Planning next step with context...")
    html = state['html_snapshot']
    browser = active_browsers.get(job_id)
    current_url = browser.page.url if (browser and browser.page) else state['url']
    
    print(f"[{job_id}] plan_node: current_url={current_url}")
    print(f"[{job_id}] plan_node: failed_steps={failed_steps}")
    print(f"[{job_id}] plan_node: accumulated_texts={[item['url'] for item in accumulated_texts]}")
    
    # Format list of URLs we have already extracted from
    extracted_urls = [item['url'] for item in accumulated_texts]
    extracted_urls_str = "\n".join([f"- {url}" for url in extracted_urls]) if extracted_urls else "None"
    
    # Format list of failed steps
    failed_steps_str = "\n".join([f"- {json.dumps(step)}" for step in failed_steps]) if failed_steps else "None"
    
    prompt = f"""You are an intelligent, step-by-step web crawling and research agent. You are currently on the URL: {current_url}

OBJECTIVE: {state['objective']}

Pages you have ALREADY extracted content from:
{extracted_urls_str}

Actions/selectors that FAILED execution previously (do NOT try these again):
{failed_steps_str}

Below is the ACTUAL cleaned HTML of the page you are currently on:
---HTML START---
{html}
---HTML END---

Your task is to decide the NEXT single step to get closer to the objective.

CRITICAL RULES:
1. ONLY use CSS selectors that LITERALLY appear in the HTML above. Do NOT guess or invent selectors.
2. Do NOT click a link if it leads to the page you are already on. Check your current URL: {current_url}. If you are already on a page (e.g. '/en/tools/overview' or '/en/inputs'), do NOT click any link that points to that page.
3. If you have just navigated/clicked to a new page that contains relevant information for the objective, your very first action on this new page MUST be to extract its content: [{{"action": "extract_page_content"}}]
4. Do NOT try to click a link that previously failed (listed in the failed list above). Try an alternative link or action instead.
5. If the target information is NOT directly visible in the HTML above and you don't see a specific link for it, try clicking a general portal link like 'Documentation', 'Introduction', 'Get Started', 'Home', or 'Tools Overview' first. This is likely to reveal a sidebar or navigation menu containing the specific links you need on the next page.
6. If you have extracted content from all relevant pages (or have gathered enough information to fully address the objective), output: [{{"action": "finish_and_synthesize"}}]
7. Output ONLY a raw JSON array containing this single action. No markdown wrapping, no explanation.

Supported actions:
- {{"action": "click", "selector": "CSS_SELECTOR"}}
- {{"action": "type_text", "selector": "CSS_SELECTOR", "text": "TEXT"}}
- {{"action": "waitForSelector", "selector": "CSS_SELECTOR"}}
- {{"action": "extract_page_content"}} - Extracts text from current page and stores it in crawl memory
- {{"action": "finish_and_synthesize"}} - Ends the crawl and compiles the final answer using all stored pages"""
    
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        # Clean markdown wrapping
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        new_steps = json.loads(content)
        if not isinstance(new_steps, list):
            new_steps = [new_steps]
            
        # Ensure plan is not empty
        if not new_steps:
            new_steps = [{"action": "extract_page_content"}]
            
        current_steps = list(state.get('steps', []))
        current_steps.extend(new_steps)
        new_step_index = len(current_steps) - len(new_steps)
        
        print(f"[{job_id}] Plan generated: {new_steps}. Active step index: {new_step_index}")
    except Exception as e:
        print(f"[{job_id}] LLM Error during planning: {str(e)}")
        # Fallback: finish and synthesize
        current_steps = list(state.get('steps', []))
        current_steps.append({"action": "finish_and_synthesize"})
        new_step_index = len(current_steps) - 1
        
    return {"steps": current_steps, "current_step_index": new_step_index, "status": "running"}

async def execute_node(state: ScraperState) -> Dict[str, Any]:
    job_id = state['job_id']
    step_index = state['current_step_index']
    steps = state['steps']
    
    if step_index >= len(steps):
        return {"status": "done"}
        
    step = steps[step_index]
    print(f"[{job_id}] Executing step {step_index}: {step}")
    
    browser = active_browsers.get(job_id)
    if not browser:
        return {"error_message": "Browser not initialized", "status": "failed"}

    success = False
    try:
        action = step.get("action")
        selector = step.get("selector")
        cleaned_selector = clean_selector(selector) if selector else None
        
        if action == "navigate":
            success = await browser.navigate(step.get("url"))
        elif action == "click":
            success = await browser.click(cleaned_selector)
        elif action == "type_text":
            success = await browser.type_text(cleaned_selector, step.get("text"))
        elif action in ["waitForSelector", "waitForElement"]:
            success = await browser.wait_for_selector(cleaned_selector)
        elif action == "extract_page_content":
            current_url = browser.page.url if browser.page else state['url']
            page_text = await browser.get_text()
            
            accumulated_texts = list(state.get('accumulated_texts', []))
            # Check if this URL is already in memory, if not, append it
            if not any(item['url'] == current_url for item in accumulated_texts):
                accumulated_texts.append({"url": current_url, "text": page_text})
                print(f"[{job_id}] Extracted content from: {current_url}")
            
            history = state.get('history', [])
            history.append({"step": step, "status": "success"})
            
            return {
                "current_step_index": step_index + 1,
                "history": history,
                "accumulated_texts": accumulated_texts,
                "retry_count": 0,
                "error_message": None,
                "status": "running"
            }
        elif action in ["extract", "finish_and_synthesize"]:
            return {"current_step_index": step_index + 1, "status": "done"}
            
        print(f"[{job_id}] execute_node: step={step}, success={success}")
        if success:
            history = state.get('history', [])
            history.append({"step": step, "status": "success"})
            return {
                "current_step_index": step_index + 1,
                "history": history,
                "retry_count": 0,
                "error_message": None,
                "status": "running"
            }
        else:
            history = state.get('history', [])
            history.append({"step": step, "status": "failed"})
            
            failed_steps = list(state.get('failed_steps', []))
            failed_steps.append(step)
            
            clean_html = await browser.get_clean_html()
            return {
                "current_step_index": step_index + 1,
                "history": history,
                "failed_steps": failed_steps,
                "html_snapshot": clean_html[:80000],
                "error_message": f"Action '{action}' failed: selector '{step.get('selector', 'N/A')}' not found.",
                "status": "running"
            }
    except Exception as e:
        history = state.get('history', [])
        history.append({"step": step, "status": "failed"})
        
        failed_steps = list(state.get('failed_steps', []))
        failed_steps.append(step)
        
        clean_html = await browser.get_clean_html()
        return {
            "current_step_index": step_index + 1,
            "history": history,
            "failed_steps": failed_steps,
            "html_snapshot": clean_html[:80000],
            "error_message": f"Exception during '{step.get('action')}': {str(e)}",
            "status": "running"
        }

async def correct_node(state: ScraperState) -> Dict[str, Any]:
    job_id = state['job_id']
    retry_count = state['retry_count']
    max_retries = state['max_retries']
    
    print(f"[{job_id}] Self-correcting (attempt {retry_count + 1}/{max_retries})...")
    
    # If max retries reached, SKIP the failing step and go straight to extract
    if retry_count >= max_retries:
        print(f"[{job_id}] Max retries reached. Skipping to extraction with whatever data is on the page.")
        # Replace remaining steps with just finish_and_synthesize
        return {
            "steps": [{"action": "finish_and_synthesize"}],
            "current_step_index": 0,
            "retry_count": 0,
            "status": "running",
            "error_message": f"Skipped failing step after {max_retries} retries. Extracting available data."
        }

    step = state['steps'][state['current_step_index']]
    prompt = f"""A browser automation step failed.

Failed step: {json.dumps(step)}
Error: {state['error_message']}

Current page HTML (cleaned):
---HTML START---
{state['html_snapshot']}
---HTML END---

CRITICAL RULES:
1. Look at the HTML above and find a selector that ACTUALLY EXISTS.
2. If the failed selector simply doesn't exist on this page, output [{{"action": "finish_and_synthesize"}}] to extract data from the current page instead.
3. Do NOT invent selectors. Only use ones you can see in the HTML.
4. Output ONLY a raw JSON array of replacement steps. No markdown, no explanation."""
    
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        new_steps = json.loads(content)
        
        # Modify the steps list
        current_steps = list(state['steps'])
        current_steps.pop(state['current_step_index'])
        for i, new_step in enumerate(new_steps):
            current_steps.insert(state['current_step_index'] + i, new_step)
            
        return {
            "steps": current_steps,
            "retry_count": retry_count + 1,
            "status": "running",
            "error_message": f"Retrying after correction (attempt {retry_count + 1})"
        }
    except Exception as e:
        # If correction itself fails, skip to extract
        return {
            "steps": [{"action": "finish_and_synthesize"}],
            "current_step_index": 0,
            "retry_count": 0,
            "status": "running",
            "error_message": f"Correction failed: {e}. Falling back to extraction."
        }

async def extract_node(state: ScraperState) -> Dict[str, Any]:
    job_id = state['job_id']
    print(f"[{job_id}] Extracting and synthesizing final response...")
    
    accumulated_texts = state.get('accumulated_texts', [])
    
    # Fallback to current page content if accumulated_texts is empty
    if not accumulated_texts:
        browser = active_browsers.get(job_id)
        if browser:
            page_text = await browser.get_text()
            current_url = browser.page.url if browser.page else state['url']
            accumulated_texts = [{"url": current_url, "text": page_text}]
        else:
            return {"error_message": "Browser not initialized and no crawler memory found", "status": "failed"}

    # Format all crawled pages text for the synthesis prompt
    collected_sources = ""
    for idx, item in enumerate(accumulated_texts):
        # Allow up to 25,000 characters per page to prevent truncation of detail
        snippet = item['text'][:25000]
        collected_sources += f"--- SOURCE {idx+1}: {item['url']} ---\n{snippet}\n\n"

    prompt = f"""You are an expert researcher and data synthesizer.

OBJECTIVE: {state['objective']}

Below is the text content gathered from the website pages we crawled:
=========================================
{collected_sources}
=========================================

Based on the gathered content, perform two tasks:
1. Write a direct, highly detailed, comprehensive human-readable final response (in Markdown format) that fully satisfies the objective. Organize it beautifully with headers, bullet points, code blocks, and lists where appropriate.
2. Extract the structured facts/data as a JSON object (a clean schema reflecting the objective).

Output your response as a JSON object with exactly two top-level keys:
- "response": A string containing the markdown-formatted natural language answer.
- "structured_data": A JSON object/array containing the extracted structured data/metadata.

Output ONLY the raw JSON object. No markdown wrapping, no explanation."""
    
    try:
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        content = response.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        data = json.loads(content)
        # Verify structure and add wrapper if missing
        if not isinstance(data, dict) or "response" not in data or "structured_data" not in data:
            data = {
                "response": "Here is the extracted information:\n\n" + json.dumps(data, indent=2),
                "structured_data": data
            }
        return {"scraped_data": data, "status": "done"}
    except json.JSONDecodeError:
        return {
            "scraped_data": {
                "response": content,
                "structured_data": {"raw": content}
            },
            "status": "done"
        }
    except Exception as e:
        return {
            "scraped_data": {
                "response": f"Error during extraction: {e}",
                "structured_data": {"error": str(e)}
            },
            "status": "done"
        }
