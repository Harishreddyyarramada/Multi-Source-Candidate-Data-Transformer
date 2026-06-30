import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  CheckCircle2,
  ClipboardList,
  Code2,
  Database,
  Download,
  Edit3,
  ExternalLink,
  FileJson,
  GitBranch,
  Link as LinkIcon,
  Loader2,
  Mail,
  MapPin,
  Phone,
  Play,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  Upload,
  UserRound
} from "lucide-react";

const fallbackCsv =
  "name,email,phone,current_company,title,location,github_username,linkedin_url,portfolio_url,skills,years_experience\nAsha Rao,asha@example.com,9876543210,Eightfold.ai,Software Engineering Intern Candidate,\"Bengaluru, India\",octocat,https://linkedin.com/in/asha-rao,https://asha.dev,\"Python; React; SQL\",1.5\nRavi Kumar,ravi@example.com,+1 415 555 0100,CloudWorks,Backend Engineer,\"San Francisco, USA\",missing-eightfold-user,https://linkedin.com/in/ravi-kumar,https://ravi.dev,\"Go; Docker; Kubernetes\",4\nMeera Shah,meera@example.com,9876543211,DataNest,Data Analyst,\"Mumbai, India\",,https://linkedin.com/in/meera-shah,,\"Python; SQL; pandas\",2\nAsha Rao,asha@example.com,+91 98765 43210,Duplicate Co,Duplicate Row,\"Bengaluru, India\",octocat,,,,\n";

