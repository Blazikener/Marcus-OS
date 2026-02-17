"""
Browser Agent — executes generated test cases via browser-use Agent.
"""

import asyncio
import json
import os
import re
import sys
import time
import tempfile
from datetime import datetime
from dotenv import load_dotenv

# ─── Windows fix: browser-use hardcodes Path('/tmp/...') for downloads ────────
# On Windows, /tmp resolves to \tmp on the current drive root, which is typically
# not writable. browser-use creates BrowserProfile() at module-load time in
# session.py, which calls Path('/tmp/browser-use-downloads-<uuid>').mkdir().
# Fix: (1) monkey-patch Path.mkdir to redirect /tmp/browser-use-* to system temp
#      (2) patch the Pydantic model validator to store the correct path too.
# Both patches are needed: mkdir for the immediate error, validator for the
# stored downloads_path used later by Playwright.
if sys.platform.startswith('win'):
    from pathlib import Path as _Path
    import importlib
    import uuid as _uuid

    _real_tmp = tempfile.gettempdir()

    # Patch 1: redirect mkdir calls for /tmp/browser-use-* to system temp
    _orig_mkdir = _Path.mkdir

    def _patched_mkdir(self, mode=0o777, parents=False, exist_ok=False):
        s = str(self)
        if os.sep + 'tmp' + os.sep + 'browser-use' in s:
            redirected = _Path(_real_tmp) / self.name
            return _orig_mkdir(redirected, mode=mode, parents=parents, exist_ok=exist_ok)
        return _orig_mkdir(self, mode=mode, parents=parents, exist_ok=exist_ok)

    _Path.mkdir = _patched_mkdir

    # Patch 2: replace the validator so stored downloads_path is in system temp
    _profile = importlib.import_module('browser_use.browser.profile')

    def _fixed_downloads_validator(self):
        if self.downloads_path is None:
            _uid = str(_uuid.uuid4())[:8]
            _dl = _Path(_real_tmp) / f'browser-use-downloads-{_uid}'
            while _dl.exists():
                _uid = str(_uuid.uuid4())[:8]
                _dl = _Path(_real_tmp) / f'browser-use-downloads-{_uid}'
            self.downloads_path = _dl
            self.downloads_path.mkdir(parents=True, exist_ok=True)
        return self

    _profile.BrowserProfile.set_default_downloads_path = _fixed_downloads_validator

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


def extract_target_url(test: dict) -> str:
    """Extract the target URL from test steps (first URL found)."""
    for step in test.get('steps', []):
        match = re.search(r'https?://[^\s\'"<>]+', step)
        if match:
            return match.group(0).rstrip('.,;)')
    return ""


def build_execution_log(result, max_length=2000) -> str:
    """Build human-readable step log from AgentHistoryList."""
    lines = []
    try:
        for i, ar in enumerate(result.action_results(), 1):
            if ar.error:
                lines.append(f"Step {i}: ERROR - {str(ar.error)[:100]}")
            elif ar.extracted_content:
                lines.append(f"Step {i}: {ar.extracted_content[:150]}")
            elif ar.is_done:
                lines.append(f"Step {i}: DONE")
    except Exception:
        return str(result)[:max_length]
    log = "\n".join(lines)
    return log[:max_length] if log else str(result)[:max_length]


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
            "execution_log": result.get("execution_log", "")[:2000],
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

    target_url = extract_target_url(test)
    test_type = test.get('type', 'positive').upper()

    negative_guidance = ""
    if test_type == "NEGATIVE":
        negative_guidance = "\nThis is a NEGATIVE test: PASS means the bad/unexpected behavior was correctly PREVENTED or the error was handled gracefully.\n"

    task_prompt = f"""You are a QA test executor. Your browser starts on a BLANK page.

**TARGET URL: {target_url}**
**YOUR FIRST ACTION MUST BE: navigate to {target_url}**
Do NOT wait or observe the blank page. Navigate immediately.

Test: TC{test.get('id', 0)} — {test_title}
Type: {test_type}
Expected: {test.get('expected_result', 'Manual Check Needed')}
{negative_guidance}
Steps:
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(test.get('steps', [])))}

After completing ALL steps, return ONLY this JSON (no other text):
{{"verdict": "PASS or FAIL", "reason": "1 sentence explaining what you observed", "final_url": "the current URL"}}

PASS means the expected result WAS observed.
FAIL means the expected result was NOT observed.
"""

    llm = ChatOpenAI(model="gpt-4o-mini")
    agent = None
    needs_cleanup = True  # agent.run() calls close() internally on success

    try:
        print(f"[{ts()}][TEST {test_id}] Executing with {timeout}s timeout...")
        agent = Agent(task=task_prompt, llm=llm, max_failures=4)

        try:
            result = await asyncio.wait_for(agent.run(max_steps=15), timeout=float(timeout))
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
            # 1. Extract final content from the last completed action (clean string)
            final_content = ""
            last_judgement = None
            for ar in reversed(result.action_results()):
                if ar.is_done:
                    if ar.extracted_content:
                        final_content = ar.extracted_content
                    if ar.judgement is not None:
                        last_judgement = ar.judgement
                    break

            # 2. Try JSON from extracted_content first (clean, no repr noise)
            parsed = extract_json_from_text(final_content) if final_content else None

            # 3. Fall back to full str(result) if extracted_content had no JSON
            if parsed is None:
                parsed = extract_json_from_text(result_str)

            if parsed is not None:
                status = parsed.get("verdict", "FAIL")
                reason = parsed.get("reason", "No reason in JSON")
                final_url = parsed.get("final_url", "")
            elif last_judgement is not None:
                # 4. No JSON anywhere — use the agent's own judgement
                if last_judgement.verdict:
                    status = "PASS"
                else:
                    status = "FAIL"
                reason = last_judgement.failure_reason or last_judgement.reasoning or "No reason provided"
                reason = reason[:300]
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
            "execution_log": build_execution_log(result) if status != "TIMEOUT" else "TIMEOUT",
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
            "execution_log": str(e)[:500],
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
        await asyncio.sleep(8)  # Pause between tests to avoid OpenAI rate limits

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