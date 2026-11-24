# Isn't she lovely

공업수학·수리물리를 녹슬지 않게 유지하는 개인용 웹 게임. https://ryujh28.github.io/math/

## 구조

```
index.html          게임 (홈·세션·스킬 지도)
check.html          점검 화면 (팩·수식 렌더링·저장소·엔진 점검, 기록 내보내기·가져오기)
app/js/             game.js(게임) · session.js(세션 구성) · modes.js(미니멀 훈련·순서 맞추기)
                    engine.js(복습 엔진) · store.js(기기 저장소) · packs.js · tex.js · check.js
app/css/            스타일
app/vendor/         KaTeX 0.19.1, ts-fsrs 5.4.2 (빌드 단계 없이 그대로 사용)
packs/              빌드 결과: index.json + 장별 chNN.json  ← 앱이 읽는 것은 이것뿐
content/            콘텐츠 원본 (장별 폴더: chapter.yaml, atoms.yaml, schemas.yaml, templates/*.py)
content/catalog.yaml  39개 장 목록과 선수 관계
content/errors.yaml   전역 오류 분류
tools/build.py      원본 → 검증 → packs/ 생성
tools/reports/      장별 빌드 리포트 (실패·제외된 사례)
tools/checks.py     생성기·빌드가 함께 쓰는 판정 도구
tools/test_engine.mjs, test_session.mjs  엔진·세션 테스트
```

## 자주 쓰는 명령

```bash
pip install -r tools/requirements.txt     # 처음 한 번
python3 tools/build.py                    # 모든 장 빌드 (특정 장만: python3 tools/build.py 10)
node tools/test_engine.mjs && node tools/test_session.mjs   # 테스트
python3 -m http.server 8000               # 로컬 실행 → http://localhost:8000
```

`index.html`을 파일로 직접 열면 브라우저가 팩(JSON)을 읽지 못한다. 위처럼 간단한 서버로 연다.

## 배포

이 저장소 이름이 `math`이고 GitHub Pages(Settings → Pages → Deploy from branch, `main` / root)를 켜면
https://ryujh28.github.io/math/ 에서 열린다. 팩을 새로 빌드했으면 `packs/`도 함께 커밋한다.

## 기록과 동기화

- 시도 하나 = 로그 한 줄. 기기 안 IndexedDB에 추가만 한다.
- 복습 상태(FSRS)는 저장하지 않고 로그를 다시 재생해 계산한다. 그래서 두 기기의 로그는 id 기준으로 합치기만 하면 된다.
- 동기화는 M2에서 비밀 GitHub Gist로 붙인다. 지금은 점검 화면의 내보내기·가져오기로 옮길 수 있다.

## 콘텐츠 원칙

- 문제는 원본(content/)의 생성기가 만들고, `tools/build.py`가 검증해 `packs/`로 내보낸다.
- 정답·정답 단계는 판정 함수(ok)를 통과해야 하고, 오답 보기·오답 블록은 통과하지 못해야 남는다.
- 판정 함수는 생성기의 손 계산과 별도로 SymPy 고수준 연산(det, eigenvals, dsolve, 수치 Laplace 적분 등)으로 만든다.
- 판정 함수가 반복문 변수를 늦게 묶으면(late binding) 빌드가 자동으로 거부한다. TeX에 소수 근삿값이 섞여도 거부한다.
- 실패·제외된 사례는 `tools/reports/chNN.md`에 남는다.
