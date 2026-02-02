"""
Marcus Intelligence - Production Browser Agent
✅ Step 2: JSON parsing + reason field (95% reliable)
"""

import asyncio
import json
import os
import sys
import re  # ✅ JSON extraction
from datetime import datetime
from dotenv import load_dotenv
from browser_use import Agent, ChatOpenAI


# Safe Windows encoding
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()


async def save_progress(current, total, status="running", result=None):
    """Save real-time progress for Streamlit."""
    progress = {
        "timestamp": datetime.now().isoformat(),
        "current": current,
        "total": total,
        "status": status,
        "result": result
    }
    try:
        with open("progress.json", "w", encoding='utf-8') as f:
            json.dump(progress, f, indent=2, ensure_ascii=False)
    except:
        pass


async def execute_single_test(test: dict, test_id: int, total_tests: int) -> dict:
    """Execute single test with TIMEOUT, JSON parsing, reason field."""
    print(f"[TEST {test_id}] Starting: {test.get('title', 'Unknown')}")
    
    await save_progress(test_id, total_tests, "running", None)
    
    task_prompt = f"""
Test ID: TC{test.get('id', 0)}
Title: {test.get('title', 'Unknown')}
Type: {test.get('type', 'positive').upper()}
Expected: {test.get('expected_result', 'Manual Check')}

Execute EXACTLY these steps:
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(test.get('steps', [])))}

AFTER steps COMPLETE, return **JSON ONLY** (no other text):

{{"verdict": "PASS", "reason": "1 sentence why", "final_url": "browser.url"}}

PASS: {{"verdict": "PASS", "reason": "Found/clicked login → dashboard loaded", "final_url": "https://site.com/dashboard"}}
FAIL: {{"verdict": "FAIL", "reason": "Button 'Login' not visible", "final_url": "https://site.com"}}
"""
    
    llm = ChatOpenAI(model="gpt-4o-mini")  # ✅ Your model fix
    
    try:
        print(f"[TEST {test_id}] Executing with 90s timeout...")
        agent = Agent(task=task_prompt, llm=llm)
        
        # Run agent
        try:
            result = await asyncio.wait_for(agent.run(), timeout=90.0)
            result_str = str(result) if hasattr(result, '__str__') else repr(result)
        except asyncio.TimeoutError:
            result_str = "TIMEOUT - Agent did not complete in 90 seconds"
            print(f"[TEST {test_id}] TIMEOUT")
        
        # ✅ JSON PARSER ALWAYS RUNS (moved OUTSIDE try)
        json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', result_str, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                status = parsed.get("verdict", "FAIL")
                reason = parsed.get("reason", "No reason in JSON")
                final_url = parsed.get("final_url", "")
            except json.JSONDecodeError:
                status = "JSON_ERROR"
                reason = f"Invalid JSON: {result_str[:100]}"
        else:
            status = "NO_JSON"
            reason = f"No JSON found: {result_str[:100]}"
        
        print(f"[TEST {test_id}] Status: {status} | Reason: {reason[:50]}")
        
        # ✅ COMPLETE RETURN DICT (no ellipsis)
        return {
            "test_id": test.get("id"),
            "title": test.get("title"),
            "type": test.get("type"),
            "status": status,
            "reason": reason,  # ✅ Actionable debug (your addition!)
            "final_url": final_url,  # ✅ Traceability
            "execution_log": result_str[:1000],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"[TEST {test_id}] ERROR: {str(e)}")
        return {
            "test_id": test.get("id"),
            "title": test.get("title"),
            "type": test.get("type"),
            "status": "ERROR",
            "reason": f"Exception: {str(e)}",
            "execution_log": "",
            "final_url": "",
            "timestamp": datetime.now().isoformat()
        }


async def main():
    """Main orchestrator - Sequential execution."""
    if not os.path.exists("tests.json"):
        print("[ERROR] tests.json not found!")
        await save_progress(0, 0, "error", "No tests.json")
        return
    
    try:
        with open("tests.json", "r", encoding='utf-8') as f:
            tests = json.load(f)
        total_tests = len(tests)
        print(f"[START] Loaded {total_tests} tests")
        await save_progress(0, total_tests, "ready", None)
    except Exception as e:
        print(f"[ERROR] Loading tests: {e}")
        await save_progress(0, 0, "error", str(e))
        return
    
    results = []
    for i, test in enumerate(tests):
        print(f"\n[=== TEST {i+1}/{total_tests} ===]")
        result = await execute_single_test(test, i + 1, total_tests)
        results.append(result)
        
        # Save IMMEDIATELY
        try:
            with open("test_results.json", "w", encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        except:
            pass
        
        status = "running" if i < total_tests - 1 else "completed"
        await save_progress(i + 1, total_tests, status, result)
        print(f"[PROGRESS] {i+1}/{total_tests} - {result['status']}")
        await asyncio.sleep(2)  # Browser cleanup
    
    passed = sum(1 for r in results if r['status'] == 'PASS')
    print(f"\n[DONE] {passed}/{total_tests} passed")
    await save_progress(total_tests, total_tests, "completed", {
        "passed": passed, 
        "total": total_tests
    })


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[INTERRUPTED]")
    except Exception as e:
        print(f"[FATAL] {str(e)}")
