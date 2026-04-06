# Screen AI Tool Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a simple Windows Python application that captures stable frames from an Android IP Camera MJPEG stream on global hotkey, rectifies the computer screen, sends the image to a vision model, and serves the latest result on a LAN web page without a database.

**Architecture:** A single Python process hosts both the FastAPI web server and the background capture-analysis pipeline. The code is split into small modules for configuration, task state, MJPEG frame capture, screen detection, best-frame selection, AI analysis, and static result serving so the first version stays simple but debuggable.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, OpenCV, NumPy, Requests, Pydantic, PyYAML, keyboard

---

### Task 1: Scaffold project structure and configuration loading

**Files:**
- Create: `app.py`
- Create: `config.yaml`
- Create: `requirements.txt`
- Create: `README.md`
- Create: `src/__init__.py`
- Create: `src/config.py`
- Create: `src/models.py`
- Create: `src/state_store.py`

**Step 1: Write the failing test**

No test file in first pass. Instead validate by importing `src.config` and loading `config.yaml`.

**Step 2: Run test to verify it fails**

Run: `python -c "from src.config import load_settings; print(load_settings('config.yaml').hotkey)"`
Expected: import or file-not-found failure before implementation.

**Step 3: Write minimal implementation**

Implement:

- `Settings` model
- `AISettings` nested model
- `load_settings(path)` function
- output directory bootstrap helper

**Step 4: Run test to verify it passes**

Run: `python -c "from src.config import load_settings; s=load_settings('config.yaml'); print(s.hotkey)"`
Expected: prints configured hotkey.

**Step 5: Commit**

Skip in this workspace if git repository is unavailable.

### Task 2: Implement result models and in-memory state store

**Files:**
- Modify: `src/models.py`
- Modify: `src/state_store.py`

**Step 1: Write the failing test**

Add a small validation command:

```python
from src.state_store import AppStateStore
store = AppStateStore(history_limit=3)
assert store.snapshot()["status"] == "idle"
```

**Step 2: Run test to verify it fails**

Run: `python -c "from src.state_store import AppStateStore; store=AppStateStore(3); print(store.snapshot()['status'])"`
Expected: class missing before implementation.

**Step 3: Write minimal implementation**

Implement:

- `AnalysisRecord`
- `FrameScore`
- thread-safe `AppStateStore`
- methods to set status, save success, save error, return latest/history

**Step 4: Run test to verify it passes**

Run: `python -c "from src.state_store import AppStateStore; store=AppStateStore(3); print(store.snapshot()['status'])"`
Expected: prints `idle`.

**Step 5: Commit**

Skip if not in git repository.

### Task 3: Implement MJPEG frame capture

**Files:**
- Create: `src/stream_client.py`

**Step 1: Write the failing test**

Use a simple import and constructor smoke check:

```python
from src.stream_client import MjpegStreamClient
client = MjpegStreamClient("http://example/stream", False)
assert client is not None
```

**Step 2: Run test to verify it fails**

Run: `python -c "from src.stream_client import MjpegStreamClient; print(MjpegStreamClient('http://example', False))"`
Expected: import failure before implementation.

**Step 3: Write minimal implementation**

Implement:

- MJPEG byte stream parser
- `capture_frames(frame_count, timeout_sec)` method
- OpenCV JPEG decoding
- clear exceptions on timeout and no frame cases

**Step 4: Run test to verify it passes**

Run: `python -c "from src.stream_client import MjpegStreamClient; print(MjpegStreamClient('http://example', False).__class__.__name__)"`
Expected: prints class name.

**Step 5: Commit**

Skip if not in git repository.

### Task 4: Implement screen detection and perspective rectification

**Files:**
- Create: `src/screen_rectifier.py`

**Step 1: Write the failing test**

Smoke check expected symbols:

```python
from src.screen_rectifier import detect_screen_quad, rectify_screen
assert callable(detect_screen_quad)
assert callable(rectify_screen)
```

**Step 2: Run test to verify it fails**

Run: `python -c "from src.screen_rectifier import detect_screen_quad, rectify_screen; print('ok')"`
Expected: import failure before implementation.

**Step 3: Write minimal implementation**

Implement:

- contour search
- quad scoring
- corner ordering
- perspective transform
- optional debug overlay image

**Step 4: Run test to verify it passes**

