# 원자력 공부 노트 (Nuclear Daily)

원자력·핵융합을 공부하는 학생을 위해 **매일 뉴스 해설**, **매주 새 논문 동향**, **원자력 채용 공고**를 한 사이트에 모읍니다.

- 사이트: <https://monami-lab-2026.github.io/nuclear_digest/> (홈 화면 앱으로 설치 가능)
- 운영: 전북대학교 MONAMI LAB
- 처음이라면 **[사용방법.md](사용방법.md)** 부터 보세요 (보기 · 설정 · 앱 설치 · 문제 해결).

## 화면 구성

| 메뉴 | 내용 |
|---|---|
| 홈 | 오늘의 원자력·핵융합 뉴스 요약, 이번 주 논문(관심 분야별), 채용, 지난 일주일 |
| 오늘의 뉴스 | **원자력 / 핵융합** 탭. 뉴스마다 무슨 일이 있었나 · 기술 배경 · 왜 중요한가 · 개념 풀이 · 생각해 볼 질문 |
| 뉴스 모아보기 | 분야별 날짜 아카이브 |
| 이번 주 논문 | **원자력 / 핵융합** 탭. 트렌드 키워드, 저널·연구 영역·국가 분포, 토픽 지도, 급상승 키워드, 관심 분야 추적기 |
| 논문 DB | 분야별 누적 논문 검색·필터, CSV·Excel 내려받기 |
| 취업 | 원자력 공공기관 공고(공공데이터포털), 채용 동향, 채용·인력 뉴스, 링크집 |

### 무엇을 모으나

- **원자력 뉴스**: Google 뉴스(국내·해외), World Nuclear News, IAEA, U.S. NRC, ANS Nuclear Newswire
- **핵융합 뉴스**: 핵융합 키워드(핵융합, KSTAR, 인공태양, ITER, tokamak, fusion energy 등)로 같은 방식으로 따로 수집
- **원자력 논문**: Nuclear Engineering and Design, Annals of Nuclear Energy, Nuclear Engineering and Technology, Progress in Nuclear Energy, Nuclear Technology, Nuclear Science and Techniques
- **핵융합 논문**: Fusion Engineering and Design, Nuclear Fusion, Fusion Science and Technology, Journal of Fusion Energy, Plasma Physics and Controlled Fusion, Nuclear Materials and Energy 전체 + 위 원자력 저널 중 핵융합 관련 논문(제목·초록 키워드)

## 자동 실행 일정 (한국 시간)

| 언제 | 무엇 | 누가 |
|---|---|---|
| 매일 01:17 (보통 2~4시간 늦게 시작) | 원자력·핵융합 뉴스 수집 → 제목만 있는 페이지 먼저 게시 | GitHub Actions `daily-news.yml` |
| 매일 06:50 · 10:50 | 원자력·핵융합 뉴스 해설 작성, 논문 제목 번역 다듬기 | Claude 예약 작업 |
| 매일 09:13 | 뉴스 수집 재시도 (아침 수집이 실패했을 때만) | `daily-news.yml` |
| 매주 월 07:00 | 논문 수집: Crossref → OpenAlex 보강 → 제목 번역 → DB → 대시보드·Excel | `weekly-papers.yml` |
| 매주 월 08:37 | 원자력 공공기관 채용 공고 수집 | `weekly-jobs.yml` |
| 매주 월 12:00 | 논문 수집 재시도 (실패했을 때만) | `weekly-papers.yml` |
| `docs/` 가 push 될 때 | 사이트 재배포 | `deploy-pages.yml` |

## 설정 파일

| 파일 | 내용 |
|---|---|
| `config/site.json` | 사이트 이름·주소, 하단 소스 코드(`credit`)·원본 출처(`based_on`)·운영(`maintainer`), 관심 분야(`interests`), 뉴스 해설 방식(`news_commentary`), 이메일·구독 |
| `config/news.json` | 원자력 뉴스: RSS 피드, 포함/제외 키워드, 분류, '더 공부하기' 링크 |
| `config/news_fusion.json` | 핵융합 뉴스: 같은 구조 (`NEWS_TOPIC=fusion` 으로 실행할 때 사용) |
| `config/papers.json` | 원자력 저널(`journals`)과 핵융합 구역(`fusion`: 저널·키워드·연구 영역·트렌드 키워드), 번역 용어집 |
| `config/jobs.json` | 채용 수집 기관·필터·링크집 |

