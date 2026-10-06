# Contributing

## Development setup

1. Fork the repository and create a branch from `main`.
2. Create a Python 3.12 or newer virtual environment.
3. Install the project with development dependencies:

   ```powershell
   python -m pip install -e ".[dev]"
   ```

4. Copy `.env.example` to `.env` and use only synthetic local data.
5. Run the test suite before opening a pull request:

   ```powershell
   python -m pytest
   ```

## Pull requests

- Keep changes focused and explain the behavior being changed.
- Add or update tests for observable behavior.
- Do not commit credentials, local databases, private documents, user paths, or generated indexes.
- Preserve the mandatory approval boundary for file-writing features.
- Document security implications for new tools or filesystem access.
- Update public documentation when configuration or API behavior changes.

## Security reports

Do not open a public issue for a suspected vulnerability involving private data or credentials. Follow the guidance in [docs/SECURITY.md](docs/SECURITY.md).

