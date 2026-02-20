# TMC Redação - Development Continuation Prompt

Continue developing the TMC Redação project.

## Step 1: Read the Master Plan
**File:** `docs/MVP_PLAN_FEB_2026.md`

This file contains everything you need:
- **Progress Tracker** - Shows completed, in-progress, and pending tasks
- **Architecture decisions** - Technical approach and key decisions
- **File paths** - All files to create or modify
- **Hour estimates** - Time breakdown for each task
- **Success criteria** - What defines "done"

## Step 2: Check Progress Tracker
The Progress Tracker at the top of the plan shows:
- ✅ **Completed** - What's already done
- 🔄 **In Progress** - What was being worked on
- ⏳ **Pending** - What comes next

## Step 3: Continue from Current State
1. Find the first incomplete task in the Progress Tracker
2. Read the relevant section of the plan for details
3. Implement following the quality standards below

## Step 4: Update Progress & Commit
After completing each task:

1. **Update the Progress Tracker** in `docs/MVP_PLAN_FEB_2026.md`:
   - Move task from "Pending" or "In Progress" to "Completed"
   - Add date and relevant file paths
   - Update "In Progress" with the next task you're starting

2. **Commit your changes** with a descriptive message:
   ```
   feat: <short description of what was implemented>
   ```
   Common prefixes: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`

3. **Commit frequently** - After each logical unit of work, not just at the end

## Project Structure
```
Projeto Ferramenta TMC/
├── tmc-redacao/                # React frontend
├── tmc-redacao-wp/             # WordPress plugin
├── FeedRSS/tmc-rss-collector/  # Azure Functions backend
└── docs/MVP_PLAN_FEB_2026.md   # Master plan (READ THIS)
```

## Quality Standards
- Follow existing code patterns in the codebase
- Add loading and error states for async operations
- Use PropTypes for React components
- Follow WordPress coding standards for PHP files
- Test the build after changes

## Git Reference
- Tag `v0.0.0-mockup` preserves the original mockup state
- Main branch: `main`
- Commit after each completed task
- Keep commits atomic and descriptive


---

**Start by reading `docs/MVP_PLAN_FEB_2026.md`, check the Progress Tracker, and continue from where we left off.**
