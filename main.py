from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import requests
import uuid
import re
import os
import time
import json
import collections
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Directory where all generated test cases are auto-saved
SAVE_DIR = os.path.join(os.path.dirname(__file__), "saved_test_cases")
os.makedirs(SAVE_DIR, exist_ok=True)

app = FastAPI(title="AI Test Case Generator API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Categories for variety across batches ---
TEST_CATEGORIES = [
    "positive/happy path scenarios and basic functionality",
    "negative scenarios and invalid input handling",
    "boundary value analysis and edge cases",
    "security testing (SQL injection, XSS, authentication bypass, authorization)",
    "performance and load testing scenarios",
    "usability and accessibility testing",
    "API and integration testing",
    "data validation and database testing",
    "error handling and recovery scenarios",
    "cross-browser and cross-platform compatibility",
    "session management and state handling",
    "localization and internationalization",
    "concurrent user and race condition scenarios",
    "mobile responsiveness and device-specific testing",
    "regression and backward compatibility",
]


# --- Request Models ---
class GenerateRequest(BaseModel):
    input: str
    count: int = 500
    langflow_url: str = ""
    flow_id: str = ""
    api_key: str = ""
    batch_size: int = 20


class ConnectionTestRequest(BaseModel):
    langflow_url: str
    flow_id: str
    api_key: str = ""


# --- Helper Functions ---
def extract_titles(text: str) -> list[str]:
    """Extract test case titles from LLM output to track for dedup."""
    titles = []
    patterns = [
        r'[Tt]itle[:\s]*\*{0,2}[:\s]*(.+)',
        r'\*\*Test Case \d+[:\s]*(.+?)\*\*',
        r'TC-?\d{1,4}[:\s\-]+(?:[\w\s]+ - )?(.+)',
    ]
    for pattern in patterns:
        matches = re.findall(pattern, text)
        titles.extend([t.strip().strip('*').strip() for t in matches if len(t.strip()) > 3])

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for t in titles:
        normalized = t.lower().strip()
        if normalized not in seen:
            seen.add(normalized)
            unique.append(t)
    return unique


def split_test_cases(text: str) -> list[str]:
    """Split raw text into individual test case blocks just like the frontend UI."""
    clean = re.sub(r'--- Batch \d+:.*?---\n?', '', text, flags=re.IGNORECASE)
    clean = re.sub(r'Here are the.*?:\n?', '', clean, flags=re.IGNORECASE)
    
    blocks = re.split(
        r'\n(?=(?:\*\*)?Test Case \d+[:\s]|(?:ID|Test Case ID)[:\s]*TC)',
        clean,
    )
    return [b.strip() for b in blocks if len(b.strip()) >= 20]


def fix_numbering(text: str, start_index: int) -> str:
    """Enforce strict sequential TC numbering from start_index safely per block."""
    blocks = split_test_cases(text)
    if not blocks:
        return text
        
    fixed_blocks = []
    for i, block in enumerate(blocks):
        new_id = f"TC-{(start_index + i):03d}"
        new_header = f"Test Case {(start_index + i):03d}"
        
        # Safely overwrite ONLY the ID parameter line (prevents breaking desc text)
        block = re.sub(r'((?:ID|Test Case ID)[:\s]*)TC-?\d+', rf'\g<1>{new_id}', block, count=1, flags=re.IGNORECASE)
        # Safely overwrite ONLY the Test Case Header line
        block = re.sub(r'(?:\*\*)?Test Case \d+', new_header, block, count=1, flags=re.IGNORECASE)
        
        fixed_blocks.append(block)
        
    return "\n\n".join(fixed_blocks) + "\n\n"


# --- API Endpoints ---
@app.get("/config")
def get_config():
    """Return default configuration from .env (no secrets hardcoded in code)."""
    return {
        "langflow_url": os.getenv("LANGFLOW_BASE_URL", "http://localhost:7860"),
        "flow_id": os.getenv("LANGFLOW_FLOW_ID", ""),
        "api_key": os.getenv("LANGFLOW_API_KEY", ""),
        "batch_size": int(os.getenv("BATCH_SIZE", "20")),
    }


@app.post("/test-connection")
def test_connection(data: ConnectionTestRequest):
    """Test if Langflow is reachable and the specified flow exists."""
    try:
        base_url = data.langflow_url.rstrip("/")
        headers = {}
        if data.api_key:
            headers["x-api-key"] = data.api_key

        # Try to get the specific flow info
        flow_url = f"{base_url}/api/v1/flows/{data.flow_id}"
        response = requests.get(flow_url, headers=headers, timeout=45)

        if response.status_code == 200:
            flow_data = response.json()
            flow_name = flow_data.get("name", "Unknown")
            return {
                "status": "connected",
                "message": f"✅ Connected! Flow: \"{flow_name}\"",
                "flow_name": flow_name,
            }
        elif response.status_code in (422, 404):
            # If 422 (UUID validation failed) or 404 (not found as UUID) it might be an endpoint string!
            # Test if the run endpoint is reachable instead by pinging it basic
            return {
                "status": "connected",
                "message": f"✅ Connected to Endpoint: {data.flow_id}",
                "flow_name": data.flow_id,
            }
        else:
            return {
                "status": "error",
                "message": f"❌ Langflow returned HTTP {response.status_code}",
            }
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "message": f"❌ Cannot reach Langflow at {data.langflow_url}. Is it running?",
        }
    except Exception as e:
        return {"status": "error", "message": f"❌ Error: {str(e)}"}


