# 원자력 공부 노트 (Nuclear Daily)

> 처음이라면 **[사용방법.md](사용방법.md)** 부터 보세요 (보기 · 설정 · 올리기 · 앱 설치).

매일 아침 국내외 **원자력 뉴스 해설**과 매주 주요 저널의 **신규 논문 동향**을 한 사이트에서 봅니다.
`malmok2/Nuclear_News`(뉴스 브리핑)와 `malmok2/PaperCollection`(주간 논문 다이제스트)을 하나의 앱으로 합친 버전입니다.

```
홈            오늘의 뉴스 요약 + 이번 주 논문(내 관심 분야별) + 지난 일주일
오늘의 뉴스    뉴스 5건 해설: 무슨 일이 있었나 / 기술 배경 / 왜 중요한가 / 개념 풀이 / 생각해 볼 질문
뉴스 모아보기  날짜별 아카이브
이번 주 논문   저널·토픽·국가·키워드 동향, 관심 분야 추적기
논문 DB       누적 논문 검색·필터·CSV, Excel 내려받기
이메일로 받기  상단 버튼. 방문자가 이메일로 뉴스·논문 알림을 구독 (Buttondown, 현재 꺼 둠)
```

## 1. 처음 설정 (약 10분)

1. **GitHub에 새 저장소를 만들고 이 폴더를 올립니다** (예: `nuclear-digest`, Public).
   ```bash
   cd nuclear-digest
   git init && git add . && git commit -m "first commit"
   git branch -M main
   git remote add origin https://github.com/<내 아이디>/nuclear-digest.git
   git push -u origin main
   ```
2. **`config/site.json`을 고칩니다.** 이 파일 하나가 개인 설정입니다.
   - `site_url`, `repo_url`: `YOUR-GITHUB-ID`를 내 아이디로
   - `title`, `subtitle`, `owner`: 사이트 이름
   - `interests`: 내 관심 분야와 키워드. 논문은 이 키워드로 「관심 분야 추적기」를 만들고, 뉴스 해설은 비슷하게 중요한 뉴스 중 이 분야를 먼저 고릅니다.
   - `email.recipients`: 주간 논문 메일 받을 주소
3. 저장소 **Settings → Pages → Source: GitHub Actions**
4. 저장소 **Actions** 탭에서 워크플로 사용을 허용하고, `Daily nuclear news brief` → **Run workflow**로 한 번 돌려 봅니다.

### 선택 설정 (Settings → Secrets and variables → Actions)

| 종류 | 이름 | 용도 |
|---|---|---|
| Secret | `ANTHROPIC_API_KEY` | 뉴스 해설을 Actions에서 바로 작성 + 논문 제목 번역 품질 향상 (사용량만큼 과금) |
| Secret | `BUTTONDOWN_API_KEY` | 구독자에게 뉴스·논문 메일 발송 (아래 2-1) |
| Secret | `SMTP_USER`, `SMTP_PASSWORD` | `email.recipients`(나)에게 주간 논문 메일 직접 발송 (Gmail 주소 + **앱 비밀번호** 16자리). 구독 기능과 별개, 없어도 됨 |
| Secret | `OPENALEX_API_KEY`, `ELSEVIER_API_KEY` | 논문 메타데이터 보강 (없어도 됨) |
| Variable | `SITE_URL` | `config/site.json`의 주소 대신 쓸 때 |

## 1-1. 홈 화면 앱으로 쓰기

사이트가 GitHub Pages에 올라가면 앱처럼 설치할 수 있습니다(설치 파일·스토어 없음, 무료).
- **안드로이드 / PC(크롬·엣지):** 사이트를 열고 주소창 옆 「앱 설치」 또는 메뉴 → 「앱 설치」
- **아이폰:** 사파리에서 열고 공유 버튼 → 「홈 화면에 추가」

열면 주소창 없는 별도 창으로 뜨고, 내용은 매일·매주 자동 갱신되므로 앱 업데이트가 필요 없습니다.
인터넷이 끊겨도 마지막으로 본 페이지는 열립니다. 아이콘 아래 이름은 `config/site.json`의 `app_name`,
아이콘 그림은 `docs/icon.svg` · `docs/icons/`입니다.

