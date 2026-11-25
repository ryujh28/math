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
content/            콘텐츠 원본 (장별 폴더: chapter.yaml, atoms.yaml, schemas.yaml, derivations.yaml, templates/*.py)
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
node tools/test_engine.mjs && node tools/test_session.mjs && node tools/test_sync.mjs   # 테스트
node tools/check_tex.mjs                  # 팩의 모든 수식·문장을 KaTeX로 렌더링 검사
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
- 단위마다 짧은 유도(derivations.yaml)가 있고, 앱의 "유도 보기"에서 열린다. 항목은 `goal`과 `steps` 두 가지가 모두 있어야 하며, 없으면 빌드가 멈춘다.
  - `goal` (문제 상황): 무엇이 주어지고 무엇을 구하거나 보이는지 한두 문장. 유도만 읽어서는 "이게 무슨 문제였지?"가 되기 쉬워서 필수로 한다.
  - `steps`: 한 줄은 문장 또는 `$$…$$` 수식 블록.
  - 유도 창은 문제 상황 → 이 단위의 실제 예시 문제(가장 낮은 단계, 눌러서 답 보기) → 유도 순으로 보여 준다. 예시 문제는 팩에서 자동으로 고른다.
- 힌트·오답 설명·장 요약·연결 카드·유도의 수식은 `$…$`로 감싼 TeX로 쓴다. 앱이 KaTeX로 그리고, `check_tex.mjs`가 `$` 밖에 남은 TeX 흔적이나 유니코드 위첨자를 잡는다.

## 기기 동기화 (GitHub Gist)

- 설정 → 기기 동기화에 GitHub 토큰(Gist 권한만)을 넣으면 연결된다. 첫 기기는 비밀 Gist를 만들고, 다음 기기는 같은 설명의 Gist를 찾아 붙는다.
- Gist 안 파일: `log-<기기 id>-<YYYYMM>.json` (그 기기가 그 달에 남긴 시도 기록 배열). 기기는 자기 파일만 쓰고 모든 파일을 읽어 id 기준으로 합친다 → 동시에 플레이해도 덮어쓰기 충돌이 없다.
- 언제: 앱을 열 때, 세션이 끝날 때, 앱으로 돌아올 때(visibilitychange), "지금 동기화".
- 올리기는 개수가 달라진 달 파일만, 받기는 크기가 달라진 파일만. 1MB가 넘어 응답에서 잘린 파일은 raw_url로 받는다.
- 토큰은 이 브라우저의 IndexedDB(ryujh28.github.io 출처)에만 저장된다. 같은 출처의 다른 페이지도 읽을 수 있으므로 Gist 권한만 준 토큰을 쓴다.
- 검사: `node tools/test_sync.mjs` (가짜 Gist 서버로 두 기기·월 경계·잘린 파일·기기 초기화 복구).

## 화면 폭 원칙 (모바일)

- 가로로 밀어야 보이는 화면을 만들지 않는다. 기준 폭 390px(일반 휴대폰), 340px까지 확인.
- 문제 TeX는 최상위 `\text{…}`를 HTML 글자로 빼고, 최상위 `,\ ` · `,\quad` · `\qquad`에서 수식을 조각낸다 (`splitPrompt`). 글자와 조각 사이에서 줄바꿈된다.
- 그래도 넓은 수식(큰 행렬 등)은 글자 크기를 줄여 맞춘다 (`fit`, 최소 55%). 보기 하나라도 넘치면 보기를 한 줄에 하나씩 놓는다. 블록·보기 안의 인라인 수식은 `=`·`+` 뒤에서 줄바꿈될 수 있다.
- 장 화면 표는 560px 이하에서 단위·상태·기억·유도 열만 남긴다.
- 점검: `tools/measure.html`을 띄워 (로컬 서버에서) 모든 문제를 실제 CSS로 그리고 넘치는 요소를 센다 (개발용, 배포에 필요 없음).

## M2.2 변경

- 오류 사냥 모드: 풀이 뼈대 단위를 순서 맞추기로 2번 이상 맞히면, 복습 때 오류 사냥과 순서 맞추기를 번갈아 낸다.
  - 순서 문제의 오답 블록(자리·오류 종류·이유가 이미 붙어 있음) 하나를 제자리에 끼워 한 줄만 틀린 풀이를 만든다. 새 콘텐츠 없음.
  - (1) 틀린 줄 탭 → (2) 오류 종류 4개 중 선택 (그 장에 실제로 나오는 종류만) → (3) 같은 자리의 다른 오답이 있으면 올바른 줄 고르기.
  - 채점: 첫 탭에 찾고 종류도 맞힘 → Good (빠르고 고치기까지 맞히면 Easy), 두 번째 탭에 찾았거나 종류가 틀림 → Hard, 세 번 안에 못 찾음 → Again.
- 검사: `node tools/test_hunt.mjs` (모든 순서 문제에서 사례 생성·모드 배정·채점).

## M2.1 변경

- GitHub Gist 기기 동기화 (위 절).

## M1.4 변경

- 모바일 가로 넘침 수정: 390px에서 넘치던 문제 1,201개 → 0개 (340px에서는 가우스 소거의 첨가행렬 블록 일부만 블록 안 스크롤).
- 유도 창에 문제 상황(goal)과 예시 문제를 추가. 95개 단위 모두에 goal 작성.
- 장 화면 표를 좁은 화면에 맞게 줄임.

## M1.3 변경

- 채점: 객관식은 틀리면 Again, 4초 안에 맞히면 Easy, 그 밖에 맞히면 Good.
- 한 판 더: 세션 요약에서 약 5분짜리 추가 판. 기억 확률이 낮은 배운 단위 + 보너스 새 단위 최대 2개 (하루 새 단위는 설정값의 2배까지).
- 하루 새 단위 기본값 3 → 5. 예전 기본값 3으로 저장된 설정은 5로 올린다.
- 공식 원자(`kind: formula`)는 `generator: "fxN:fn"`으로 구체적 적용 문제를, `variants:`로 손으로 쓴 변형을 더 가질 수 있다. 판정은 생성기 원자와 같다.
- `tools/verify_derivations.py`: 유도 펼치기의 식들을 SymPy로 검사.
