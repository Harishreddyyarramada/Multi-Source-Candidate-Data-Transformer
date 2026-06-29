import { useEffect, useMemo, useState } from "react";
import {
  CheckCircle2,
  ClipboardList,
  Code2,
  Database,
  FileJson,
  GitBranch,
  Loader2,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles
} from "lucide-react";

const fallbackCsv =
  "name,email,phone,current_company,title\nAsha Rao,asha@example.com,9876543210,Eightfold.ai,Software Engineering Intern Candidate\n";

const fallbackUsernames = "octocat\n";

const fallbackConfig = {
  fields: null,
  include_confidence: true,
  on_missing: "null"
};

const stages = [
  ["Detect", "Find valid CSV and GitHub sources."],
  ["Extract", "Convert inputs into standard SourceValue records."],
  ["Normalize", "Clean phones, countries, dates, emails, and skills."],
  ["Merge", "Resolve conflicts with source priority and provenance."],
  ["Confidence", "Score fields and profile-level reliability."],
  ["Project", "Apply runtime field selection and renaming."],
  ["Validate", "Check schema before returning JSON."]
];

export default function App() {
  const [csv, setCsv] = useState(fallbackCsv);
  const [usernames, setUsernames] = useState(fallbackUsernames);
  const [configText, setConfigText] = useState(JSON.stringify(fallbackConfig, null, 2));
  const [result, setResult] = useState(null);
  const [logs, setLogs] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch("/api/sample")
      .then((response) => response.json())
      .then((sample) => {
        if (sample.csv) setCsv(sample.csv);
        if (sample.usernames) setUsernames(sample.usernames);
        if (sample.config) setConfigText(JSON.stringify(sample.config, null, 2));
      })
      .catch(() => {
        setLogs("Using built-in sample values because the backend sample endpoint was unavailable.");
      });
  }, []);

  const firstProfile = Array.isArray(result) && result.length > 0 ? result[0] : null;
  const confidence = firstProfile?.overall_confidence ?? firstProfile?.score ?? null;

  const configValid = useMemo(() => {
    try {
      JSON.parse(configText);
      return true;
    } catch {
      return false;
    }
  }, [configText]);

  async function runPipeline() {
    setLoading(true);
    setError("");
    setLogs("");
    try {
      const parsedConfig = JSON.parse(configText);
      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ csv, usernames, config: parsedConfig })
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Pipeline failed.");
      setResult(payload.output);
      setLogs(payload.logs);
    } catch (runError) {
      setError(runError.message);
    } finally {
      setLoading(false);
    }
  }

  function resetSamples() {
    setCsv(fallbackCsv);
    setUsernames(fallbackUsernames);
    setConfigText(JSON.stringify(fallbackConfig, null, 2));
    setResult(null);
    setError("");
    setLogs("");
  }

  return (
    <main className="app-shell">
      <section className="topbar">
        <div>
          <div className="eyebrow">
            <Sparkles size={16} />
            Eightfold.ai Internship Assignment
          </div>
          <h1>Candidate Data Transformer</h1>
          <p>Run CSV and GitHub sources through the deterministic canonical profile pipeline.</p>
        </div>
        <div className="status-strip" aria-label="Pipeline contract">
          <span><ShieldCheck size={16} /> No invented values</span>
          <span><GitBranch size={16} /> Provenance tracked</span>
          <span><CheckCircle2 size={16} /> Schema validated</span>
        </div>
      </section>

      <section className="stage-row" aria-label="Pipeline stages">
        {stages.map(([name, detail], index) => (
          <article className="stage" key={name} title={detail}>
            <span>{index + 1}</span>
            <strong>{name}</strong>
          </article>
        ))}
      </section>

      <section className="workspace">
        <div className="panel input-panel">
          <PanelTitle icon={<Database size={18} />} title="Sources" />
          <label>
            Recruiter CSV
            <textarea value={csv} onChange={(event) => setCsv(event.target.value)} spellCheck="false" />
          </label>
          <label>
            GitHub usernames
            <textarea
              className="short-textarea"
              value={usernames}
              onChange={(event) => setUsernames(event.target.value)}
              spellCheck="false"
            />
          </label>
        </div>

        <div className="panel config-panel">
          <PanelTitle icon={<Code2 size={18} />} title="Runtime Config" />
          <label>
            Projection JSON
            <textarea
              value={configText}
              onChange={(event) => setConfigText(event.target.value)}
              spellCheck="false"
            />
          </label>
          <div className="actions">
            <button className="primary-button" onClick={runPipeline} disabled={loading || !configValid}>
              {loading ? <Loader2 className="spin" size={18} /> : <Play size={18} />}
              {loading ? "Running" : "Run Pipeline"}
            </button>
            <button className="ghost-button" onClick={resetSamples}>
              <RotateCcw size={18} />
              Reset
            </button>
          </div>
          {!configValid && <p className="inline-error">Config JSON is not valid.</p>}
          {error && <p className="inline-error">{error}</p>}
          {logs && <pre className="logs">{logs}</pre>}
        </div>

        <div className="panel output-panel">
          <PanelTitle icon={<FileJson size={18} />} title="Output" />
          {firstProfile ? (
            <>
              <div className="metric-grid">
                <Metric label="Candidate" value={firstProfile.full_name || firstProfile.name || firstProfile.candidate_id || firstProfile.id} />
                <Metric label="Confidence" value={confidence === null ? "n/a" : confidence} />
                <Metric label="Skills" value={(firstProfile.skills || []).length} />
              </div>
              <pre className="json-view">{JSON.stringify(result, null, 2)}</pre>
            </>
          ) : (
            <div className="empty-state">
              <ClipboardList size={42} />
              <strong>Ready to transform</strong>
              <span>Edit inputs or run the sample data to generate canonical JSON.</span>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

function PanelTitle({ icon, title }) {
  return (
    <div className="panel-title">
      {icon}
      <h2>{title}</h2>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

