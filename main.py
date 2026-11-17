"""Compare local academic report files and write a similarity review."""
import argparse
import sys
from pathlib import Path

from extractor import SUPPORTED_EXTENSIONS, extract_document
from report import generate_html_report
from similarity import compute_similarity_matrix


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Compare PDF and DOCX reports and produce a local HTML review."
    )
    parser.add_argument("-i", "--input", type=Path, required=True,
                        help="Folder of reports (subfolders are included)")
    parser.add_argument("-o", "--output", type=Path, default=Path("results"),
                        help="Folder for the HTML report (default: results)")
    parser.add_argument("-t", "--threshold", type=float, default=0.6,
                        help="Score at which to show side-by-side review (default: 0.6)")
    parser.add_argument("-m", "--method", choices=["tfidf", "semantic", "both"],
                        default="tfidf", help="Comparison method (default: tfidf)")
    parser.add_argument("-s", "--sections", nargs="+",
                        help="Section headings to compare (default: full extractable text)")
    args = parser.parse_args(argv)
    if not 0 <= args.threshold <= 1:
        parser.error("--threshold must be between 0 and 1")
    if not args.input.is_dir():
        parser.error(f"input folder not found: {args.input}")
    return args


def main(argv=None):
    args = parse_args(argv)
    files = sorted(
        path for path in args.input.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
        and not path.name.startswith("~$")
    )
    documents = []
    skipped = []
    for path in files:
        name = path.relative_to(args.input).as_posix()
        try:
            document = extract_document(path, args.sections, name)
        except ValueError as exc:
            skipped.append((name, str(exc)))
            continue
        if document["text"].strip():
            documents.append(document)
        else:
            reason = (
                "Requested sections were missing or empty."
                if args.sections else "No readable text found."
            )
            skipped.append((name, reason))

    for name, reason in skipped:
        print(f"Skipped {name}: {reason}", file=sys.stderr)
    if len(documents) < 2:
        print(
            f"Need at least two reports with comparable text. "
            f"Found {len(files)} PDF/DOCX files and extracted text from {len(documents)}.",
            file=sys.stderr,
        )
        return 1

    scope = ", ".join(args.sections) if args.sections else "Full extractable text"
    print(f"Comparing {len(documents)} reports (scope: {scope}; method: {args.method}).")
    try:
        results = compute_similarity_matrix(documents, method=args.method)
        args.output.mkdir(parents=True, exist_ok=True)
        report_path = args.output / "similarity_report.html"
        generate_html_report(
            results, documents, args.threshold, report_path,
            skipped=skipped, scope=scope, method=args.method,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Could not finish the review: {exc}", file=sys.stderr)
        return 1

    flagged = sum(pair["combined"] >= args.threshold for pair in results["pairs"])
    print(f"{len(results['pairs'])} pairs compared. {flagged} at or above the review threshold.")
    print(f"Open {report_path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
