"""Render an offline report of pairwise similarities and review evidence."""

from html import escape
from pathlib import Path
import re


MATCH_WORDS = 10

STYLE = """
* { box-sizing: border-box; }
body { margin: 0 auto; max-width: 78rem; padding: 1.25rem;
       font: 16px/1.5 system-ui, sans-serif; color: #182936; background: #f5f7f8; }
h1, h2, h3 { margin-bottom: .4rem; }
h2 { margin-top: 2rem; }
p { margin-top: .35rem; }
a { color: #135581; }
summary { cursor: pointer; font-weight: 600; }
table { border-collapse: collapse; width: 100%; background: white; }
th, td { text-align: left; padding: .5rem .65rem; border-bottom: 1px solid #c9d6dd; }
th { background: #e4edf2; }
td, th, h3 { overflow-wrap: anywhere; }
.numbers { white-space: nowrap; font-variant-numeric: tabular-nums; }
.table-wrap { overflow: auto; max-height: 34rem; border: 1px solid #c9d6dd; }
.table-wrap thead th { position: sticky; top: 0; }
.matrix { width: max-content; }
.matrix th, .matrix td { text-align: center; }
.above { background: #fff0cd; font-weight: 600; }
.card { background: white; border: 1px solid #c9d6dd; border-radius: .35rem;
        margin-top: .8rem; padding: 1rem; }
.comparison { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
              gap: 1rem; margin-top: .75rem; }
.text { white-space: pre-wrap; overflow-wrap: anywhere; overflow: auto;
        border: 1px solid #c9d6dd; border-radius: .3rem; max-height: 25rem; padding: .75rem; }
.muted { color: #475b67; }
mark { background: #fbe091; color: inherit; }
@media (max-width: 45rem) { .comparison { grid-template-columns: 1fr; } }
"""


def _score(value):
    return "—" if value is None else f"{value:.3f}"


def _words_and_phrases(text):
    words = list(re.finditer(r"\S+", text))
    tokens = [word.group() for word in words]
    phrases = [tuple(tokens[i:i + MATCH_WORDS]) for i in range(len(tokens) - MATCH_WORDS + 1)]
    return words, phrases


def _highlight(text, words, phrases, shared):
    """Escape the text and wrap the ranges covered by shared phrases."""
    ranges = []
    for index, phrase in enumerate(phrases):
        if phrase not in shared:
            continue
        start = words[index].start()
        end = words[index + MATCH_WORDS - 1].end()
        if ranges and start < ranges[-1][1]:
            ranges[-1] = (ranges[-1][0], end)
        else:
            ranges.append((start, end))

    html = []
    cursor = 0
    for start, end in ranges:
        html.extend((escape(text[cursor:start]), "<mark>", escape(text[start:end]), "</mark>"))
        cursor = end
    html.append(escape(text[cursor:]))
    return "".join(html)


def _comparison(doc_a, doc_b):
    text_a, text_b = doc_a["text"], doc_b["text"]
    words_a, phrases_a = _words_and_phrases(text_a)
    words_b, phrases_b = _words_and_phrases(text_b)
    shared = set(phrases_a).intersection(phrases_b)
    if shared:
        explanation = (
            f"Highlighted passages contain shared sequences of at least {MATCH_WORDS} words. "
            "Word matching is case-sensitive and ignores whitespace differences."
        )
    else:
        explanation = f"No exact sequences of {MATCH_WORDS} or more words were found."

    return f"""
<p class="muted">{explanation}</p>
<div class="comparison">
  <div><strong>{escape(doc_a['filename'])}</strong>
    <div class="text">{_highlight(text_a, words_a, phrases_a, shared)}</div></div>
  <div><strong>{escape(doc_b['filename'])}</strong>
    <div class="text">{_highlight(text_b, words_b, phrases_b, shared)}</div></div>
</div>"""


