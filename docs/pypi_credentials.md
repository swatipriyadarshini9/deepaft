# PyPI credentials (no secrets in git)

Store API tokens only in environment variables or your local `~/.pypirc`. Full upload commands: **[pypi_upload.md](pypi_upload.md)**.

```powershell
$env:TWINE_USERNAME = "__token__"
$env:TWINE_PASSWORD = "pypi-..."   # TestPyPI or PyPI token
```

Never paste tokens into chat, commits, or `README.md`.
