# Multi-Source Candidate Data Transformer

Eightfold Engineering Intern Assignment, July-December 2026.

This project takes messy candidate data from different sources and converts it into clean JSON profiles. It can read recruiter CSV data, GitHub usernames, and recruiter notes, then merge everything into one trusted profile per candidate.

The project includes:

- Python transformer pipeline for the main logic
- React UI for uploading/editing inputs and viewing output
- Runtime JSON config to change the output shape
- Tests for normalization, merging, notes parsing, GitHub input cleanup, config validation, and projection

## Features

- Upload a recruiter CSV or edit the default CSV manually
- Add GitHub usernames and recruiter notes
- Run the full pipeline from the UI or command line
- View each candidate as raw JSON or profile details
- Download selected candidate JSON
- Track provenance, conflicts, and confidence scores
- Generate both default and custom-configured output JSON
- Canonicalize common skill aliases and typos such as `ml`, `machinelearning`, `k8s`, `reactjs`, and `sklearn`
- Accept GitHub usernames as plain names, `@handles`, or GitHub profile URLs

## Tech Stack

- Python
- React + Vite
- Express local API server
- GitHub public API
- `requests`, `phonenumbers`, `pycountry`

## Project Structure

```text
Eightfold/
  README.md
  requirements.txt
  transformer/
    main.py
    config.json
    custom_config.json
    extractor/
    sample_inputs/
    output/
    tests/
  ui/
    server.js
    package.json
    src/
```

## Quick Start

Run these commands from the project root:

```powershell
cd C:\Users\yarra\Desktop\Eightfold
python -m pip install -r requirements.txt
python -m unittest discover -s transformer/tests
```

If tests pass, run the default pipeline:

```powershell
python -m transformer.main `
  --csv transformer/sample_inputs/candidates.csv `
  --github-usernames transformer/sample_inputs/github_usernames.txt `
  --notes transformer/sample_inputs/recruiter_notes.txt `
  --config transformer/config.json `
  --output transformer/output/default_output.json
```

Output file:

```text
transformer/output/default_output.json
```

## Run Custom Config Output

```powershell
python -m transformer.main `
  --csv transformer/sample_inputs/candidates.csv `
  --github-usernames transformer/sample_inputs/github_usernames.txt `
  --notes transformer/sample_inputs/recruiter_notes.txt `
  --config transformer/custom_config.json `
  --output transformer/output/custom_output.json
```

Output file:

```text
transformer/output/custom_output.json
```

## Run The UI

Open a terminal in the project root and run:

```powershell
cd ui
npm install
npm run dev
```

Open the URL printed by Vite. Usually it is:

```text
http://127.0.0.1:5173
```

If `5173` is busy, Vite will show another URL like `http://127.0.0.1:5175`.

## How To Use The UI

1. Open the UI in the browser.
2. In `Sources`, choose `Upload CSV` or `Manual editor`.
3. Add or edit GitHub usernames.
4. Add or edit recruiter notes.
5. Check the runtime config JSON.
6. Click `Run Pipeline`.
7. The output opens in raw JSON view by default.
8. Use the toggle to switch between `Profile details` and `View raw JSON`.
9. Click `Download JSON` to download the selected candidate profile.

## Pipeline Flow

```text
Detect -> Extract -> Normalize -> Merge -> Confidence -> Project -> Validate
```

Simple explanation:

- `Detect`: checks which input files exist
- `Extract`: reads CSV, GitHub, and notes into a common format
- `Normalize`: cleans phones, countries, skills, dates, GitHub handles, and common skill aliases/typos
- `Merge`: combines duplicate candidates into one profile
- `Confidence`: scores how trustworthy each value is
- `Project`: applies the runtime config
- `Validate`: checks the final JSON before writing output

## Runtime Config Example

Default config:

```json
{
  "fields": null,
  "include_confidence": true,
  "on_missing": "null"
}
```

Example custom config:

```json
{
  "fields": [
    { "path": "name", "from": "full_name", "type": "string", "required": true },
    { "path": "primary_email", "from": "emails[0]", "type": "string", "required": true },
    { "path": "phone", "from": "phones[0]", "type": "string", "normalize": "E164" },
    { "path": "skills", "from": "skills[].name", "type": "string[]", "normalize": "canonical" },
    { "path": "score", "from": "overall_confidence", "type": "number" }
  ],
  "include_confidence": false,
  "on_missing": "null"
}
```

`on_missing` options:

- `null`: output missing fields as `null`
- `omit`: skip missing fields
- `error`: stop the run if a required field is missing

## Tests

Run all tests:

```powershell
python -m unittest discover -s transformer/tests
```

Expected result:

```text
Ran 19 tests

OK
```

## Common Errors And Quick Fixes

### `python` is not recognized

Install Python and make sure it is added to PATH. Then reopen the terminal.

### `ModuleNotFoundError`

Install dependencies from the root folder:

```powershell
python -m pip install -r requirements.txt
```

### `npm` is not recognized

Install Node.js LTS, then reopen the terminal.

### Port already in use

If Vite says port `5173` is busy, use the alternate URL printed in the terminal.

### GitHub API rate limit

The project uses the public GitHub API. If GitHub rate-limits requests, wait a few minutes and run again.

## Demo Checklist

For a quick project demo:

1. Run tests.
2. Run the CLI command and open `transformer/output/default_output.json`.
3. Start the UI with `npm run dev`.
4. Click `Run Pipeline`.
5. Show raw JSON output.
6. Switch to profile details.
7. Download one candidate JSON file.
8. Show provenance, confidence, and conflict handling in the output.

## Notes

- The transformer never invents unknown values.
- Missing or bad optional sources should not crash the run.
- Recruiter notes are parsed conservatively, including common sentence patterns like `Asha Rao is based in Bengaluru`.
- Skill typo matching is deliberately limited to close matches against known canonical skills to avoid inventing unknown skills.
- The UI is only a thin input/output layer. The main logic is in the Python transformer.
- Temporary UI runtime files are written to `transformer/output/ui_runtime/`.
