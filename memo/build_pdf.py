#!/usr/bin/env python3
"""Render a memo markdown file to an A4 PDF and report the page count.

Run:  python3 -I memo/build_pdf.py memo/out_of_moves_memo_v0.3.md [--max-pages 2]

Handles the markdown subset the memo uses (headings, paragraphs, bold, italics, code, links,
bullet and numbered lists, tables, images with an italic caption line, block quotes) and prints
through headless Chrome. Fonts: Carlito from the local TeX tree if present, else Calibri/Arial.
Exits with an error if the PDF has more pages than --max-pages.
"""
import argparse
import html
import os
import re
import subprocess
import sys
import tempfile

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FONT_DIR = os.path.expanduser("~/Library/TinyTeX/texmf-dist/fonts/truetype/google/carlito")

CSS = """
@page { size: A4; margin: 13mm 16mm 12mm 16mm; }
* { box-sizing: border-box; }
body { font-family: Carlito, Calibri, "Helvetica Neue", Arial, sans-serif; font-size: %(size)spt; line-height: 1.3;
       font-variant-ligatures: none;   /* so copied or extracted text reads "offers", not a ligature glyph */
       color: #141414; margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
h1 { color: #1F3864; font-size: 21pt; line-height: 1.1; margin: 0 0 2pt; }
h2 { color: #1F3864; font-size: 12pt; margin: 8pt 0 2.5pt; break-after: avoid; }
h3 { color: #1F3864; font-size: 10.6pt; margin: 6pt 0 2pt; break-after: avoid; }
p { margin: 0 0 4.6pt; }
p.sub { font-size: 11.4pt; margin-bottom: 1pt; }
p.byline { color: #6B6B6B; font-size: 9.3pt; margin-bottom: 5pt; }
p.sign { color: #6B6B6B; font-size: 9.3pt; margin-top: 5pt; }
ul, ol { margin: 0 0 4.6pt; padding-left: 13pt; }
li { margin-bottom: 2.6pt; }
a { color: #1F3864; text-decoration: none; }
code { font-family: Menlo, Consolas, monospace; font-size: 0.86em; }
table { border-collapse: collapse; width: 100%%; font-size: 0.94em; margin: 3pt 0 6pt; }
th, td { border-top: 0.5pt solid #c9c9c9; padding: 2pt 7pt 2pt 0; vertical-align: top; text-align: left; }
th { color: #1F3864; border-top: none; }
tr:last-child td { border-bottom: 0.5pt solid #c9c9c9; }
table.kv td:first-child { font-weight: bold; white-space: nowrap; width: 1%%; color: #1F3864; }
thead { display: table-header-group; }
tr, figure, li { break-inside: avoid; }
h2 + table, h3 + table, p + table { break-before: avoid; }
figure { margin: 5pt 0 5pt; }
figure img { width: %(img)s%%; display: block; margin: 0 auto; }
figcaption { font-size: 8.7pt; color: #6B6B6B; margin-top: 2pt; }
blockquote { margin: 0 0 5pt; padding-left: 8pt; border-left: 2pt solid #c9c9c9; color: #444; }
"""


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<![\w*])\*([^*]+)\*(?![\w*])", r"<i>\1</i>", s)
    return s


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def convert(md, base):
    lines = md.split("\n")
    out, i, n_p = [], 0, 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = re.match(r"(#{1,3}) (.*)", line)
        if m:
            out.append(f"<h{len(m.group(1))}>{inline(m.group(2))}</h{len(m.group(1))}>")
            i += 1
            continue
        m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)\s*$", line)
        if m:
            src = "file://" + os.path.abspath(os.path.join(base, m.group(2)))
            cap, j = "", i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and re.match(r"\*[^*].*\*$", lines[j].strip()):
                cap = f"<figcaption>{inline(lines[j].strip()[1:-1])}</figcaption>"
                i = j
            out.append(f'<figure><img src="{src}" alt="{html.escape(m.group(1))}">{cap}</figure>')
            i += 1
            continue
        if line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(cells(lines[i]))
                i += 1
            head, body = rows[0], [r for r in rows[2:]]
            if any(head):
                t = "<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr></thead>"
            else:
                t = '<table class="kv">'
            t += "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) + "</table>"
            out.append(t)
            continue
        if re.match(r"(- |\d+\. )", line):
            tag = "ul" if line.startswith("- ") else "ol"
            items = []
            while i < len(lines) and re.match(r"(- |\d+\. )", lines[i]):
                items.append(re.sub(r"^(- |\d+\. )", "", lines[i]))
                i += 1
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in items) + f"</{tag}>")
            continue
        if line.startswith("> "):
            out.append(f"<blockquote>{inline(line[2:])}</blockquote>")
            i += 1
            continue
        if line.strip() == "---":
            out.append("<hr>")
            i += 1
            continue
        para = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r"(#{1,3} |\||- |\d+\. |> |!\[)", lines[i]):
            para.append(lines[i])
            i += 1
        n_p += 1
        text = " ".join(para)
        cls = ""
        if n_p == 1 and text.startswith("**") and text.endswith("**"):
            cls, text = ' class="sub"', text
        elif n_p == 2 and " · " in text:   # the byline under the subtitle
            cls = ' class="byline"'
        elif i >= len(lines) - 1 and " · " in text and ("@" in text or "linkedin.com/in/" in text):
            cls = ' class="sign"'
        out.append(f"<p{cls}>{inline(text)}</p>")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("markdown")
    ap.add_argument("--max-pages", type=int)
    ap.add_argument("--size", default="10.2", help="body font size in pt")
    ap.add_argument("--img", default="100", help="figure width in percent of the text width")
    args = ap.parse_args()
    src = os.path.abspath(args.markdown)
    md = open(src, encoding="utf-8").read()
    faces = ""
    for name, weight, style in (("Carlito-Regular", 400, "normal"), ("Carlito-Bold", 700, "normal"),
                                ("Carlito-Italic", 400, "italic"), ("Carlito-BoldItalic", 700, "italic")):
        path = os.path.join(FONT_DIR, name + ".ttf")
        if os.path.exists(path):
            faces += f'@font-face {{ font-family: Carlito; font-weight: {weight}; font-style: {style}; src: url("file://{path}"); }}\n'
    title = re.search(r"^# (.*)", md, re.M).group(1)
    page = (f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title>'
            f"<style>{faces}{CSS % {'size': args.size, 'img': args.img}}</style></head><body>{convert(md, os.path.dirname(src))}</body></html>")
    pdf = os.path.splitext(src)[0] + ".pdf"
    with tempfile.TemporaryDirectory() as tmp:
        hpath = os.path.join(tmp, "memo.html")
        with open(hpath, "w", encoding="utf-8") as f:
            f.write(page)
        done = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--print-to-pdf-no-header",
                               f"--user-data-dir={os.path.join(tmp, 'profile')}", f"--print-to-pdf={pdf}", "file://" + hpath],
                              capture_output=True, text=True, timeout=120)
    if not os.path.exists(pdf):
        sys.exit("Chrome did not write the PDF:\n" + done.stderr[-800:])
    pages = len(re.findall(rb"/Type\s*/Page(?![s\w])", open(pdf, "rb").read()))
    words = len(re.findall(r"[A-Za-zÀ-ÿ0-9][\w'’.,%+-]*", re.sub(r"!\[[^\]]*\]\([^)]*\)|\|[-| ]+\|", " ", md)))
    print(f"wrote {os.path.relpath(pdf)}: {pages} pages, about {words} words in the source")
    if args.max_pages and pages > args.max_pages:
        sys.exit(f"too long: {pages} pages, limit {args.max_pages}")


if __name__ == "__main__":
    main()
