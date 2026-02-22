# DESIGN SKILL — Basket Monitor

## Aesthetic Direction
Professional terminal-finance. Think Bloomberg Terminal meets modern 
crypto dashboard. Sober, dense, data-first. Every pixel earns its place.

## Non-negotiables
- True black backgrounds only (#050505, #080808). Never grey.
- IBM Plex Mono for ALL numbers, prices, returns, percentages.
- Green (#00ff9d) = positive, long, profit. Never use for anything else.
- Red (#ff3d5a) = negative, short, loss. Never use for anything else.
- Amber (#f5a623) = warnings, volatility only.
- No shadows except subtle green glow on active tab indicator.
- No rounded corners above 4px anywhere.
- No white. No light mode. No gradients except the specified ones.

## What "professional" means here
- Labels at 9px uppercase with 0.18em letter-spacing
- Numbers always tabular-nums, monospaced, right-aligned in tables
- Borders at #1a1a1a — barely visible, structural not decorative
- Hover states at #0d0d0d — subtle, not flashy
- Active states use color, not background fill

## What to avoid
- Card shadows or elevation effects
- Colored backgrounds on stat tiles
- Any blue except benchmark chart line (#3d7eff)
- Gradient text
- Animations beyond 150ms transitions on hover
```

---

**Luego al inicio del prompt del agente agregá:**
```
Also read DESIGN_SKILL.md before touching any component. 
Every styling decision must be justified against that file.
If a choice is not covered in DESIGN_SKILL.md, default to 
"more minimal, more black, more mono".