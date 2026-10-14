#!/usr/bin/env python3
"""엔진 없이 파이프라인만 검증: 문장 분리 → 합성(가짜 사인파) → wav 연결 → mp3 → OpenAI 요청 파싱.  python3 selftest.py"""
import json, math, struct, wave, io
import app

SR = 16000
class Fake:
    calls = []
    def voices(self): return ["KR"]
    def synth(self, text, voice, speed):
        self.calls.append(text)
        n = int(SR * 0.1 * max(1, len(text) // 10))      # 글자 수에 비례한 길이
        return SR, b"".join(struct.pack("<h", int(8000 * math.sin(2 * math.pi * 440 * i / SR))) for i in range(n))
app.ENGINE = Fake()

# 1) 문장 분리: 한국어 문장부호, 숫자 속 점(3.5%)·소수점·줄바꿈
s = app.split_sentences("예산은 3.5% 늘었습니다. 두 번째 안건입니다!\n세 번째? 네.")
assert s == ["예산은 3.5% 늘었습니다.", "두 번째 안건입니다!", "세 번째?", "네."], s

# 2) wav: 문장별 합성 결과가 하나로 이어지고 길이가 합산된다
data, mime, secs = app.speak("첫 문장입니다. 둘째 문장입니다.", "KR", 1.0, "wav")
assert mime == "audio/wav" and len(Fake.calls) == 2
with wave.open(io.BytesIO(data)) as w:
    assert w.getframerate() == SR and abs(w.getnframes() / SR - secs) < 1e-6 and secs >= 0.2

# 3) mp3 (ffmpeg 있을 때만) — 헤더/프레임 싱크 확인
if app.FFMPEG:
    m, mime, _ = app.speak("mp3 테스트.", "KR", 1.0, "mp3")
    assert mime == "audio/mpeg" and (m[:3] == b"ID3" or m[0] == 0xFF), m[:4]

# 4) 입력 검증
for bad in [("", "KR", 1.0, "wav"), ("x", "KR", 5.0, "wav"), ("x", "KR", 1.0, "ogg")]:
    try: app.speak(*bad); assert False, bad
    except ValueError: pass

# 5) OpenAI 요청 바디 필드 매핑 (input/voice/response_format/speed) — 핸들러 로직과 같은 키
req = json.loads('{"model":"melo","input":"안녕","voice":"KR","response_format":"mp3","speed":1.2}')
assert (req.get("input") or req.get("text")) == "안녕" and (req.get("response_format") or "wav") == "mp3"

# 6) 실행 기록 저장/조회
meta = app.save_run(app.WS, "t", "KR", 1.0, "wav", data, secs)
assert meta["run_id"] in [r["run_id"] for r in app.list_runs(app.WS)]
# 저작권 표기: 서버가 화면에 붙이는 코드가 있어야 한다 (LICENSE·NOTICE)
_src = open(__import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "app.py"), encoding="utf-8").read()
assert "wqkgMjAyNiBnZ2dnODY1NyDCtyBkb25nanVraW0uZGV2QGdtYWlsLmNvbQ==" in _src and "signed(" in _src and "X-Author" in _src, "저작권 표기 누락"

print("selftest OK — ffmpeg:", "yes" if app.FFMPEG else "no", "runs:", [r["run_id"] for r in app.list_runs(app.WS)[:2]])

# GPU 후보: 부모 후보가 0,1,2 면 3(운영 vLLM 전용)을 절대 고르지 않음 — nvidia-smi 출력은 가짜, 예약 장부는 임시 폴더
import gpu_pick as _gp, os as _os, tempfile as _tf, shutil as _sh
_smi0, _dir0, _env0 = _gp._smi, _gp.RES_DIR, dict(_os.environ)
try:
    _gp._smi = lambda: "0, 1000, 90\n1, 2000, 90\n2, 3000, 90\n3, 90000, 0\n"  # 3 이 가장 한가해 보이게
    _gp.RES_DIR = _tf.mkdtemp()
    for _k in ("GPU_POOL", "GPU_RESERVED", "VLLM_GPUS"): _os.environ.pop(_k, None)
    for _res in ("none", "3"):
        _os.environ.update(CUDA_VISIBLE_DEVICES="0,1,2", GPU_RESERVED=_res)
        assert [g["index"] for g in _gp.gpus()] == ["0", "1", "2"]
        assert _gp.pick(0, hold_s=0)["index"] == "2" and _gp.torch_device(_gp.pick(0, hold_s=0)) == "cuda:2"
        assert _gp.pool_env(_os.environ)["CUDA_VISIBLE_DEVICES"] == "0,1,2" == _gp.env_for(None, _os.environ)["CUDA_VISIBLE_DEVICES"]
    # 셸(~/.zshrc)에서 2,3 을 물려받아도 예약된 3 은 빼고 2 만 — 보이는 번호는 cuda:0
    _os.environ.update(CUDA_VISIBLE_DEVICES="2,3", GPU_RESERVED="3")
    assert _gp.pick(0, hold_s=0)["index"] == "2" and _gp.torch_device(_gp.pick(0, hold_s=0)) == "cuda:0"
    assert _gp.pool_env(_os.environ)["CUDA_VISIBLE_DEVICES"] == "2"
    _os.environ.pop("GPU_RESERVED"); _os.environ["VLLM_GPUS"] = "3"  # GPU_RESERVED 없으면 VLLM_GPUS
    assert _gp.pick(0, hold_s=0)["index"] == "2"
    _os.environ["GPU_POOL"] = "0,1"  # 교집합이 비면 GPU 를 하나도 안 보임(CPU)
    assert _gp.pick(0, hold_s=0) is None and _gp.pool_env(_os.environ)["CUDA_VISIBLE_DEVICES"] == ""
    if hasattr(app, "worker_env"):  # 작업자(그림·영상) 프로세스 환경
        assert app.worker_env({"CUDA_VISIBLE_DEVICES": "0,1,2", "GPU_RESERVED": "none"}, ["0", "1", "2", "3"])["CUDA_VISIBLE_DEVICES"] == "0,1,2"
        assert app.worker_env({"CUDA_VISIBLE_DEVICES": "2,3", "GPU_RESERVED": "3"}, ["0", "1", "2", "3"])["CUDA_VISIBLE_DEVICES"] == "2"
        assert app.worker_env({"GPU_POOL": "0,1,2,3", "VLLM_GPUS": "3"}, ["0", "1", "2", "3"])["CUDA_VISIBLE_DEVICES"] == "0,1,2"
finally:
    _sh.rmtree(_gp.RES_DIR, ignore_errors=True); _gp._smi, _gp.RES_DIR = _smi0, _dir0; _os.environ.clear(); _os.environ.update(_env0)
print("selftest GPU 후보 OK — 0,1,2 에서 3 안 고름")
