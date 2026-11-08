import os
import re
import json
import csv
import zipfile
from datetime import datetime
from html.parser import HTMLParser
from database import insert_interactions_batch, get_total_interactions_count

class SimpleHTMLTextExtractor(HTMLParser):
    """Extracts text content and conversation structure from HTML exports."""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.in_script_or_style = False

    def handle_starttag(self, tag, attrs):
        if tag in ["script", "style"]:
            self.in_script_or_style = True
        elif tag in ["p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4"]:
            self.text_parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ["script", "style"]:
            self.in_script_or_style = False
        elif tag in ["p", "div", "li", "tr"]:
            self.text_parts.append("\n")

    def handle_data(self, data):
        if not self.in_script_or_style:
            self.text_parts.append(data)

    def get_text(self) -> str:
        return "".join(self.text_parts)

def _parse_timestamp(val) -> str:
    """Standardizes timestamp strings into 'YYYY-MM-DD HH:MM:SS'."""
    if not val:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    val_str = str(val).strip()
    # Try ISO format
    try:
        dt = datetime.fromisoformat(val_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    # If already matches standard format or short
    if len(val_str) >= 19 and val_str[10] in [" ", "T"]:
        return val_str[:19].replace("T", " ")
    return val_str

def parse_json_data(data) -> list[tuple[str, str, str]]:
    """
    Parses conversation turns from various JSON structures:
    - Google Takeout chats.json
    - Google AI Studio export
    - Standard list of {user_input, response, timestamp}
    - Role-based lists [{role: user, ...}, {role: model, ...}]
    - ChatGPT / generic conversation trees
    """
    results = []

    def extract_text(part):
        if isinstance(part, str):
            return part
        if isinstance(part, dict):
            return part.get("text", "") or part.get("content", "") or str(part)
        if isinstance(part, list):
            return " ".join([extract_text(p) for p in part])
        return str(part)

    # 1. Direct list of records
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue

            # Case A: {"user_input": "...", "response": "...", "timestamp": "..."}
            user_keys = ["user_input", "user", "prompt", "query", "question", "input"]
            resp_keys = ["response", "answer", "model", "gemini", "assistant", "output", "reply"]
            time_keys = ["timestamp", "create_time", "created_at", "date", "time"]

            u_key = next((k for k in user_keys if k in item and item[k]), None)
            r_key = next((k for k in resp_keys if k in item and item[k]), None)
            t_key = next((k for k in time_keys if k in item and item[k]), None)

            if u_key and r_key:
                ts = _parse_timestamp(item.get(t_key, ""))
                results.append((ts, extract_text(item[u_key]), extract_text(item[r_key])))
                continue

            # Case B: Google Takeout Gemini format with "events" or "messages"
            # e.g. {"title": "...", "create_time": "...", "events": [{"prompt": "...", "response": "..."}]}
            events = item.get("events") or item.get("conversation") or item.get("turns")
            if isinstance(events, list):
                for ev in events:
                    if isinstance(ev, dict):
                        p = ev.get("prompt") or ev.get("user") or ev.get("user_input")
                        r = ev.get("response") or ev.get("gemini") or ev.get("model") or ev.get("answer")
                        ev_ts = _parse_timestamp(ev.get("timestamp") or item.get("create_time"))
                        if p and r:
                            results.append((ev_ts, extract_text(p), extract_text(r)))
                continue

            # Case C: Google Takeout / AI Studio with "messages" array
            messages = item.get("messages") or item.get("parts")
            if isinstance(messages, list):
                curr_user = ""
                curr_ts = _parse_timestamp(item.get("create_time") or item.get("timestamp"))
                for msg in messages:
                    if isinstance(msg, dict):
                        author = (msg.get("author") or msg.get("role") or msg.get("sender") or "").lower()
                        text = extract_text(msg.get("content") or msg.get("text") or msg.get("parts") or "")
                        if "user" in author or author == "human":
                            curr_user = text
                        elif ("gemini" in author or "model" in author or "assistant" in author or "bard" in author) and curr_user:
                            results.append((curr_ts, curr_user, text))
                            curr_user = ""
                continue

    # 2. Dict container (e.g. {"conversations": [...]}, {"chats": [...]}, {"messages": [...]})
    elif isinstance(data, dict):
        for container_key in ["conversations", "chats", "events", "items", "history", "prompts"]:
            if container_key in data and isinstance(data[container_key], list):
                sub_results = parse_json_data(data[container_key])
                if sub_results:
                    return sub_results

        # If it's a single chat with "messages"
        if "messages" in data and isinstance(data["messages"], list):
            curr_user = ""
            for msg in data["messages"]:
                if isinstance(msg, dict):
                    author = (msg.get("author") or msg.get("role") or "").lower()
                    text = extract_text(msg.get("content") or msg.get("parts") or msg.get("text") or "")
                    if "user" in author or author == "human":
                        curr_user = text
                    elif ("gemini" in author or "model" in author or "assistant" in author or "bard" in author) and curr_user:
                        results.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), curr_user, text))
                        curr_user = ""

    return results

