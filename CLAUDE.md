# CLAUDE.md

This file provides context and instructions for Claude Code when working on this project.

## Project Overview

networking-ai - A networking AI project.

## Picking Up Work from Claude Code

### How to Resume Previous Work

1. **Use the `/resume` command** - In Claude Code CLI, type `/resume` to see a list of recent sessions and select one to continue where you left off.

2. **Reference previous conversations** - You can describe what you were working on, and Claude will help you continue from that context.

3. **Check git history** - Review recent commits to understand what changes were made:
   ```bash
   git log --oneline -10
   git diff HEAD~1
   ```

4. **Use branch context** - If work was done on a feature branch, checkout that branch to continue:
   ```bash
   git branch -a
   git checkout <branch-name>
   ```

### Session Continuity Tips

- **Commit frequently** - Make small, descriptive commits so work can be easily resumed
- **Use TODO comments** - Mark incomplete work with `// TODO:` comments
- **Document in-progress work** - Update this file or create notes about ongoing tasks

### Useful Claude Code Commands

| Command | Description |
|---------|-------------|
| `/resume` | Resume a previous session |
| `/status` | Show current session status |
| `/clear` | Clear conversation history |
| `/help` | Show all available commands |
| `/compact` | Summarize conversation to reduce context |

### Best Practices for This Project

- Follow existing code patterns and conventions
- Write tests for new functionality
- Keep commits atomic and well-documented
- Update documentation when making significant changes

## Development Guidelines

- Use clear, descriptive commit messages
- Create feature branches for new work
- Review changes before pushing

## Notes

Add project-specific notes, conventions, or context here that will help Claude understand and work with this codebase effectively.
