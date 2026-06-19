"""
Validated writer for LearnKit data files.
All structured writes go through this script — never written directly by the agent.

Usage: python data_writer.py <subcommand> [args]
Output: JSON to stdout — {"success": true/false, ...}

Subcommands:
  pool add          Append problems (JSON array on stdin) to problem_pool.json
  pool remove       Delete a problem from problem_pool.json
  image add         Append image records (JSON array on stdin) to image_bank.json
  image remove      Delete an image record from image_bank.json
  deadline add      Append entry to global_deadlines.json
  deadline complete Mark deadline completed in global_deadlines.json
  notes write       Write study notes file from stdin
  log entry         Append one-liner to activity_log.md(s)
"""
import argparse
import json
import pathlib
import sys
from datetime import datetime, date

VALID_DEADLINE_TYPES = {"exam", "quiz", "assignment", "lab", "lab_practical", "presentation", "other"}
VALID_QUESTION_TYPES = {"mcq", "short_answer", "matching", "labeling", "true_false", "essay"}


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


def pool_path(savedata: pathlib.Path, course: str) -> pathlib.Path:
    return savedata / "courses" / course / "data" / "problem_pool.json"


def pool_default(course: str) -> dict:
    return {"course": None, "course_id": course, "last_updated": None, "problems": []}


def image_bank_path(savedata: pathlib.Path, course: str) -> pathlib.Path:
    return savedata / "courses" / course / "data" / "image_bank.json"


def image_bank_default(course: str) -> dict:
    return {"course": None, "course_id": course, "last_updated": None, "images": []}


def _normalize_q(text: str) -> str:
    return " ".join((text or "").lower().split())


def _norm_figure(fig):
    """Normalize a problem's optional figure. Returns None unless a dict with a
    non-empty image_path is given (so bad/empty figures degrade to text-only)."""
    if not isinstance(fig, dict):
        return None
    ip = fig.get("image_path")
    if not ip:
        return None
    return {
        "image_path": ip,
        "bbox": fig.get("bbox"),       # normalized [x,y,w,h] display crop, or null
        "caption": fig.get("caption"),
    }


# ── pool add ──────────────────────────────────────────────────────────────────

def cmd_pool_add(args):
    savedata = pathlib.Path(args.savedata)
    path = pool_path(savedata, args.course)
    data = load_json(path, pool_default(args.course))
    data.setdefault("problems", [])

    raw = sys.stdin.buffer.read().decode("utf-8-sig").strip()
    if not raw:
        fail("no input on stdin (expected JSON array of problems)")
    try:
        incoming = json.loads(raw)
    except Exception as e:
        fail(f"invalid JSON on stdin: {e}")
    if not isinstance(incoming, list):
        fail("stdin JSON must be an array of problem objects")

    existing_norm = {_normalize_q(p.get("question", "")) for p in data["problems"]}
    prefix = f"prob_{args.course}_"
    maxnum = 0
    for p in data["problems"]:
        pid = p.get("problem_id", "")
        if pid.startswith(prefix):
            try:
                maxnum = max(maxnum, int(pid[len(prefix):]))
            except ValueError:
                pass

    added_ids = []
    skipped = 0
    for prob in incoming:
        if not isinstance(prob, dict):
            fail("each problem must be a JSON object")
        q = (prob.get("question") or "").strip()
        qtype = prob.get("question_type")
        if not q:
            fail("problem missing 'question'")
        if qtype not in VALID_QUESTION_TYPES:
            fail(f"invalid question_type: {qtype!r}. Valid: {sorted(VALID_QUESTION_TYPES)}")
        norm = _normalize_q(q)
        if norm in existing_norm:
            skipped += 1
            continue
        existing_norm.add(norm)
        maxnum += 1
        pid = f"{prefix}{maxnum:03d}"
        data["problems"].append({
            "problem_id": pid,
            "unit_id": prob.get("unit_id"),
            "unit_slug": prob.get("unit_slug"),
            "topic": prob.get("topic"),
            "question_type": qtype,
            "question": q,
            "options": prob.get("options") or [],
            "answer": prob.get("answer"),
            "rationale": prob.get("rationale"),
            "tags": prob.get("tags") or [],
            "source": prob.get("source"),
            "source_file": prob.get("source_file") or "manual",
            "source_type": prob.get("source_type") or "manual",
            "verbatim": bool(prob.get("verbatim", False)),
            "figure": _norm_figure(prob.get("figure")),
            "date_added": today_str(),
        })
        added_ids.append(pid)

    data["last_updated"] = now_iso()
    save_json(path, data)
    out({"success": True, "added": len(added_ids), "skipped": skipped, "ids": added_ids})


# ── pool remove ───────────────────────────────────────────────────────────────

def cmd_pool_remove(args):
    savedata = pathlib.Path(args.savedata)
    path = pool_path(savedata, args.course)
    data = load_json(path, pool_default(args.course))
    data.setdefault("problems", [])

    before = len(data["problems"])
    data["problems"] = [p for p in data["problems"]
                        if p.get("problem_id") != args.problem_id]
    if len(data["problems"]) == before:
        fail(f"problem id not found: {args.problem_id!r}")
    data["last_updated"] = now_iso()
    save_json(path, data)
    out({"success": True, "removed": args.problem_id})


# ── image add ─────────────────────────────────────────────────────────────────

