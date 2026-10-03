#!/usr/bin/env bash
# 폐쇄망 반입 번들 — 인터넷 되는 PC에서 실행. linux-x64 / Python 3.11 wheels + 모델을 tar.gz 하나로.
#   ./pack.sh                 # → dist-offline/tts-local-linux-x64.tar.gz
# 전제: 이 PC에서 setup.sh 를 한 번 돌려 모델이 캐시에 있어야 함 (~/.cache/huggingface).
set -euo pipefail
cd "$(dirname "$0")"
STAGE=dist-offline/tts-local-linux-x64; rm -rf "$STAGE"; mkdir -p "$STAGE/wheels" "$STAGE/models/hub"
PYV="${PYV:-3.11}"
# 1) wheels: 순수 파이썬/소스 전용 패키지(melotts git, g2pkk 등)는 --only-binary 로 못 받으니 두 단계
.venv/bin/python -m pip download -q -d "$STAGE/wheels" --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 \
  --python-version "$PYV" --only-binary=:all: torch torchaudio transformers==4.27.4 librosa==0.9.1 numpy scipy numba llvmlite \
  tokenizers huggingface_hub python-mecab-ko python-mecab-ko-dic unidic_lite mecab-python3 || true
.venv/bin/python -m pip wheel -q -w "$STAGE/wheels" --no-deps -r requirements.txt   # melotts(git) + setuptools 를 wheel 로
.venv/bin/python -m pip download -q -d "$STAGE/wheels" --no-deps --python-version "$PYV" \
  $(.venv/bin/python -m pip freeze | grep -viE 'melotts|torch|mecab|unidic|librosa|numpy|scipy|numba|llvmlite|transformers|tokenizers|huggingface' | cut -d= -f1) || true
# 2) 모델 (HF 캐시 → 번들)
for m in models--myshell-ai--MeloTTS-Korean models--kykim--bert-kor-base; do cp -R "${HF_HOME:-$HOME/.cache/huggingface}/hub/$m" "$STAGE/models/hub/"; done
# 3) 앱
cp app.py ui.html selftest.py setup.sh requirements.txt MeCab.py README.md NOTICE LICENSE "$STAGE/"
cat > "$STAGE/INSTALL.md" <<'INS'
# 폐쇄망 설치
tar -xzf tts-local-linux-x64.tar.gz && cd tts-local-linux-x64
export HF_HOME=$PWD/models HF_HUB_OFFLINE=1      # setup.sh 가 models/ 를 보면 자동 설정
bash setup.sh                                    # wheels/ 가 있으면 pip --no-index 로 설치
# GPU: TTS_DEVICE=cuda bash setup.sh
INS
( cd dist-offline && tar -czf tts-local-linux-x64.tar.gz tts-local-linux-x64 ); ls -lh dist-offline/*.tar.gz
