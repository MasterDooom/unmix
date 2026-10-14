import { ChangeEvent, FormEvent, useMemo, useState } from "react";
import { StemLane } from "./components/StemLane";

type Mode = "track" | "mix";
type Stem = { name: string; url: string };
type TrackResult = { stems: Stem[] };
type MixResult = TrackResult & {
  sample_rate: number; converged: boolean; iterations: number; mixture_url: string;
  metrics: { mean_absolute_correlation: number; mean_si_sdr_db: number; per_source: Array<{ source_index: number; estimate_index: number; absolute_correlation: number; si_sdr_db: number }> };
};

const colors = ["#3be3b1", "#5fb7ff", "#a987ff", "#f4b864", "#ff7f9b", "#52d9e9"];
const identityMatrix = (count: number) => JSON.stringify(Array.from({ length: count }, (_, row) => Array.from({ length: count }, (_, column) => row === column ? 1 : 0)), null, 2);
const requestError = async (response: Response) => {
  const body = await response.json().catch(() => ({}));
  return body.detail || `Request failed (${response.status}).`;
};

function UploadPanel({ mode, onTrack, onMix }: { mode: Mode; onTrack: (file: File) => void; onMix: (files: FileList) => void }) {
  const [track, setTrack] = useState<File | null>(null);
  const [sources, setSources] = useState<FileList | null>(null);
  const submit = (event: FormEvent) => { event.preventDefault(); if (mode === "track" && track) onTrack(track); if (mode === "mix" && sources) onMix(sources); };
  return <form className="upload-panel" onSubmit={submit}>
    <div className="upload-copy"><p className="eyebrow">{mode === "track" ? "PRETRAINED STEM ESTIMATION" : "FROM-SCRATCH ICA EXPERIMENT"}</p><h2>{mode === "track" ? "Open a finished track" : "Bring in clean source tracks"}</h2><p>{mode === "track" ? "Estimate the stems a supported model returns. They are estimates, not the original studio tracks." : "Create a known linear mix and measure blind recovery without assuming a fixed source count."}</p></div>
    <label className="dropzone"><input aria-label={mode === "track" ? "Track file" : "Source files"} type="file" accept="audio/*,.flac,.ogg,.m4a" multiple={mode === "mix"} onChange={(event: ChangeEvent<HTMLInputElement>) => mode === "track" ? setTrack(event.target.files?.[0] ?? null) : setSources(event.target.files)} />
      <span>⇧</span><strong>{mode === "track" ? track?.name ?? "Choose an audio file" : sources?.length ? `${sources.length} source files selected` : "Choose two or more source files"}</strong><small>WAV, FLAC, MP3, M4A, or OGG · 100 MB per file</small>
    </label>
    <button className="primary" type="submit" disabled={mode === "track" ? !track : !sources || sources.length < 2}>{mode === "track" ? "Estimate stems" : "Set up Mix Lab"}</button>
  </form>;
}

function StemBoard({ stems, original, mixture }: { stems: Stem[]; original?: Stem; mixture?: Stem }) {
  const [solo, setSolo] = useState<string | null>(null);
  const [syncTime, setSyncTime] = useState(0);
  const rows = [...(original ? [original] : []), ...(mixture ? [mixture] : []), ...stems];
  return <section className="results" aria-live="polite"><div className="section-title"><div><p className="eyebrow">PLAYBACK DESK</p><h2>Waveform + spectral detail</h2></div><p>Each lane shares a visual playback cursor; solo, mute, level, and download use actual returned audio files.</p></div>
    {rows.map((stem, index) => <StemLane key={`${stem.name}-${stem.url}`} id={`${stem.name}-${index}`} label={stem.name.replace(/_/g, " ")} url={stem.url} color={colors[index % colors.length]} isSoloed={solo === `${stem.name}-${index}`} anotherStemSoloed={solo !== null} onSolo={setSolo} syncTime={syncTime} onTime={setSyncTime} />)}
  </section>;
}

function Metrics({ result }: { result: MixResult }) {
  return <section className="metrics"><p className="eyebrow">AMBIGUITY-AWARE EVALUATION</p><h2>Recovery report</h2><div className="metric-grid"><div><strong>{result.metrics.mean_absolute_correlation.toFixed(3)}</strong><span>mean |correlation|</span></div><div><strong>{result.metrics.mean_si_sdr_db.toFixed(1)} dB</strong><span>mean SI-SDR</span></div><div><strong>{result.iterations}</strong><span>FastICA iterations</span></div><div><strong>{result.converged ? "Yes" : "No"}</strong><span>converged</span></div></div><p className="metric-note">Matches account for component order, sign, and scale. PCA whitening is the baseline transform; FastICA is the recovered output shown above.</p></section>;
}

