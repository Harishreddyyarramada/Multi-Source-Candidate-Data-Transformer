# Multi-Source Candidate Data Transformer

This folder contains the Python transformer package. The full project README is one level above this folder at `../README.md`.

## Pipeline

```text
DETECT -> EXTRACT -> NORMALIZE -> MERGE -> CONFIDENCE -> PROJECT -> VALIDATE
```

## Run From Project Root

```powershell
cd C:\Users\yarra\Desktop\Eightfold
python -m pip install -r requirements.txt
python -m unittest discover -s transformer/tests
python -m transformer.main `
  --csv transformer/sample_inputs/candidates.csv `
  --github-usernames transformer/sample_inputs/github_usernames.txt `
  --notes transformer/sample_inputs/recruiter_notes.txt `
  --config transformer/config.json `
  --output transformer/output/default_output.json
```

## Run UI

```powershell
cd C:\Users\yarra\Desktop\Eightfold\ui
npm install
npm run dev
```

Open:

```text
http://127.0.0.1:5173
```

The UI shows the seven pipeline steps with arrow indicators while the process is running. It supports pasted CSV, CSV upload, GitHub usernames, recruiter notes, and runtime projection config.