저널을 추가하면 이미 수집한 주차 중 최근 `new_journal_backfill_weeks` 주는 자동으로 소급 수집합니다.

### 뉴스 해설을 누가 쓰나 (`news_commentary`)

| 값 | 동작 |
|---|---|
| `session` (지금 설정) | 수집은 Actions, 해설은 Claude 예약 작업이 `app.news.session_brief` 로 작성 |
| `api` | Secret `ANTHROPIC_API_KEY` 로 수집 직후 바로 작성 |
| `none` | 해설 없이 제목·링크만 |

### GitHub Secrets (Settings → Secrets and variables → Actions)

| 이름 | 용도 |
|---|---|
| `DATA_GO_KR_KEY` | 채용 공고 수집 (공공데이터포털 인증키) |
| `ANTHROPIC_API_KEY` | (선택) Actions에서 해설·번역 바로 작성 |
| `OPENALEX_API_KEY`, `ELSEVIER_API_KEY` | (선택) 논문 초록·국가 정보 보강 |
| `SMTP_USER`, `SMTP_PASSWORD`, `BUTTONDOWN_API_KEY` | (선택) 주간 메일·구독 메일. 지금은 꺼져 있음 |

## 로컬 실행

```bash
pip install -r requirements.txt
python -m app.news.run_daily                          # 오늘 원자력 뉴스 수집
NEWS_TOPIC=fusion python -m app.news.run_daily        # 오늘 핵융합 뉴스 수집
python -m app.news.run_daily --render-only            # 뉴스 페이지만 다시 생성 (핵융합은 NEWS_TOPIC=fusion)
python -m app.news.session_brief prompt               # 해설할 날의 규칙·후보 출력 (apply brief.json 으로 반영)
python -m app.papers.run_weekly --no-email            # 이번 주 논문 수집
python -m app.papers.run_weekly --skip-collect --no-email   # DB로 논문 페이지만 다시 생성
python -m app.papers.session_translate prompt         # 다시 번역할 논문 제목 출력 (apply 로 반영)
python -m app.jobs.run_daily --render-only            # 취업 페이지만 다시 생성
python -m app.build_home                              # 홈만 다시 생성
python -m unittest discover -s tests                  # 점검
```

## 폴더 구조

```
config/          site.json · news.json · news_fusion.json · papers.json · jobs.json
app/             config.py · site_theme.py(공통 디자인·메뉴) · build_home.py · build_app.py(홈 화면 앱) · newsletter.py
app/news/        collect(RSS) · brief(해설 규칙) · session_brief(예약 작업용) · build_site · run_daily
app/papers/      collect(Crossref/OpenAlex) · translate · database · build_dashboard · build_database_page · build_excel · run_weekly
app/jobs/        채용 공고 수집·페이지
data/news/, data/fusion/   날짜별 원자력·핵융합 뉴스 JSON
data/papers/     literature.sql(누적 DB, 실행 시 sqlite로 복원) · translations_ko.json · raw/
state/           마지막 실행 기록, 이미 게시한 기사 목록
docs/            공개 사이트 (news/ · fusion/ · papers/ · papers/fusion/ · jobs/)
```

## 저작권·정확성 원칙

- 기사 본문·사진은 수집·게시하지 않고 제목·매체·링크만 싣습니다. 전문 매체 RSS의 한 줄 요지는 AI 입력으로만 쓰고 저장하지 않습니다.
- 해설은 새로 쓴 글이며 기사 문장 복제·직접 인용을 하지 않습니다. 해설은 제목·요지만 근거로 하므로 세부 내용은 원문으로 확인해야 합니다.
- 논문은 Crossref·OpenAlex 메타데이터(제목·저자·초록·DOI)만 쓰고, 본문은 DOI 링크로 연결합니다. 한글 제목은 기계번역입니다.

## 출처

이 프로젝트는 한양대학교 THINK LAB(<https://thinklab.hanyang.ac.kr/ko>)의 다음 저장소를 바탕으로 합쳐 만들고 확장했습니다.
- 원자력 뉴스 브리핑: <https://github.com/malmok2/Nuclear_News>
- 원자력공학 논문 주간 다이제스트: <https://github.com/malmok2/PaperCollection>

화면 디자인 규칙도 같은 연구실 홈페이지(`malmok2/Think_webpage`)를 따릅니다.
이 저장소에서 더한 것: 원자력·핵융합 분야 탭(뉴스·논문), 핵융합 저널·뉴스 수집, 채용 페이지, 홈 화면 앱, Claude 예약 작업 기반 해설·번역.