export default function App() {
  const [mode, setMode] = useState<Mode>("track");
  const [trackFile, setTrackFile] = useState<File | null>(null);
  const [sourceFiles, setSourceFiles] = useState<File[]>([]);
  const [matrix, setMatrix] = useState(identityMatrix(2));
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [trackResult, setTrackResult] = useState<TrackResult | null>(null);
  const [mixResult, setMixResult] = useState<MixResult | null>(null);
  const sourcePreviews = useMemo(() => mixResult ? sourceFiles.map((file) => ({ name: `source · ${file.name}`, url: URL.createObjectURL(file) })) : [], [sourceFiles, mixResult]);
  const original = useMemo(() => trackResult && trackFile ? { name: `original · ${trackFile.name}`, url: URL.createObjectURL(trackFile) } : undefined, [trackFile, trackResult]);

  const chooseTrack = async (file: File) => {
    setTrackFile(file); setTrackResult(null); setError(null); setProcessing(true);
    const form = new FormData(); form.append("track", file);
    try { const response = await fetch("/api/track-lab/separate", { method: "POST", body: form }); if (!response.ok) throw new Error(await requestError(response)); setTrackResult(await response.json()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Track Lab could not process this file."); }
    finally { setProcessing(false); }
  };
  const chooseMix = (files: FileList) => { const selected = Array.from(files); setSourceFiles(selected); setMatrix(identityMatrix(selected.length)); setMixResult(null); setError(null); };
  const runMix = async () => {
    if (sourceFiles.length < 2) return; setError(null); setProcessing(true);
    const form = new FormData(); sourceFiles.forEach((source) => form.append("sources", source)); form.append("mixing_matrix", matrix);
    try { const response = await fetch("/api/mix-lab/separate", { method: "POST", body: form }); if (!response.ok) throw new Error(await requestError(response)); setMixResult(await response.json()); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Mix Lab could not run the experiment."); }
    finally { setProcessing(false); }
  };

  return <main><header><a className="brand" href="#top" aria-label="Unmix home"><span>∿</span> UNMIX</a><nav><button className={mode === "track" ? "nav-active" : ""} onClick={() => setMode("track")}>Track Lab</button><button className={mode === "mix" ? "nav-active" : ""} onClick={() => setMode("mix")}>Mix Lab</button></nav><div className="header-status"><i /> Local workspace</div></header>
    <div id="top" className="hero"><div><p className="eyebrow">MUSIC REVERSE-ENGINEERING WORKSPACE</p><h1>See inside the <em>mix.</em></h1><p className="lede">A rigorous home for source-separation experiments: model-based stem estimates for finished tracks, and a transparent FastICA lab for controlled mixtures.</p></div><aside><span>01 / {mode === "track" ? "TRACK" : "MIX"}</span><p>{mode === "track" ? "Model outputs are useful estimates. They cannot establish original production stems." : "Known source files stay out of the separator and return only for evaluation."}</p></aside></div>
    <section className="workbench"><div className="mode-tabs"><button className={mode === "track" ? "selected" : ""} onClick={() => setMode("track")}>Track Lab <small>pretrained</small></button><button className={mode === "mix" ? "selected" : ""} onClick={() => setMode("mix")}>Mix Lab <small>FastICA</small></button></div>
      <UploadPanel mode={mode} onTrack={chooseTrack} onMix={chooseMix} />
      {mode === "mix" && sourceFiles.length >= 2 && <section className="matrix"><div><p className="eyebrow">MIXING MATRIX A</p><h2>Define observed channels</h2><p>Rows are mixtures; columns are sources. The matrix must be finite, full-column-rank, and have at least as many rows as columns.</p></div><textarea aria-label="Mixing matrix JSON" value={matrix} onChange={(event) => setMatrix(event.target.value)} spellCheck={false} /><button className="primary" onClick={runMix} disabled={processing}>Run ICA recovery</button></section>}
      {processing && <div className="notice working"><span className="spinner" /> Processing audio. The request has a bounded server timeout.</div>}
      {error && <div className="notice error" role="alert">{error}</div>}
      {mode === "track" && trackResult && <StemBoard stems={trackResult.stems} original={original} />}
      {mode === "mix" && mixResult && <><Metrics result={mixResult} /><StemBoard stems={mixResult.stems} mixture={{ name: "generated mixtures", url: mixResult.mixture_url }} />{sourcePreviews.length > 0 && <details><summary>Ground-truth source previews (evaluation only)</summary><StemBoard stems={sourcePreviews} /></details>}</>}
    </section><footer>Upload only audio you have the rights to use. Files are stored in temporary per-job directories and are cleaned after the local retention window.</footer>
  </main>;
}
