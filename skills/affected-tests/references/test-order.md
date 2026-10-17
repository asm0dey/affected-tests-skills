# test-order reference

Docs: https://parttimenerd.github.io/test-order/ (Getting started, Maven plugin, CLI reference).
Status: experimental (SapMachine team). Maven plugin `0.1.0` is on Maven Central; the Gradle plugin
was not on the Gradle Plugin Portal or Central when this skill was written — Gradle needs the Sonatype
snapshot repo (`0.0.1-SNAPSHOT`). The versions below go stale: run `scripts/check_versions.py` and use
the versions it reports.

## Setup

Done by the `affected-tests-setup` skill (`/affected-tests-setup`). One thing worth knowing here
too: `Processed collector fallback payloads` in a log means the plugin is declared without
`<extensions>true</extensions>` (or isn't declared at all). The index stays empty and every run
selects 100% of tests.

## Lifecycle

1. First `mvn test` after setup = learn run: instruments compiled classes offline and records
   test → class/member dependencies into `.test-order/`. Cost ≈ full suite + a few %.
   Works with `@QuarkusTest` (verified on a Quarkus 3.40 app).
2. Then `mvn test-order:affected test` — selects tests for the uncommitted git changes
   (default change mode; non-git projects: `-Dtestorder.changeMode=since-last-run`).
3. `mvn test-order:run-remaining test` — the deferred rest.
4. A resolved-classpath change (dependency bump, SNAPSHOT rebuild) automatically re-learns.

Useful goals: `show` (ranking), `explain` (per-test score for the current change set),
`diagnose` (setup health), `clean` (wipe state). `-Dtestorder.mode=order` fails instead of silently
re-learning when no index exists.

## Reading the output

- `Selected N tests (A scored + B new), deferred M` — the selection. "new" = test classes not in the
  index yet; they are always included.
- `Changed class X appears in deps of >50% of tests. Selection signal is weak` — near-full run;
  tell the user.
- `Shaded test-order-core-all.jar not found … falling back to unshaded jar` — harmless warning in 0.1.0.

## Measured on calit (Quarkus 3.40, 302 test classes, full suite 285 s)

Four injected bugs, each also run through the full suite to get the true set of failing tests:

| Bug | Full suite: failing classes | test-order: classes selected / time / failing caught |
|---|---|---|
| leaf service (`ChannelRouter`) | 6 | 42 / 137 s / 6 |
| HTTP resource guard | 4 | 44 / 106 s / 4 |
| Qute template attribute | 1 | 6 / 39 s / 1 |
| domain entity (`DateOverride`) | 2 | 25 / 233 s / 2 |

Every failing test the full suite found, test-order found too. The learn run took 304 s.
A name/import heuristic run on the same bugs missed the template bug entirely and caught
only 2 of 6 and 1 of 4 failing classes on the first two: that is why the skill has no
heuristic fallback.
