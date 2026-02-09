"""
Browser Agent — executes generated test cases via browser-use Agent.
"""

import asyncio
import json
import os
import sys
import time
import tempfile
from datetime import datetime
from dotenv import load_dotenv
from browser_use import Agent, ChatOpenAI


# Safe Windows encoding
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

# ─── Configuration ────────────────────────────────────────────────────────────
TEST_TIMEOUT = int(os.getenv("MARCUS_TEST_TIMEOUT", "180"))

# ─── Multi-tenancy: Supabase service client (bypasses RLS) ──────────────────
MARCUS_RUN_ID = os.getenv("MARCUS_RUN_ID")
MARCUS_USER_ID = os.getenv("MARCUS_USER_ID")
MARCUS_ORG_ID = os.getenv("MARCUS_ORG_ID")


def ts() -> str:
    """Timestamp for log output."""
    return datetime.now().strftime('%H:%M:%S')


def atomic_json_write(filepath: str, data):
    """Write JSON atomically: temp file + os.replace (safe on Windows)."""
    dir_name = os.path.dirname(os.path.abspath(filepath))
    try:
        fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix='.tmp', prefix='.marcus_')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, filepath)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except (IOError, OSError, TypeError, ValueError) as e:
        print(f"[{ts()}][IO] Atomic write failed for {filepath}: {e}")


def extract_json_from_text(text: str):
    """Extract the first valid JSON object from text using bracket counting.
    Handles arbitrarily nested JSON, unlike regex which only handles 1 level.
    Returns parsed dict or None.
    """
    start_idx = 0
    while True:
        start = text.find('{', start_idx)
        if start == -1:
            return None

        depth = 0
        in_string = False
        escape_next = False

        for i in range(start, len(text)):
            c = text[i]

            if escape_next:
                escape_next = False
                continue

            if c == '\\' and in_string:
                escape_next = True
                continue

            if c == '"' and not escape_next:
                in_string = not in_string
                continue

            if in_string:
                continue

            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    try:
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        break  # Try next opening brace

        start_idx = start + 1


def get_service_client():
    """Get Supabase client with service role key (bypasses RLS).
    Returns None if credentials are not available (legacy/standalone mode).
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if url and key:
        try:
            from supabase import create_client
            return create_client(url, key)
        except Exception as e:
            print(f"[{ts()}][SUPABASE] Failed to create service client: {e}")
    return None


def save_result_to_supabase(supa, result: dict):
    """Insert a single test result row into Supabase."""
    if not supa or not MARCUS_RUN_ID:
        return
    try:
        supa.table("test_results").insert({
            "run_id": int(MARCUS_RUN_ID),
            "test_id": result.get("test_id"),
            "title": result.get("title"),
            "type": result.get("type"),
            "status": result.get("status"),
            "reason": result.get("reason"),
            "final_url": result.get("final_url"),
            "execution_log": result.get("execution_log", "")[:1000],
        }).execute()
    except Exception as e:
        print(f"[{ts()}][SUPABASE] Failed to save result: {e}")


def update_run_status(supa, status: str):
    """Update the test_runs row status in Supabase."""
    if not supa or not MARCUS_RUN_ID:
        return
    try:
        supa.table("test_runs").update({
            "status": status,
            "updated_at": datetime.now().isoformat(),
        }).eq("id", int(MARCUS_RUN_ID)).execute()
    except Exception as e:
        print(f"[{ts()}][SUPABASE] Failed to update run status: {e}")


def save_progress(current, total, status="running", result=None,
                  current_test_title=None, test_start_time=None):
    """Save real-time progress for Streamlit dashboard."""
    elapsed = None
    if test_start_time is not None:
        elapsed = round(time.time() - test_start_time, 1)

    progress = {
        "timestamp": datetime.now().isoformat(),
        "current": current,
        "total": total,
        "status": status,
        "result": result,
        "current_test_title": current_test_title,
        "test_elapsed_seconds": elapsed,
    }
    atomic_json_write("progress.json", progress)


async def execute_single_test(test: dict, test_id: int, total_tests: int,
                              timeout: int = 180) -> dict:
    """Execute a single test case with timeout, JSON parsing, and cleanup."""
    # Initialize all result fields upfront to prevent NameError
    final_url = ""
    status = "ERROR"
    reason = "Unknown error"
    result_str = ""

    test_title = test.get('title', 'Unknown')
    print(f"[{ts()}][TEST {test_id}] Starting: {test_title}")

    task_prompt = f"""
Test ID: TC{test.get('id', 0)}
Title: {test_title}
Type: {test.get('type', 'positive').upper()}
Expected: {test.get('expected_result', 'Manual Check Needed')}

Execute EXACTLY these steps:
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(test.get('steps', [])))}

AFTER steps COMPLETE, return **JSON ONLY** (no other text):

{{"verdict": "PASS", "reason": "1 sentence why", "final_url": "browser.url"}}

