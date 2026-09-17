# CI Nurse

CI Nurse is a desktop chat client for the CI Nurse backend.

The repository keeps the source code only. Installers are generated automatically by GitHub Actions and published under **GitHub Releases**.

## Run locally

### GUI

```bash
python -m pip install -r requirements.txt
python gui.py
```

This is the main development/testing entry point.

### CLI

```bash
python cli.py
```

The CLI uses the same `AgentClient` as the GUI and is intentionally kept in the repository for debugging, testing, and headless use.

## Project structure

```text
.
├── gui.py
├── cli.py
├── client.py
├── config.py
├── main.py
├── requirements.txt
├── requirements-dev.txt
├── packaging/
│   ├── windows/
│   │   └── ci_nurse_installer.iss
│   └── linux/
│       └── build_deb.sh
└── .github/
    └── workflows/
        └── release.yml
```

`client.py` contains the HTTP API client.

`config.py` contains shared application configuration such as `DEFAULT_SERVER_URL`.

`gui.py` contains the Tkinter GUI.

`cli.py` contains the command-line interface.

`main.py` is a small GUI launcher kept for convenience.

## Publish a release

Create and push a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

GitHub Actions will automatically:

1. Build the Windows GUI executable.
2. Package it as `CI-Nurse-Setup.exe`.
3. Build the Linux GUI executable.
4. Package it as a `.deb`.
5. Create a GitHub Release.
6. Attach both installers to the Release.

Users then download the correct installer from the repository's **Releases** page.

## Release assets

Windows:

```text
CI-Nurse-Setup.exe
```

Linux:

```text
ci-nurse_<version>_<architecture>.deb
```

## Notes

The source repository does not store generated installers.

The GUI and CLI share the same `client.py`, so changes to API behavior only need to be implemented once.
