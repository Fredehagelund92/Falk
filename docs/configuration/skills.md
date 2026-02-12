# Agent Skills

falk integrates [pydantic-ai-skills](https://github.com/DougTrajano/pydantic-ai-skills) so you can bring your own skills. Skills are modular collections of instructions, scripts, and resources that extend the agent's capabilities.

## Why Use Skills?

- **Domain expertise** — add specialized knowledge (e.g., data quality checks, report templates)
- **Progressive disclosure** — load skill details only when relevant (saves tokens)
- **Composable** — mix and match skills from your team or the community
- **Type-safe** — built on the [Agent Skills spec](https://agentskills.io)

## Configuration

Edit `falk_project.yaml`:

```yaml
skills:
  enabled: true
  directories: ["./skills"]
```

Create a `skills/` directory and add skills as subdirectories, each with a `SKILL.md` file:

```
skills/
├── data-quality-check/
│   └── SKILL.md
└── my-custom-skill/
    ├── SKILL.md
    ├── scripts/
    │   └── my_script.py
    └── resources/
        └── REFERENCE.md
```

## Minimal SKILL.md

```yaml
---
name: my-skill
description: Brief description of what this skill does and when to use it
---

# My Skill

## When to Use This Skill

Use this skill when you need to:
- Do specific task A
- Handle scenario B

## Instructions

1. Step 1
2. Step 2
```

## Learn More

- [pydantic-ai-skills](https://github.com/DougTrajano/pydantic-ai-skills) — full documentation
- [Agent Skills spec](https://agentskills.io) — structure and conventions
- [Agent Skills Cookbook](https://cookbook.agentskills.io) — examples and patterns
