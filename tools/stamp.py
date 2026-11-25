"""배포 전에 실행: 앱 파일에 버전 꼬리표를 붙여 브라우저가 옛 파일을 쓰지 않게 한다.

python3 tools/stamp.py

- index.html·check.html의 CSS·모듈 주소에 ?v=<해시>를 붙인다.
- 모듈끼리의 import('./engine.js' 등)는 import map으로 같은 꼬리표 주소에 연결한다.
  (JS 파일 자체는 고치지 않는다.)
- 해시는 app/js·app/css 내용으로 정하므로, 내용이 그대로면 꼬리표도 그대로다.
팩(JSON)은 이미 cache: 'no-cache'로 받아서 꼬리표가 필요 없다.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JS = sorted((ROOT / "app" / "js").glob("*.js"))
CSS = sorted((ROOT / "app" / "css").glob("*.css"))


def version():
    h = hashlib.sha1()
    for f in JS + CSS:
        h.update(f.name.encode())
        h.update(f.read_bytes())
    return h.hexdigest()[:10]


def stamp(html_path, v):
    s = html_path.read_text()
    # CSS·진입 모듈 주소
    s = re.sub(r'(href="app/css/[\w.-]+\.css)(\?v=\w+)?"', rf'\1?v={v}"', s)
    s = re.sub(r'(src="app/js/[\w.-]+\.js)(\?v=\w+)?"', rf'\1?v={v}"', s)
    # import map: 모듈 안의 상대 import도 같은 꼬리표로
    imap = {"imports": {f"./app/js/{f.name}": f"./app/js/{f.name}?v={v}" for f in JS}}
    block = '<script type="importmap" id="stamp">' + json.dumps(imap, ensure_ascii=False) + "</script>"
    if 'id="stamp"' in s:
        s = re.sub(r'<script type="importmap" id="stamp">.*?</script>', block, s, flags=re.S)
    else:
        # import map은 첫 모듈 스크립트보다 앞에 있어야 한다
        s = s.replace("</head>", block + "\n</head>", 1)
    html_path.write_text(s)


if __name__ == "__main__":
    v = version()
    for name in ("index.html", "check.html"):
        stamp(ROOT / name, v)
    print(f"버전 꼬리표 {v}")
