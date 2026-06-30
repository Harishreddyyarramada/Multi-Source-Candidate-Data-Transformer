# Multi-Source Candidate Data Transformer

Eightfold Engineering Intern Assignment, July-December 2026.

This project converts messy candidate data from multiple sources into one deterministic, canonical JSON profile per candidate. It keeps the transformer logic explainable: every emitted value can be traced to a source and method, conflicts are preserved, and the final output can be reshaped through a runtime config without changing the pipeline code.

## What It Supports

Sources handled:

- Recruiter CSV, including `name`, `email`, `phone`, `current_company`, `title`, `location`, `github_username`, `linkedin_url`, `portfolio_url`, `skills`, and `years_experience`
- GitHub usernames file, resolved through the public GitHub API
- Recruiter notes `.txt`, parsed conservatively for emails, phones, locations, and skills

Output includes:

- One canonical candidate profile per matched person
- E.164 phone normalization
- ISO-3166 alpha-2 country normalization
- Canonical lowercase skill names
- Provenance for source and extraction method
- Conflict records for disagreeing source values
- Field-level and overall confidence
- Runtime projection config for custom output shapes

## Repository Layout

```text
.
├── README.md
├── requirements.txt
├── transformer/
│   ├── main.py
│   ├── models.py
│   ├── normalizer.py
│   ├── merger.py
│   ├── projector.py
│   ├── validator.py
│   ├── config.json
│   ├── custom_config.json
│   ├── extractor/
│   │   ├── csv_extractor.py
│   │   ├── github_extractor.py
│   │   └── notes_extractor.py
│   ├── sample_inputs/
│   │   ├── candidates.csv
│   │   ├── github_usernames.txt
│   │   └── recruiter_notes.txt
│   ├── output/
│   │   ├── default_output.json
│   │   └── custom_output.json
│   └── tests/
│       ├── test_merger.py
│       ├── test_normalizer.py
│       ├── test_notes_extractor.py
│       └── test_projector.py
└── ui/
    ├── server.js
    ├── package.json
    └── src/
        ├── App.jsx
        └── styles.css
```

## Quick Start

Install Python dependencies from the repository root:

```powershell
python -m pip install -r requirements.txt
```

Run the test suite:

```powershell
python -m unittest discover -s transformer/tests
```

Generate the default canonical output:

```powershell
python -m transformer.main `
  --csv transformer/sample_inputs/candidates.csv `
  --github-usernames transformer/sample_inputs/github_usernames.txt `
  --notes transformer/sample_inputs/recruiter_notes.txt `
  --config transformer/config.json `
  --output transformer/output/default_output.json
```

Generate the custom projected output:

```powershell
python -m transformer.main `
  --csv transformer/sample_inputs/candidates.csv `
  --github-usernames transformer/sample_inputs/github_usernames.txt `
  --notes transformer/sample_inputs/recruiter_notes.txt `
  --config transformer/custom_config.json `
  --output transformer/output/custom_output.json
```

On macOS or Linux, use the same commands with `\` line continuations instead of PowerShell backticks.

## Run The UI

Install UI dependencies:

```powershell
cd ui
npm install
```

Start the React app and local API server:

```powershell
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

If port `5173` is already in use, Vite will print the alternate local URL.

The UI provides:

- CSV source toggle for file upload or manual CSV editor
- Success message with uploaded CSV filename
- GitHub username and recruiter notes inputs
- Runtime projection config editor
- Candidate list for deduplicated profiles
- Raw JSON view shown by default after a run
- Toggle between profile details and raw candidate JSON
- Download button for the selected candidate JSON
- Collapsible full-run JSON output

## Pipeline Design

The implementation follows a fixed seven-step pipeline:

```text
DETECT -> EXTRACT -> NORMALIZE -> MERGE -> CONFIDENCE -> PROJECT -> VALIDATE
```

`DETECT`: Checks whether each source exists and is usable. Missing or empty optional sources do not crash the run.

