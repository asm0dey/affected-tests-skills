---
name: affected-tests
description: Run only the Java/Kotlin tests affected by the current code changes using the test-order plugin (Maven or Gradle; JUnit 4/5/6, TestNG, Kotest), fix what fails, and report the time saved versus the full suite. Use this whenever the user wants fast test feedback on a JVM project — "run the tests for my change", "run affected tests", "test what I touched", "did I break anything", "quick check before I commit", "the full suite takes forever", "only run relevant tests", "smart/selective/incremental test run" — and also when you have just edited Java/Kotlin code yourself and need to verify it before reporting done. Prefer it over a blind `mvn test` / `./gradlew test` whenever the suite is slow or the change is local.
---

# Affected tests

Goal: the shortest test run that still tells the truth about the change, then a fix loop on what fails.

Selection is done by **test-order** (`me.bechberger:test-order-*`): during one learn run it records which classes and members each test actually executes, then selects tests for the uncommitted git changes. It sees tests that reach code over HTTP, through templates or DI, which name/import heuristics miss. A heuristic selector was tried and dropped for that reason: on a Quarkus app it came back green on a real template bug. When test-order can't be used, run the full suite; a fast green that is wrong is worse than a slow one.

## Workflow

### 1. Read project constraints

Check `CLAUDE.md` / `CONTRIBUTING.md` for how tests must be run (Docker, Testcontainers reuse, no concurrent runs, required `-D` flags, toolchain managers). Pass such flags through to every command below. Use `./mvnw` / `./gradlew` when the wrapper exists.

### 2. Check the plugin and its versions

```bash
python3 <skill-dir>/scripts/check_versions.py --repo .
```

It reports, as JSON, the latest published Maven plugin, whether a Gradle plugin is published yet (Plugin Portal or Central) and its version, and what this project configures.

- `maven.update_available` / `gradle.update_available` → tell the user (`configured → latest`) and offer the one-line bump. Don't bump silently: a new version can rename properties or tasks, so glance at the changelog linked from the docs first.
- `gradle.published: true` on a Gradle project still set up through the snapshot repo or init script → tell the user a released Gradle plugin now exists and offer to switch to it.
- `errors` present (offline, proxy) → mention it in one line and carry on with what's configured.

Then decide:

- Plugin configured and `.test-order/test-dependencies.lz4` exists → step 3.
- Plugin configured, no index → the next run is a full learn run (≈ full suite + ~7%). Say so, with the expected time, before running. It pays off from the second run.
- Plugin not configured → offer `/affected-tests-setup` (the `affected-tests-setup` skill: one pom edit for Maven, or an init script with no build edits for Gradle, then the learn run). It changes the build, so ask first. If the user declines, run the full suite and say that's what you did.

### 3. Run the affected tests

```bash
./mvnw test-order:affected test          # Maven
./gradlew testOrderAffected              # Gradle: on its own, never `testOrderAffected test`
```

On Gradle, don't append `test`: `./gradlew testOrderAffected test` also runs the regular `:test` task, which is the full suite (seen on exchange-bot: both ran, every failure printed twice). `testOrderAffected` runs the selected subset by itself.

Report the `[test-order] Selected N tests (A scored + B new), deferred M` line. If it warns that a changed class "appears in deps of >50% of tests", the run is close to the full suite: say so rather than presenting it as selective.

### 4. Fix loop

On failure:
1. Read failures from report files, not the console tail: Maven `target/surefire-reports/*.txt` (and `failsafe-reports`), Gradle `build/test-results/test/*.xml`. Logs can contain binary bytes, so use `grep -a`.
2. Find the root cause in the changed code; the change under test is the prime suspect. A failure from an unrelated pre-existing problem (an unbuilt asset, a missing env var) gets reported, not "fixed".
3. Fix production code. Changing a test's expectations is a behavior decision: ask, unless the test plainly encodes what the user asked to change.
4. Re-run only what failed: Maven `-Dtest=FooTest#method+other`, Gradle `--tests 'com.x.FooTest.method'`.
5. Once green, re-run `test-order:affected` once more to catch fallout from the fix.
6. After 3 failed attempts on the same test, stop and report what you learned instead of looping.

### 5. Report

```
Ran 25 of 299 test classes in 61 s (full suite ≈ 285 s).   ✅ green
  — or —   ❌ 2 failing → fixed DateOverride.resolve (global fallback), now green
Before pushing: ./mvnw test-order:run-remaining test   (the 274 deferred tests)
```

Full-suite time: use a measured number (this session, the learn run, the user); otherwise write "full suite not measured" rather than guessing.

## Things that skew the numbers

- Kotlin: verified on a Kotest 6.2.5 project (exchange-bot) with CLASS mode: every failing spec the full suite found in 3 injected bugs was caught, including one inside an `inline fun`. Precision drops around `inline fun` unless the project uses `-Dtestorder.instrumentation.mode=CLASS` (set by `/affected-tests-setup`). Kotest gets class-level ordering only, and only through `kotest-runner-junit5`.

- Quarkus / Spring Boot suites pay a fixed boot cost (~30 s) no matter how few tests run.
- `@TestProfile` / `@DirtiesContext` tests restart the app. A selection that pulls several in can approach full-suite time; on calit one selection of 25 classes took 233 s against 285 s for the full suite.
- Root build files (root `pom.xml`, `settings.gradle*`, version catalogs) and dependency changes trigger a re-learn or a near-full selection. That's correct behaviour.