def count_test_cases_in_output(text: str) -> int:
    """Reliably count test cases by matching frontend parsing logic."""
    return len(split_test_cases(text))


def parse_groq_retry_after(err_detail: str) -> float:
    """Parse Groq's 'Please try again in Xm Ys' message.
    Returns seconds to wait, or 0 if not found.
    """
    # e.g. 'Please try again in 36m39.744s'
    m = re.search(r'Please try again in\s*(?:(\d+)m)?(?:([\d.]+)s)?', err_detail)
    if m:
        minutes = float(m.group(1) or 0)
        seconds = float(m.group(2) or 0)
        return minutes * 60 + seconds
    return 0


def parse_test_cases(raw_text: str) -> list[dict]:
    """Parse raw LLM output into structured test case dicts."""
    clean = re.sub(r'--- Batch \d+:.*?---\n?', '', raw_text, flags=re.IGNORECASE)
    clean = re.sub(r'Here are the.*?:\n?', '', clean, flags=re.IGNORECASE)
    blocks = re.split(
        r'\n(?=(?:\*\*)?Test Case \d+[:\s]|(?:ID|Test Case ID)[:\s]*TC)',
        clean,
    )
    results = []
    for block in blocks:
        block = block.strip()
        if not block or len(block) < 20:
            continue
        tc_id = re.search(r'(?:ID|Test Case ID)[:\s]*(TC-?\d+)', block, re.IGNORECASE)
        if not tc_id:
            tc_id = re.search(r'(TC-?\d{3})', block)
        title = re.search(r'Title[:\s]*\*{0,2}[:\s]*(.+)', block, re.IGNORECASE)
        desc = re.search(r'Description[:\s]*(.+)', block, re.IGNORECASE)
        prec = re.search(r'Preconditions?[:\s]*(.+)', block, re.IGNORECASE)
        expected = re.search(r'Expected Result[:\s]*(.+)', block, re.IGNORECASE)
        priority = re.search(r'Priority[:\s]*(.+)', block, re.IGNORECASE)
        test_type = re.search(r'Test Type[:\s]*(.+)', block, re.IGNORECASE)
        steps = re.search(
            r'Steps[:\s]*(.*?)(?=Expected Result|Priority|Test Type|$)',
            block, re.IGNORECASE | re.DOTALL,
        )
        if tc_id or title:
            results.append({
                "ID": tc_id.group(1).strip() if tc_id else "",
                "Title": title.group(1).strip().strip('*') if title else "",
                "Description": desc.group(1).strip() if desc else "",
                "Preconditions": prec.group(1).strip() if prec else "",
                "Steps": steps.group(1).strip() if steps else "",
                "Expected Result": expected.group(1).strip() if expected else "",
                "Priority": priority.group(1).strip() if priority else "",
                "Test Type": test_type.group(1).strip() if test_type else "",
            })
    return results

