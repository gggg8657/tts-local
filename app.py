#!/usr/bin/env python3
"""tts-local — 한국어 로컬 TTS (MeloTTS) 웹 UI + OpenAI 호환 /v1/audio/speech.
외부 파이썬 의존성은 .venv 안에만 (MeloTTS). 서버 코드는 stdlib.

  .venv/bin/python app.py                              # http://localhost:8771
  .venv/bin/python app.py --cli "안녕하세요" -o out.wav [--voice KR --speed 1.0]
  curl localhost:8771/v1/audio/speech -H 'Content-Type: application/json' \
       -d '{"model":"melo","input":"안녕하세요","voice":"KR","response_format":"mp3"}' -o a.mp3
"""
import datetime
import io
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from gpu_pick import Lazy, label, pick, release, torch_device

ROOT = os.path.dirname(os.path.abspath(__file__))
WS = os.environ.get("WORKSPACE") or os.path.join(ROOT, "_workspace")  # 포털이 AGENT_DATA/<도구> 로 모아 줌
PORT = int(os.environ.get("PORT", "8771"))
ENGINE_NAME = os.environ.get("TTS_ENGINE", "melo")       # ponytail: melo만 구현. cosyvoice/kokoro(영문)은 README 참고
DEVICE = os.environ.get("TTS_DEVICE", "auto")     # cuda 면 GPU 를 고정하지 않고, 올릴 때마다 여유 메모리가 가장 큰 GPU 를 고른다
DEFAULT_VOICE = os.environ.get("TTS_DEFAULT_VOICE", "KR")
FFMPEG = shutil.which("ffmpeg")
LOCK = threading.Lock()  # ponytail: 전역 락, 동시 사용자 몇 명이면 충분. 많아지면 워커 풀


# ── 엔진 ────────────────────────────────────────────────────────────────
class Melo:
    """MeloTTS Korean. synth(text, voice, speed) -> (sample_rate, pcm16 bytes)"""
    def __init__(self):
        self._m = Lazy(self._load, "MeloTTS", log=lambda s: print(s, flush=True), cleanup=self._drop_bert)  # 오래 안 쓰면 GPU 에서 내림(GPU_IDLE_UNLOAD_S)
        self.where = "아직 안 올림"

    def _load(self):
        from melo.api import TTS
        dev, g = DEVICE if DEVICE != "auto" else "cpu", None   # ponytail: 이 모델은 CPU도 충분히 빠름. GPU면 TTS_DEVICE=cuda
        if dev == "cuda":
            g = pick(2000)                             # 약 1GB 모델 — 여유 2GB 넘는 GPU 중 가장 넉넉한 것, 없으면 CPU
            dev, self.where = torch_device(g), label(g)
        else:
            self.where = dev
        print(f"[tts] MeloTTS {self.where} 에서 로드", flush=True)
        try:
            return TTS(language="KR", device=dev)
        finally:
            release(g)  # 다 올렸으니 예약 해제 (실제 사용량은 이제 nvidia-smi 에 보임)

    @staticmethod
    def _drop_bert():
        """MeloTTS 한국어는 BERT 를 모듈 전역(japanese_bert.models·model)에 붙들고 있다(장치 구분 없이) —
        같이 비워야 VRAM 이 빠지고, 다음에 다른 GPU 로 올릴 때 BERT 도 그 GPU 로 새로 올라간다"""
        mod = sys.modules.get("melo.text.japanese_bert")
        if mod is not None:
            mod.models.clear(); mod.model = None

    def voices(self):
        with self._m.use() as m:
            return list(m.hps.data.spk2id.keys())

    def synth(self, text, voice, speed):
        with self._m.use() as m:
            ids = m.hps.data.spk2id            # HParams: keys()/[] 만 있고 get() 없음
            spk = ids[voice] if voice in ids.keys() else 0
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                path = f.name
            try:
                m.tts_to_file(text, spk, path, speed=float(speed), quiet=True)
                with wave.open(path, "rb") as w:
                    return w.getframerate(), w.readframes(w.getnframes())
            finally:
                os.unlink(path)


ENGINE = Melo()


