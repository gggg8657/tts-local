# 제3자 구성요소 고지 (THIRD_PARTY_NOTICES)

tts-local 의 원저작물은 DongJu Kim(gggg8657)이 작성했습니다(`NOTICE`, `LICENSE`). 아래 제3자 구성요소는 각자의 라이선스를 따르며, 이 저장소의 라이선스(PolyForm Noncommercial 1.0.0)로 바뀌지 않습니다.
조사일: 2026-10-12 (실제 파일·`.venv` 설치 메타데이터·한국어 합성 1회 후 로드된 모듈·setup.sh·pack.sh 기준). "상업 이용" 칸은 확인한 라이선스 문구를 요약한 것이며 법률 판단이 아닙니다.

이 저장소에는 제3자 코드·가중치·음성이 **들어 있지 않습니다**(`.venv/`, `models/` 는 `.gitignore`). `MeCab.py`·`pykakasi.py` 는 이 저장소 저작자가 쓴 스텁입니다(일본어용 mecab·pykakasi 자리를 대신함). 아래는 `setup.sh` 가 설치하거나 내려받는 것입니다. `pack.sh` 로 만든 폐쇄망 번들은 휠과 가중치를 함께 묶으므로(재배포) 번들을 외부에 넘길 때는 아래 라이선스를 같이 전달하세요.