PASS: {{"verdict": "PASS", "reason": "Found/clicked login -> dashboard loaded", "final_url": "https://site.com/dashboard"}}
FAIL: {{"verdict": "FAIL", "reason": "Button 'Login' not visible", "final_url": "https://site.com"}}
"""

    llm = ChatOpenAI(model="gpt-4o-mini")
    agent = None
    needs_cleanup = True  # agent.run() calls close() internally on success

    try:
        print(f"[{ts()}][TEST {test_id}] Executing with {timeout}s timeout...")
        agent = Agent(task=task_prompt, llm=llm, max_failures=2)

        try:
            result = await asyncio.wait_for(agent.run(max_steps=25), timeout=float(timeout))
            result_str = str(result) if hasattr(result, '__str__') else repr(result)
            needs_cleanup = False  # agent.run() already called close() on success
        except asyncio.TimeoutError:
            result_str = "TIMEOUT"
            status = "TIMEOUT"
            reason = "Agent timed out after {}s".format(timeout)
            print(f"[{ts()}][TEST {test_id}] TIMEOUT after {timeout}s")
            needs_cleanup = True  # run was cancelled, browser still alive

        # Parse JSON from agent output (skip if already timed out)
        if status != "TIMEOUT":
            parsed = extract_json_from_text(result_str)
            if parsed is not None:
                status = parsed.get("verdict", "FAIL")
                reason = parsed.get("reason", "No reason in JSON")
                final_url = parsed.get("final_url", "")
            else:
                status = "NO_JSON"
                reason = "No JSON found: {}".format(result_str[:200])

        print(f"[{ts()}][TEST {test_id}] Status: {status} | Reason: {reason[:80]}")

        return {
            "test_id": test.get("id"),
            "title": test_title,
            "type": test.get("type"),
            "status": status,
            "reason": reason,
            "final_url": final_url,
            "execution_log": result_str[:1000],
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        needs_cleanup = True  # exception means run didn't finish cleanly
        print(f"[{ts()}][TEST {test_id}] ERROR: {str(e)}")
        return {
            "test_id": test.get("id"),
            "title": test_title,
            "type": test.get("type"),
            "status": "ERROR",
            "reason": "Exception: {}".format(str(e)[:300]),
            "execution_log": result_str[:1000] if result_str else "",
            "final_url": "",
            "timestamp": datetime.now().isoformat()
        }

    finally:
        # Only close manually if agent.run() didn't complete normally
        # (agent.run() calls self.close() internally on success — calling it
        #  again on an already-closed session causes a hang/deadlock)
        if agent is not None and needs_cleanup:
            print(f"[{ts()}][TEST {test_id}] Cleaning up browser session...")
            try:
                await asyncio.wait_for(agent.close(), timeout=10.0)
                print(f"[{ts()}][TEST {test_id}] Agent closed")
            except asyncio.TimeoutError:
                print(f"[{ts()}][TEST {test_id}] agent.close() hung — force-killing browser")
                try:
                    if hasattr(agent, 'browser_session') and agent.browser_session is not None:
                        await asyncio.wait_for(agent.browser_session.kill(), timeout=5.0)
                except Exception:
                    pass
            except Exception as close_err:
                print(f"[{ts()}][TEST {test_id}] Cleanup error: {close_err}")


async def main():
    """Main orchestrator — sequential execution with per-test error isolation."""
    if not os.path.exists("tests.json"):
        print(f"[{ts()}][ERROR] tests.json not found!")
        save_progress(0, 0, "error", "No tests.json")
        return

    # Initialize Supabase service client (None if not available)
    supa = get_service_client()
    if supa and MARCUS_RUN_ID:
        print(f"[{ts()}][SUPABASE] Connected. Run ID: {MARCUS_RUN_ID}")
        update_run_status(supa, "running")
    else:
        print(f"[{ts()}][SUPABASE] Not configured — running in local-only mode")

    try:
        with open("tests.json", "r", encoding='utf-8') as f:
            tests = json.load(f)
        total_tests = len(tests)
        print(f"[{ts()}][START] Loaded {total_tests} tests (timeout: {TEST_TIMEOUT}s per test)")
        save_progress(0, total_tests, "ready", None)
    except Exception as e:
        print(f"[{ts()}][ERROR] Loading tests: {e}")
        save_progress(0, 0, "error", str(e))
        update_run_status(supa, "failed")
        return

    results = []
    for i, test in enumerate(tests):
        test_title = test.get("title", "Unknown") if isinstance(test, dict) else "Unknown"
        test_start = time.time()

        print(f"\n[{ts()}][=== TEST {i + 1}/{total_tests} ===]")
        save_progress(i, total_tests, "running", None,
                      current_test_title=test_title, test_start_time=test_start)

        # Error isolation: one bad test cannot crash remaining tests
        try:
            result = await execute_single_test(test, i + 1, total_tests, timeout=TEST_TIMEOUT)
        except Exception as e:
            print(f"[{ts()}][TEST {i + 1}] UNHANDLED ERROR: {e}")
            result = {
                "test_id": test.get("id") if isinstance(test, dict) else i + 1,
                "title": test_title,
                "type": test.get("type", "unknown") if isinstance(test, dict) else "unknown",
                "status": "ERROR",
                "reason": "Unhandled exception: {}".format(str(e)[:200]),
                "final_url": "",
                "execution_log": "",
                "timestamp": datetime.now().isoformat(),
            }

        results.append(result)

        # Save locally (for live monitoring) — atomic write
        atomic_json_write("test_results.json", results)

        # Save to Supabase
        save_result_to_supabase(supa, result)

        loop_status = "running" if i < total_tests - 1 else "completed"
        save_progress(i + 1, total_tests, loop_status, result,
                      current_test_title=test_title if loop_status == "running" else None,
                      test_start_time=test_start if loop_status == "running" else None)
        print(f"[{ts()}][PROGRESS] {i + 1}/{total_tests} - {result['status']}")
        await asyncio.sleep(2)  # Brief pause between tests

    passed = sum(1 for r in results if r['status'] == 'PASS')
    failed = sum(1 for r in results if r['status'] == 'FAIL')
    print(f"\n[{ts()}][DONE] {passed}/{total_tests} passed, {failed} failed")
    update_run_status(supa, "completed")
    save_progress(total_tests, total_tests, "completed", {
        "passed": passed,
        "failed": failed,
        "total": total_tests
    })


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n[{ts()}][INTERRUPTED]")
    except Exception as e:
        print(f"[{ts()}][FATAL] {str(e)}")
