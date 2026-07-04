# Non-JS/TS Manifest → Stack Dir

Loaded on demand by `rules/detect-stack.md` Step 2 when a non-JS/TS
manifest is detected. JS/TS resolution lives inline in the rule (it has
framework-aware branching that fires often).

| Manifest / signal            | Stack dir    |
| ---------------------------- | ------------ |
| `go.mod`                       | `golang`      |
| `Cargo.toml`                   | `rust`        |
| `pyproject.toml` / `requirements.txt` / `setup.py` | `python` |
| `Gemfile`                       | `ruby`        |
| `composer.json`                 | `php`         |
| `pubspec.yaml` (Flutter/Dart)    | `dart`        |
| `Package.swift`                  | `swift`       |
| `*.csproj` (C#)                | `csharp`      |
| `*.fsproj` or `.fs` files (F#)  | `fsharp`      |
| `CMakeLists.txt` / `.c` / `.cpp` / `.h` | `cpp`   |
| `build.gradle` + `.java`          | `java`        |
| `build.gradle.kts` + `.kt`        | `kotlin`      |
| HarmonyOS project (`oh-package.json5`, `.ets` files) | `arkts` |
| `Makefile.PL` / `cpanfile` / `.pl` | `perl`      |

Mapping is 1:1 with the language — no framework branching. If a manifest
signals a stack dir that does not exist, fall back per Step 2 of
`rules/load-stack-conventions.md`.
