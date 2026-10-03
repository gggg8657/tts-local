# tts-local — 한국어 로컬 TTS 서버 (MeloTTS) · OpenAI `/v1/audio/speech` 호환

> **한 줄 요약** — 오픈소스 한국어 TTS [MeloTTS](https://github.com/myshell-ai/MeloTTS)(MIT, 한국어 모델 198MB)를 폐쇄망에서 바로 쓰는 음성 서버로 묶었습니다.
> 웹 UI에 글을 붙여넣으면 문장 단위로 합성해 wav/mp3를 내려주고, OpenAI 음성 API와 같은 주소·형식(`/v1/audio/speech`)을 제공해서
> 다른 도구(회의록 낭독, 팟캐스트 생성, 사내 방송 문구)가 코드 수정 없이 붙습니다. CPU만으로 실시간보다 빠르고(M1 Max 약 10자/초), GPU면 더 빠릅니다.
> 클라우드·API 키 없음. 한국어 외 언어는 지원하지 않습니다(영어 섞인 문장은 읽음).
>
> - **설치**: `bash setup.sh` 하나 (Python 3.11 venv → MeloTTS → 모델 다운로드 → 자가검증 → 서버). 폐쇄망은 `pack.sh` 번들.
> - **외부 통신**: 모델 최초 다운로드만. 반입 후 `HF_HUB_OFFLINE=1`.
> - **품질**: 또박또박 읽는 뉴스 톤 1종(`KR`). 감정·화자 복제는 없음 → 필요하면 CosyVoice2(Apache, 한국어, GPU) 또는 F5-TTS(MIT, 복제)로 교체.

## 실행

```bash
bash setup.sh                       # http://localhost:8771
bash setup.sh stop
.venv/bin/python app.py --cli "2026년 10월 4일 회의를 시작하겠습니다." -o out.mp3 --speed 1.1
```

| 환경변수 | 기본 | 설명 |
|---|---|---|
| `PORT` | `8771` | |
| `TTS_DEVICE` | `auto`(=cpu) | `cuda` 로 GPU |
| `TTS_DEFAULT_VOICE` | `KR` | MeloTTS 한국어는 화자 1개 |
| `TTS_ENGINE` | `melo` | 현재 melo만 구현 |
| `HF_HOME` / `HF_HUB_OFFLINE` | | 모델 캐시 위치 / 폐쇄망 1 |

## API (OpenAI 호환)

```bash
curl localhost:8771/v1/audio/speech -H 'Content-Type: application/json' \
  -d '{"model":"melo","input":"안녕하세요. 오늘 안건은 세 가지입니다.","voice":"KR","response_format":"mp3","speed":1.0}' -o a.mp3
curl localhost:8771/v1/audio/voices      # {"voices":["KR"],...}
curl localhost:8771/v1/models
```

OpenAI SDK도 그대로: `OpenAI(base_url="http://<서버>:8771/v1", api_key="x").audio.speech.create(model="melo", voice="KR", input="...")`.
긴 글은 `. ! ? …` 와 줄바꿈 기준으로 문장을 나눠 순서대로 합성한 뒤 이어 붙입니다(`3.5%` 같은 숫자 속 점은 안 자름). mp3 는 ffmpeg 가 있을 때만.

## 폐쇄망 반입

```bash
./pack.sh        # linux-x64 · Python 3.11 wheels + 모델(HF 캐시) → dist-offline/tts-local-linux-x64.tar.gz
```
내부망: 풀고 `bash setup.sh` (wheels/·models/ 가 있으면 다운로드 없이 설치, `HF_HUB_OFFLINE=1` 자동). 이 맥에서는 pack.sh 를 아직 실행해 보지 않았음(PoC).

## 구현 메모
- 서버는 stdlib `http.server`, 합성은 venv 안 MeloTTS 인프로세스. 전역 락 1개(동시 사용자 몇 명 수준).
- macOS 전용 우회: 대소문자 무시 파일시스템에서 MeloTTS 의존성 `mecab-python3`(일본어용)와 `python-mecab-ko`(한국어)가 같은 폴더로 합쳐져 깨짐 → setup.sh 가 한국어 것만 남기고, `MeCab.py` 스텁이 일본어 모듈 자리를 채움. Linux 서버에서는 해당 없음.
- 일본어용 사전 `unidic`(500MB) 다운로드 대신 `unidic_lite` 를 링크(한국어엔 안 쓰임).
- `selftest.py` 는 가짜 엔진으로 분리·연결·mp3·API 파싱만 검사(모델 불필요).

출처·라이선스: `NOTICE`.
