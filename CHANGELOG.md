# Changelog

## 0.5.2

- Use tomllib for newer Python, and tomli as fallback
- Catch all exceptions when starting the kernel, so that the fallback can be
started in most situations.
- More detailed error messages in the fallback

## 0.5.1

- Cleaned up unnecessary log output
- Set repo URL in package

## 0.5.0

- Changed name to pyproject-local-kernel (previously ryeish-kernel)
- Now supports Rye, PDM, Poetry, Hatch and custom configuration
