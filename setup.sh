#!/usr/bin/env bash
# tts-local — 원샷 설치·실행 (macOS / Linux)
#   bash setup.sh          # Python 3.11 venv → MeloTTS 설치 → 모델 다운로드 → selftest → 서버 기동 → 브라우저
#   bash setup.sh stop
# 환경변수: PORT(8771) TTS_DEVICE(auto|cpu|cuda) TTS_DEFAULT_VOICE(KR) HF_HUB_OFFLINE=1(폐쇄망)
set -euo pipefail
REPO=https://github.com/gggg8657/tts-local.git
PORT="${PORT:-8771}"
if [ -t 1 ]; then B=$'\033[1m'; D=$'\033[2m'; C=$'\033[36m'; G=$'\033[32m'; R=$'\033[31m'; N=$'\033[0m'; else B= D= C= G= R= N=; fi
STEP=0; step() { STEP=$((STEP+1)); printf '  %s[%d/7]%s %s%-12s%s ' "$D" "$STEP" "$N" "$B" "$1" "$N"; }
ok() { printf '%s✔%s %s\n' "$G" "$N" "${1:-}"; }; skip() { printf '%s–%s %s\n' "$D" "$N" "${1:-}"; }
die() { printf '%s✘ %s%s\n' "$R" "$*" "$N" >&2; exit 1; }
has() { command -v "$1" >/dev/null 2>&1; }; probe() { curl -fsS -m 2 "$1" >/dev/null 2>&1; }
spin() { local msg=$1; shift; local log; log=$(mktemp); "$@" >"$log" 2>&1 & local pid=$! f='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏' i=0
  while kill -0 $pid 2>/dev/null; do printf '\r  %s      %s%s%s %s' "$D" "$C" "${f:i%10:1}" "$N" "$msg"; i=$((i+1)); sleep 0.1; done; printf '\r\033[K'
  if wait $pid; then rm -f "$log"; else printf '%s' "$D"; tail -8 "$log" | sed 's/^/        /'; printf '%s' "$N"; rm -f "$log"; return 1; fi; }
printf '\n  %stts-local%s — 한국어 로컬 TTS (MeloTTS, MIT)\n\n' "$B" "$N"

step "OS"; case "$(uname -s)" in Darwin*) OS=mac;; Linux*) OS=linux;; *) die "지원하지 않는 OS";; esac; ok "$OS ($(uname -m))"

step "패키지"; if [ -f "$(dirname "${BASH_SOURCE[0]:-.}")/app.py" ]; then cd "$(dirname "${BASH_SOURCE[0]}")"; ok "$(pwd)"
elif [ -f ./tts-local/app.py ]; then cd tts-local; ok "$(pwd)"
else has git || die "git 없음. zip을 풀고 그 안에서 실행"; spin "git clone" git clone -q "$REPO" tts-local || die "클론 실패"; cd tts-local; ok "$(pwd)"; fi

if [ "${1:-}" = "stop" ]; then [ -f .server.pid ] && kill "$(cat .server.pid)" 2>/dev/null && rm -f .server.pid && ok "서버 종료" || skip "실행 중인 서버 없음"; exit 0; fi

step "Python 3.11"; PY=""; for c in python3.11 python3.12 python3.10 python3; do
  has "$c" && "$c" -c 'import sys; sys.exit(0 if (3,10) <= sys.version_info < (3,13) else 1)' 2>/dev/null && { PY=$c; break; }; done
[ -n "$PY" ] || die "Python 3.10~3.12 필요 (mac: brew install python@3.11 / linux: apt install python3.11-venv)"
ok "$($PY --version) ($PY)"

