# Repository Guidance

## Language rule

Use Simplified Technical English (STE) for all repository documents, task
records, code comments, commit messages, and explanations to the user. Apply
this rule to new text and to text that you revise. Preserve exact API names,
code, equations, citations, and quoted source text.

Use [ASD-STE100 Issue 9](https://www.asd-ste100.org/assets/files/ASD-STE100_ISSUE9.pdf)
as the primary source. Its Part 1 gives writing rules. Its Part 2 gives the
approved dictionary. Use these rules when you write:

- Use an approved word with its approved meaning and part of speech. Use a
  necessary technical noun or technical verb consistently. Explain it at first
  use if a reader might not know it.
- Use American English spelling. Use the same term for the same item. Do not
  use slang, idioms, or unnecessary abbreviations.
- Write short, direct sentences. Put one instruction or main idea in each
  sentence. Use active voice and simple verb forms.
- Write no more than 20 words in an instruction sentence. Write no more than
  25 words in a descriptive sentence. Split long sentences without loss of
  technical meaning.
- Use clear headings, lists, and tables. Make conditions and sequence explicit.
  Keep safety instructions clear and separate from general information.
- Check terminology, sentence length, and meaning before you finish. Do not
  claim full ASD-STE100 compliance unless a dictionary and rule review proves it.

These rules apply to proposed material too. Clear language does not change a
proposal into an approved product decision or a validated result.

## Project scope

VNizer converts PDF documents into narrated visual novel videos.
The source brief is preserved in `docs/archive/sprint-001-original-brief.md`.
Product requirements are in `docs/product/sprint-001.md`.

## Task workflow

Read `ops/README.md` and the current sprint brief before substantive work.
Use `ops/001-zhil/sprint-001/tasks/{backlog,active,archive}/`.
Create a task before implementation. Record its plan, results, checks, and risks.
Use repository-wide task IDs such as `TASK-S001-001`.
Move completed tasks to `archive/` with `status: done`.
Each phase has a P01, P02, or later controller. Commit each completed phase.
Do not report checks that did not run.

## Implementation rules

Keep source documents, model weights, secrets, and generated media out of Git.
Keep temporary review files in `/tmp/vnizer/`.
Preserve source page references and intermediate parser responses.
Use bounded requests, restart checkpoints, and explicit failure states.
Do not deploy Docker services. The user will deploy them.