const fallbackUsernames = "octocat\nmissing-eightfold-user\n";
const fallbackNotes =
  "Asha Rao is based in Bengaluru, India.\nEmail: asha@example.com\nPhone: +91 98765 43210\nStrong Python, React, SQL and Docker candidate.\n\nRavi Kumar is based in San Francisco, USA.\nEmail: ravi@example.com\nStrong Go, Docker and Kubernetes backend engineer.\n\nMeera Shah is based in Mumbai, India.\nEmail: meera@example.com\nStrong Python, SQL and pandas analyst.\n";

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
  const [notes, setNotes] = useState(fallbackNotes);
  const [configText, setConfigText] = useState(JSON.stringify(fallbackConfig, null, 2));
  const [result, setResult] = useState(null);
  const [logs, setLogs] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [activeStage, setActiveStage] = useState(-1);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [outputView, setOutputView] = useState("json");
  const [csvMode, setCsvMode] = useState("editor");
  const [uploadedCsvName, setUploadedCsvName] = useState("");

  useEffect(() => {
    fetch("/api/sample")
      .then((response) => response.json())
      .then((sample) => {
        if (sample.csv) setCsv(sample.csv);
        if (sample.usernames) setUsernames(sample.usernames);
        if (sample.notes) setNotes(sample.notes);
        if (sample.config) setConfigText(JSON.stringify(sample.config, null, 2));
      })
      .catch(() => {
        setLogs("Using built-in sample values because the backend sample endpoint was unavailable.");
      });
  }, []);

  const profiles = Array.isArray(result) ? result : [];
  const selectedProfile = profiles[selectedIndex] || profiles[0] || null;
  const confidence = selectedProfile?.overall_confidence ?? selectedProfile?.score ?? null;

  const configValid = useMemo(() => {
    try {
      JSON.parse(configText);
      return true;
    } catch {
      return false;
    }
  }, [configText]);

  useEffect(() => {
    if (!loading) return undefined;
    setActiveStage(0);
    const timer = window.setInterval(() => {
      setActiveStage((stage) => Math.min(stage + 1, stages.length - 1));
    }, 650);
    return () => window.clearInterval(timer);
  }, [loading]);

  async function runPipeline() {
    setLoading(true);
    setError("");
    setLogs("");
    setResult(null);
    try {
      const parsedConfig = JSON.parse(configText);
      const response = await fetch("/api/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ csv, usernames, notes, config: parsedConfig })
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "Pipeline failed.");
      setResult(payload.output);
      setSelectedIndex(0);
      setLogs(payload.logs);
      setActiveStage(stages.length);
      setOutputView("json");
    } catch (runError) {
      setError(runError.message);
      setActiveStage(-1);
    } finally {
      setLoading(false);
    }
  }

  function resetSamples() {
    setCsv(fallbackCsv);
    setUsernames(fallbackUsernames);
    setNotes(fallbackNotes);
    setConfigText(JSON.stringify(fallbackConfig, null, 2));
    setResult(null);
    setError("");
    setLogs("");
    setActiveStage(-1);
    setSelectedIndex(0);
    setOutputView("json");
    setCsvMode("editor");
    setUploadedCsvName("");
  }

  async function uploadCsv(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setCsv(await file.text());
    setUploadedCsvName(file.name);
    event.target.value = "";
  }

  function downloadSelectedJson() {
    if (!selectedProfile) return;
    const baseName = selectedProfile.candidate_id || profileName(selectedProfile).toLowerCase().replace(/[^a-z0-9]+/g, "-");
    downloadJson(selectedProfile, `${baseName || "candidate"}-profile.json`);
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

      <section className="stage-row" aria-label="Live pipeline stages">
        {stages.map(([name, detail], index) => (
          <div className="stage-step" key={name}>
            <article className={stageClass(index, activeStage, loading)} title={detail}>
              <span>{index + 1}</span>
              <strong>{name}</strong>
              <small>{stageStatus(index, activeStage, loading)}</small>
            </article>
            {index < stages.length - 1 && (
              <ArrowRight
                className={index < activeStage ? "stage-arrow stage-arrow-done" : "stage-arrow"}
                size={20}
                aria-hidden="true"
              />
            )}
          </div>
        ))}
      </section>

      <section className="workspace">
        <div className="panel input-panel">
          <PanelTitle icon={<Database size={18} />} title="Sources" />
          <div className="source-control">
            <div className="source-header">
              <span>Recruiter CSV</span>
              <div className="source-toggle" aria-label="Recruiter CSV input mode">
                <button
                  className={csvMode === "upload" ? "source-toggle-button source-toggle-active" : "source-toggle-button"}
                  onClick={() => setCsvMode("upload")}
                  type="button"
                >
                  <Upload size={15} />
                  Upload CSV
                </button>
                <button
                  className={csvMode === "editor" ? "source-toggle-button source-toggle-active" : "source-toggle-button"}
                  onClick={() => setCsvMode("editor")}
                  type="button"
                >
                  <Edit3 size={15} />
                  Manual editor
                </button>
              </div>
            </div>
            {csvMode === "upload" ? (
              <div className="upload-dropzone">
              <input id="csv-upload" type="file" accept=".csv,text/csv" onChange={uploadCsv} />
              <label className="upload-button" htmlFor="csv-upload">
                <Upload size={16} />
                Choose CSV file
              </label>
                {uploadedCsvName ? (
                  <p className="upload-success">Successfully uploaded: <strong>{uploadedCsvName}</strong></p>
                ) : (
                  <p className="upload-hint">The selected file will replace the CSV text used by the pipeline.</p>
                )}
              </div>
            ) : (
              <label>
                Manual CSV editor
                <textarea value={csv} onChange={(event) => setCsv(event.target.value)} spellCheck="false" />
              </label>
            )}
          </div>
          <label>
            GitHub usernames
            <textarea
              className="short-textarea"
              value={usernames}
              onChange={(event) => setUsernames(event.target.value)}
              spellCheck="false"
            />
          </label>
          <label>
            Recruiter notes
            <textarea
              className="short-textarea"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
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
          <PanelTitle icon={<FileJson size={18} />} title="Candidate Output" />
          {selectedProfile ? (
            <>
              <div className="metric-grid">
                <Metric label="Unique Profiles from CSV and Github" value={profiles.length} />
                <Metric label="Confidence" value={confidence === null ? "n/a" : confidence} />
                <Metric label="Skills" value={profileSkills(selectedProfile).length} />
              </div>
              <div className="profile-browser">
                <aside className="profile-list" aria-label="Unique candidates">
                  {profiles.map((profile, index) => (
                    <button
                      className={index === selectedIndex ? "profile-list-item profile-list-item-active" : "profile-list-item"}
                      key={profile.candidate_id || profile.id || index}
                      onClick={() => {
                        setSelectedIndex(index);
                      }}
                    >
                      <UserRound size={18} />
                      <span>
                        <strong>{profileName(profile)}</strong>
                        <small>{primaryEmail(profile) || profile.candidate_id || profile.id}</small>
                      </span>
                    </button>
                  ))}
                </aside>
                <div className="profile-content">
                  <div className="output-view-toolbar" aria-label="Candidate output view">
                    <button
                      className={outputView === "details" ? "view-toggle view-toggle-active" : "view-toggle"}
                      onClick={() => setOutputView("details")}
                      type="button"
                    >
                      <UserRound size={16} />
                      Profile details
                    </button>
                    <button
                      className={outputView === "json" ? "view-toggle view-toggle-active" : "view-toggle"}
                      onClick={() => setOutputView("json")}
                      type="button"
                    >
                      <FileJson size={16} />
                      View raw JSON
                    </button>
                    <button
                      className="download-json-button"
                      onClick={downloadSelectedJson}
                      type="button"
                    >
                      <Download size={16} />
                      Download JSON
                    </button>
                  </div>
                  {outputView === "details" ? (
                    <ProfileDetail profile={selectedProfile} />
                  ) : (
                    <CandidateJsonPanel profile={selectedProfile} index={selectedIndex} />
                  )}
                </div>
              </div>
              <details className="raw-output">
                <summary>Full run JSON</summary>
                <pre className="json-view">{JSON.stringify(result, null, 2)}</pre>
              </details>
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

function CandidateJsonPanel({ profile, index }) {
  const fieldCount = Object.keys(profile || {}).length;

  return (
    <section className="candidate-json-panel" aria-label="Selected candidate raw JSON">
      <div className="json-panel-header">
        <div>
          <span>Raw candidate JSON</span>
          <strong>{profileName(profile)}</strong>
        </div>
        <small>#{index + 1}, {fieldCount} fields</small>
      </div>
      <pre className="json-view candidate-json-view">{JSON.stringify(profile, null, 2)}</pre>
    </section>
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

function ProfileDetail({ profile }) {
  const links = profile.links || {};
  const skills = profileSkills(profile);
  const experience = profile.experience || [];
  const conflicts = Object.entries(profile.conflicts || {});
  const provenance = profile.provenance || [];

  return (
    <section className="profile-detail">
      <header className="profile-header">
        <div>
          <h2>{profileName(profile)}</h2>
          <p>{profile.headline || currentTitle(profile) || "Candidate profile"}</p>
        </div>
        <div className="score-stack">
          <span>Overall {formatScore(profile.overall_confidence ?? profile.score)}</span>
          <span>Match {formatScore(profile.match_confidence)}</span>
        </div>
      </header>

      <div className="detail-grid">
        <InfoItem icon={<Mail size={16} />} label="Email" value={primaryEmail(profile)} />
        <InfoItem icon={<Phone size={16} />} label="Phone" value={primaryPhone(profile)} />
        <InfoItem icon={<MapPin size={16} />} label="Location" value={formatLocation(profile.location)} />
        <InfoItem icon={<LinkIcon size={16} />} label="Candidate ID" value={profile.candidate_id || profile.id} />
      </div>

      <section className="detail-section">
        <h3>Links</h3>
        <div className="link-row">
          <ExternalAnchor label="LinkedIn" href={links.linkedin} />
          <ExternalAnchor label="GitHub" href={links.github || profile.github} />
          <ExternalAnchor label="Portfolio" href={links.portfolio} />
          {(links.other || []).map((href) => <ExternalAnchor key={href} label="Other" href={href} />)}
        </div>
      </section>

      <section className="detail-section">
        <h3>Skills</h3>
        <div className="skill-row">
          {skills.length ? skills.map((skill) => (
            <span className="skill-pill" key={skill.name || skill}>
              {skill.name || skill}
              {skill.confidence !== undefined && <small>{formatScore(skill.confidence)}</small>}
            </span>
          )) : <span className="muted">No skills found</span>}
        </div>
      </section>

      <section className="detail-section">
        <h3>Experience</h3>
        {experience.length ? experience.map((item, index) => (
          <article className="experience-item" key={`${item.company}-${item.title}-${index}`}>
            <strong>{item.title || "Role unknown"}</strong>
            <span>{item.company || "Company unknown"}</span>
            {(item.start || item.end) && <small>{item.start || "?"} - {item.end || "Present"}</small>}
          </article>
        )) : <span className="muted">No experience found</span>}
      </section>

      {conflicts.length > 0 && (
        <section className="detail-section">
          <h3>Conflicts Resolved</h3>
          <div className="evidence-list">
            {conflicts.map(([field, items]) => (
              <div className="evidence-item" key={field}>
                <strong>{field}</strong>
                <span>{items.length} source values, chosen value marked in output JSON</span>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="detail-section">
        <h3>Evidence Trail</h3>
        <div className="evidence-list">
          {provenance.slice(0, 8).map((item, index) => (
            <div className="evidence-item" key={`${item.field}-${item.source}-${item.method}-${index}`}>
              <strong>{item.field}</strong>
              <span>{item.source} via {item.method}</span>
            </div>
          ))}
          {provenance.length > 8 && <span className="muted">+{provenance.length - 8} more evidence entries in raw JSON</span>}
        </div>
      </section>
    </section>
  );
}

function InfoItem({ icon, label, value }) {
  return (
    <div className="info-item">
      {icon}
      <span>{label}</span>
      <strong>{value || "Not available"}</strong>
    </div>
  );
}

function ExternalAnchor({ href, label }) {
  if (!href) return <span className="link-chip link-chip-empty">{label}: not available</span>;
  return (
    <a className="link-chip" href={href} target="_blank" rel="noreferrer">
      {label}
      <ExternalLink size={14} />
    </a>
  );
}

function profileName(profile) {
  return profile.full_name || profile.name || profile.candidate_id || profile.id || "Unknown candidate";
}

function primaryEmail(profile) {
  return profile.primary_email || profile.emails?.[0] || profile.contact_emails?.[0] || "";
}

function primaryPhone(profile) {
  return profile.phone || profile.phones?.[0] || profile.contact_phones?.[0] || "";
}

function profileSkills(profile) {
  return Array.isArray(profile.skills) ? profile.skills : [];
}

function currentTitle(profile) {
  return profile.experience?.[0]?.title || "";
}

function formatLocation(location) {
  if (!location) return "";
  return [location.city, location.region, location.country].filter(Boolean).join(", ");
}

function formatScore(value) {
  return value === undefined || value === null ? "n/a" : Number(value).toFixed(2);
}

function stageClass(index, activeStage, loading) {
  if (activeStage > index) return "stage stage-done";
  if (loading && activeStage === index) return "stage stage-active";
  return "stage";
}

function stageStatus(index, activeStage, loading) {
  if (activeStage > index) return "Done";
  if (loading && activeStage === index) return "Running";
  return "Pending";
}

function downloadJson(data, filename) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
