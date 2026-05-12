import argparse
import json
import pathlib
import zipfile

EXCLUDE_NAMES = {"machine.config.json"}
EXCLUDE_DIRS = {"raw"}
EXCLUDE_PREFIXES = ("source_",)


def should_exclude(rel: pathlib.PurePosixPath) -> bool:
    if rel.parts[0] in EXCLUDE_DIRS:
        return True
    if rel.name in EXCLUDE_NAMES:
        return True
    for prefix in EXCLUDE_PREFIXES:
        if rel.name.startswith(prefix):
            return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--savedata", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = pathlib.Path(args.savedata)
    included = []

    with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in sorted(root.rglob("*")):
            if not file.is_file():
                continue
            rel = pathlib.PurePosixPath(file.relative_to(root))
            if should_exclude(rel):
                continue
            zf.write(file, rel)
            included.append(str(rel))

    size_kb = round(pathlib.Path(args.output).stat().st_size / 1024, 1)
    print(json.dumps({"success": True, "count": len(included), "size_kb": size_kb, "files": included}))


if __name__ == "__main__":
    main()
