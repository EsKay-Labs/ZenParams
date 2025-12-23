# Changelog

## [v2.0.0] - 2025-12-24

### Major Refactor (The "Zen" Update)

#### 🚀 Performance

- **$O(N)$ Dependency Crawler:** Replaced the legacy matrix scan with a high-speed forward-indexer. Performance improved by ~20x on large models (0.1s scan time).
- **Lazy Loading:** UI now initializes instantly and loads data asynchronously.

#### 🏗 Architecture

- **Class-Based Add-in:** Migrated from a simple script to a robust OOP structure (`ZenParamsAddin`).
- **Lifecycle Safety:** Fixed "Object not valid" crashes by implementing strict handler cleanup in `stop()`.
- **Native Persistence:** Replaced file-based storage (`json` files) with Fusion 360 `design.attributes`. Presets travel with the file.

#### 💅 UI Polish

- **Adaptive Auto-Fit:** Columns now automatically resize to fit the widest content (Name & Value) on startup.
- **Horizontal Scrolling:** Enabled `overflow-x` to prevent text clipping on long expressions.
- **Reliable Grouping:** Fixed group expansion logic to handle complex naming.
- **Legacy Theme:** Retained the beloved dark theme while upgrading the underlying CSS layout engine.

#### 🐛 Fixes

- Fixed `UnicodeEncodeError` in stress tests.
- Fixed `double-delete` crash on palette shutdown.
- Fixed "Droplist" (Group Header) click reliability.
