# SESSION_NOTES

半自动会话记录：`start` 自动记录会话开始，`end` 自动记录最近一次提交并附人工 next。

## [2026-02-08 23:56:34] START frontend-m1
- branch: `feat-frontend`
- head: `30ed1b6`
- worktree: `D:\CodeSpace\prj_rechnung\bills__frontend`
- status: in_progress

## [2026-02-10 13:55:35] END frontend-m1
- branch: `feat-frontend`
- scope: `frontend/**` M1->M2.1 upload/manual-review workflow
- status: in_progress
- note: Upload and Manual Review UI are connected; one-click Submit in Confirm Results now chains review + queue merge.
- note: Monthly Excel source switch now supports `from Local` and `from Lark` (scaffold); local maps to `local://<filename>`.
- next: split first-version frontend commits into tooling/contracts/upload/review/docs and push for backend联调.
- risk: Local Excel currently passes only string path token, backend has no binary upload parsing yet.