## 2. 뉴스 해설을 누가 쓰나 — `config/site.json`의 `news_commentary`

| 값 | 동작 | 비용 |
|---|---|---|
| `session` (기본) | 수집은 Actions가 하고, 해설은 **Claude 예약 작업**이 아침에 씀 | Claude 구독 사용량 |
| `api` | `ANTHROPIC_API_KEY`로 수집 직후 바로 해설 | API 요금 |
| `none` | 해설 없이 제목·링크만 | 무료 |

`session`을 쓰려면 Claude에서 매일 아침 실행되는 예약 작업을 만듭니다(저장소를 Claude에 연결한 뒤 Claude에게 "이 예약 작업 만들어 줘"라고 하면 됩니다). 예약 작업 지시문:

```
저장소 <내 아이디>/nuclear-digest 에서:
1. python3 -m app.news.session_brief prompt 를 실행한다. SKIP 으로 시작하면 그 줄만 보고하고 끝낸다.
2. 출력된 규칙과 후보 기사만 보고(웹 검색·원문 열람 없이) 해설 JSON을 brief.json 으로 저장한다.
3. python3 -m app.news.session_brief apply brief.json 을 실행한다. ERROR 가 나오면 고쳐서 다시 apply 한다.
4. 바뀐 data/ docs/ 를 커밋하고 main 에 push 한다. 그다음 1번부터 반복한다(밀린 날이 없으면 SKIP).
```
06:50, 10:50(KST) 두 번 돌리면 수집이 늦은 날도 따라잡습니다. 해설 한 번에 입력 3~4천 + 출력 3~5천 토큰 정도입니다.

## 2-1. 이메일 구독 (상단 「이메일로 받기」)

> **지금은 꺼져 있습니다** (`config/site.json` → `newsletter.enabled: false`). `true`로 바꾸면 상단 버튼과 신청 페이지가 나타납니다.

이 사이트는 GitHub Pages라 이메일을 저장할 곳이 없어서, 구독자 관리는 뉴스레터 서비스 **Buttondown**이 맡습니다.
신청 확인 메일, 구독 취소 링크, 주소 보관을 Buttondown이 처리하고, 이 저장소는 발송할 내용만 보냅니다.

1. <https://buttondown.com> 가입 → 사용자 이름(username)을 정합니다. 구독자 100명까지 무료입니다.
2. `config/site.json` → `"newsletter": {"username": "내 Buttondown 이름"}`. 그전까지 구독 폼은 「준비 중」으로 표시됩니다.
3. Buttondown **Settings → API** 에서 키를 복사해 GitHub 저장소 Secret `BUTTONDOWN_API_KEY`로 등록합니다.

보내는 메일:
- **뉴스**: 해설이 사이트에 올라오면 그날 한 번. 해설이 없는 날은 보내지 않습니다. (워크플로는 원본 일정 그대로 두기 위해 빼 두었습니다. 켤 때 `python -m app.newsletter news`를 실행하는 워크플로를 추가해야 합니다.)
- **논문**: 월요일 주간 실행 끝에 한 번.
- 같은 날·같은 주는 두 번 보내지 않습니다(`state/*/newsletter-sent.json`).

**골라서 받기** — `"choose_lists": true`로 바꾸면 구독 폼에 「뉴스 / 논문」 체크박스가 생기고, 각 메일은 그 항목을 고른 사람에게만 갑니다.
Buttondown의 **태그 기능(유료 추가 옵션, 월 9달러)**이 필요합니다. `false`(기본값)이면 무료 플랜으로 구독자 전원에게 둘 다 보냅니다.

시험 발송 없이 내용만 확인: `python -m app.newsletter news --dry-run`, `python -m app.newsletter papers --dry-run`

## 3. 자동 실행 일정

```
매일 01:17 KST   뉴스 수집 (GitHub Actions, 실제 시작은 2~4시간 늦을 수 있음) → 제목만 있는 페이지 게시
매일 06:50·10:50 뉴스 해설 (예약 작업, session 모드일 때)
매일 09:13       뉴스 수집 재시도 (아침 수집이 실패했을 때만)
해설이 올라올 때  구독자에게 뉴스 메일 (Buttondown 설정 시)
매주 월 07:00    논문 수집: Crossref → OpenAlex 보강 → 제목 번역 → DB → 대시보드·Excel·메일
매주 월 12:00    논문 재시도 (실패했을 때만)
```
두 작업 모두 끝나면 홈 화면을 다시 만들고, 결과를 저장소에 커밋한 뒤 사이트를 재배포합니다.