def parse_text_transcript(text: str) -> list[tuple[str, str, str]]:
    """
    Parses conversational plain text or markdown transcripts.
    Recognizes patterns like:
    User: <question>
    Gemini: <answer>
    """
    results = []
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Pattern for User / Gemini pairs
    pattern = re.compile(
        r"(?:^|\n)\s*(?:###\s*)?(?:User|Human|Prompt|You):\s*(.*?)\n\s*(?:###\s*)?(?:Gemini|Aurvyn|Assistant|Model|Bard):\s*(.*?)(?=\n\s*(?:###\s*)?(?:User|Human|Prompt|You):|\Z)",
        re.DOTALL | re.IGNORECASE
    )

    for match in pattern.finditer(text):
        user_q = match.group(1).strip()
        resp_a = match.group(2).strip()
        if user_q and resp_a:
            results.append((current_time, user_q, resp_a))

    return results

def parse_csv_file(file_path: str) -> list[tuple[str, str, str]]:
    """Parses conversations from CSV files with header auto-detection."""
    results = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return results

        # Find best matching columns
        field_map = {fn.strip().lower(): fn for fn in reader.fieldnames}
        user_keys = ["user_input", "user", "prompt", "query", "question", "input"]
        resp_keys = ["response", "answer", "model", "gemini", "assistant", "output", "reply"]
        time_keys = ["timestamp", "create_time", "created_at", "date", "time"]

        u_col = next((field_map[k] for k in user_keys if k in field_map), None)
        r_col = next((field_map[k] for k in resp_keys if k in field_map), None)
        t_col = next((field_map[k] for k in time_keys if k in field_map), None)

        if not u_col or not r_col:
            # Fall back to first 2 columns if columns are not recognized
            if len(reader.fieldnames) >= 2:
                u_col = reader.fieldnames[0]
                r_col = reader.fieldnames[1]
                t_col = reader.fieldnames[2] if len(reader.fieldnames) >= 3 else None

        for row in reader:
            u_text = (row.get(u_col) or "").strip()
            r_text = (row.get(r_col) or "").strip()
            ts_text = _parse_timestamp(row.get(t_col)) if t_col else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if u_text and r_text:
                results.append((ts_text, u_text, r_text))

    return results

def parse_html_content(html_str: str) -> list[tuple[str, str, str]]:
    """Extracts conversation exchanges from Google Takeout MyActivity.html or chat HTML exports."""
    parser = SimpleHTMLTextExtractor()
    parser.feed(html_str)
    raw_text = parser.get_text()

    # Try standard transcript parse first
    turns = parse_text_transcript(raw_text)
    if turns:
        return turns

    # Fallback: Google Activity format ("Prompted <query>", "Gemini responded <answer>")
    results = []
    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    blocks = re.findall(r"Prompted\s+(.*?)\s+(?:Gemini|Bard)?\s*Answered\s+(.*?)(?=Prompted|\Z)", raw_text, re.DOTALL | re.IGNORECASE)
    for q, a in blocks:
        q_clean = q.strip()
        a_clean = a.strip()
        if q_clean and a_clean:
            results.append((now_ts, q_clean, a_clean))

    return results

