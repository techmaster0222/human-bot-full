# Contributing Guide

## Branch Strategy

```
main        ← Production (protected, 2 approvals required)
staging     ← QA/Testing (protected, 1 approval required)
develop     ← Integration (protected, 1 approval required)
feature/*   ← New features
fix/*       ← Bug fixes
hotfix/*    ← Critical production fixes
```

## Workflow

### Regular Development
```bash
# 1. Start from develop
git checkout develop
git pull origin develop

# 2. Create feature branch
git checkout -b feature/TASK-123-description

# 3. Make changes & commit
git add .
git commit -m "feat: add user authentication"

# 4. Push and create PR
git push origin feature/TASK-123-description
# Create PR: feature/* → develop
```

### Hotfixes (Critical Production Issues)
```bash
# 1. Branch from main
git checkout main
git pull origin main
git checkout -b hotfix/critical-bug-fix

# 2. Fix and commit
git commit -m "fix: resolve critical authentication bug"

# 3. PR directly to main (requires 2 approvals)
git push origin hotfix/critical-bug-fix
```

## Commit Message Format

```
type(scope): description

[optional body]

[optional footer]
```

### Types
| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation |
| `style` | Formatting (no code change) |
| `refactor` | Code restructuring |
| `test` | Adding tests |
| `chore` | Maintenance tasks |
| `ci` | CI/CD changes |
| `perf` | Performance improvements |

### Examples
```
feat(auth): add JWT token refresh
fix(proxy): resolve connection timeout issue
docs(api): update endpoint documentation
refactor(bot): simplify session management
test(proxy): add unit tests for rotation
```

## Code Quality

### Before Committing
```bash
# Format code
make format

# Run linter
make lint

# Run tests
make test
```

### Pre-commit Checklist
- [ ] Code formatted (`black`, `prettier`)
- [ ] Linter passes (`ruff`)
- [ ] Tests pass (`pytest`)
- [ ] No sensitive data committed
- [ ] Documentation updated

## Pull Request Process

1. **Create PR** with descriptive title
2. **Fill template** completely
3. **Request reviewers** (auto-assigned via CODEOWNERS)
4. **Address feedback** and update
5. **Squash & merge** when approved

## Release Process

### Version Format
```
v1.0.0      # Major.Minor.Patch
v1.0.0-rc.1 # Release candidate
v1.0.0-beta # Beta release
```

### Creating a Release
```bash
# 1. Merge develop → staging (QA testing)
# 2. After QA approval, merge staging → main
# 3. Tag the release
git checkout main
git pull origin main
git tag -a v1.0.0 -m "Release v1.0.0"
git push origin v1.0.0
```

## Questions?

Contact: @techmaster0222
