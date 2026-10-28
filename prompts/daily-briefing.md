# 매일 경제 브리핑 작업 지침

매일 07:40 KST에 루틴이 새 클라우드 세션을 띄워 이 지침대로 브리핑을 작성한다.
결과물은 `briefings/YYYY-MM-DD.md` 한 파일이고, 보기용으로 Artifact 페이지
https://claude.ai/artifact/4usQTC3hvoJ7W55kw9Ngdh 를 같은 URL로 갱신한다. 날짜는 KST 기준 오늘이다.

## 1. 준비

1. 작업 디렉터리가 `alephnull-hub/news` 저장소가 아니면 `git clone https://github.com/alephnull-hub/news`로 받는다.
2. 브리핑 브랜치 `claude/jolly-tesla-u8r0gz`로 이동해 최신 상태를 받는다.
   ```
   git fetch origin claude/jolly-tesla-u8r0gz
   git checkout claude/jolly-tesla-u8r0gz
   git pull origin claude/jolly-tesla-u8r0gz
   ```
3. 오늘 브리핑 파일이 이미 있으면 새로 쓰지 말고 끝낸다. 중복 실행을 막기 위해서다.

## 2. 데이터 수집

```
python3 scripts/fetch_market.py
python3 scripts/fetch_news.py
```

- `data/<오늘>/market.json`: ECOS·FRED 공식 수치. API 키가 없는 소스는 `skipped`로 남는다.
- `data/<오늘>/news.json`: 최근 30시간 RSS 헤드라인.
- 스크립트가 실패해도 멈추지 말고, 수집된 만큼으로 진행한다.

## 3. 수치 원칙 (가장 중요)

- **모든 숫자에는 기준일과 출처를 붙인다.** 예: `KOSPI 5,638.34 (+3.09%, 10/27 종가, ECOS)`
- 우선순위는 다음과 같다.
  1. `market.json`의 `status: ok` 값
  2. `news.json`에 있는 시황 기사의 본문에 나온 수치. 예: 연합뉴스 "코스피 … 마감(종합)", "나스닥 …(종합)", "국고채 금리 …(종합)". 본문은 `python3 scripts/article_text.py <링크>`로 읽는다.
  3. 웹 검색
- 웹 검색 결과는 **기사 날짜가 대상 거래일과 일치할 때만** 쓴다. 날짜가 섞여 나오는 경우가 잦으니 반드시 확인한다.
- 위 어디서도 확인하지 못한 값은 `확인 불가`로 적는다. **추정하거나 지어내지 않는다.**
- 2·3순위로 얻은 수치에는 `(기사 인용)`을 붙이고 기사 링크를 남긴다.
- 주말이나 휴장일에는 마지막 거래일 종가임을 명시한다. 한국 휴장일이면 "국내 증시 휴장"으로 표시한다.

## 4. 뉴스 선정

- `news.json`에서 국내 5건, 글로벌 5건을 고른다.
- 기준: 시장 영향(금리·환율·수출·반도체·에너지·정책) > 대형 기업 실적 > 기타.
- 같은 사안을 다룬 여러 매체 기사는 하나로 묶는다.
- 단순 게시판·인사·행사 공지는 제외한다.
- 각 항목은 2~3줄로 요약하고 원문 링크를 붙인다.
- 링크는 `news.json` 항목의 `link`(기사 주소)를 쓴다. 피드 주소는 쓰지 않는다.
- 요약에 넣는 수치와 사실은 기사 본문(`article_text.py`)이나 RSS 요약에서 확인한 것만 쓴다.
- MarketWatch처럼 본문 접근이 막힌(401·403) 기사는 RSS 제목과 요약만 근거로 쓴다. 접근 제한을 우회하지 않는다.
- 영문 기사는 한국어로 요약한다.

## 5. 양식

```markdown
# 경제 브리핑 YYYY-MM-DD (요일)

> 한 줄 총평: 오늘 시장을 이해하는 데 가장 중요한 한 문장

## 밤사이 글로벌 시장
| 지표 | 종가 | 등락 | 기준일 | 출처 |
|---|---|---|---|---|
| S&P 500 | | | | |
| 나스닥 | | | | |
| 다우 | | | | |
| 필라델피아 반도체 | | | | |
| VIX | | | | |
| 미 국채 10년 | | | | |
| WTI | | | | |
| 브렌트 | | | | |

(2~3줄 해설: 무엇이 시장을 움직였나)

## 국내 시장
| 지표 | 종가 | 등락 | 기준일 | 출처 |
|---|---|---|---|---|
| KOSPI | | | | |
| KOSDAQ | | | | |
| 외국인 순매수(유가증권) | | — | | |
| 원/달러 환율 | | | | |
| 국고채 10년 | | | | |

(2~3줄 해설)

## 국내 주요 뉴스
1. **제목** — 요약. [매체](링크)

## 글로벌 주요 뉴스
1. **제목** — 요약. [매체](링크)

## 오늘의 일정
- 오늘 발표되는 국내외 경제지표, 중앙은행 일정, 주요 실적 발표
- 웹 검색으로 확인하고, 확인되지 않으면 이 섹션을 "확인된 일정 없음"으로 둔다.

## 체크포인트
- 오늘 장에서 지켜볼 점 2~3개

---
수집: market.json(ECOS/FRED 상태), news.json(피드 n/10 성공) · 생성 시각 HH:MM KST
```

## 6. 저장과 푸시

1. `briefings/YYYY-MM-DD.md`로 저장한다. `data/`는 `.gitignore` 대상이라 커밋되지 않는다.
2. 커밋 메시지는 `briefing: YYYY-MM-DD`로 한다.
3. `git push -u origin claude/jolly-tesla-u8r0gz`로 푸시한다. 네트워크 오류일 때만 2·4·8·16초 간격으로 최대 4번 재시도한다.

## 7. Artifact 페이지 갱신

1. `python3 scripts/render_page.py`로 `site/index.html`을 만든다. 최근 60일 브리핑이 한 페이지에 들어간다.
2. Artifact 도구로 기존 페이지를 먼저 읽는다: `action: "read"`, `url: "https://claude.ai/artifact/4usQTC3hvoJ7W55kw9Ngdh"`.
3. 같은 URL로 다시 게시한다: `file_path: "site/index.html"`, `url: "https://claude.ai/artifact/4usQTC3hvoJ7W55kw9Ngdh"`. `icon`은 넘기지 않는다.
4. 새 Artifact를 만들지 않는다. 게시가 실패하면 커밋은 그대로 두고, 마지막 응답에 실패 사유를 적는다.

## 8. 마지막 응답

마지막 응답은 푸시 알림으로 전달되므로 짧게 쓴다.
- 1줄: 한 줄 총평
- 1줄: 핵심 수치 3개 (예: `KOSPI +1.2% · S&P −0.4% · 원/달러 1,324원`)
- 1줄: 페이지 링크 https://claude.ai/artifact/4usQTC3hvoJ7W55kw9Ngdh , 또는 실패했다면 어느 단계에서 왜 실패했는지
