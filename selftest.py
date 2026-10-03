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
meta = app.save_run("t", "KR", 1.0, "wav", data, secs)
assert meta["run_id"] in [r["run_id"] for r in app.list_runs()]
print("selftest OK — ffmpeg:", "yes" if app.FFMPEG else "no", "runs:", [r["run_id"] for r in app.list_runs()[:2]])
