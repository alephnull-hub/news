# 매일 경제 브리핑 작업 지침

매일 07:40 KST에 루틴이 새 클라우드 세션을 띄워 이 지침대로 브리핑을 작성한다.
결과물은 `briefings/YYYY-MM-DD.json` 한 파일이다(날짜는 KST 기준 오늘). 이 파일로 보기용 Artifact 페이지
https://claude.ai/artifact/4usQTC3hvoJ7W55kw9Ngdh 를 같은 URL로 갱신한다.
형식의 예시는 `briefings/2026-10-28.json`이다. 처음 작업할 때 한 번 열어 보고 같은 수준으로 쓴다.

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
- `data/<오늘>/news.json`: 29개 출처(국내 12, 해외 9, 트렌드 6, 해설 2)의 직전 24시간 기사. 피드별 성공 여부는 `feeds`에 있다.
  해설(`explainer`)은 어피티와 뉴닉이다. 어피티 광고 글은 수집 단계에서 빠지고, 뉴닉은 공개 사이트맵과 기사 메타 정보(제목·요약)만 읽는다.
- `data/<오늘>/titles.txt`: 한 줄에 기사 하나(`id`, 지역, 시각, 매체, 제목). 이슈를 묶고 세는 데 쓴다.
- 기사 본문은 `python3 scripts/article_text.py <링크>`로 읽는다.
- 스크립트가 실패해도 멈추지 말고, 수집된 만큼으로 진행한다.

## 3. 수치 원칙 (가장 중요)

- **모든 숫자에는 기준일과 출처를 붙인다.** 시세판 타일은 `note`에 `10/27 · 연합뉴스`처럼 적는다.
- 우선순위는 다음과 같다.
  1. `market.json`의 `status: ok` 값
  2. 시황 기사 본문에 나온 수치. 예: 연합뉴스 "코스피 … 마감(종합)", "나스닥 …(종합)", "국고채 금리 …(종합)"
  3. 웹 검색
- 웹 검색 결과는 **기사 날짜가 대상 거래일과 일치할 때만** 쓴다.
- 확인하지 못한 값은 `"value": "확인 불가", "dir": "na"`로 둔다. **추정하거나 "100달러 아래" 같은 어림값으로 채우지 않는다.**
- 주말이나 휴장일에는 마지막 거래일 종가임을 `market.note`에 적는다.
- 요약에 넣는 사실과 수치는 기사 본문이나 RSS 제목·요약에서 확인한 것만 쓴다.
- 본문이 막힌(401·403) 기사나 유료 기사는 제목과 요약만 근거로 쓴다. 접근 제한을 우회하지 않는다.

## 4. 이슈 선정과 보도 건수

1. `titles.txt`를 지역별로 훑어 같은 사안을 다룬 기사들을 이슈로 묶는다.
2. 각 이슈의 건수는 `count_titles.py`로 센다. 핵심어 패턴은 해당 이슈만 잡히도록 좁게 잡는다.
   ```
   python3 scripts/count_titles.py --region domestic "하이닉스" "SK하닉"
   ```
   예를 들어 "경기"는 "경기도"까지 잡으므로 "경기 ?전망"처럼 좁힌다. 결과로 나온 샘플 제목을 보고 엉뚱한 기사가 섞였으면 패턴을 고친다.
3. 국내 5개, 글로벌 5개를 건수 순으로 고른다. 단순 게시판·인사·행사 공지는 제외한다.
4. 각 이슈는 다음으로 구성한다.
   - `summary`: 3~4문장, 구체적인 수치 포함
   - `why`: 2문장, 시장·생활에 미치는 영향
   - `sources`: 원문 링크 3~6개. `news.json`의 `link`를 쓰고, 매체명이 겹치면 괄호로 구분한다. 예: `연합뉴스 (기업 경기 전망)`
5. **산업·기업 동향**: 투자·M&A·계약·규제·상장 소식 8~12개를 한 줄씩 쓴다.
6. **트렌드 인사이트**: 여러 기사(트렌드 피드 포함)를 묶은 흐름 3개를 쓴다. 각각 근거 4~5개(출처 포함)와 2문장 분석으로 구성한다.
7. **급상승 검색어**: `news.json`에서 `traffic`이 있는 Google 트렌드 항목 중 5~7개를 고른다. 이유를 알 수 있는 것만 `comment`에서 설명한다.
8. **이번 주 일정**: 한국 시간으로 쓴다. 해외 일정은 웹 검색으로 확인하고, 확인하지 못한 일정은 넣지 않는다. 오늘과 내일의 핵심 일정은 `hot: true`로 표시한다.
   - 미국 서머타임(3월 둘째 일요일~11월 첫째 일요일)에는 한국과 13시간, 그 외에는 14시간 차이다.
