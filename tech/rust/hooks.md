---
paths:
  - "**/*.rs"
  - "**/Cargo.toml"
---
# Rust Hooks

> This file extends common/hooks.md (../common/hooks.md) with Rust-specific content.

## Post-Edit Checks

Run after editing Rust files:

- **cargo fmt**: Auto-format `.rs` files after edit
- **cargo clippy**: Run lint checks after editing Rust files
- **cargo check**: Verify compilation after changes (faster than `cargo build`)
