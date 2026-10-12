# ponytail: stub for MeloTTS's Japanese module (unused here). The real pykakasi is GPL-3.0-or-later and MeloTTS
# imports it at load time even for Korean (melo/text/cleaner.py → japanese.py). This file shadows it so the GPL
# package is never loaded; Japanese text fails loudly instead. See THIRD_PARTY_NOTICES.md / issue #2.
class _Conv:
    def do(self, text):
        raise RuntimeError("tts-local: Japanese (pykakasi) is disabled — Korean only")


class kakasi:
    def __init__(self, *a, **k): pass
    def setMode(self, *a, **k): pass
    def getConverter(self): return _Conv()
