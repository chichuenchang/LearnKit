import argparse
import json
import pathlib
import zipfile

NEVER_OVERWRITE = {"machine.config.json"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True)
    parser.add_argument("--savedata", required=True)
    args = parser.parse_args()

    root = pathlib.Path(args.savedata)
    root.mkdir(parents=True, exist_ok=True)

    restored = []
    skipped = []

    with zipfile.ZipFile(args.zip, "r") as zf:
        for member in zf.namelist():
            if pathlib.Path(member).name in NEVER_OVERWRITE:
                skipped.append(member)
                continue
            dest = root / member
            dest.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(member) as src, open(dest, "wb") as dst:
                dst.write(src.read())
            restored.append(member)

    print(json.dumps({"success": True, "restored": restored, "skipped": skipped}))


if __name__ == "__main__":
    main()