## 4. 설정 파일

| 파일 | 내용 |
|---|---|
| `config/site.json` | **개인 설정**: 사이트 이름·주소, 이메일, 구독(`newsletter`), 하단 출처 표시(`credit`), 관심 분야, 뉴스 해설 방식, 독자 설명(`audience`) |
| `config/news.json` | RSS 피드(`enabled:false`로 끄기), 포함/제외 키워드, 뉴스 분류, '더 공부하기' 링크, 하루 해설 수(`min_stories`/`max_stories`) |
| `config/papers.json` | 수집 저널(이름: ISSN, 추가하면 지난 기간도 자동 소급 수집), 토픽 분류 규칙, 번역 용어집 |

## 5. 로컬 실행

```bash
pip install -r requirements.txt
python -m app.news.run_daily                          # 오늘 뉴스 수집(+API 키가 있으면 해설)
python -m app.news.run_daily --render-only            # 저장된 데이터로 뉴스 페이지만 다시 생성
python -m app.papers.run_weekly --no-email            # 이번 주 논문
python -m app.papers.run_weekly --skip-collect --no-email   # DB로 논문 페이지만 다시 생성
python -m app.build_home                              # 홈 화면만 다시 생성
python -m unittest tests.test_news_offline -v         # 네트워크 없이 뉴스 흐름 점검
```
`docs/index.html`을 브라우저로 열면 사이트를 바로 볼 수 있습니다.

## 6. 폴더 구조

```
config/          site.json(개인) · news.json · papers.json
app/             config.py(공통 설정) · site_theme.py(공통 디자인·메뉴) · build_home.py(홈) · build_subscribe.py(구독 페이지) · newsletter.py(구독 메일 발송)
app/news/        collect(RSS) · brief(해설 규칙·API) · session_brief(예약 작업용) · build_site · run_daily
app/papers/      collect(Crossref/OpenAlex) · translate · database · build_dashboard · build_database_page · build_excel · build_email · send_email · run_weekly
data/news/       날짜별 브리핑 JSON
data/papers/     literature.sql(누적 DB, 실행 시 sqlite로 복원) · translations_ko.json · raw/
state/           news/(게시한 기사, 마지막 실행) · papers/(마지막 실행, 메일 발송 이력)
docs/            공개 사이트: index.html(홈) · news/ · papers/
outputs/papers/  주간 메일 HTML
```

## 7. 저작권·정확성 원칙 (원본 그대로 유지)

- 기사 본문·사진은 수집·게시하지 않고, 제목·매체·링크만 원문 링크로 싣습니다.
- 전문 매체 RSS의 한 줄 요지는 AI 입력으로만 쓰고 저장하지 않습니다.
- 해설은 새로 쓴 글이며 기사 문장 복제·직접 인용을 금지합니다. 참고 링크는 `reference_library`에서만 고릅니다.
- 해설은 제목·요지만 근거로 하므로 세부 내용은 원문으로 확인해야 합니다.

## 8. 처음부터 들어 있는 데이터

원본 두 저장소의 데이터(뉴스 2026-09-27~10-22, 논문 9회차 688편)를 옮겨 와서 사이트가 처음부터 채워져 있습니다.
새로 시작하려면 `data/news/days/`, `state/news/seen.json`, `data/papers/`, `state/papers/`를 비우면 됩니다.

## 출처

이 프로젝트는 한양대학교 THINK LAB(<https://thinklab.hanyang.ac.kr/ko>)의 다음 저장소를 바탕으로 합쳐 만들었습니다.
- 원자력 뉴스 브리핑: <https://github.com/malmok2/Nuclear_News>
- 원자력공학 논문 주간 다이제스트: <https://github.com/malmok2/PaperCollection>

화면 디자인 규칙도 같은 연구실 홈페이지(`malmok2/Think_webpage`)를 따릅니다.