Run: `python -c "from src.screen_rectifier import detect_screen_quad, rectify_screen; print(callable(detect_screen_quad), callable(rectify_screen))"`
Expected: prints `True True`.

**Step 5: Commit**

Skip if not in git repository.

### Task 5: Implement multi-frame scoring and best-frame selection

**Files:**
- Create: `src/frame_selector.py`

**Step 1: Write the failing test**

Smoke check exported selector:

```python
from src.frame_selector import select_best_frame
assert callable(select_best_frame)
```

**Step 2: Run test to verify it fails**

Run: `python -c "from src.frame_selector import select_best_frame; print(select_best_frame)"`
Expected: import failure before implementation.

**Step 3: Write minimal implementation**

Implement:

- Laplacian variance sharpness
- per-frame rectifier probe
- stability computation from adjacent quads
- normalized weighted total score
- best-frame payload return

**Step 4: Run test to verify it passes**

Run: `python -c "from src.frame_selector import select_best_frame; print(callable(select_best_frame))"`
Expected: prints `True`.

**Step 5: Commit**

Skip if not in git repository.

### Task 6: Implement AI analysis adapter

**Files:**
- Create: `src/ai_analyzer.py`

**Step 1: Write the failing test**

Smoke check client creation:

```python
from src.ai_analyzer import VisionAnalyzer
assert VisionAnalyzer is not None
```

**Step 2: Run test to verify it fails**

Run: `python -c "from src.ai_analyzer import VisionAnalyzer; print(VisionAnalyzer)"`
Expected: import failure before implementation.

**Step 3: Write minimal implementation**

Implement:

- image to base64 helper
- OpenAI-compatible chat-completions request body
- timeout and error handling
- response text extraction

**Step 4: Run test to verify it passes**

Run: `python -c "from src.ai_analyzer import VisionAnalyzer; print(VisionAnalyzer.__name__)"`
Expected: prints `VisionAnalyzer`.

**Step 5: Commit**

Skip if not in git repository.

### Task 7: Implement FastAPI web server and HTML page

**Files:**
- Create: `src/web_server.py`

**Step 1: Write the failing test**

Smoke check app factory:

```python
from src.web_server import create_app
assert create_app is not None
```

**Step 2: Run test to verify it fails**

Run: `python -c "from src.web_server import create_app; print(create_app)"`
Expected: import failure before implementation.

**Step 3: Write minimal implementation**

Implement:

- FastAPI app factory
- `/api/status`
- `/api/latest`
- `/api/history`
- root HTML page with polling
- static files mount for result images

**Step 4: Run test to verify it passes**

Run: `python -c "from src.web_server import create_app; print(callable(create_app))"`
Expected: prints `True`.

**Step 5: Commit**

Skip if not in git repository.

### Task 8: Wire hotkey and background job pipeline

**Files:**
- Create: `src/hotkey_listener.py`
- Modify: `app.py`

**Step 1: Write the failing test**

Smoke check runner creation:

```python
from app import build_runtime
assert build_runtime() is not None
```

**Step 2: Run test to verify it fails**

Run: `python -c "from app import build_runtime; print(build_runtime())"`
Expected: import failure before implementation.

**Step 3: Write minimal implementation**

Implement:

- runtime wiring
- single-job lock
- hotkey callback
- background pipeline
- uvicorn startup

**Step 4: Run test to verify it passes**

Run: `python -c "from app import build_runtime; print(type(build_runtime()).__name__)"`
Expected: prints runtime class name.

**Step 5: Commit**

Skip if not in git repository.

### Task 9: Verify end-to-end imports and document usage

**Files:**
- Modify: `README.md`

**Step 1: Write the failing test**

Use a startup smoke command:

```python
from app import build_runtime
runtime = build_runtime()
assert runtime is not None
```

**Step 2: Run test to verify it fails**

Run: `python -c "from app import build_runtime; runtime=build_runtime(); print(runtime.settings.server_port)"`
Expected: failure until all imports and wiring are correct.

**Step 3: Write minimal implementation**

Document:

- install steps
- config steps
- startup command
- LAN access pattern
- troubleshooting notes

**Step 4: Run test to verify it passes**

Run: `python -c "from app import build_runtime; runtime=build_runtime(); print(runtime.settings.server_port)"`
Expected: prints configured port.

**Step 5: Commit**

Skip if not in git repository.
