# news

매일 07:40 KST에 Claude Code 클라우드 루틴이 국내·글로벌 경제 브리핑을 작성해
`briefings/YYYY-MM-DD.md`로 커밋하고, 완료되면 휴대폰 푸시 알림을 보낸다.
보기용 페이지: https://claude.ai/artifact/4usQTC3hvoJ7W55kw9Ngdh (매일 같은 URL로 갱신, 최근 60일 보관)

## 구성

| 경로 | 역할 |
|---|---|
| `prompts/daily-briefing.md` | 루틴이 따르는 작업 지침과 브리핑 양식 |
| `scripts/fetch_market.py` | 한국은행 ECOS·FRED 공식 수치 수집 → `data/<날짜>/market.json` |
| `scripts/fetch_news.py` | 국내외 경제 RSS 10개 수집 → `data/<날짜>/news.json` |
| `scripts/article_text.py` | 기사 본문 추출 (시황 기사의 수치 인용용) |
| `scripts/render_page.py` | `briefings/`를 Artifact 페이지(`site/index.html`)로 변환 |
| `briefings/` | 매일의 브리핑 결과 |

스크립트는 표준 라이브러리만 쓴다(Python 3.9+).

## 공식 수치용 API 키 (선택)

키가 없으면 해당 소스는 건너뛰고, 수치는 시황 기사 인용으로 채운다. 기사에서 확인되지 않은 값은 `확인 불가`로 표시한다.
클라우드 환경 설정의 환경 변수에 넣는다.

- `ECOS_API_KEY`: KOSPI·KOSDAQ·외국인 순매수·원/달러·국고채. https://ecos.bok.or.kr/api/ 에서 발급
- `FRED_API_KEY`: S&P 500·나스닥·다우·VIX·미 국채 10년·WTI. https://fred.stlouisfed.org/docs/api/api_key.html 에서 발급

## 네트워크 허용 도메인

`www.yna.co.kr`, `www.hankyung.com`, `www.mk.co.kr`, `feeds.content.dowjones.io`,
`feeds.bbci.co.uk`, `ecos.bok.or.kr`, `api.stlouisfed.org`

## 수동 실행

```bash
python3 scripts/fetch_market.py && python3 scripts/fetch_news.py
```