9. **쉽게 읽는 해설**: `--region explainer` 기사 중 오늘 이슈와 관련 있는 경제·생활 경제 글 4~6개(짝수)를 고른다. 정치·사건 기사는 넣지 않는다.
   - 제목은 원문을 살리되, 끝의 이모지는 뺀다.
   - `summary`는 RSS 요약이나 메타 설명을 바탕으로 1~2문장으로 직접 쓴다. 원문을 길게 옮기지 않는다.
10. **생각해 볼 점**: 기회 4개, 리스크 4개, 지켜볼 키워드 5~6개를 쓴다.
11. **lead**: 오늘 가장 중요한 흐름을 2문장으로 쓴다.

## 5. JSON 형식

```json
{
  "date": "YYYY-MM-DD",
  "generated_at": "HH:MM",
  "collection": {"window": "MM/DD HH:MM – MM/DD HH:MM KST", "feeds_ok": 27, "feeds_total": 27, "articles": 1229, "failed": ["열리지 않은 피드 이름"]},
  "title": "오늘의 비즈니스·경제 브리핑",
  "lead": "2문장",
  "market": {
    "note": "10/27 종가 기준",
    "tiles": [{"name": "코스피", "value": "5,638.34", "change": "168.87 (+3.09%)", "dir": "up|down|flat|na", "note": "10/27 · 연합뉴스"}],
    "foot": "기준 설명",
    "sources": [{"label": "연합뉴스 (국내 증시·환율)", "url": "https://..."}]
  },
  "domestic": [{"title": "", "tags": ["반도체", "증시"], "count": 59, "summary": "", "why": "", "sources": [{"label": "", "url": ""}]}],
  "global": [/* domestic과 같은 형식 */],
  "industry": [{"who": "네이버", "what": "한 줄", "source": {"label": "", "url": ""}}],
  "trends": [{"title": "", "evidence": [{"text": "", "source": {"label": "", "url": ""}}], "insight": ""}],
  "explainers": [{"title": "", "summary": "1~2문장", "source": {"label": "어피티|뉴닉", "url": ""}}],
  "search_trends": {"note": "Google 트렌드 한국 · 수집 시점 기준", "items": [{"term": "", "traffic": "500+"}], "comment": ""},
  "schedule": {"note": "모두 한국 시간", "rows": [{"when": "10/29(목) 03:00", "event": "", "watch": "", "hot": true}], "foot": "", "sources": [{"label": "", "url": ""}]},
  "watch": {"opportunities": ["문장" , {"text": "문장", "source": {"label": "", "url": ""}}], "risks": ["..."], "keywords": ["..."]},
  "notes": ["특이사항이 있을 때만"]
}
```

- 시세판 타일은 4의 배수(8개 또는 12개)로 맞춘다. 기본 구성은 다음 12개다: 코스피, 코스닥, 원/달러, 국고채 10년, S&P 500, 나스닥, 다우, 필라델피아 반도체, WTI, 브렌트, 미 국채 10년, VIX.
- `change`에는 부호 대신 크기만 쓰고 방향은 `dir`로 표시한다. 화살표(▲▼)와 색은 페이지가 붙인다.
- 문자열에 HTML을 넣지 않는다. 페이지가 모두 글자로 처리한다.
- JSON 문법을 확인한다: `python3 -c "import json; json.load(open('briefings/YYYY-MM-DD.json'))"`.

## 6. 저장과 푸시

1. `briefings/YYYY-MM-DD.json`을 저장한다. `data/`와 `site/`는 `.gitignore` 대상이라 커밋되지 않는다.
2. 커밋 메시지는 `briefing: YYYY-MM-DD`로 한다.
3. `git push -u origin claude/jolly-tesla-u8r0gz`로 푸시한다. 네트워크 오류일 때만 2·4·8·16초 간격으로 최대 4번 재시도한다.

## 7. Artifact 페이지 갱신

1. `python3 scripts/render_page.py`로 `site/index.html`을 만든다. 최근 60일 브리핑이 한 페이지에 들어간다.
2. Artifact 도구로 기존 페이지를 먼저 읽는다: `action: "read"`, `url: "https://claude.ai/artifact/4usQTC3hvoJ7W55kw9Ngdh"`.
3. 같은 URL로 다시 게시한다: `file_path: "site/index.html"`, `url: "https://claude.ai/artifact/4usQTC3hvoJ7W55kw9Ngdh"`. `icon`은 넘기지 않는다.
4. 새 Artifact를 만들지 않는다. 게시가 실패하면 커밋은 그대로 두고, 마지막 응답에 실패 사유를 적는다.

## 8. 마지막 응답

마지막 응답은 푸시 알림으로 전달되므로 짧게 쓴다.
- 1줄: lead의 첫 문장
- 1줄: 핵심 수치 3개 (예: `코스피 +1.2% · S&P −0.4% · 원/달러 1,324원`)
- 1줄: 페이지 링크 https://claude.ai/artifact/4usQTC3hvoJ7W55kw9Ngdh , 또는 실패했다면 어느 단계에서 왜 실패했는지