def _score_matrix(matrix, filenames, threshold):
    headers = "".join(
        f'<th scope="col" title="{escape(name)}">{index}</th>'
        for index, name in enumerate(filenames, 1)
    )
    rows = []
    for i, name in enumerate(filenames):
        cells = [f'<th scope="row" title="{escape(name)}">{i + 1}</th>']
        for j in range(len(filenames)):
            if i == j:
                cells.append("<td>—</td>")
                continue
            value = matrix[i][j]
            cell_class = ' class="above"' if value >= threshold else ""
            cells.append(f"<td{cell_class}>{_score(value)}</td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")

    return f"""
<details>
  <summary>Similarity matrix</summary>
  <p>Report numbers follow the extraction table. Highlighting marks scores at or above the review threshold.</p>
  <div class="table-wrap">
    <table class="matrix numbers"><thead><tr><th>Report</th>{headers}</tr></thead>
    <tbody>{''.join(rows)}</tbody></table>
  </div>
</details>"""


def _extraction_table(documents, skipped):
    rows = []
    for number, doc in enumerate(documents, 1):
        coverage = ", ".join(doc['sections_found']) or "Full extracted text"
        rows.append(
            f"<tr><td>{number}</td><td>{escape(doc['filename'])}</td>"
            f"<td>{escape(coverage)}</td></tr>"
        )
    for name, reason in skipped:
        rows.append(f"<tr><td>—</td><td>{escape(name)}</td><td>Skipped. {escape(reason)}</td></tr>")

    return f"""
<div class="table-wrap">
  <table><thead><tr><th>Report</th><th>File</th><th>Coverage</th></tr></thead>
  <tbody>{''.join(rows)}</tbody></table>
</div>"""


def generate_html_report(
    results: dict, documents: list[dict], threshold: float, output_path: Path,
    *, skipped: list[tuple[str, str]], scope: str, method: str,
):
    """Write all pair scores and attach comparison text for pairs meeting the threshold."""
    ranked = []
    evidence = []
    for rank, pair in enumerate(results["pairs"], 1):
        doc_a, doc_b = documents[pair["i"]], documents[pair["j"]]
        score = pair["combined"]
        if score >= threshold:
            reference = f'<a href="#pair-{rank}">Compare text</a>'
            evidence.append(f"""
<article class="card" id="pair-{rank}">
  <h3>{rank}. {escape(doc_a['filename'])} and {escape(doc_b['filename'])}</h3>
  <p>Similarity score <strong>{_score(score)}</strong></p>
  <details>
    <summary>Open compared text</summary>
    {_comparison(doc_a, doc_b)}
  </details>
</article>""")
        else:
            reference = "—"
        ranked.append(f"""
<tr><td>{rank}</td><td>{escape(doc_a['filename'])}</td><td>{escape(doc_b['filename'])}</td>
<td class="numbers{' above' if score >= threshold else ''}">{_score(score)}</td>
<td class="numbers">{_score(pair.get('tfidf'))}</td>
<td class="numbers">{_score(pair.get('semantic'))}</td><td>{reference}</td></tr>""")

    filenames = results["filenames"]
    comparisons = "".join(evidence) or "<p>No pairs reached the review threshold.</p>"
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'">
  <title>Report Similarity Review</title>
  <style>{STYLE}</style>
</head>
<body>
<main>
  <h1>Report Similarity Review</h1>
  <p>{len(documents)} reports compared · {len(skipped)} skipped · {len(ranked)} pairs · {len(evidence)} pairs for review</p>
  <p>Scope <strong>{escape(scope)}</strong> · Method <strong>{escape(method)}</strong>
     · Review threshold <strong>{_score(threshold)}</strong></p>
  <p class="muted">Use the similarity scores to prioritize manual review. Compare each passage in context, including shared templates and cited material.</p>

  <h2>Extraction coverage</h2>
  {_extraction_table(documents, skipped)}

  <h2>Ranked pairs</h2>
  <div class="table-wrap">
    <table><thead><tr><th>Rank</th><th>File A</th><th>File B</th><th>Similarity</th>
    <th>TF-IDF</th><th>Semantic</th><th>Review</th></tr></thead>
    <tbody>{''.join(ranked)}</tbody></table>
  </div>
  {_score_matrix(results['combined'], filenames, threshold)}

  <h2>Side-by-side review</h2>
  {comparisons}
</main>
</body>
</html>"""
    output_path.write_text(page, encoding="utf-8")