def cmd_image_add(args):
    savedata = pathlib.Path(args.savedata)
    path = image_bank_path(savedata, args.course)
    data = load_json(path, image_bank_default(args.course))
    data.setdefault("images", [])

    raw = sys.stdin.buffer.read().decode("utf-8-sig").strip()
    if not raw:
        fail("no input on stdin (expected JSON array of image records)")
    try:
        incoming = json.loads(raw)
    except Exception as e:
        fail(f"invalid JSON on stdin: {e}")
    if not isinstance(incoming, list):
        fail("stdin JSON must be an array of image records")

    existing_keys = {(im.get("source_file"), im.get("page"), im.get("image_path")) for im in data["images"]}
    prefix = f"img_{args.course}_"
    maxnum = 0
    for im in data["images"]:
        iid = im.get("image_id", "")
        if iid.startswith(prefix):
            try:
                maxnum = max(maxnum, int(iid[len(prefix):]))
            except ValueError:
                pass

    added_ids = []
    skipped = 0
    for rec in incoming:
        if not isinstance(rec, dict):
            fail("each image record must be a JSON object")
        src = rec.get("source_file")
        page = rec.get("page")
        if src is None or page is None:
            fail("image record missing source_file or page")
        key = (src, page, rec.get("image_path"))
        if key in existing_keys:
            skipped += 1
            continue
        existing_keys.add(key)

        norm_structs = []
        for s in (rec.get("structures") or []):
            ssource = s.get("source") or "slide"
            norm_structs.append({
                "name": s.get("name"),
                "type": s.get("type"),   # free-form / optional (course-agnostic label)
                "source": ssource,
                "label_bbox": s.get("label_bbox"),
                "confidence": s.get("confidence"),
                "verified": bool(s.get("verified", ssource == "slide")),
            })

        maxnum += 1
        iid = f"{prefix}{maxnum:03d}"
        data["images"].append({
            "image_id": iid,
            "unit_id": rec.get("unit_id"),
            "unit_slug": rec.get("unit_slug"),
            "source_file": src,
            "page": int(page),
            "image_path": rec.get("image_path"),
            "image_w": rec.get("image_w"),
            "image_h": rec.get("image_h"),
            "title": rec.get("title"),
            "label_source": rec.get("label_source"),
            "structures": norm_structs,
            "date_added": today_str(),
        })
        added_ids.append(iid)

    data["last_updated"] = now_iso()
    save_json(path, data)
    out({"success": True, "added": len(added_ids), "skipped": skipped, "ids": added_ids})


# ── image remove ──────────────────────────────────────────────────────────────

def cmd_image_remove(args):
    savedata = pathlib.Path(args.savedata)
    path = image_bank_path(savedata, args.course)
    data = load_json(path, image_bank_default(args.course))
    data.setdefault("images", [])

    before = len(data["images"])
    data["images"] = [im for im in data["images"] if im.get("image_id") != args.image_id]
    if len(data["images"]) == before:
        fail(f"image id not found: {args.image_id!r}")
    data["last_updated"] = now_iso()
    save_json(path, data)
    out({"success": True, "removed": args.image_id})


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


# ── notes write ──────────────────────────────────────────────────────────────

def cmd_notes_write(args):
    content = sys.stdin.buffer.read().decode("utf-8-sig")
    dest = pathlib.Path(args.dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    out({"success": True})


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

    if args.course:
        course_log = savedata / "courses" / args.course / "activity_log.md"
        _append_log(course_log, args.entry)

    out({"success": True})


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(prog="data_writer")
    sub = parser.add_subparsers(dest="group")

    # pool
    plg = sub.add_parser("pool")
    plg_sub = plg.add_subparsers(dest="action")

    pa = plg_sub.add_parser("add")
    pa.add_argument("--savedata", required=True)
    pa.add_argument("--course", required=True)

    pr = plg_sub.add_parser("remove")
    pr.add_argument("--savedata", required=True)
    pr.add_argument("--course", required=True)
    pr.add_argument("--problem-id", required=True)

    # image
    img = sub.add_parser("image")
    img_sub = img.add_subparsers(dest="action")

    ia = img_sub.add_parser("add")
    ia.add_argument("--savedata", required=True)
    ia.add_argument("--course", required=True)

    ir = img_sub.add_parser("remove")
    ir.add_argument("--savedata", required=True)
    ir.add_argument("--course", required=True)
    ir.add_argument("--image-id", required=True)

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

    # notes
    ng = sub.add_parser("notes")
    ng_sub = ng.add_subparsers(dest="action")

    nw = ng_sub.add_parser("write")
    nw.add_argument("--dest", required=True)

    # log
    lg = sub.add_parser("log")
    lg_sub = lg.add_subparsers(dest="action")

    le = lg_sub.add_parser("entry")
    le.add_argument("--savedata", required=True)
    le.add_argument("--entry", required=True)
    le.add_argument("--course", default="")

    args = parser.parse_args()

    try:
        if args.group == "pool":
            if args.action == "add":
                cmd_pool_add(args)
            elif args.action == "remove":
                cmd_pool_remove(args)
        elif args.group == "image":
            if args.action == "add":
                cmd_image_add(args)
            elif args.action == "remove":
                cmd_image_remove(args)
        elif args.group == "deadline":
            if args.action == "add":
                cmd_deadline_add(args)
            elif args.action == "complete":
                cmd_deadline_complete(args)
        elif args.group == "notes":
            if args.action == "write":
                cmd_notes_write(args)
        elif args.group == "log":
            if args.action == "entry":
                cmd_log_entry(args)
        else:
            fail(f"unknown subcommand: {args.group} {getattr(args, 'action', '')}")
    except Exception as e:
        fail(str(e))


if __name__ == "__main__":
    main()
