import os
import tempfile
from pathlib import Path

REPO = os.environ.get(
    'RYONA_REPO',
    str(Path(__file__).resolve().parents[3]),
)
GAME_DIR = os.environ.get('RYONA_GAME_DIR', '')
OUT = os.environ.get(
    'RYONA_OUT',
    os.path.join(REPO, 'language', 'zh_CN', 'Picture', 'Menu'),
)
PO = os.environ.get(
    'RYONA_PO',
    os.path.join(REPO, 'language', 'zh_CN', 'RPG_RT.ldb.po'),
)
EDB = os.environ.get('RYONA_EDB', '')
FONT = os.environ.get('RYONA_FONT', r'C:\Windows\Fonts\simsun.ttc')
TMP = os.environ.get('RYONA_TMP', tempfile.gettempdir())
STAGE = OUT
ITM_LIST = os.environ.get(
    'RYONA_ITM_LIST',
    os.path.join(REPO, 'tools', 'images', 'data', 'itm_magic_ids.txt'),
)
