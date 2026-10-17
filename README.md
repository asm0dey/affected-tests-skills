# affected-tests skills

Agent skills that run only the JVM tests your change can break, using
[test-order](https://parttimenerd.github.io/test-order/), the coverage-based test selector from the
SapMachine team.

| Skill | What it does |
|---|---|
| `affected-tests` | Runs `test-order:affected`, fixes failures, reports tests run and time saved, and points at `run-remaining` before you push. Checks for newer plugin versions each time. |
| `affected-tests-setup` | One-time setup: adds the plugin at the latest published version, runs the learn pass, and checks that the index really got written. |

Works with Maven and Gradle, Java and Kotlin, and JUnit 4/5/6, TestNG or Kotest.

## Install

The skills use the standard `SKILL.md` format, so any agent that reads Agent Skills can load them.
Install both together, because `affected-tests-setup` calls a script that lives in `affected-tests`.

Claude Code:

```bash
git clone https://github.com/asm0dey/affected-tests-skills
cp -r affected-tests-skills/skills/* ~/.claude/skills/
```

Then `/affected-tests-setup` once per project, and `/affected-tests` (or just "run the tests for my
change") after that. For other agents, copy `skills/*` into that agent's skills directory.

Requirements: `python3` (standard library only), `git`, and the project's own Maven/Gradle toolchain.

## Why coverage-based selection, not file-name matching

Measured on a Quarkus app with 302 test classes (full suite 285 s): four injected bugs, each checked
against the full suite to get the real list of failing tests.

| Bug | Full suite: failing classes | test-order: classes selected / time / failing caught |
|---|---|---|
| leaf service | 6 | 42 / 137 s / 6 |
| HTTP resource guard | 4 | 44 / 106 s / 4 |
| Qute template | 1 | 6 / 39 s / 1 |
| domain entity | 2 | 25 / 233 s / 2 |

test-order caught every failing test. A name-and-import heuristic tried on the same bugs went green
on the template bug, so these skills have no heuristic fallback: without test-order they run the
full suite.

Same check on a Kotlin/Kotest Gradle project (38 specs, 3 injected bugs): every failing spec caught,
9–18 s per run.

## Status

- test-order is experimental. Maven plugin `0.1.0` is on Maven Central.
- The Gradle plugin isn't published yet. `affected-tests-setup` builds it from the matching release
  tag into `~/.m2` and applies it with an init script, so no build files change.
- Verified by hand: Maven + Quarkus (Java) and Gradle + Kotest (Kotlin), the numbers above.
- Not yet verified: an end-to-end run of `affected-tests-setup` exactly as written.

test-order ships its own short [official skill](https://github.com/parttimenerd/test-order/tree/main/skills/test-order)
(goal reference, JSON output, error recovery). These skills add the version check, the
setup-and-verify flow, the fix loop, and the measured caveats.

## License

MIT
