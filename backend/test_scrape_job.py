import urllib.request
import json
import time

def test():
    url = "http://localhost:8000/api/scrape"
    payload = {
        "url": "https://docs.crewai.com/",
        "objective": "i want all the infromation of existing tools in crewai"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    
    print("Launching agent...")
    try:
        response = urllib.request.urlopen(req)
        res_data = json.loads(response.read().decode())
        job_id = res_data['job_id']
        print(f"Agent launched successfully. Job ID: {job_id}")
    except Exception as e:
        print(f"Failed to launch agent: {e}")
        return

    status = "started"
    while status not in ["done", "failed"]:
        time.sleep(2)
        try:
            status_url = f"http://localhost:8000/api/scrape/{job_id}"
            res = urllib.request.urlopen(status_url)
            state = json.loads(res.read().decode())
            status = state.get("status")
            steps = state.get("steps", [])
            current_idx = state.get("current_step_index", 0)
            
            print(f"Status: {status} | Steps Count: {len(steps)} | Active Index: {current_idx}")
            if steps:
                print(f"  Current planned steps: {steps[current_idx:]}")
        except Exception as e:
            print(f"Error checking status: {e}")
            break

    print("\nFinal State:")
    try:
        status_url = f"http://localhost:8000/api/scrape/{job_id}"
        res = urllib.request.urlopen(status_url)
        state = json.loads(res.read().decode())
        print(json.dumps(state, indent=2))
    except Exception as e:
        print(f"Failed to fetch final state: {e}")

if __name__ == "__main__":
    test()
