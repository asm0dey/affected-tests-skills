---
name: affected-tests-setup
description: One-time setup of selective (affected-only) test runs for a Java/Kotlin Maven or Gradle project. Adds the test-order plugin at the latest published version, ignores its state dir, runs the learn pass and confirms the index actually got written. Use when the user runs /affected-tests-setup, or asks to "set up test-order", "enable affected tests", "make tests selective", "install smart test selection" in a JVM project. It edits build files, so use it only on an explicit request or after the user accepted the offer from affected-tests.
---

# Affected tests setup (test-order)

End state: `./mvnw test-order:affected test` (or `./gradlew testOrderAffected`) selects tests from a
learned index. The day-to-day loop lives in the `affected-tests` skill; this skill only
does the setup.

## 1. Inspect

- Build tool: `pom.xml` → Maven, `settings.gradle*` / `build.gradle*` → Gradle. For a Maven
  multi-module build, find the pom the modules inherit from (`<parent>`). That's where the plugin
  goes. It's often the root pom, but an aggregator-only root isn't a parent.
- Read `CLAUDE.md` / `CONTRIBUTING.md` for test-run constraints (Docker, required `-D` flags,
  no concurrent runs). The learn run in step 4 must respect them.
- Versions, configured and published:
  ```bash
  python3 <this-skill-dir>/../affected-tests/scripts/check_versions.py --repo .   # sibling skill; install both together
  ```
  Use `maven.latest` / `gradle.latest` from that output, never a version remembered from docs.
  If the plugin is already configured, this skill reduces to offering the version bump plus steps 4–5.

## 2. Show the plan, get a yes

One short message: which file changes, the exact snippet, and that the learn run takes about as
long as the full suite (+~7%). Changing the build is the user's call. Wait for confirmation.

## 3. Apply

**Maven:** in the parent pom's `<build><plugins>`, before `maven-surefire-plugin`:

```xml
<plugin>
  <groupId>me.bechberger</groupId>
  <artifactId>test-order-maven-plugin</artifactId>
  <version>LATEST_FROM_STEP_1</version>
  <extensions>true</extensions>
  <executions><execution><goals><goal>prepare</goal></goals></execution></executions>
</plugin>
```

Keep the project's conventions: if plugin versions live in `<properties>` or `<pluginManagement>`,
put it there the same way. `<extensions>true</extensions>` is required. See step 5 for what goes
wrong without it.

**Gradle**, depending on `gradle.published` from step 1:
- `true` → add `id("me.bechberger.test-order") version "<gradle.latest>"` to the `plugins {}` block
  (Groovy: `id 'me.bechberger.test-order' version '<v>'`) of each JVM project, or once via a
  convention plugin if the build has one.
- `false` → the Gradle plugin isn't published anywhere (no release, no snapshot), but its source
  is tagged with each release. Offer to build it locally. This runs a third-party build, so ask first:
  ```bash
  git clone --depth 1 --branch v<maven.latest> https://github.com/parttimenerd/test-order /tmp/test-order-src
  (cd /tmp/test-order-src/test-order-gradle-plugin && ./gradlew publishToMavenLocal -x test)
  ```
  Build from the **release tag**, not `main`: `main` moves ahead of the released core and fails to
  compile against it. The rest of test-order (core, agent, JUnit integration) still comes from
  Maven Central. Then copy `assets/test-order-init.gradle` (it resolves the plugin from
  `mavenLocal()`) into the project, or into `~/.gradle/init.d/` for all projects, which is the
  user's choice. Pass `--init-script test-order-init.gradle` on every Gradle call unless it lives
  in `init.d`. Replace `VERSION` in it with `maven.latest`. Tell the user this is a locally built
  plugin; once `gradle.published` turns `true`, switch to the plugins block above.

**Kotlin projects** (`src/*/kotlin`, `*.kt`): test-order tracks compiled bytecode, so Kotlin works, but
`inline fun` bodies are copied into call sites and the default MEMBER tracking loses them. Use
class-level tracking: `-Dtestorder.instrumentation.mode=CLASS` on the learn run and every later
run (or set it once in the plugin config). Kotest specs need `kotest-runner-junit5`; specs run without
the JUnit Platform runner are invisible to test-order. Tested upstream with Kotest 5.9.1 only.

**Both:** append `.test-order/` to `.gitignore`, unless the user wants the index shared (CI publishes
it and `test-order:download` fetches it).

## 4. Learn run

Run it in the background; it is a full suite:

```bash
./mvnw test        # Maven: prepare auto-switches to learn mode when no index exists
./gradlew test     # Gradle (add --init-script … when using the init script)
```

Pre-existing test failures don't block learning; note them for the user separately.

## 5. Verify, don't assume

Success needs both:
- the log contains `Index written: … (N tests)` with N close to the number of test classes, and
- `.test-order/test-dependencies.lz4` exists and is non-empty.

`Processed collector fallback payloads` plus a later `Selected N / N tests (100%)` means
instrumentation never ran: almost always `<extensions>true</extensions>` is missing or the plugin
sits in a pom the module doesn't inherit. Fix and re-run step 4. `./mvnw test-order:diagnose` helps.

Finish with a smoke test: touch one source file with a dedicated test, run
`./mvnw test-order:affected test`, confirm the selection is a small subset, then revert the touch.

## 6. Report

```
test-order 0.1.0 added to pom.xml (+ .test-order/ in .gitignore)
Learn run: 304 s, 297 test classes indexed
Smoke test: touching ChannelRouter.java selects 42 of 299 classes
Daily use: ./mvnw test-order:affected test   ·   before push: ./mvnw test-order:run-remaining test
```
