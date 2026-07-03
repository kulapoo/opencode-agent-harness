---
paths:
  - "**/*.swift"
  - "**/Package.swift"
---
# Swift Hooks

> This file extends [common/hooks.md](../common/hooks.md) with Swift specific content.

## Post-Edit Checks

Run after editing Swift files:

- **SwiftFormat**: Auto-format `.swift` files after edit
- **SwiftLint**: Run lint checks after editing `.swift` files
- **swift build**: Type-check modified packages after edit

## Warning

Flag `print()` statements — use `os.Logger` or structured logging instead for production code.
