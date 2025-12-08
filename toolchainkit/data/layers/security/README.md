# Security Layers

This directory contains YAML layer definitions for security hardening features.

## Available Security Layers

### Stack Protection

| Layer | Level | Protection Scope | Overhead | Recommended For |
|-------|-------|-----------------|----------|----------------|
| `stack-protector-strong` | strong | Functions with arrays/buffers/address-taken | <5% | Production builds |
| `stack-protector-all` | all | All functions | 5-15% | Security-critical builds |

**Stack Protector** adds canaries to detect stack buffer overflows at runtime.

### Fortification

| Layer | Level | Features | Overhead | Compiler Requirement |
|-------|-------|----------|----------|---------------------|
| `fortify` | 2 | Standard buffer overflow checks | <2% | GCC 4.0+, Clang 3.0+ |
| `fortify-3` | 3 | Enhanced checks + dynamic arrays | 2-5% | GCC 12+, Clang 16+ |

**Fortify Source** adds compile-time and runtime checks for buffer overflows in standard library functions.

### Memory Protection

| Layer | Mode | Protection | Overhead | Platform |
|-------|------|------------|----------|----------|
| `relro-full` | full | Complete GOT/PLT protection | <2% startup | Linux only |

**RELRO** (RELocation Read-Only) protects the GOT/PLT from overwrites on Linux.

### Address Space Layout Randomization

| Layer | Features | Overhead | Platform |
|-------|----------|----------|----------|
| `pie` | Full ASLR support | <1% | All platforms |

**PIE** (Position Independent Executable) enables full ASLR to randomize code location.

### Composite Profiles

| Layer | Includes | Total Overhead | Recommended For |
|-------|----------|---------------|----------------|
| `hardened` | stack-protector-strong + fortify-2 + relro-full + pie | <5% | Production baseline |

## Usage Examples

### Basic Security (Stack Protection)
```yaml
layers:
  - type: base
    name: gcc-13
  - type: security
    name: stack-protector-strong
```

### Fortified Build
```yaml
layers:
  - type: base
    name: gcc-13
  - type: security
    name: fortify  # Level 2
  - type: optimization
    name: o2  # Required for fortify
```

### Hardened Production Build
```yaml
layers:
  - type: base
    name: gcc-13
  - type: security
    name: hardened  # Complete security baseline
```

### Maximum Security
```yaml
layers:
  - type: base
    name: gcc-13
  - type: security
    name: stack-protector-all
  - type: security
    name: fortify-3  # GCC 12+ required
  - type: security
    name: relro-full
  - type: security
    name: pie
```

## Security Level Recommendations

### Development
- Stack Protector: strong
- Fortify: 2
- RELRO: none (for faster builds)
- PIE: optional

### Production
- Use `hardened` profile (recommended baseline)
- Or: stack-protector-strong + fortify + relro-full + pie

### Security-Critical
- Stack Protector: all
- Fortify: 3 (if GCC 12+ available)
- RELRO: full
- PIE: required
- Consider: Additional sanitizers (AddressSanitizer, etc.)

## Platform Support

| Feature | Linux | Windows | macOS |
|---------|-------|---------|-------|
| Stack Protector | ✓ | ✓ | ✓ |
| Fortify Source | ✓ | ✓ (MinGW) | ✓ |
| RELRO | ✓ | ✗ | ✗ |
| PIE | ✓ | ✓ | ✓ (default) |

## Conflicts

Security layers may conflict with:
- **Static linking**: PIE may conflict on some platforms
- **Sanitizers**: Some sanitizers provide their own stack protection
- **Performance profiling**: Some profilers incompatible with hardening
- **Legacy code**: Older code may not be compatible with all features

## Performance Impact

Typical overhead for common configurations:

| Configuration | Compile Time | Startup Time | Runtime | Binary Size |
|---------------|--------------|--------------|---------|-------------|
| No security | baseline | baseline | baseline | baseline |
| stack-protector-strong | +2% | - | +3% | +2% |
| + fortify-2 | +3% | - | +4% | +2% |
| + relro-full | +3% | +2% | +4% | +2% |
| + pie | +3% | +2% | +5% | +3% |
| hardened (all) | +5% | +2% | +5% | +5% |

## Best Practices

1. **Start with hardened profile** for production builds
2. **Enable fortify with -O2 or higher** optimization
3. **Test thoroughly** when enabling new security features
4. **Profile performance** in your specific application
5. **Use security layers consistently** across all builds
6. **Document security choices** in your build configuration
7. **Update regularly** as compilers add new security features

## Resources

- [GCC Security Options](https://gcc.gnu.org/onlinedocs/gcc/Instrumentation-Options.html)
- [Clang Security](https://clang.llvm.org/docs/UsersManual.html#controlling-code-generation)
- [Linux Security Modules](https://www.kernel.org/doc/html/latest/security/lsm.html)
- [OWASP Secure Coding](https://owasp.org/www-project-secure-coding-practices-quick-reference-guide/)
