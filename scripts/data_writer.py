"""
Validated writer for LearnKit data files.
All structured writes go through this script — never written directly by the agent.

Usage: python data_writer.py <subcommand> [args]
Output: JSON to stdout — {"success": true/false, ...}

Subcommands:
  progress quiz     Write quiz result to progress.json
  progress study    Increment study_sessions in progress.json
  progress ingest   Increment materials_ingested in progress.json
  deadline add      Append entry to global_deadlines.json
  deadline complete Mark deadline completed in global_deadlines.json
  manifest add      Append entry to materials_manifest.json
  index update      Recalculate units_completed + next_deadline in courses_index.json
  log entry         Append one-liner to activity_log.md(s)
"""
import argparse
import json
import pathlib
import sys
from datetime import datetime, date

VALID_DEADLINE_TYPES = {"exam", "quiz", "assignment", "lab", "lab_practical", "presentation", "other"}
VALID_CONFIDENCE = {"high", "medium", "low", "user_assigned"}
VALID_INGEST_METHODS = {"raw_folder", "path_paste"}
VALID_UNIT_SPECIAL = {"unclassified", "multi_unit", "syllabus"}
STATUS_PROGRESSION = ["not_started", "in_progress", "materials_complete", "quiz_passed", "mastered"]
PASSING_SCORE = 70.0


# ── helpers ──────────────────────────────────────────────────────────────────

def out(payload: dict):
    print(json.dumps(payload, ensure_ascii=False))
    sys.exit(0)


def fail(msg: str):
    out({"success": False, "error": msg})


def load_json(path: pathlib.Path, default: dict) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as e:
            raise ValueError(f"Failed to parse {path.name}: {e}")
    return default


