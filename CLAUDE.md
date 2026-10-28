# news

사용자가 "오늘 브리핑 만들어줘"라고 하면 `prompts/daily-briefing.md`를 처음부터 끝까지 따라
오늘(KST) 브리핑을 만든다. 순서는 데이터 수집 → `briefings/YYYY-MM-DD.json` 작성 →
`claude/jolly-tesla-u8r0gz` 브랜치에 커밋·푸시 → Artifact 페이지 갱신이다.

- 마지막 응답은 지침 8절의 3줄 요약에 페이지 링크를 붙인다.
- 오늘 파일이 이미 있으면(예: 화요일 07:40 루틴이 먼저 만든 경우) 새로 쓰지 말고, 있다는 사실과 페이지 링크만 알린다.
  사용자가 다시 만들라고 하면 그때 덮어쓴다.
- 정기 루틴은 매주 화요일 07:40 KST에 같은 지침으로 돈다(trigger `trig_01EdVpHTnY5H4Dj9BfSmmYLi`).
