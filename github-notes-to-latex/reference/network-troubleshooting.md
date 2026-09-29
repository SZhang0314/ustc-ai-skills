# Fetching from GitHub on flaky networks

Some networks (notably from certain regions) intermittently **reset TLS
connections** to `github.com`, `api.github.com`, `raw.githubusercontent.com`.
Symptoms seen in practice:

- `The underlying connection was closed: An unexpected error occurred on a send.`
- `Remote end closed connection without response`
- `WinError 10060` (connection attempt timed out)
- The **first** request occasionally succeeds, then the next several fail.
- `api.github.com` may be blocked while `github.com` works, or vice versa.

## What works

1. **Set TLS ≥ 1.2 explicitly.** In PowerShell:
   ```powershell
   [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
   ```
   In Python `fetch_repo.py` does this via `ssl.SSLContext.minimum_version`.

2. **Retry in a loop.** Treat the first 2–5 failures as expected. `fetch_repo.py`
   retries up to 8 times with backoff.

3. **Download the ZIP archive, not the API.**
   `https://github.com/<owner>/<repo>/archive/refs/heads/<branch>.zip`
   is the most reliable endpoint and fetches the whole tree in one request.
   This is method 1 in `fetch_repo.py`.

4. **Fall back to the GitHub API zipball** if the archive 404s:
   `https://api.github.com/repos/<owner>/<repo>/zipball/<branch>`
   (needs a `User-Agent` header).

5. **Use a mirror/proxy** when GitHub itself is unreachable:
   - `--mirror https://ghproxy.com/` (or `https://gh-proxy.com/`)
   - jsDelivr for single files: `https://cdn.jsdelivr.net/gh/<owner>/<repo>@<branch>/<path>`
   - Gitee mirrors for some popular repos.
   `fetch_repo.py --mirror` prepends the prefix to the archive URL.

6. **Set a browser `User-Agent`.** Some endpoints reject the default Python UA.

## What does *not* work reliably

- `git clone` when `git` isn't installed (this environment had no `git`).
- `raw.githubusercontent.com` for bulk fetching (one request per file → many
  chances to fail). Prefer the ZIP.
- Trusting a single success: always verify the file size / leaf count.

## PowerShell recipe (when Python isn't handy)

```powershell
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ok = $false
for ($i = 1; $i -le 15 -and -not $ok; $i++) {
  try {
    Invoke-WebRequest -Uri "https://github.com/<owner>/<repo>/archive/refs/heads/main.zip" `
      -OutFile repo.zip -UseBasicParsing -TimeoutSec 90 -Headers @{ "User-Agent"="Mozilla/5.0" }
    $ok = $true
  } catch { Start-Sleep -Seconds 2 }
}
Expand-Archive -LiteralPath repo.zip -DestinationPath repo -Force
```

## Verifying a fetch

```bash
# leaf count sanity check
find repo -type f | wc -l
# or on Windows PowerShell
(Get-ChildItem -LiteralPath repo -Recurse -File).Count
```

Then run the converter and confirm `Generated N files.` matches expectations.
