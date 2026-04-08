from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from src.config import Settings
from src.state_store import AppStateStore


def _page_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Screen AI Monitor</title>
  <style>
    :root {
      --bg: #f1efe8;
      --card: #fffdf8;
      --ink: #1e2430;
      --muted: #5b6573;
      --accent: #b24c2b;
      --line: #ddd4c8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(178, 76, 43, 0.14), transparent 28%),
        linear-gradient(135deg, #efe7da, #f7f3ec 45%, #ece6dc);
      color: var(--ink);
    }
    .wrap {
      max-width: 1180px;
      margin: 0 auto;
      padding: 24px;
    }
    .hero {
      padding: 24px;
      border: 1px solid var(--line);
      border-radius: 24px;
      background: rgba(255, 253, 248, 0.86);
      backdrop-filter: blur(10px);
      box-shadow: 0 18px 55px rgba(60, 40, 20, 0.08);
    }
    h1 {
      margin: 0;
      font-size: 34px;
      line-height: 1.05;
      letter-spacing: 0.02em;
    }
    .sub {
      margin-top: 10px;
      color: var(--muted);
    }
    .status {
      display: inline-block;
      margin-top: 16px;
      padding: 10px 14px;
      border-radius: 999px;
      background: #f8e7df;
      color: var(--accent);
      font-weight: 700;
    }
    .grid {
      display: grid;
      grid-template-columns: 1.25fr 0.75fr;
      gap: 18px;
      margin-top: 18px;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px;
      box-shadow: 0 10px 35px rgba(60, 40, 20, 0.06);
    }
    .click-card {
      cursor: pointer;
      transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
    }
    .click-card:hover {
      transform: translateY(-2px);
      border-color: #c8a98d;
      box-shadow: 0 16px 40px rgba(60, 40, 20, 0.1);
    }
    .image-shell {
      min-height: 420px;
      display: flex;
      align-items: center;
      justify-content: center;
      overflow: hidden;
      border-radius: 16px;
      background: linear-gradient(135deg, #e9e0d2, #fbfaf7);
      border: 1px dashed #cebfae;
    }
    img {
      width: 100%;
      display: block;
      border-radius: 14px;
    }
    pre {
      white-space: pre-wrap;
      word-break: break-word;
      margin: 0;
      line-height: 1.6;
      font-size: 15px;
    }
    .history-item {
      padding: 12px 0;
      border-top: 1px solid var(--line);
    }
    .meta {
      color: var(--muted);
      font-size: 13px;
      margin-top: 8px;
    }
    @media (max-width: 920px) {
      .grid {
        grid-template-columns: 1fr;
      }
      h1 {
        font-size: 28px;
      }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>Screen AI Capture</h1>
      <div class="sub">Press the global hotkey on the PC and this page will refresh with the newest corrected screen image and AI result.</div>
      <div id="status" class="status">Status: Loading</div>
    </section>
    <section class="grid">
      <article class="card">
        <h2>Latest Raw Image</h2>
        <div class="image-shell">
          <img id="latest-raw-image" alt="latest raw result" style="display:none;" />
          <div id="raw-image-empty">No raw image yet</div>
        </div>
      </article>
      <article class="card">
        <h2>Latest Rectified Image</h2>
        <div class="image-shell">
          <img id="latest-rectified-image" alt="latest rectified result" style="display:none;" />
          <div id="rectified-image-empty">No rectified image yet</div>
        </div>
      </article>
    </section>
    <section id="analysis-card" class="card click-card" style="margin-top:18px;">
      <h2>AI Analysis</h2>
      <pre id="latest-text">No result yet</pre>
      <div id="latest-meta" class="meta"></div>
      <div class="meta">Click to open the analysis in a dedicated tab.</div>
    </section>
    <section class="card" style="margin-top:18px;">
      <h2>Recent History</h2>
      <div id="history">No history yet</div>
    </section>
  </div>
  <script>
    async function refresh() {
      const [statusResp, latestResp, historyResp] = await Promise.all([
        fetch('/api/status'),
        fetch('/api/latest'),
        fetch('/api/history')
      ]);
      const status = await statusResp.json();
      const latest = await latestResp.json();
      const history = await historyResp.json();

      document.getElementById('status').textContent = `Status: ${status.status} | ${status.message}`;

      const rawImage = document.getElementById('latest-raw-image');
      const rawImageEmpty = document.getElementById('raw-image-empty');
      if (latest && latest.raw_capture_url) {
        rawImage.src = `${latest.raw_capture_url}?t=${Date.now()}`;
        rawImage.style.display = 'block';
        rawImageEmpty.style.display = 'none';
      } else {
        rawImage.style.display = 'none';
        rawImageEmpty.style.display = 'block';
      }

      const rectifiedImage = document.getElementById('latest-rectified-image');
      const rectifiedImageEmpty = document.getElementById('rectified-image-empty');
      if (latest && latest.rectified_url) {
        rectifiedImage.src = `${latest.rectified_url}?t=${Date.now()}`;
        rectifiedImage.style.display = 'block';
        rectifiedImageEmpty.style.display = 'none';
      } else {
        rectifiedImage.style.display = 'none';
        rectifiedImageEmpty.style.display = 'block';
      }

      document.getElementById('latest-text').textContent =
        latest ? (latest.summary_text || latest.error_message || 'This run did not return any text') : 'No result yet';
      document.getElementById('latest-meta').textContent =
        latest ? `${latest.created_at} | ${latest.status}` : '';

      const historyWrap = document.getElementById('history');
      if (!history.length) {
        historyWrap.textContent = 'No history yet';
      } else {
        historyWrap.innerHTML = history.map(item => `
          <div class="history-item">
            <strong>${item.record_id}</strong> | ${item.status}
            <div class="meta">${item.created_at}</div>
            <div>${(item.summary_text || item.error_message || '').slice(0, 180)}</div>
          </div>
        `).join('');
      }
    }
    document.getElementById('analysis-card').addEventListener('click', () => {
      window.open('/analysis/latest', '_blank', 'noopener,noreferrer');
    });
    refresh();
    setInterval(refresh, 2000);
  </script>
</body>
</html>"""


def _analysis_page_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI Analysis</title>
  <style>
    :root {
      --bg: #f4efe6;
      --card: #fffdf9;
      --ink: #19202b;
      --muted: #5f6876;
      --accent: #b24c2b;
      --line: #ddd4c8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "PingFang SC", sans-serif;
      background:
        radial-gradient(circle at top right, rgba(178, 76, 43, 0.15), transparent 30%),
        linear-gradient(145deg, #ece4d7, #f7f3ec 42%, #efe8dc);
      color: var(--ink);
    }
    .wrap {
      max-width: 1000px;
      margin: 0 auto;
      padding: 28px;
    }
    .panel {
      background: rgba(255, 253, 249, 0.92);
      border: 1px solid var(--line);
      border-radius: 28px;
      padding: 28px;
      box-shadow: 0 18px 55px rgba(60, 40, 20, 0.08);
      backdrop-filter: blur(10px);
    }
    h1 {
      margin: 0;
      font-size: 40px;
      line-height: 1.05;
      letter-spacing: 0.02em;
    }
    .meta {
      margin-top: 12px;
      color: var(--muted);
      font-size: 14px;
    }
    .tip {
      margin-top: 10px;
      color: var(--accent);
      font-size: 13px;
      letter-spacing: 0.01em;
    }
    pre {
      margin: 24px 0 0;
      white-space: pre-wrap;
      word-break: break-word;
      line-height: 1.8;
      font-size: 19px;
      min-height: 360px;
      color: var(--ink);
    }
    @media (max-width: 720px) {
      .wrap {
        padding: 18px;
      }
      .panel {
        padding: 20px;
        border-radius: 22px;
      }
      h1 {
        font-size: 30px;
      }
      pre {
        font-size: 17px;
      }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <section class="panel">
      <h1>AI Analysis</h1>
      <div id="analysis-meta" class="meta">Loading...</div>
      <div class="tip">Auto scroll mode: pause 10s, then slowly move one section like a teleprompter.</div>
      <pre id="analysis-text">Loading...</pre>
    </section>
  </div>
  <script>
    const teleprompter = {
      pauseMs: 10000,
      moveMs: 6500,
      segmentRatio: 0.58,
      minSegmentPx: 260,
      direction: 1,
      phase: 'pause',
      phaseStartedAt: performance.now(),
      fromY: 0,
      toY: 0,
      contentKey: '',
    };

    function scrollingRoot() {
      return document.scrollingElement || document.documentElement;
    }

    function maxScrollTop() {
      const root = scrollingRoot();
      return Math.max(root.scrollHeight - window.innerHeight, 0);
    }

    function setScrollTop(value) {
      scrollingRoot().scrollTop = value;
    }

    function nextSegmentSize() {
      return Math.max(window.innerHeight * teleprompter.segmentRatio, teleprompter.minSegmentPx);
    }

    function resetTeleprompter(goTop = true) {
      if (goTop) {
        setScrollTop(0);
      }
      teleprompter.direction = 1;
      teleprompter.phase = 'pause';
      teleprompter.phaseStartedAt = performance.now();
      teleprompter.fromY = 0;
      teleprompter.toY = 0;
    }

    function startMove(now) {
      const currentTop = scrollingRoot().scrollTop;
      const maxTop = maxScrollTop();
      if (maxTop <= 1) {
        teleprompter.phase = 'pause';
        teleprompter.phaseStartedAt = now;
        return;
      }

      const segment = nextSegmentSize();
      let target = currentTop + (teleprompter.direction * segment);
      target = Math.max(0, Math.min(maxTop, target));

      if (Math.abs(target - currentTop) < 2) {
        teleprompter.direction = currentTop >= maxTop - 2 ? -1 : 1;
        teleprompter.phase = 'pause';
        teleprompter.phaseStartedAt = now;
        return;
      }

      teleprompter.fromY = currentTop;
      teleprompter.toY = target;
      teleprompter.phase = 'move';
      teleprompter.phaseStartedAt = now;
    }

    function stepTeleprompter(now) {
      if (teleprompter.phase === 'pause') {
        if (now - teleprompter.phaseStartedAt >= teleprompter.pauseMs) {
          startMove(now);
        }
      } else {
        const progress = Math.min((now - teleprompter.phaseStartedAt) / teleprompter.moveMs, 1);
        const eased = 0.5 - (Math.cos(Math.PI * progress) / 2);
        const nextTop = teleprompter.fromY + ((teleprompter.toY - teleprompter.fromY) * eased);
        setScrollTop(nextTop);

        if (progress >= 1) {
          const maxTop = maxScrollTop();
          if (teleprompter.toY >= maxTop - 2) {
            teleprompter.direction = -1;
          } else if (teleprompter.toY <= 2) {
            teleprompter.direction = 1;
          }
          teleprompter.phase = 'pause';
          teleprompter.phaseStartedAt = now;
        }
      }

      window.requestAnimationFrame(stepTeleprompter);
    }

    async function refresh() {
      const latestResp = await fetch('/api/latest');
      const latest = await latestResp.json();
      const meta = document.getElementById('analysis-meta');
      const text = document.getElementById('analysis-text');

      if (!latest) {
        meta.textContent = 'No latest record';
        text.textContent = 'No result yet';
        return;
      }

      const nextText = latest.summary_text || latest.error_message || 'This run did not return any text';
      const nextContentKey = `${latest.record_id || ''}|${latest.created_at || ''}|${latest.status || ''}|${nextText}`;

      meta.textContent = `${latest.created_at} | ${latest.status}`;
      text.textContent = nextText;

      if (teleprompter.contentKey !== nextContentKey) {
        teleprompter.contentKey = nextContentKey;
        resetTeleprompter(true);
      }
    }
    window.addEventListener('resize', () => resetTeleprompter(false));
    refresh();
    setInterval(refresh, 2000);
    window.requestAnimationFrame(stepTeleprompter);
  </script>
</body>
</html>"""


def _decorate_record(record: dict[str, Any] | None) -> dict[str, Any] | None:
    if not record:
        return None
    data = dict(record)
    data["raw_capture_url"] = "/files/" + data["raw_capture_path"] if data.get("raw_capture_path") else None
    data["rectified_url"] = "/files/" + data["rectified_path"] if data.get("rectified_path") else None
    data["debug_url"] = "/files/" + data["debug_path"] if data.get("debug_path") else None
    return data


def create_app(settings: Settings, store: AppStateStore, runtime: Any) -> FastAPI:
    app = FastAPI(title="Screen AI Capture")
    app.mount("/files", StaticFiles(directory=str(settings.output_dir)), name="files")

    @app.get("/", response_class=HTMLResponse)
    def home() -> str:
        return _page_html()

    @app.get("/analysis/latest", response_class=HTMLResponse)
    def analysis_latest() -> str:
        return _analysis_page_html()

    @app.get("/api/status", response_class=JSONResponse)
    def status() -> dict[str, str]:
        return store.snapshot()

    @app.get("/api/latest", response_class=JSONResponse)
    def latest() -> dict[str, Any] | None:
        return _decorate_record(store.latest())

    @app.get("/api/history", response_class=JSONResponse)
    def history() -> list[dict[str, Any]]:
        return [_decorate_record(record) for record in store.history()]

    @app.on_event("shutdown")
    def on_shutdown() -> None:
        runtime.shutdown()

    return app
