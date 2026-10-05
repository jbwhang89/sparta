"""폴더 안의 CSV 파일들을 병합하고, 용량이 크면 여러 파일로 나눠서 저장합니다.

사용법 (Windows, Python 3 필요 / 추가 설치 없음):
    python merge_csv.py
    python merge_csv.py --max-mb 25

- 하위 폴더까지 모든 *.csv 를 찾습니다.
- 열(헤더)이 파일마다 달라도 합집합으로 맞춰 병합합니다.
- 어느 파일에서 왔는지 알 수 있도록 'source_file' 열을 추가합니다.
- 결과 파일 1개가 --max-mb(기본 25MB)를 넘으면 part1, part2, ... 로 나눕니다.
"""
import argparse
import csv
import sys
from pathlib import Path

csv.field_size_limit(sys.maxsize)

JOBS = [
    (r"C:\Users\korea\OneDrive\연구\GIS\fishing_byvessel", "fishing_byvessel_merged"),
    (r"C:\Users\korea\OneDrive\연구\GIS\GFW_data_v2", "GFW_data_v2_merged"),
]
ENCODINGS = ["utf-8-sig", "cp949", "latin-1"]


def detect_encoding(path):
    for enc in ENCODINGS:
        try:
            with open(path, encoding=enc, newline="") as f:
                while f.read(1 << 20):
                    pass
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def read_header(path, enc):
    with open(path, encoding=enc, newline="") as f:
        return next(csv.reader(f), [])


def merge(folder, out_name, out_dir, max_bytes):
    folder = Path(folder)
    files = sorted(folder.rglob("*.csv"))
    if not files:
        print(f"[건너뜀] CSV 없음: {folder}")
        return
    print(f"\n== {folder} ({len(files)}개 파일)")

    encs = {p: detect_encoding(p) for p in files}
    columns = []
    for p in files:
        for c in read_header(p, encs[p]):
            if c not in columns:
                columns.append(c)
    columns.append("source_file")

    part, out, writer, written = 0, None, None, 0

    def open_part():
        nonlocal part, out, writer, written
        if out:
            out.close()
        part += 1
        path = out_dir / f"{out_name}_part{part}.csv"
        out = open(path, "w", encoding="utf-8-sig", newline="")
        writer = csv.DictWriter(out, fieldnames=columns, restval="")
        writer.writeheader()
        written = out.tell()
        print(f"  -> {path.name}")

    open_part()
    total = 0
    for p in files:
        rel = str(p.relative_to(folder))
        with open(p, encoding=encs[p], newline="") as f:
            for row in csv.DictReader(f):
                row.pop(None, None)  # 헤더보다 열이 많은 줄의 초과분 제거
                row["source_file"] = rel
                writer.writerow(row)
                total += 1
                if total % 5000 == 0:
                    out.flush()
                    written = out.tell()
                    if written >= max_bytes:
                        open_part()
    out.close()

    # 파트가 1개뿐이면 _part1 제거
    if part == 1:
        src = out_dir / f"{out_name}_part1.csv"
        src.replace(out_dir / f"{out_name}.csv")
    print(f"  완료: {total:,}행, {part}개 파일")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-mb", type=float, default=25, help="파일 1개 최대 크기(MB)")
    ap.add_argument("--out", default=r"C:\Users\korea\OneDrive\연구\GIS\merged_output")
    args = ap.parse_args()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for folder, name in JOBS:
        merge(folder, name, out_dir, int(args.max_mb * 1024 * 1024))
    print(f"\n결과 폴더: {out_dir}")


if __name__ == "__main__":
    main()