# ── 텍스트 → 오디오 ──────────────────────────────────────────────────────
def split_sentences(text):
    """문장 단위 분리. 숫자 사이 점(3.5%)·줄 끝 없는 점은 안 자른다."""
    out = []
    for para in re.split(r"\n+", text):
        para = para.strip()
        if para:
            out += [s for s in re.split(r"(?<=[.!?。？！…])\s+", para) if s.strip()]
    return out


def wav_bytes(sr, pcm):
    if not pcm:
        raise ValueError("발음할 텍스트가 없습니다 (문장부호만?)")
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm)
    return b.getvalue()


def to_mp3(wav):
    if not FFMPEG:
        raise RuntimeError("ffmpeg 없음 — mp3 변환 불가 (wav 로 받으세요)")
    r = subprocess.run([FFMPEG, "-v", "error", "-i", "pipe:0", "-f", "mp3", "-b:a", "96k", "pipe:1"],
                       input=wav, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg: " + r.stderr.decode(errors="replace")[:200])
    return r.stdout


def speak(text, voice=DEFAULT_VOICE, speed=1.0, fmt="wav", on_progress=None):
    """전체 파이프라인: 분리 → 문장별 합성 → 연결 → 포맷. returns (bytes, mime, seconds)"""
    text = (text or "").strip()
    if not text:
        raise ValueError("빈 입력")
    if not 0.5 <= float(speed) <= 2.0:
        raise ValueError("speed 는 0.5~2.0")
    if fmt not in ("wav", "mp3"):
        raise ValueError("response_format 은 wav|mp3")
    sents = split_sentences(text)
    pcm, sr = b"", None
    with LOCK:
        for i, s in enumerate(sents):
            if on_progress:
                on_progress(i, len(sents), s)
            sr, p = ENGINE.synth(s, voice, speed)
            pcm += p
    wav = wav_bytes(sr, pcm)
    secs = len(pcm) / 2 / sr
    return (to_mp3(wav), "audio/mpeg", secs) if fmt == "mp3" else (wav, "audio/wav", secs)


def save_run(text, voice, speed, fmt, data, secs):
    run_id = f"{datetime.date.today()}-{secrets.token_hex(2)}"
    d = os.path.join(WS, run_id)
    os.makedirs(d)
    with open(os.path.join(d, f"audio.{fmt}"), "wb") as f:
        f.write(data)
    meta = {"run_id": run_id, "text": text, "voice": voice, "speed": speed, "format": fmt, "seconds": round(secs, 2),
            "ts": datetime.datetime.now().isoformat(timespec="seconds")}
    with open(os.path.join(d, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False)
    return meta


def list_runs():
    out = []
    if os.path.isdir(WS):
        for name in sorted(os.listdir(WS), key=lambda n: os.path.getmtime(os.path.join(WS, n)), reverse=True)[:50]:
            p = os.path.join(WS, name, "meta.json")
            if os.path.exists(p):
                try:
                    out.append(json.load(open(p, encoding="utf-8")))
                except Exception:
                    pass
    return out


# ── HTTP ───────────────────────────────────────────────────────────────
HTML = open(os.path.join(ROOT, "ui.html"), encoding="utf-8").read() if os.path.exists(os.path.join(ROOT, "ui.html")) else "ui.html 없음"
RUN_RE = r"\d{4}-\d{2}-\d{2}-[0-9a-f]{4}"

# ── 저작권 표기 (LICENSE·NOTICE 참고) ─────────────────────────────────────
_SIG = __import__("base64").b64decode("wqkgMjAyNiBnZ2dnODY1NyDCtyBkb25nanVraW0uZGV2QGdtYWlsLmNvbQ==").decode()
_SIG_A = __import__("base64").b64decode("Z2dnZzg2NTcgPGRvbmdqdWtpbS5kZXZAZ21haWwuY29tPg==").decode()


def signed(html):
    """화면에 저작권 표기를 붙인다. ui.html 에서 지워져도 서버가 내보낼 때 다시 붙는다."""
    name, mail = _SIG.split(" · ")
    if 'name="author"' not in html:
        meta = f'<meta name="author" content="{name[7:]} <{mail}>">'
        html = html.replace("<head>", "<head>" + meta, 1) if "<head>" in html else meta + html
    if "data-sig" not in html:
        tag = (f'<!-- {_SIG} --><div data-sig title="{mail}" style="text-align:center;font-size:11px;color:#9aa0a6;'
               f'opacity:.55;margin:28px 0 8px">{name}</div>')
        html = html.replace("</body>", tag + "</body>", 1) if "</body>" in html else html + tag
    return html


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        if "/v1/" in (str(a[0]) if a else "") or "/api/tts" in (str(a[0]) if a else ""):
            super().log_message(fmt, *a)

    def _send(self, body, ctype="application/json", code=200):
        b = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("X-Author", _SIG_A)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _json(self):
        return json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")

    def do_GET(self):
        self.path = self.path.split("?")[0]
        try:
            if self.path in ("/api/voices", "/v1/audio/voices"):
                return self._send({"voices": ENGINE.voices(), "default": DEFAULT_VOICE, "engine": ENGINE_NAME, "device": getattr(ENGINE, "where", DEVICE)})
            if self.path == "/v1/models":
                return self._send({"object": "list", "data": [{"id": ENGINE_NAME, "object": "model", "owned_by": "local"}]})
            if self.path == "/api/runs":
                return self._send(list_runs())
            m = re.fullmatch(rf"/audio/({RUN_RE})\.(wav|mp3)", self.path)
            if m:
                with open(os.path.join(WS, m.group(1), f"audio.{m.group(2)}"), "rb") as f:
                    return self._send(f.read(), "audio/mpeg" if m.group(2) == "mp3" else "audio/wav")
            self._send(signed(HTML.replace("%VOICE%", json.dumps(DEFAULT_VOICE))).encode(), "text/html; charset=utf-8")
        except FileNotFoundError:
            self._send({"error": "없음"}, code=404)
        except Exception as e:
            self._send({"error": f"{type(e).__name__}: {e}"}, code=500)

    def do_POST(self):
        self.path = self.path.split("?")[0]
        try:
            req = self._json()
            text = req.get("input") or req.get("text") or ""
            voice, speed = req.get("voice") or DEFAULT_VOICE, float(req.get("speed") or 1.0)
            fmt = (req.get("response_format") or req.get("format") or "wav").lower()
            if self.path == "/v1/audio/speech":          # OpenAI 호환: 오디오 바이트 그대로
                data, mime, _ = speak(text, voice, speed, fmt)
                return self._send(data, mime)
            if self.path == "/api/tts":                   # 웹 UI: 저장 + 메타 JSON
                data, mime, secs = speak(text, voice, speed, fmt)
                return self._send(save_run(text, voice, speed, fmt, data, secs))
            self._send({"error": "없음"}, code=404)
        except ValueError as e:
            self._send({"error": {"message": str(e), "type": "invalid_request_error"}}, code=400)
        except Exception as e:
            self._send({"error": {"message": f"{type(e).__name__}: {e}", "type": "server_error"}}, code=500)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        a = sys.argv[2:]
        text = a[0] if a and not a[0].startswith("-") else ("" if sys.stdin.isatty() else sys.stdin.read())
        g = lambda k, d: a[a.index(k) + 1] if k in a else d
        out = g("-o", "out.wav")
        data, _, secs = speak(text, g("--voice", DEFAULT_VOICE), float(g("--speed", 1.0)), out.rsplit(".", 1)[-1],
                              on_progress=lambda i, n, s: print(f"[{i + 1}/{n}] {s[:40]}", file=sys.stderr))
        open(out, "wb").write(data)
        print(f"{out} ({secs:.1f}s)")
        sys.exit(0)
    print(f"tts-local → http://localhost:{PORT}  (engine={ENGINE_NAME}, device={DEVICE}{' — GPU 는 올릴 때 여유 많은 것 자동' if DEVICE == 'cuda' else ''}, ffmpeg={'yes' if FFMPEG else 'no'})  {_SIG}")
    ThreadingHTTPServer(("", PORT), H).serve_forever()