def save_json(path: pathlib.Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def today_str() -> str:
    return date.today().isoformat()


def progress_path(savedata: pathlib.Path, course: str) -> pathlib.Path:
    return savedata / "courses" / course / "data" / "progress.json"


def progress_default(course: str) -> dict:
    return {"course": None, "course_id": course, "last_updated": None,
            "weak_areas_global": [], "units": {}}


def unit_default() -> dict:
    return {"status": "not_started", "materials_ingested": 0, "study_sessions": 0,
            "quiz_history": [], "weak_areas": [], "confidence_level": 0}


def advance_status(current: str, target: str) -> str:
    try:
        ci = STATUS_PROGRESSION.index(current)
        ti = STATUS_PROGRESSION.index(target)
        return STATUS_PROGRESSION[max(ci, ti)]
    except ValueError:
        return target


# ── progress quiz ─────────────────────────────────────────────────────────────

def cmd_progress_quiz(args):
    savedata = pathlib.Path(args.savedata)
    path = progress_path(savedata, args.course)
    data = load_json(path, progress_default(args.course))
    data.setdefault("units", {})

    unit = data["units"].setdefault(args.unit, unit_default())

    weak_topics = [t.strip() for t in args.weak_topics.split(",")] if args.weak_topics else []
    qta = {}
    if args.mcq:
        qta["mcq"] = args.mcq
    if args.sa:
        qta["short_answer"] = args.sa

    quiz_id = f"quiz_{args.unit[:6]}_{len(unit['quiz_history']) + 1}_{date.today().strftime('%Y%m%d')}"
    entry = {
        "quiz_id": quiz_id,
        "date": today_str(),
        "score_pct": round(float(args.score_pct), 1),
        "total_questions": int(args.total),
        "correct": int(args.correct),
        "incorrect": int(args.incorrect),
        "skipped": int(args.skipped),
        "partial": bool(args.partial),
        "adaptive_used": bool(args.adaptive),
        "weak_topics": weak_topics,
        "question_type_accuracy": qta,
    }
    unit["quiz_history"].append(entry)
    unit["weak_areas"] = weak_topics

    if float(args.score_pct) >= PASSING_SCORE:
        unit["status"] = advance_status(unit["status"], "quiz_passed")

    # update global weak areas
    all_weak = set(data.get("weak_areas_global", []))
    all_weak.update(weak_topics)
    data["weak_areas_global"] = sorted(all_weak)
    data["last_updated"] = now_iso()

    save_json(path, data)
    out({"success": True, "quiz_id": quiz_id, "status": unit["status"]})


# ── progress study ────────────────────────────────────────────────────────────

def cmd_progress_study(args):
    savedata = pathlib.Path(args.savedata)
    path = progress_path(savedata, args.course)
    data = load_json(path, progress_default(args.course))
    data.setdefault("units", {})

    unit = data["units"].setdefault(args.unit, unit_default())
    unit["study_sessions"] = unit.get("study_sessions", 0) + 1
    if unit["status"] == "not_started":
        unit["status"] = "in_progress"
    data["last_updated"] = now_iso()

    save_json(path, data)
    out({"success": True, "study_sessions": unit["study_sessions"]})


# ── progress ingest ───────────────────────────────────────────────────────────

def cmd_progress_ingest(args):
    savedata = pathlib.Path(args.savedata)
    path = progress_path(savedata, args.course)
    data = load_json(path, progress_default(args.course))
    data.setdefault("units", {})

    unit = data["units"].setdefault(args.unit, unit_default())
    unit["materials_ingested"] = unit.get("materials_ingested", 0) + 1
    if unit["status"] == "not_started":
        unit["status"] = "in_progress"
    data["last_updated"] = now_iso()

    save_json(path, data)
    out({"success": True, "materials_ingested": unit["materials_ingested"]})


# ── deadline add ──────────────────────────────────────────────────────────────

def cmd_deadline_add(args):
    if args.type not in VALID_DEADLINE_TYPES:
        fail(f"invalid type: {args.type!r}. Valid: {sorted(VALID_DEADLINE_TYPES)}")

    savedata = pathlib.Path(args.savedata)
    path = savedata / "data" / "global_deadlines.json"
    data = load_json(path, {"last_updated": None, "deadlines": []})

    # generate next id
    prefix = f"dl_{args.course_id}_"
    existing = [d["id"] for d in data["deadlines"] if d["id"].startswith(prefix)]
    nums = []
    for eid in existing:
        try:
            nums.append(int(eid.replace(prefix, "")))
        except ValueError:
            pass
    next_num = (max(nums) + 1) if nums else 1
    new_id = f"{prefix}{next_num:03d}"

    entry = {
        "id": new_id,
        "course_id": args.course_id,
        "course_code": args.course_code,
        "type": args.type,
        "title": args.title,
        "date": args.date,
        "time": args.time or None,
        "location": args.location or None,
        "details": args.details or None,
        "source_date": today_str(),
        "completed": False,
    }
    data["deadlines"].append(entry)
    data["last_updated"] = now_iso()

    save_json(path, data)
    out({"success": True, "id": new_id})


# ── deadline complete ─────────────────────────────────────────────────────────

def cmd_deadline_complete(args):
    savedata = pathlib.Path(args.savedata)
    path = savedata / "data" / "global_deadlines.json"
    data = load_json(path, {"last_updated": None, "deadlines": []})

    for d in data["deadlines"]:
        if d["id"] == args.deadline_id:
            d["completed"] = True
            data["last_updated"] = now_iso()
            save_json(path, data)
            out({"success": True, "id": args.deadline_id})
    fail(f"deadline id not found: {args.deadline_id!r}")


# ── manifest add ──────────────────────────────────────────────────────────────

def cmd_manifest_add(args):
    if args.confidence not in VALID_CONFIDENCE:
        fail(f"invalid confidence: {args.confidence!r}. Valid: {sorted(VALID_CONFIDENCE)}")
    if args.method not in VALID_INGEST_METHODS:
        fail(f"invalid method: {args.method!r}. Valid: {sorted(VALID_INGEST_METHODS)}")

    savedata = pathlib.Path(args.savedata)
    path = savedata / "data" / "materials_manifest.json"
    data = load_json(path, {"last_updated": None, "total_files": 0, "files": []})

    prefix = f"mat_{args.course_id}_"
    existing = [f["manifest_id"] for f in data["files"] if f["manifest_id"].startswith(prefix)]
    nums = []
    for eid in existing:
        try:
            nums.append(int(eid.replace(prefix, "")))
        except ValueError:
            pass
    next_num = (max(nums) + 1) if nums else 1
    new_id = f"{prefix}{next_num:03d}"

    entry = {
        "manifest_id": new_id,
        "course_id": args.course_id,
        "course_code": args.course_code,
        "original_filename": args.filename,
        "ingestion_method": args.method,
        "original_path": args.original_path or None,
        "ingestion_date": now_iso(),
        "file_type": args.file_type,
        "unit_assigned": args.unit,
        "confidence": args.confidence,
        "filed_path": args.filed_path,
        "summary_path": args.summary_path,
        "page_count": int(args.page_count),
        "word_count": int(args.word_count),
        "summary_generated": True,
    }
    data["files"].append(entry)
    data["total_files"] = len(data["files"])
    data["last_updated"] = now_iso()

    save_json(path, data)
    out({"success": True, "manifest_id": new_id})


# ── index update ──────────────────────────────────────────────────────────────

def cmd_index_update(args):
    savedata = pathlib.Path(args.savedata)
    index_path = savedata / "data" / "courses_index.json"
    data = load_json(index_path, {"last_updated": None, "active_courses": [], "archived_courses": []})

    course_entry = next((c for c in data["active_courses"] if c["course_id"] == args.course), None)
    if not course_entry:
        fail(f"course not found in active_courses: {args.course!r}")

    # count completed units from progress.json
    prog_path = progress_path(savedata, args.course)
    prog = load_json(prog_path, progress_default(args.course))
    completed_statuses = {"quiz_passed", "mastered"}
    units_completed = sum(1 for u in prog.get("units", {}).values()
                          if u.get("status") in completed_statuses)
    course_entry["units_completed"] = units_completed

    # find next deadline
    dl_path = savedata / "data" / "global_deadlines.json"
    dl_data = load_json(dl_path, {"last_updated": None, "deadlines": []})
    future = [d for d in dl_data["deadlines"]
              if d["course_id"] == args.course and not d.get("completed")]
    future.sort(key=lambda d: d["date"])
    if future:
        course_entry["next_deadline_date"] = future[0]["date"]
        course_entry["next_deadline_title"] = future[0]["title"]
    else:
        course_entry["next_deadline_date"] = None
        course_entry["next_deadline_title"] = None

    data["last_updated"] = now_iso()
    save_json(index_path, data)
    out({"success": True, "units_completed": units_completed})


# ── log entry ─────────────────────────────────────────────────────────────────

def _append_log(log_path: pathlib.Path, entry: str):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    today = date.today()
    heading = f"## {today.strftime('%Y-%m-%d')} ({today.strftime('%A')})"

    if log_path.exists():
        content = log_path.read_text(encoding="utf-8-sig")
    else:
        content = ""

    if heading in content:
        # insert after heading line
        lines = content.splitlines(keepends=True)
        out_lines = []
        inserted = False
        for line in lines:
            out_lines.append(line)
            if not inserted and line.strip() == heading:
                out_lines.append(entry + "\n")
                inserted = True
        content = "".join(out_lines)
    else:
        # find insertion point: after file header (lines starting with #, **, <!-- until first ---)
        lines = content.splitlines(keepends=True)
        insert_at = 0
        for i, line in enumerate(lines):
            if line.strip() == "---":
                insert_at = i + 1
                break
        block = f"\n{heading}\n{entry}\n"
        lines.insert(insert_at, block)
        content = "".join(lines)

    log_path.write_text(content, encoding="utf-8")


def cmd_log_entry(args):
    savedata = pathlib.Path(args.savedata)
    global_log = savedata / "data" / "activity_log.md"
    _append_log(global_log, args.entry)

    if args.course:
        course_log = savedata / "courses" / args.course / "activity_log.md"
        _append_log(course_log, args.entry)

    out({"success": True})


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(prog="data_writer")
    sub = parser.add_subparsers(dest="group")

    # progress
    pg = sub.add_parser("progress")
    pg_sub = pg.add_subparsers(dest="action")

    pq = pg_sub.add_parser("quiz")
    pq.add_argument("--savedata", required=True)
    pq.add_argument("--course", required=True)
    pq.add_argument("--unit", required=True)
    pq.add_argument("--score-pct", required=True, type=float)
    pq.add_argument("--correct", required=True, type=int)
    pq.add_argument("--total", required=True, type=int)
    pq.add_argument("--incorrect", required=True, type=int)
    pq.add_argument("--skipped", default=0, type=int)
    pq.add_argument("--partial", action="store_true")
    pq.add_argument("--adaptive", action="store_true")
    pq.add_argument("--weak-topics", default="")
    pq.add_argument("--mcq", default="")
    pq.add_argument("--sa", default="")

    ps = pg_sub.add_parser("study")
    ps.add_argument("--savedata", required=True)
    ps.add_argument("--course", required=True)
    ps.add_argument("--unit", required=True)

    pi = pg_sub.add_parser("ingest")
    pi.add_argument("--savedata", required=True)
    pi.add_argument("--course", required=True)
    pi.add_argument("--unit", required=True)

    # deadline
    dg = sub.add_parser("deadline")
    dg_sub = dg.add_subparsers(dest="action")

    da = dg_sub.add_parser("add")
    da.add_argument("--savedata", required=True)
    da.add_argument("--course-id", required=True)
    da.add_argument("--course-code", required=True)
    da.add_argument("--type", required=True, dest="type")
    da.add_argument("--title", required=True)
    da.add_argument("--date", required=True)
    da.add_argument("--time", default="")
    da.add_argument("--location", default="")
    da.add_argument("--details", default="")

    dc = dg_sub.add_parser("complete")
    dc.add_argument("--savedata", required=True)
    dc.add_argument("--deadline-id", required=True)

    # manifest
    mg = sub.add_parser("manifest")
    mg_sub = mg.add_subparsers(dest="action")

    ma = mg_sub.add_parser("add")
    ma.add_argument("--savedata", required=True)
    ma.add_argument("--course-id", required=True)
    ma.add_argument("--course-code", required=True)
    ma.add_argument("--filename", required=True)
    ma.add_argument("--method", required=True)
    ma.add_argument("--original-path", default="")
    ma.add_argument("--file-type", required=True)
    ma.add_argument("--unit", required=True)
    ma.add_argument("--confidence", required=True)
    ma.add_argument("--filed-path", required=True)
    ma.add_argument("--summary-path", required=True)
    ma.add_argument("--page-count", default=0, type=int)
    ma.add_argument("--word-count", default=0, type=int)

    # index
    ig = sub.add_parser("index")
    ig_sub = ig.add_subparsers(dest="action")

    iu = ig_sub.add_parser("update")
    iu.add_argument("--savedata", required=True)
    iu.add_argument("--course", required=True)

    # log
    lg = sub.add_parser("log")
    lg_sub = lg.add_subparsers(dest="action")

    le = lg_sub.add_parser("entry")
    le.add_argument("--savedata", required=True)
    le.add_argument("--entry", required=True)
    le.add_argument("--course", default="")

    args = parser.parse_args()

    try:
        if args.group == "progress":
            if args.action == "quiz":
                cmd_progress_quiz(args)
            elif args.action == "study":
                cmd_progress_study(args)
            elif args.action == "ingest":
                cmd_progress_ingest(args)
        elif args.group == "deadline":
            if args.action == "add":
                cmd_deadline_add(args)
            elif args.action == "complete":
                cmd_deadline_complete(args)
        elif args.group == "manifest":
            if args.action == "add":
                cmd_manifest_add(args)
        elif args.group == "index":
            if args.action == "update":
                cmd_index_update(args)
        elif args.group == "log":
            if args.action == "entry":
                cmd_log_entry(args)
        else:
            fail(f"unknown subcommand: {args.group} {getattr(args, 'action', '')}")
    except Exception as e:
        fail(str(e))


if __name__ == "__main__":
    main()