`EXTRACT`: Converts each source into a shared `SourceValue` format with `field`, `value`, `source`, `method`, `structured`, and `confidence`.

`NORMALIZE`: Cleans values before merge. Phones are normalized to E.164, countries to ISO-3166 alpha-2, skills to canonical lowercase names, and unknown values stay `null` rather than being invented.

`MERGE`: Deduplicates candidates and resolves conflicts. Email, GitHub username, phone, and normalized name are used as match signals. Structured recruiter data is preferred for core identity fields, while skills are unioned across sources.

`CONFIDENCE`: Assigns deterministic confidence. Repeated evidence across sources scores higher; inferred or weakly parsed values score lower; missing values score `0.0`.

`PROJECT`: Applies runtime output config. This layer can select fields, rename paths, normalize projected values, include or remove confidence, and choose missing-field behavior.

`VALIDATE`: Validates canonical profiles before projection and validates the projected output before writing JSON.

## Runtime Config

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
    { "path": "id", "from": "candidate_id", "type": "string", "required": true },
    { "path": "name", "from": "full_name", "type": "string", "required": true },
    { "path": "primary_email", "from": "emails[0]", "type": "string", "required": true },
    { "path": "phone", "from": "phones[0]", "type": "string", "normalize": "E164" },
    { "path": "skills", "from": "skills[].name", "type": "string[]", "normalize": "canonical" },
    { "path": "score", "from": "overall_confidence", "type": "number" },
    { "path": "match_confidence", "type": "number" }
  ],
  "include_confidence": false,
  "on_missing": "null"
}
```

Supported `on_missing` values:

- `null`: include missing requested fields as `null`
- `omit`: remove missing requested fields
- `error`: fail if a requested field is missing

## Output Schema

The default canonical profile contains:

```text
candidate_id
full_name
emails
phones
location
links
headline
years_experience
skills
experience
education
provenance
conflicts
match_confidence
overall_confidence
confidence
```

Sample outputs are committed at:

- `transformer/output/default_output.json`
- `transformer/output/custom_output.json`

## Robustness And Edge Cases

Handled cases:

- Missing CSV, GitHub usernames, or notes source
- Malformed or empty optional fields
- GitHub username not found
- Duplicate CSV rows for the same candidate
- Conflicting names or locations across sources
- Invalid phone values
- Missing GitHub bio or repository data
- Extra CSV columns
- Runtime config requests for missing fields

The transformer is deterministic: the same inputs and config produce the same output ordering and JSON content.

## Tests

The test suite covers:

- Phone, country, date, and skill normalization
- Conservative recruiter-notes extraction
- Candidate merge and conflict behavior
- Runtime projection and missing-field behavior

Run:

```powershell
python -m unittest discover -s transformer/tests
```

## Demo Flow For Evaluation

1. Run tests.

```powershell
python -m unittest discover -s transformer/tests
```

2. Run the CLI default output command.

```powershell
python -m transformer.main `
  --csv transformer/sample_inputs/candidates.csv `
  --github-usernames transformer/sample_inputs/github_usernames.txt `
  --notes transformer/sample_inputs/recruiter_notes.txt `
  --config transformer/config.json `
  --output transformer/output/default_output.json
```

3. Start the UI.

```powershell
cd ui
npm install
npm run dev
```

4. Click `Run Pipeline`.

5. Show the default raw JSON view, profile details toggle, provenance entries, conflicts, and JSON download.

6. Change the runtime config to `transformer/custom_config.json` shape, rerun, and show the projected output.

## Notes And Assumptions

- The GitHub source uses the public GitHub API and may be rate-limited without authentication.
- Recruiter notes parsing is intentionally conservative. Uncertain text is not invented into profile fields.
- The UI is a thin input/output surface. Core correctness lives in the Python transformer.
- Temporary UI runtime files are written under `transformer/output/ui_runtime/`.
- Generated build artifacts under `ui/dist/` are not required to run the project from source.
