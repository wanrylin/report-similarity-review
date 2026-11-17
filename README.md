# Report Similarity Review

Compare submissions from one assignment or project on your computer. The tool reads PDF and DOCX files, ranks every pair by text similarity, and writes a browser-readable HTML report. Pairs above a review threshold have side-by-side text for manual comparison.

The default comparison uses **TF-IDF cosine similarity** on English words and word pairs. The score is a relative measure of text similarity within the batch. Shared templates, assignment wording, bibliography entries, and common technical language can raise the score. Review the original reports and matching passages before drawing a conclusion.

## Install

Python 3.11 or 3.12 is recommended. Open a terminal in this folder.

**macOS or Linux**

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

**Windows PowerShell**

```powershell
py -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Run the examples below using `.venv/bin/python` on macOS/Linux or `./.venv/Scripts/python.exe` on Windows.

## Review project reports

1. If the submissions came as a Brightspace ZIP, extract it into a folder. The tool searches subfolders, so the export can retain its existing layout.
2. Run the comparison. Replace the example input path with the extracted folder.

   ```sh
   .venv/bin/python main.py --input "/path/to/project-submissions" --output "./results"
   ```

3. Open `results/similarity_report.html` in a browser. Check which files were compared or skipped, scan the ranked pairs, and use the side-by-side passages to verify any overlap against the originals.

Whole-report text is the default because project report headings can vary. Use the names of the report sections when comparing a narrower scope. Quote any heading that contains spaces.

```sh
.venv/bin/python main.py --input "/path/to/project-submissions" --output "./results-sections" --sections "Results and Discussion" Conclusion
```

PDF section matching relies on headings appearing on their own line. DOCX extraction reads body paragraphs and table text. Text embedded in images, scans, charts, equations, and footnotes may be omitted. Export Word's older `.doc` format to PDF or DOCX, and use a text-searchable PDF for scanned reports.

The tool lists skipped files. Section mode skips a report if its selected headings yield no text. If it omits a report you expected, check the headings in the source, then rerun with matching section names or use the full text.

## Read the scores

- All pairs in the included batch are ranked. The default review threshold is `0.60`. Set a lower threshold with `--threshold 0.45` to show side-by-side text for more pairs. Use a new output folder to retain both runs.
- Similarity is a screening score. For example, 0.60 represents a cosine score, and a match can come from required report wording. Longer reports can also dilute a short shared passage. Consider a targeted section comparison when a specific part of a report is at issue.
- Semantic comparison is optional. Install `requirements-semantic.txt` and run with `--method semantic` or `--method both`. The model downloads on first use and runs locally. Semantic mode compares a leading excerpt per report, which may be shortened further by the model's input limit. The default TF-IDF mode compares all extracted text. In `both` mode, the rank uses the mean of the two scores.
- Results compare against reports in the supplied folder. Use the quoted passages and original documents for follow-up. Similarity does not establish authorship, copying direction, or AI use.

## Share the tool

Share the source directory or its ZIP. The HTML report can contain report filenames and student writing, so keep reports and results in a local working folder. For GitHub, push the source files in this directory. Common submission folders and report formats are listed in `.gitignore`.

Run `python main.py --help` for the full list of options.
