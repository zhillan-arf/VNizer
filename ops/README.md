# Operations and Planning

This directory holds sprint briefs and task records. Task records are grouped
by owner and sprint:

```text
ops/
|-- README.md
|-- _task-template.md
|-- 001-zhil/
|   |-- sprint-001/
|   |   |-- brief.md
|   |   |-- tasks/{backlog,active,archive}/
```

## Task workflow

Substantive work is tracked under
`ops/001-zhil/sprint-XXX/tasks/{backlog,active,archive}/`.

1. Read this file, the current sprint brief, and its task directories.
2. Continue a matching task or create one from the shared
   [_task-template.md](_task-template.md) in that sprint's `backlog/`.
3. Move the task to `active/` and record context and a plan before making
   substantive changes.
4. Record decisions, changed files, verification performed, and remaining
   questions in the task file.
5. On completion, set `status: done` and move the task to `archive/`. If blocked,
   leave it in `backlog/` with `status: blocked` and state the blocker.

Task IDs are repository-wide and sortable, in the form `TASK-S001-001`,
`TASK-S001-002`, and so on. Search every task directory before assigning an ID.
The task's sprint, ID, title, lifecycle status, path, and heading must agree.
Formal dependencies are individual bullets containing only a backticked task
ID; use prose for related work that does not block execution.

Do not claim tests or runtime verification that were not run. As the project
adds code and verification commands, document their intended use in the task
and repository README.

The `001-zhil` owner path identifies the initial project owner. The layout can
expand if other contributors need separate ownership trees.