**음성 복제 기능·복제용 모델은 없습니다.** F5-TTS 는 쓰지 않습니다(코드는 MIT 이지만 공개 가중치 [SWivid/F5-TTS](https://huggingface.co/SWivid/F5-TTS) 는 CC-BY-NC-4.0 — 비상업).

## 엔진·가중치

| 이름 | 버전 | 쓰임 | 라이선스 | 링크 | 상업 이용 | 비고 |
|---|---|---|---|---|---|---|
| MeloTTS (`melotts`) | git main (0.1.2) | 설치 (`requirements.txt`) — 음성 합성 | MIT (MyShell.ai) | [myshell-ai/MeloTTS](https://github.com/myshell-ai/MeloTTS) | 가능 | 수정 없이 씀 |
| `myshell-ai/MeloTTS-Korean` | — | 내려받는 가중치 (HF 캐시, `pack.sh` 번들에 복사) | MIT (HF 모델 카드) | [HF](https://huggingface.co/myshell-ai/MeloTTS-Korean) | 가능 | 목소리 `KR` 1종 |
| `kykim/bert-kor-base` | — | 내려받는 가중치 — MeloTTS 한국어 전처리가 내부에서 고정으로 받음 (`pack.sh` 번들에 복사) | HF 카드 표기 없음 · 원 저장소 README 는 "Apache-2.0" 과 "상업적 사용은 MOU" 를 함께 적음 | [HF](https://huggingface.co/kykim/bert-kor-base) · [kiyoungkim1/LMkor](https://github.com/kiyoungkim1/LMkor) | **확인 필요** — [#1](https://github.com/gggg8657/tts-local/issues/1) | 학습 데이터에 웹 수집 텍스트·모두의 말뭉치 포함 |
| g2pkk | 0.1.2 | 설치 (MeloTTS 의존) — 한국어 발음 변환 | Apache-2.0 | [harmlessman/g2pkk](https://github.com/harmlessman/g2pkk) | 가능 | |
| python-mecab-ko / python-mecab-ko-dic | 1.3.7 / 2.1.1 | 설치 (`requirements.txt`) — 형태소 분석 | BSD-3-Clause / Apache-2.0 | [jonghwanhyeon/python-mecab-ko](https://github.com/jonghwanhyeon/python-mecab-ko) | 가능 | |
| jamo, num2words | 0.4.1 / 0.5.12 | 설치 (MeloTTS 의존) — 한국어 전처리에서 import | Apache-2.0 / LGPL | PyPI | 가능 / 조건부 | LGPL: 수정 배포 시 소스 제공 |
| PyTorch, torchaudio | 2.12 / 2.11 (+cu126) | 설치 (MeloTTS 의존) | BSD-3-Clause | [pytorch/pytorch](https://github.com/pytorch/pytorch) | 가능 | `setup.sh` 가 드라이버에 맞는 CUDA 빌드를 고름 |
| transformers | 4.27.4 | 설치 (MeloTTS 의존) | Apache-2.0 | [huggingface/transformers](https://github.com/huggingface/transformers) | 가능 | |

## MeloTTS 가 함께 설치하는 다른 언어용 의존성

MeloTTS 는 한국어만 써도 모든 언어 모듈을 import 합니다(`melo/text/cleaner.py`). 그래서 아래가 설치되고, 표시한 것은 실행 중 실제로 로드됩니다.

| 이름 | 버전 | 라이선스 | 실행 중 로드 | 상업 이용 | 비고 |
|---|---|---|---|---|---|
| pykakasi | 2.2.1 | GPL-3.0-or-later | **아니오** — 저장소의 `pykakasi.py` 스텁이 대신 로드됨(2026-10-12부터) | 조건부 (설치만 됨) — [#2](https://github.com/gggg8657/tts-local/issues/2) | 일본어용, 이 도구는 쓰지 않음. 일본어 문장은 오류로 거부 |
| Unidecode | 1.3.7 | GPL-2.0-or-later | 아니오 | 조건부 — [#2](https://github.com/gggg8657/tts-local/issues/2) | 설치만 됨 |
| Distance | 0.1.3 | GPL | 아니오 | 조건부 — [#2](https://github.com/gggg8657/tts-local/issues/2) | 설치만 됨 |
| fugashi, unidic, unidic-lite, mecab-python3 | 1.3.0 / 1.1.0 / 1.0.8 / 1.0.9 | MIT / MIT / MIT / BSD | 예 (일부) | 가능 | 일본어용. `setup.sh` 는 unidic 사전(500MB) 대신 unidic-lite 를 링크 |
| g2p-en, nltk, inflect, eng_to_ipa, gruut(+lang) | — | Apache-2.0 / Apache-2.0 / MIT / 표기 없음 / MIT | 예 (일부) | 가능 (eng_to_ipa 미확인) | 영어용. g2p-en 은 처음 import 때 nltk 데이터(cmudict 등)를 내려받음 |
| jieba, pypinyin, cn2an | — | MIT | 예 | 가능 | 중국어용 |
| gradio, fastapi 등 | — | Apache-2.0 / MIT 등 | 아니오 | 가능 | MeloTTS 의 자체 웹 UI 용, 이 도구는 쓰지 않음 |
| NVIDIA CUDA 런타임·cuBLAS·cuDNN·NCCL 등 (`nvidia-*-cu12`) | 12.6 / 9.10 | NVIDIA 독점 (LicenseRef-NVIDIA-Proprietary) | GPU 사용 시 | 조건부 — [#2](https://github.com/gggg8657/tts-local/issues/2) | torch GPU 빌드 의존. 재배포 범위 확인 |

전체 목록은 `.venv/bin/python -m pip list` 또는 `uv pip list -p .venv/bin/python` 으로 볼 수 있습니다.

## 외부 프로그램 (동봉 안 함)

| 이름 | 쓰임 | 라이선스 | 링크 | 상업 이용 | 비고 |
|---|---|---|---|---|---|
| ffmpeg | MP3 변환 (`app.py`, 별도 프로세스) | LGPL-2.1+ / GPL (빌드에 따라) | [ffmpeg.org/legal](https://ffmpeg.org/legal.html) | 가능 | 시스템 설치본. 없으면 WAV 만 |
| nvidia-smi | GPU 고르기 (`gpu_pick.py`) | NVIDIA 드라이버 구성요소 | — | 가능 | 시스템 설치본 |

## 확인 필요

- [#1 kykim/bert-kor-base — Apache-2.0 표기 vs 상업 이용 MOU 안내 상충](https://github.com/gggg8657/tts-local/issues/1)
  - MeloTTS 한국어가 내부에서 고정으로 받는 BERT. 원 저장소 README 에 "상업적 사용은 MOU 를 통해 무료" 문구가 있어 상업 이용 전 저작자 확인 필요.
  - 회피: 저작자 문의 / MeloTTS 패치로 다른 한국어 BERT 사용(`monologg/kobert` Apache-2.0 — 토크나이저가 달라 그대로 교체 불가, `klue/bert-base` CC-BY-SA-4.0) / `TTS_ENGINE` 자리에 다른 엔진 구현(예: CosyVoice2-0.5B, HF 카드 Apache-2.0). 모두 음질 재검증 필요.
- [#2 MeloTTS 의존성 pykakasi·Unidecode·Distance (GPL) / NVIDIA CUDA 휠 (독점) — pack.sh 번들 재배포](https://github.com/gggg8657/tts-local/issues/2)
  - 내부에서 서버로 쓰는 것은 배포가 아님. `pack.sh` 번들을 **외부에 넘길 때** GPL·NVIDIA 조건 확인.
  - 적용함: `pykakasi.py` 스텁 — 실행 중 GPL 패키지를 로드하지 않음(합성 결과 바이트 단위 동일 확인).
  - 남은 회피: 쓰지 않는 GPL 휠(pykakasi·Unidecode·Distance)을 번들에서 빼기, 번들 대신 받는 쪽이 `setup.sh` 로 직접 설치.