step "venv·의존성"
# ponytail: uv venv 에는 pip 이 없다 → 설치/삭제는 전부 이 헬퍼로 (uv 있으면 uv pip, 없으면 python -m pip)
pipx() { local c=$1; shift; if has uv; then uv pip "$c" -q -p .venv/bin/python "$@"; else .venv/bin/python -m pip "$c" -q "$@"; fi; }
if [ -x .venv/bin/python ] && .venv/bin/python -c "import melo, mecab" 2>/dev/null; then ok "이미 설치됨"
else
  rm -rf .venv
  if has uv; then uv venv -q --python "$(command -v $PY)" .venv; else "$PY" -m venv .venv; fi
  if [ -d wheels ]; then                      # 폐쇄망 번들 (pack.sh)
    spin "오프라인 wheels 설치" pipx install --no-index --find-links wheels -r requirements.txt || die "오프라인 설치 실패"
  else
    curl -fsS -m 5 https://pypi.org >/dev/null 2>&1 || die "인터넷 없음. pack.sh 번들을 쓰세요"
    spin "의존성 설치 (torch 포함, 수 분)" pipx install -r requirements.txt || die "설치 실패"
  fi
  if [ "$OS" = mac ]; then  # ponytail: macOS 대소문자 무시 FS에서 MeCab/(ja)·mecab/(ko) 충돌 → ko만 남김 (MeCab.py 스텁이 ja 자리 대신)
    SP=$(.venv/bin/python -c "import sysconfig;print(sysconfig.get_paths()['purelib'])")
    pipx uninstall mecab-python3 python-mecab-ko python-mecab-ko-dic || true
    rm -rf "$SP/MeCab" "$SP/mecab"
    spin "python-mecab-ko 재설치 (macOS)" pipx install python-mecab-ko || die "mecab 설치 실패"
    .venv/bin/python -c "import mecab" || die "한국어 mecab import 실패"
  fi
  # ponytail: unidic(500MB, 일본어용) 다운로드 대신 unidic_lite 를 같은 자리에 링크
  .venv/bin/python - <<'PY'
import os, unidic, unidic_lite
d = os.path.join(os.path.dirname(unidic.__file__), "dicdir")
if not os.path.exists(d): os.symlink(unidic_lite.DICDIR, d)
PY
  ok "설치 완료"
fi

step "모델"
if [ -d models ] && [ -z "${HF_HOME:-}" ]; then export HF_HOME="$PWD/models" HF_HUB_OFFLINE=1; fi   # 번들 반입분
spin "MeloTTS-Korean (198MB) + bert-kor-base 확인/다운로드" .venv/bin/python -c "
import warnings; warnings.filterwarnings('ignore')
import os; os.environ.setdefault('PYTHONWARNINGS','ignore')
from melo.api import TTS; TTS(language='KR', device='cpu')" || die "모델 로드 실패 (폐쇄망이면 models/ 번들 + HF_HUB_OFFLINE=1)"
ok "준비됨"

step "자가검증"; spin "파이프라인 (분리·연결·mp3·API 파싱)" .venv/bin/python selftest.py || die "selftest 실패"; ok "통과"

step "서버"; [ -f .server.pid ] && kill "$(cat .server.pid)" 2>/dev/null || true
has lsof && lsof -tnP -iTCP:"$PORT" -sTCP:LISTEN 2>/dev/null | xargs kill 2>/dev/null || true; sleep 1   # 이전 서버 잔존 시
PORT=$PORT nohup .venv/bin/python app.py > server.log 2>&1 & echo $! > .server.pid
for _ in $(seq 1 30); do probe "http://localhost:$PORT/v1/models" && break; sleep 1; done
probe "http://localhost:$PORT/v1/models" || { cat server.log; die "서버가 뜨지 않음"; }
URL="http://localhost:$PORT"; ok "$URL"
case "$OS" in mac) open "$URL";; linux) has xdg-open && xdg-open "$URL" >/dev/null 2>&1 || true;; esac
printf '\n  %s준비 완료%s  %s%s%s   종료: bash setup.sh stop   로그: server.log\n' "$B" "$N" "$C" "$URL" "$N"
printf '  API:  curl %s/v1/audio/speech -H "Content-Type: application/json" -d '"'"'{"input":"안녕하세요","voice":"KR","response_format":"mp3"}'"'"' -o a.mp3\n\n' "$URL"
