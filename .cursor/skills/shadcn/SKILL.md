---
name: shadcn
description: Build and maintain shadcn/ui components in React apps using Tailwind CSS. Use when the user asks for shadcn components, UI scaffolding, component variants, or design-system aligned frontend work.
---

# shadcn/ui Skill

## When to use

Use this skill when implementing or updating UI with shadcn/ui patterns in a React frontend.

## Workflow

1. Identify the frontend app root (where `package.json` and Tailwind config live).
2. Verify shadcn setup:
   - `components.json` exists.
   - Tailwind is configured.
   - Alias paths in `components.json` match the project.
3. Add missing components with the shadcn CLI.
4. Compose UI using generated primitives and project conventions.
5. Keep behavior accessible (labels, keyboard support, semantic HTML).

## Commands

Use these commands from the frontend app directory:

```bash
npx shadcn@latest init
npx shadcn@latest add button input card dialog dropdown-menu form table toast
```

If the user asked to install this Cursor skill from a remote source, use:

```bash
npx skills add https://github.com/shadcn/ui --skill shadcn
```

## Implementation guidance

- Prefer composing existing primitives before introducing custom components.
- Keep variants in the component file using `class-variance-authority` patterns when needed.
- Reuse utility functions such as `cn()` for class merging.
- Use project tokens (`bg-background`, `text-foreground`, `border-border`, etc.) instead of hardcoded colors.
- Keep client boundaries explicit in Next.js (`'use client'` only where required).

## Quality checks

- Run project lint and type checks after edits.
- Verify generated imports use project aliases and compile without path errors.
- Ensure interactive components have focus-visible styles and keyboard navigation.
