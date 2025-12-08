# E2E Tests

End-to-end tests for full workflows.

## Structure

- **Smoke tests**: Fast sanity checks (~15 min)
- **Full E2E**: Complete workflows (~45 min)

## Run

```bash
pytest -m "e2e and smoke"    # Smoke tests
pytest -m "e2e and not slow" # Full suite
```

## Fixtures

- `e2e_workspace` - Complete project with toolchain
- `system_requirements` - Checks for CMake, compilers

See main tests/README.md for details.
