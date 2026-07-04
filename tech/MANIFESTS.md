# Non-JS/TS Manifest → Tech Dir

Loaded on demand by `init-tech-declaration` when a non-JS/TS manifest is
detected. JS/TS resolution lives inline in the skill (it has framework-aware
branching that fires often).

| Manifest / signal            | Tech dir     |
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
| `CMakeLists.txt` / `.c` / `.cpp` / `.h` | `cpp`    |
| `build.gradle` + `.java`          | `java`      |
| `build.gradle.kts` + `.kt`        | `kotlin`    |
| HarmonyOS project (`oh-package.json5`, `.ets` files) | `arkts` |
| `Makefile.PL` / `cpanfile` / `.pl` | `perl`      |

Mapping is 1:1 with the language — no framework branching. If a manifest
signals a tech dir that does not exist, fall back to `common/` only and write
in the target language's idioms.
