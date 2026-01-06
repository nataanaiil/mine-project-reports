from __future__ import annotations

from pathlib import Path
import csv
import html
from urllib.parse import quote

IMG_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def read_captions(captions_csv: Path) -> dict[str, str]:
    """
    captions.csv format:
    filename,caption
    img_001.png,Some caption
    """
    caps: dict[str, str] = {}
    if not captions_csv.exists():
        return caps

    with captions_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fn = (row.get("filename") or "").strip()
            cap = (row.get("caption") or "").strip()
            if fn:
                caps[fn] = cap
    return caps


def list_images(folder: Path) -> list[Path]:
    return sorted([p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMG_EXTS])


def url_path(*parts: str) -> str:
    """
    Make a URL-safe relative path (handles spaces مثل "Modeling outputs").
    """
    return "/".join(quote(p) for p in parts)


def build_report(folder: Path) -> None:
    images = list_images(folder)
    if not images:
        return

    caps = read_captions(folder / "captions.csv")

    title = folder.name
    cards = []

    for img in images:
        # If no captions.csv, caption should be blank (طبق خواسته شما)
        caption_text = caps.get(img.name, "")
        cards.append(
            f"""
            <figure class="card">
              <a href="{url_path(img.name)}" target="_blank" rel="noopener">
                <img src="{url_path(img.name)}" alt="{html.escape(img.name)}">
              </a>
              <figcaption>{html.escape(caption_text)}</figcaption>
            </figure>
            """.strip()
        )

    page = f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Report - {html.escape(title)}</title>
  <style>
    body {{ font-family: sans-serif; margin: 24px; line-height: 1.8; }}
    header {{ margin-bottom: 16px; }}
    .muted {{ color: #666; font-size: 0.95rem; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
    }}
    .card {{
      border: 1px solid #ddd;
      border-radius: 12px;
      padding: 12px;
      background: #fff;
    }}
    img {{ width: 100%; height: auto; border-radius: 10px; }}
    figcaption {{ margin-top: 10px; color: #333; font-size: 0.95rem; min-height: 1.2em; }}
  </style>
</head>
<body>
  <header>
    <h1>گزارش: {html.escape(title)}</h1>
    <p class="muted">تعداد تصاویر: {len(images)}</p>
  </header>

  <main class="grid">
    {"".join(cards)}
  </main>
</body>
</html>
"""
    (folder / "report.html").write_text(page, encoding="utf-8")
    print(f"✅ report built: {folder / 'report.html'}")


def find_report_folders(outputs_dir: Path) -> list[Path]:
    """
    پیدا کردن همه فولدرهایی که داخل خودشان عکس دارند (نه اینکه فقط زیرشاخه داشته باشند)
    - outputs/Modeling outputs  (عکس‌ها مستقیم داخلش هستند) ✅
    - outputs/airport_analysis_output/exp1..exp5 (عکس‌ها داخل expها هستند) ✅
    """
    report_folders: list[Path] = []
    for d in sorted(outputs_dir.rglob("*")):
        if d.is_dir():
            if list_images(d):
                report_folders.append(d)
    return report_folders


def build_index_pages(root: Path, report_folders: list[Path]) -> None:
    """
    دو تا فهرست می‌سازیم:
    1) mine-project/site/index.html   (لینک‌ها با ../outputs/...)
    2) mine-project/index.html        (لینک‌ها با outputs/...)  ← برای وقتی گزارش‌ها را در repo عمومی می‌گذاری
    """
    outputs_dir = root / "outputs"
    site_dir = root / "site"
    site_dir.mkdir(parents=True, exist_ok=True)

    # دسته‌بندی: Modeling outputs جدا، airport_analysis_output/exp* جدا
    def rel_from_outputs(p: Path) -> str:
        return p.relative_to(outputs_dir).as_posix()

    items = []
    for folder in report_folders:
        rel = rel_from_outputs(folder)
        report_rel = f"{rel}/report.html"  # path relative to outputs/
        img_count = len(list_images(folder))
        items.append((rel, report_rel, img_count))

    # Sort for stable order
    items.sort(key=lambda x: x[0].lower())

    def make_html(prefix_to_outputs: str) -> str:
        # prefix_to_outputs: "outputs" یا "../outputs"
        lis = []
        for rel, report_rel, img_count in items:
            href = url_path(prefix_to_outputs, *report_rel.split("/"))
            # نمایش اسم فولدر به صورت مسیر
            label = html.escape(rel)
            lis.append(f'<li><a href="{href}">{label}</a> <span class="muted">({img_count} تصویر)</span></li>')

        return f"""<!doctype html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>فهرست گزارش‌ها</title>
  <style>
    body {{ font-family: sans-serif; margin: 24px; line-height: 1.8; }}
    .muted {{ color: #666; font-size: 0.95rem; }}
    ul {{ padding-right: 18px; }}
    li {{ margin: 8px 0; }}
  </style>
</head>
<body>
  <h1>فهرست گزارش‌ها</h1>
  <p class="muted">روی هر مورد کلیک کن تا گزارش همان فولدر باز شود.</p>
  <ul>
    {"".join(lis) if lis else "<li>گزارشی پیدا نشد.</li>"}
  </ul>
</body>
</html>
"""

    # 1) site/index.html
    (site_dir / "index.html").write_text(make_html("../outputs"), encoding="utf-8")
    print(f"✅ index built: {site_dir / 'index.html'}")

    # 2) root index.html
    (root / "index.html").write_text(make_html("outputs"), encoding="utf-8")
    print(f"✅ index built: {root / 'index.html'}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]  # mine-project/
    outputs_dir = root / "outputs"
    if not outputs_dir.exists():
        raise SystemExit("❌ outputs/ پیدا نشد")

    report_folders = find_report_folders(outputs_dir)

    # ساخت report برای هر فولدر عکس‌دار
    for folder in report_folders:
        build_report(folder)

    # ساخت فهرست‌ها
    build_index_pages(root, report_folders)

    print("🎉 Done.")


if __name__ == "__main__":
    main()
