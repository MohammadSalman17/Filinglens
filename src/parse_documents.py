import warnings
from pathlib import Path
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

RAW_DIR = Path("data/raw/sec-edgar-filings")
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_html(file_path):
    html = file_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style"]):
        tag.decompose()
    for tag in soup.find_all("ix:header"):
        tag.decompose()
    for tag in soup.find_all(style=lambda s: s and "display:none" in s.replace(" ", "")):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


for file_path in RAW_DIR.glob("*/10-K/*/primary-document.html"):
    ticker = file_path.parts[-4]
    accession = file_path.parts[-2]
    clean_text = parse_html(file_path)

    out_file = OUT_DIR / f"{ticker}_{accession}.txt"
    out_file.write_text(clean_text, encoding="utf-8")
    print(f"Saved {out_file.name}: {len(clean_text)} characters")