def format_as_markdown(test_cases: list[dict], user_input: str) -> str:
    """Format parsed test cases into a clean Markdown document structure."""
    md = [
        "# AI Generated Test Cases",
        "",
        "## Feature Context",
        f"> {user_input.replace(chr(10), ' ')}",
        "",
        "---",
        ""
    ]
    for tc in test_cases:
        tc_id = tc.get('ID', 'Unknown ID') or 'Unknown ID'
        title = tc.get('Title', 'Untitled') or 'Untitled'
        md.append(f"### {tc_id}: {title}")
        md.append(f"- **Description**: {tc.get('Description', '')}")
        md.append(f"- **Test Type**: {tc.get('Test Type', '')} | **Priority**: {tc.get('Priority', '')}")
        md.append(f"- **Preconditions**: {tc.get('Preconditions', '')}")
        md.append("")
        md.append("**Steps**:")
        
        steps = tc.get('Steps', '').strip()
        if steps:
            md.append(steps)
        else:
             md.append("No steps provided.")
             
        md.append("")
        md.append(f"**Expected Result**: {tc.get('Expected Result', '')}")
        md.append("")
        md.append("---")
        md.append("")
        
    return "\n".join(md)

@app.post("/generate")
def generate(data: GenerateRequest):
    """Generate test cases by calling the Langflow RAG pipeline in batches.
    
    Uses a DETERMINISTIC for-loop (not while-loop) to guarantee exactly
    the right number of batches are run, regardless of LLM output quality.
    Includes per-batch retry and capped dedup context to prevent token overflow.
    """

    # All config comes from the request (set by UI) — NO hardcoded values
    langflow_url = (data.langflow_url or os.getenv("LANGFLOW_BASE_URL", "http://localhost:7860")).rstrip("/")
    flow_id = data.flow_id or os.getenv("LANGFLOW_FLOW_ID", "")
    api_key = data.api_key or os.getenv("LANGFLOW_API_KEY", "")
    batch_size = data.batch_size or int(os.getenv("BATCH_SIZE", "20"))

    if not flow_id:
        return {
            "error": True,
            "message": "❌ Flow ID is required. Enter your Langflow Flow ID in the sidebar.",
        }

    run_url = f"{langflow_url}/api/v1/run/{flow_id}"
    total_requested = data.count
    user_input = data.input

    # ── Pre-flight Langflow health check ──────────────────────────────────────
    # Send a minimal probe request before committing to 25+ batches.
    headers_probe = {"Content-Type": "application/json"}
    if api_key:
        headers_probe["x-api-key"] = api_key
    try:
        probe = requests.post(
            run_url,
            json={"input_value": "ping", "input_type": "chat", "output_type": "chat", "session_id": str(uuid.uuid4())},
            headers=headers_probe,
            timeout=60,
        )
        if probe.status_code in (500, 502, 503, 504):
            try:
                err_body = probe.json()
                err_detail = err_body.get("detail") or err_body.get("message") or str(err_body)[:300]
            except Exception:
                err_detail = probe.text[:300] if probe.text else "(no response body)"
            return {
                "error": True,
                "message": (
                    f"❌ Langflow is returning HTTP {probe.status_code} — cannot start generation.\n\n"
                    f"Langflow error detail: {err_detail}\n\n"
                    "Common causes:\n"
                    "• The LLM API key inside Langflow is invalid or quota-exceeded\n"
                    "• A component in your flow is misconfigured\n"
                    "• Langflow ran out of memory — restart it and try again\n"
                    "• The Flow ID does not match a runnable flow"
                ),
            }
        elif probe.status_code == 404:
            return {
                "error": True,
                "message": f"❌ Flow not found (HTTP 404). Check that your Flow ID is correct: {flow_id}",
            }
        elif probe.status_code == 401:
            return {
                "error": True,
                "message": "❌ Langflow returned HTTP 401 Unauthorized. Check your API Key in the sidebar.",
            }
    except requests.exceptions.ConnectionError:
        return {
            "error": True,
            "message": f"❌ Cannot reach Langflow at {langflow_url}. Is Langflow running?",
        }
    except requests.exceptions.Timeout:
        return {
            "error": True,
            "message": "❌ Langflow health check timed out after 60s. The server may be overloaded.",
        }
    # ─────────────────────────────────────────────────────────────────────────

    all_test_cases = []
    all_titles = []
    category_titles = collections.defaultdict(list)
    batch_details = []
    batch_errors = []

    total_batches_est = (total_requested + batch_size - 1) // batch_size
    total_generated_so_far = 0
    total_batches_est = (total_requested + batch_size - 1) // batch_size
    # Safeguard against infinite loops: allow 50% extra batches for makeup
    max_allowed_batches = min(100, int(total_batches_est * 1.5) + 5)
    consecutive_failures = 0  # Circuit breaker counter

    batch_num = 1
    while total_generated_so_far < total_requested and batch_num <= max_allowed_batches:
        # Dynamically request exactly what is needed to reach the target
        current_batch = min(batch_size, total_requested - total_generated_so_far)
        
        # safely use total_generated_so_far for perfect gapless sequential ID numbering
        start_num = total_generated_so_far + 1
        end_num = start_num + current_batch - 1

        # Cycle through categories for variety
        category = TEST_CATEGORIES[(batch_num - 1) % len(TEST_CATEGORIES)]

        # Build STRICT category-aware dedup context
        dedup_context = ""
        past_titles = category_titles[category]
        if past_titles:
            # Cap at 100 to stay safely within context window token limits
            recent_titles = past_titles[-100:]
            titles_list = "\n".join(f"  - {t}" for t in recent_titles)
            dedup_context = (
                f"\n\n🚨 CRITICAL DEDUPLICATION RULE:\n"
                f"You have already generated the following {len(recent_titles)} test cases for the {category} category:\n"
                f"{titles_list}\n"
                f"\nYou MUST NOT duplicate ANY of the scenarios above. You are required to generate 100% NEW, unique, and deeply specific edge cases for {category}.\n"
            )

        # Build the batch prompt
        batch_prompt = (
            f"{user_input}\n\n"
            f"---\n"
            f"Batch {batch_num}: Generate exactly {current_batch} test cases, "
            f"numbered TC-{start_num:03d} to TC-{end_num:03d}.\n\n"
            f"🎯 FOCUS AREA: {category}\n\n"
            f"For EACH test case, use this EXACT format:\n\n"
            f"Test Case [number]:\n"
            f"ID: TC-[number]\n"
            f"Title: [unique descriptive title]\n"
            f"Description: [what this test verifies]\n"
            f"Preconditions: [setup needed]\n"
            f"Steps:\n"
            f"1. [step one]\n"
            f"2. [step two]\n"
            f"3. [step three]\n"
            f"Expected Result: [what should happen]\n"
            f"Priority: [High/Medium/Low]\n"
            f"Test Type: {category}\n\n"
            f"RULES:\n"
            f"- Generate EXACTLY {current_batch} test cases\n"
            f"- Each must be a COMPLETELY DIFFERENT scenario\n"
            f"- DO NOT create minor variations of the same test\n"
            f"{dedup_context}"
        )

        payload = {
            "input_value": batch_prompt,
            "input_type": "chat",
            "output_type": "chat",
            "session_id": str(uuid.uuid4()),
        }

        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["x-api-key"] = api_key

        output_text = ""
        langflow_err_detail = ""
        max_retries = 4
        batch_had_error = False
        rate_limit_abort = False  # Set True when Groq says to wait >5 min

        for attempt in range(1, max_retries + 1):
            server_backoff = 5 * (2 ** (attempt - 1))  # 5s, 10s, 20s, 40s
            net_backoff   = 2 * (2 ** (attempt - 1))   # 2s,  4s,  8s, 16s
            try:
                response = requests.post(run_url, json=payload, headers=headers, timeout=300)

                # ── Capture error body first for all error statuses ───────────
                if response.status_code in (429, 500, 502, 503, 504):
                    batch_had_error = True
                    try:
                        err_body = response.json()
                        langflow_err_detail = (
                            err_body.get("detail")
                            or err_body.get("message")
                            or str(err_body)[:300]
                        )
                    except Exception:
                        langflow_err_detail = response.text[:300] if response.text else ""

                # ── 429: Groq/LLM rate limit ──────────────────────────────────
                if response.status_code == 429:
                    wait_secs = parse_groq_retry_after(langflow_err_detail)
                    wait_mins = wait_secs / 60

                    if wait_secs > 300:  # more than 5 minutes — abort entire run
                        rate_limit_abort = True
                        output_text = (
                            f"[Batch {batch_num} FAILED: Groq daily token limit reached. "
                            f"Please wait {wait_mins:.0f} min {wait_secs % 60:.0f}s before retrying.]"
                        )
                        batch_errors.append(
                            f"RATE LIMIT: Groq token quota exhausted. "
                            f"Retry after {wait_mins:.0f}m {wait_secs % 60:.0f}s. "
                            f"Detail: {langflow_err_detail[:200]}"
                        )
                        break  # break out of retry loop
                    elif wait_secs > 0:
                        print(f"[Batch {batch_num}] Rate limited — waiting {wait_secs:.0f}s as instructed by Groq...")
                        time.sleep(wait_secs + 2)  # +2s safety buffer
                        continue  # retry after waiting
                    else:
                        # No wait time parsed — fall back to server backoff
                        if attempt < max_retries:
                            time.sleep(server_backoff)
                            continue
                        else:
                            batch_errors.append(f"Batch {batch_num}: HTTP 429 — {langflow_err_detail[:200]}")
                            output_text = f"[Batch {batch_num} FAILED: Rate limited — {langflow_err_detail[:200]}]"
                            break

                # ── 500/502/503/504: Server errors — exponential backoff ───────
                elif response.status_code in (500, 502, 503, 504):
                    if attempt < max_retries:
                        print(f"[Batch {batch_num}] HTTP {response.status_code} attempt {attempt} — retrying in {server_backoff}s...")
                        time.sleep(server_backoff)
                        continue
                    else:
                        batch_errors.append(f"Batch {batch_num}: HTTP {response.status_code} — {langflow_err_detail[:200]}")
                        output_text = f"[Batch {batch_num} FAILED: Langflow returned {response.status_code}: {langflow_err_detail[:200]}]"
                        break

                response.raise_for_status()
                result = response.json()

                try:
                    output_text = result["outputs"][0]["outputs"][0]["results"]["message"]["text"]
                except (KeyError, IndexError, TypeError):
                    try:
                        output_text = result["outputs"][0]["outputs"][0]["results"]["text"]["text"]
                    except (KeyError, IndexError, TypeError):
                        output_text = str(result)

                if output_text and len(output_text) > 50:
                    break  # Success

            except requests.exceptions.ConnectionError:
                batch_had_error = True
                if attempt == max_retries:
                    batch_errors.append(f"Batch {batch_num}: Connection failed")
                    output_text = f"[Batch {batch_num} FAILED: Could not connect to Langflow]"
                time.sleep(net_backoff)

            except requests.exceptions.Timeout:
                batch_had_error = True
                if attempt == max_retries:
                    batch_errors.append(f"Batch {batch_num}: Timed out")
                    output_text = f"[Batch {batch_num} FAILED: Request timed out]"
                time.sleep(net_backoff)

            except Exception as e:
                batch_had_error = True
                if attempt == max_retries:
                    batch_errors.append(f"Batch {batch_num}: {str(e)}")
                    output_text = f"[Batch {batch_num} FAILED: {str(e)}]"
                time.sleep(net_backoff)

        # ── If Groq rate limit hit: abort entire generation immediately ────────
        if rate_limit_abort:
            # Record this failed batch
            all_test_cases.append(
                f"--- Batch {batch_num}: {category.upper()} (Targeting TC-{start_num:03d} to TC-{end_num:03d}) ---\n"
                + output_text
            )
            batch_details.append({
                "batch": batch_num,
                "category": category,
                "requested": current_batch,
                "generated": 0,
                "range": "RATE LIMITED",
                "status": "error",
            })
            # Mark remaining expected batches as skipped
            for skipped in range(batch_num + 1, total_batches_est + 1):
                all_test_cases.append(
                    f"--- Batch {skipped}: SKIPPED (Groq daily limit) ---\n"
                    f"[Batch {skipped} SKIPPED: Groq token quota exhausted]"
                )
                batch_details.append({
                    "batch": skipped,
                    "category": TEST_CATEGORIES[(skipped - 1) % len(TEST_CATEGORIES)],
                    "requested": batch_size,
                    "generated": 0,
                    "range": "SKIPPED",
                    "status": "skipped",
                })
            break  # exit batch loop

        # ── Circuit breaker: abort if 3 consecutive batches all fail ──────────
        if batch_had_error:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                batch_errors.append(
                    f"ABORTED after batch {batch_num}: {consecutive_failures} consecutive failures. "
                    "Langflow appears to be down. Fix and retry."
                )
                # Record remaining expected batches as skipped
                for skipped in range(batch_num + 1, total_batches_est + 1):
                    all_test_cases.append(
                        f"--- Batch {skipped}: SKIPPED (circuit breaker triggered) ---\n"
                        f"[Batch {skipped} SKIPPED: Aborted due to consecutive failures]"
                    )
                    batch_details.append({
                        "batch": skipped,
                        "category": TEST_CATEGORIES[(skipped - 1) % len(TEST_CATEGORIES)],
                        "requested": batch_size,
                        "generated": 0,
                        "range": "SKIPPED",
                        "status": "skipped",
                    })
                break  # Exit the batch loop early
        else:
            consecutive_failures = 0  # Reset on success

        # Inter-batch cooldown: only if this batch succeeded quickly (no retries)
        if batch_num < max_allowed_batches and not batch_had_error:
            time.sleep(2)

        # ── Ghost-count fix: ONLY run numbering/counting on successful batches ─
        if batch_had_error:
            # Failed batch: record with 0 count, do NOT advance total_generated_so_far
            batch_header = (
                f"--- Batch {batch_num}: {category.upper()} "
                f"(Targeting TC-{start_num:03d} to TC-{end_num:03d}) ---"
            )
            all_test_cases.append(f"{batch_header}\n{output_text}")
            batch_details.append({
                "batch": batch_num,
                "category": category,
                "requested": current_batch,
                "generated": 0,
                "range": "FAILED",
                "status": "error",
            })
            batch_num += 1
            continue  # Next batch — start_num stays the same

        # Fix numbering only for successful output
        output_text = fix_numbering(output_text, start_num)

        # Extract titles for dedup
        batch_titles = extract_titles(output_text)
        all_titles.extend(batch_titles)
        category_titles[category].extend(batch_titles)

        # Count actual test cases — only for successful batches
        actual_count = count_test_cases_in_output(output_text)
        actual_count = min(actual_count, current_batch)  # Don't over-count
        total_generated_so_far += actual_count

        batch_header = (
            f"--- Batch {batch_num}: {category.upper()} "
            f"(Targeting TC-{start_num:03d} to TC-{end_num:03d}) ---"
        )
        all_test_cases.append(f"{batch_header}\n{output_text}")

        batch_details.append({
            "batch": batch_num,
            "category": category,
            "requested": current_batch,
            "generated": actual_count,
            "range": f"TC-{start_num:03d} to TC-{(start_num + actual_count - 1):03d}",
            "status": "warning" if actual_count < current_batch else "success",
        })
        batch_num += 1

    # Combine all batches
    combined = "\n\n".join(all_test_cases)
    # Total batches run is one less than batch_num if it gracefully finished or broke out
    total_batches_run = batch_num - 1

    response_data = {
        "response": combined,
        "total_requested": total_requested,
        "total_generated": total_generated_so_far,
        "batches": total_batches_run,
        "unique_titles_tracked": len(set(t.lower() for t in all_titles)),
        "batch_details": batch_details,
        "error": False,
    }

    # If some batches failed, include warnings but still return results
    if batch_errors:
        response_data["warnings"] = batch_errors
        response_data["message"] = f"⚠️ {len(batch_errors)} batch(es) had issues but {total_batches_run - len(batch_errors)} succeeded."

    # ── Auto-save to saved_test_cases/ ───────────────────────────────────
    if total_generated_so_far > 0:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"test_cases_{total_generated_so_far}_{ts}"

        # Save raw TXT
        txt_path = os.path.join(SAVE_DIR, f"{base_name}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(combined)

        # Save JSON metadata (for reloading in UI)
        meta = {
            "filename": base_name,
            "generated_at": datetime.now().isoformat(),
            "total_generated": total_generated_so_far,
            "total_requested": total_requested,
            "batches": total_batches_run,
            "unique_titles_tracked": response_data["unique_titles_tracked"],
            "batch_details": batch_details,
            "has_warnings": bool(batch_errors),
            "txt_file": f"{base_name}.txt",
            "md_file": f"{base_name}.md",
        }
        json_path = os.path.join(SAVE_DIR, f"{base_name}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        # ── Parse and Save as Structured Markdown `.md` ───────────────────────
        try:
            parsed_cases = parse_test_cases(combined)
            structured_md = format_as_markdown(parsed_cases, user_input)
            md_path = os.path.join(SAVE_DIR, f"{base_name}.md")
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(structured_md)
            print(f"[Auto-save] Saved structured markdown → {md_path}")
            response_data["saved_md"] = f"{base_name}.md"
        except Exception as e:
            print(f"Warning: Failed to generate structured markdown: {e}")

        response_data["saved_txt"] = f"{base_name}.txt"
        print(f"[Auto-save] Saved {total_generated_so_far} test cases raw txt → {txt_path}")
    # ────────────────────────────────────────────────────────────────

    return response_data


# ───────────────────────────────────────────────────────────────────
@app.get("/saved-files")
def list_saved_files():
    """Return metadata for all saved test case runs, newest first."""
    entries = []
    for fname in sorted(os.listdir(SAVE_DIR), reverse=True):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(SAVE_DIR, fname), "r", encoding="utf-8") as f:
                meta = json.load(f)
            entries.append(meta)
        except Exception:
            pass
    return {"files": entries}


@app.get("/saved-files/{filename}")
def load_saved_file(filename: str):
    """Load the raw text of a saved test case file."""
    # Security: only allow files inside SAVE_DIR
    safe_name = os.path.basename(filename)
    path = os.path.join(SAVE_DIR, safe_name)
    if not os.path.exists(path):
        return {"error": True, "message": f"File not found: {safe_name}"}
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        # Load matching metadata if available
        json_path = path.replace(".txt", ".json")
        meta = {}
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        return {
            "response": content,
            "filename": safe_name,
            "total_generated": meta.get("total_generated", "?"),
            "generated_at": meta.get("generated_at", ""),
            "batch_details": meta.get("batch_details", []),
            "error": False,
        }
    except Exception as e:
        return {"error": True, "message": str(e)}