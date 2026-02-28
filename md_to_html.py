#!/usr/bin/env python3
"""Convert report.md to report.html for browser viewing."""
import re
import html
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

md = open(os.path.join(OUTPUT_DIR, "report.md")).read()

lines = md.split("\n")
out = []
out.append("<!DOCTYPE html><html><head><meta charset='utf-8'><title>GLP-1 Report</title>")
out.append("<style>")
out.append("body{font-family:system-ui,sans-serif;max-width:900px;margin:40px auto;padding:0 20px;line-height:1.6;color:#1a1a1a}")
out.append("table{border-collapse:collapse;width:100%;margin:16px 0}th,td{border:1px solid #ddd;padding:8px 12px;text-align:left}")
out.append("th{background:#f5f5f5;font-weight:600}img{max-width:100%;height:auto;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1);margin:12px 0}")
out.append("pre{background:#f5f5f5;padding:16px;border-radius:6px;overflow-x:auto;font-size:12px}")
out.append("code{background:#f0f0f0;padding:2px 6px;border-radius:3px;font-size:13px}")
out.append("blockquote{border-left:4px solid #2563eb;margin:16px 0;padding:8px 16px;background:#f8fafc}")
out.append("h1{color:#1e3a5f;border-bottom:2px solid #2563eb;padding-bottom:8px}")
out.append("h2{color:#2563eb;margin-top:32px}h3{color:#444}")
out.append("hr{border:none;border-top:1px solid #ddd;margin:32px 0}")
out.append("li{margin:4px 0}")
out.append("</style></head><body>")

in_pre = False
in_table = False

for line in lines:
    stripped = line.strip()

    # Code blocks
    if stripped.startswith("```"):
        if in_pre:
            out.append("</pre>")
            in_pre = False
        else:
            out.append("<pre>")
            in_pre = True
        continue
    if in_pre:
        out.append(html.escape(line))
        continue

    # Tables
    if "|" in stripped and stripped.startswith("|"):
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if all(c.replace("-", "").strip() == "" for c in cells):
            continue
        if not in_table:
            out.append("<table>")
            out.append("<tr>" + "".join(f"<th>{c}</th>" for c in cells) + "</tr>")
            in_table = True
        else:
            out.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        continue
    elif in_table:
        out.append("</table>")
        in_table = False

    # Headers
    if stripped.startswith("# "):
        out.append(f"<h1>{stripped[2:]}</h1>")
    elif stripped.startswith("## "):
        out.append(f"<h2>{stripped[3:]}</h2>")
    elif stripped.startswith("### "):
        out.append(f"<h3>{stripped[4:]}</h3>")
    elif stripped.startswith("> ") or stripped == ">":
        content = stripped[2:] if stripped.startswith("> ") else ""
        if content:
            content = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", content)
            content = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", content)
            out.append(f"<blockquote>{content}<br></blockquote>")
        # bare ">" is just a continuation break — skip silently
    elif stripped.startswith("- "):
        out.append(f"<li>{stripped[2:]}</li>")
    elif stripped.startswith("!["):
        m = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
        if m:
            out.append(f'<img src="{m.group(2)}" alt="{m.group(1)}">')
    elif stripped == "---":
        out.append("<hr>")
    elif stripped:
        l = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", stripped)
        l = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", l)
        l = re.sub(r"`([^`]+)`", r"<code>\1</code>", l)
        out.append(f"<p>{l}</p>")

if in_table:
    out.append("</table>")
out.append("</body></html>")

html_path = os.path.join(OUTPUT_DIR, "report.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print(f"Created {html_path}")
