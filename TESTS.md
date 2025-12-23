# ZenParams Test Checklist

## Core Functionality Tests

### Startup

- [ ] Script loads without errors
- [ ] Palette opens correctly
- [ ] Auto-sort runs on startup
- [ ] Legacy params notice appears when applicable
- [ ] Empty state ("✨ Fresh Design") shows correctly for new designs

### Parameter Management

- [ ] Add Parameter button works
- [ ] Parameter name editable
- [ ] Parameter value editable
- [ ] Comment editable
- [ ] Delete parameter (X button) works
- [ ] Enter key in any field adds new row
- [ ] Changes sync to Fusion 360

### Preset System

- [ ] "📋 Current Design" shows in dropdown
- [ ] Selecting "Current Design" refreshes from Fusion
- [ ] Preset preview shows when selecting saved preset
- [ ] Load button applies preset to Fusion
- [ ] Save Template creates new preset
- [ ] Delete preset removes it

### Tree View

- [ ] Components show as Level 0 headers
- [ ] Bodies show as Level 1 headers (indented)
- [ ] Clicking component header toggles bodies (collapsed on expand)
- [ ] Clicking body header toggles params
- [ ] Sort button organizes params by Component/Body

### Search/Filter

- [ ] Search filters params by name
- [ ] Search filters params by value
- [ ] Search filters params by comment
- [ ] Matching params keep parent headers visible
- [ ] Clearing search shows all

### Smart Wizard

- [ ] Wizard modal opens
- [ ] Fit type dropdown populates
- [ ] Size input works
- [ ] Preview updates correctly
- [ ] Generate creates parameter

## Stability Tests

- [ ] No crashes when palette open during design work
- [ ] No freezes after extended use
- [ ] Document switch refreshes correctly
