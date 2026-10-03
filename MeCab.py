# ponytail: stub for MeloTTS's Japanese module (unused here). The real mecab-python3 collides with
# python-mecab-ko (Korean) on macOS' case-insensitive filesystem (MeCab/ vs mecab/). Linux is fine either way.
class Tagger:
    def __init__(self, *a, **k): pass
    def parse(self, s): return s
