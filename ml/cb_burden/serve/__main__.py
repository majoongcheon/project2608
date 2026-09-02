"""추론 서비스 기동.

**포트를 쓰지 않는다.** 팀에 배정된 포트가 프론트·백엔드 두 개뿐이라(9503·9523),
유닉스 도메인 소켓(파일)으로 통신한다. 네트워크에 열리지 않으므로 외부에서 닿을 수 없다.
"""
import argparse
import os
from pathlib import Path

import uvicorn

from cb_burden.serve.app import create_app

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOCK = ROOT / 'run' / 'cb-inference.sock'

ap = argparse.ArgumentParser(prog='cb_burden.serve', description='돌봄부담 추론 서비스')
ap.add_argument('--release', default=None, help='릴리스 경로 (기본 CB_MODELS_DIR 또는 models)')
ap.add_argument('--socket', default=os.getenv('CB_INFERENCE_SOCKET', str(DEFAULT_SOCK)),
                help='유닉스 소켓 경로. 포트는 쓰지 않는다')
a = ap.parse_args()

sock = Path(a.socket)
sock.parent.mkdir(parents=True, exist_ok=True)
if sock.exists():
    sock.unlink()          # 이전 프로세스가 남긴 소켓 파일을 치운다

app = create_app(a.release)
print(f'[cb-inference] unix:{sock}')
print(f'  릴리스 : {app.version}')
uvicorn.run(app, uds=str(sock), access_log=False)
