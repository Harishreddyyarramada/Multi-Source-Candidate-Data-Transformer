import express from "express";
import { execFile } from "node:child_process";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const transformerDir = path.join(projectRoot, "transformer");
const app = express();

app.use(express.json({ limit: "2mb" }));

app.get("/api/sample", async (_request, response) => {
  try {
    const [csv, usernames, config] = await Promise.all([
      readFile(path.join(transformerDir, "sample_inputs", "candidates.csv"), "utf8"),
      readFile(path.join(transformerDir, "sample_inputs", "github_usernames.txt"), "utf8"),
      readFile(path.join(transformerDir, "config.json"), "utf8")
    ]);
    let notes = "";
    try {
      notes = await readFile(path.join(transformerDir, "sample_inputs", "recruiter_notes.txt"), "utf8");
    } catch {
      notes = "";
    }
    response.json({ csv, usernames, notes, config: JSON.parse(config) });
  } catch (error) {
    response.status(500).json({ error: error.message });
  }
});

app.post("/api/run", async (request, response) => {
  let runtimeDir = "";
  try {
    const { csv, usernames, notes, config } = request.body;
    if (typeof csv !== "string" || typeof usernames !== "string" || typeof notes !== "string") {
      return response.status(400).json({ error: "CSV, GitHub usernames, and notes must be text." });
    }

    const parsedConfig = typeof config === "string" ? JSON.parse(config) : config;
    if (!parsedConfig || typeof parsedConfig !== "object" || Array.isArray(parsedConfig)) {
      return response.status(400).json({ error: "Runtime config must be a JSON object." });
    }
    runtimeDir = await mkdtemp(path.join(tmpdir(), "eightfold-ui-runtime-"));

    const csvPath = path.join(runtimeDir, "candidates.csv");
    const usernamesPath = path.join(runtimeDir, "github_usernames.txt");
    const notesPath = path.join(runtimeDir, "recruiter_notes.txt");
    const configPath = path.join(runtimeDir, "config.json");
    const outputPath = path.join(runtimeDir, "output.json");

    await Promise.all([
      writeFile(csvPath, csv, "utf8"),
      writeFile(usernamesPath, usernames, "utf8"),
      writeFile(notesPath, notes, "utf8"),
      writeFile(configPath, JSON.stringify(parsedConfig, null, 2), "utf8")
    ]);

    const result = await runPython([
      "-m",
      "transformer.main",
      "--csv",
      csvPath,
      "--github-usernames",
      usernamesPath,
      "--notes",
      notesPath,
      "--config",
      configPath,
      "--output",
      outputPath
    ]);
    const output = JSON.parse(await readFile(outputPath, "utf8"));
    response.json({ output, logs: result.stderr || result.stdout || "Pipeline completed." });
  } catch (error) {
    response.status(500).json({ error: error.message });
  } finally {
    if (runtimeDir) {
      await rm(runtimeDir, { recursive: true, force: true });
    }
  }
});

function runPython(args) {
  return new Promise((resolve, reject) => {
    execFile("python", args, { cwd: projectRoot, windowsHide: true, timeout: 45000 }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error(stderr || stdout || error.message));
        return;
      }
      resolve({ stdout, stderr });
    });
  });
}

app.listen(5174, "127.0.0.1", () => {
  console.log("API server running at http://127.0.0.1:5174");
});
