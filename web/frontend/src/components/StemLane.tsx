import { useEffect, useRef, useState, type CSSProperties } from "react";
import WaveSurfer from "wavesurfer.js";
import Spectrogram from "wavesurfer.js/dist/plugins/spectrogram.esm.js";

type StemLaneProps = {
  id: string;
  label: string;
  url: string;
  color: string;
  isSoloed: boolean;
  anotherStemSoloed: boolean;
  onSolo: (id: string | null) => void;
  syncTime: number;
  onTime: (time: number) => void;
  isClockSource: boolean;
  onRegisterPlayer: (id: string, player: WaveSurfer | null) => void;
  onTogglePlayback: (id: string) => void;
  onPlaybackEnded: () => void;
};

/** A WaveSurfer lane with shared playback, level, mute, solo, and download controls. */
export function StemLane({
  id,
  label,
  url,
  color,
  isSoloed,
  anotherStemSoloed,
  onSolo,
  syncTime,
  onTime,
  isClockSource,
  onRegisterPlayer,
  onTogglePlayback,
  onPlaybackEnded,
}: StemLaneProps) {
  const waveform = useRef<HTMLDivElement>(null);
  const instance = useRef<WaveSurfer | null>(null);
  const clockSourceRef = useRef(isClockSource);
  const [ready, setReady] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [volume, setVolume] = useState(0.85);

  useEffect(() => {
    clockSourceRef.current = isClockSource;
  }, [isClockSource]);

  useEffect(() => {
    if (!waveform.current) return;
    setReady(false);
    const wavesurfer = WaveSurfer.create({
      container: waveform.current,
      url,
      height: 74,
      waveColor: `${color}88`,
      progressColor: color,
      cursorColor: "#e8fbff",
      barWidth: 2,
      barGap: 2,
      normalize: true,
      plugins: [Spectrogram.create({ height: 46, labels: true, labelsColor: "#6e8696" })],
    });
    instance.current = wavesurfer;
    onRegisterPlayer(id, wavesurfer);
    wavesurfer.on("ready", () => setReady(true));
    wavesurfer.on("play", () => setPlaying(true));
    wavesurfer.on("pause", () => setPlaying(false));
    wavesurfer.on("finish", () => {
      setPlaying(false);
      onPlaybackEnded();
    });
    wavesurfer.on("timeupdate", (time) => {
      if (clockSourceRef.current) onTime(time);
    });
    return () => {
      onRegisterPlayer(id, null);
      instance.current = null;
      wavesurfer.destroy();
    };
  }, [url, color, onTime, onRegisterPlayer, onPlaybackEnded, id]);

  useEffect(() => {
    const audible = !muted && (!anotherStemSoloed || isSoloed);
    instance.current?.setVolume(audible ? volume : 0);
  }, [muted, volume, isSoloed, anotherStemSoloed]);

  useEffect(() => {
    const current = instance.current?.getCurrentTime() ?? 0;
    if (Math.abs(current - syncTime) > 0.08) instance.current?.setTime(syncTime);
  }, [syncTime]);

  return <article className="stem-lane" style={{ "--stem": color } as CSSProperties}>
    <div className="stem-head">
      <div><p className="eyebrow">STEM</p><h3>{label}</h3></div>
      <div className="lane-actions">
        <button className="icon-button" disabled={!ready} onClick={() => onTogglePlayback(id)} aria-label={`${playing ? "Pause" : "Play"} ${label}`}>{playing ? "Ⅱ" : "▶"}</button>
        <button className={isSoloed ? "toggle active" : "toggle"} onClick={() => onSolo(isSoloed ? null : id)} aria-pressed={isSoloed}>Solo</button>
        <button className={muted ? "toggle active" : "toggle"} onClick={() => setMuted(!muted)} aria-pressed={muted}>Mute</button>
        <label className="volume">Level <input aria-label={`${label} volume`} type="range" min="0" max="1" step="0.01" value={volume} onChange={(event) => setVolume(Number(event.target.value))} /></label>
        <a className="download" href={url} download>Download</a>
      </div>
    </div>
    <div className="wave-shell"><div ref={waveform} aria-label={`${label} waveform and spectrogram`} /></div>
  </article>;
}