def import_gemini_file(file_path: str) -> dict:
    """
    Imports Gemini conversation history from any supported file format:
    - ZIP (Google Takeout archive)
    - JSON (Google Takeout chats, Google AI Studio, Open-WebUI, or custom)
    - CSV (User / Gemini exchange spreadsheet)
    - HTML (Google Takeout activity log)
    - TXT / MD (Plain text or markdown transcripts)

    Inserts parsed conversations into aurvyn_memory.db and skips duplicates.
    Returns:
        dict: {"success": bool, "imported": int, "total_parsed": int, "message": str}
    """
    if not os.path.exists(file_path):
        return {"success": False, "imported": 0, "total_parsed": 0, "message": f"File not found: {file_path}"}

    parsed_turns = []
    ext = os.path.splitext(file_path)[1].lower()

    try:
        # 1. ZIP File (Google Takeout Archive)
        if ext == ".zip":
            with zipfile.ZipFile(file_path, "r") as z:
                for file_info in z.infolist():
                    fname = file_info.filename.lower()
                    if file_info.is_dir() or fname.startswith("__macosx"):
                        continue
                    if fname.endswith(".json"):
                        try:
                            with z.open(file_info) as f:
                                j_data = json.load(f)
                                parsed_turns.extend(parse_json_data(j_data))
                        except Exception:
                            pass
                    elif fname.endswith(".html") or fname.endswith(".htm"):
                        try:
                            with z.open(file_info) as f:
                                html_text = f.read().decode("utf-8", errors="replace")
                                parsed_turns.extend(parse_html_content(html_text))
                        except Exception:
                            pass
                    elif fname.endswith(".csv"):
                        try:
                            import io
                            with z.open(file_info) as f:
                                csv_text = io.TextIOWrapper(f, encoding="utf-8", errors="replace")
                                reader = csv.DictReader(csv_text)
                                for row in reader:
                                    vals = list(row.values())
                                    if len(vals) >= 2 and vals[0] and vals[1]:
                                        parsed_turns.append((datetime.now().strftime("%Y-%m-%d %H:%M:%S"), str(vals[0]), str(vals[1])))
                        except Exception:
                            pass

        # 2. JSON File
        elif ext == ".json":
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                j_data = json.load(f)
                parsed_turns.extend(parse_json_data(j_data))

        # 3. CSV File
        elif ext == ".csv":
            parsed_turns.extend(parse_csv_file(file_path))

        # 4. HTML File
        elif ext in [".html", ".htm"]:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                parsed_turns.extend(parse_html_content(f.read()))

        # 5. TXT / Markdown File
        elif ext in [".txt", ".md", ".log"]:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                parsed_turns.extend(parse_text_transcript(f.read()))

        else:
            # Attempt JSON first, then text
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    parsed_turns.extend(parse_json_data(json.load(f)))
            except Exception:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    parsed_turns.extend(parse_text_transcript(f.read()))

    except Exception as e:
        return {"success": False, "imported": 0, "total_parsed": 0, "message": f"Error parsing export file: {e}"}

    total_parsed = len(parsed_turns)
    if total_parsed == 0:
        return {
            "success": False,
            "imported": 0,
            "total_parsed": 0,
            "message": "No conversation turns could be identified in the file. Ensure the file contains User and Gemini exchanges."
        }

    # Batch insert into database
    imported_count = insert_interactions_batch(parsed_turns)
    duplicates_skipped = total_parsed - imported_count

    msg = f"Successfully imported {imported_count} new interaction(s) into Aurvyn AI memory."
    if duplicates_skipped > 0:
        msg += f" ({duplicates_skipped} duplicate entries were skipped)."

    return {
        "success": True,
        "imported": imported_count,
        "total_parsed": total_parsed,
        "duplicates_skipped": duplicates_skipped,
        "message": msg
    }

def import_gemini_path(path: str) -> dict:
    """
    Imports Gemini conversation history from a file or folder.
    If given a directory, traverses and processes all supported export files.
    """
    if not os.path.exists(path):
        return {"success": False, "imported": 0, "total_parsed": 0, "message": f"Path does not exist: {path}"}

    if os.path.isfile(path):
        return import_gemini_file(path)

    # Process directory
    total_imp = 0
    total_prs = 0
    total_dup = 0
    files_processed = 0

    valid_exts = {".json", ".csv", ".html", ".htm", ".txt", ".md", ".zip"}
    for root, _, files in os.walk(path):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in valid_exts:
                fpath = os.path.join(root, f)
                res = import_gemini_file(fpath)
                if res.get("total_parsed", 0) > 0:
                    total_imp += res.get("imported", 0)
                    total_prs += res.get("total_parsed", 0)
                    total_dup += res.get("duplicates_skipped", 0)
                    files_processed += 1

    if files_processed == 0:
        return {
            "success": False,
            "imported": 0,
            "total_parsed": 0,
            "message": f"No supported export files found in folder '{path}'."
        }

    return {
        "success": True,
        "imported": total_imp,
        "total_parsed": total_prs,
        "duplicates_skipped": total_dup,
        "message": f"Processed {files_processed} export file(s): successfully imported {total_imp} new interaction(s) into Aurvyn AI memory ({total_dup} duplicates skipped)."
    }

