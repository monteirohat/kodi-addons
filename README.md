# koid-addons

Custom Kodi add-ons and an installable Kodi repository for LibreELEC and Raspberry Pi.

## Available add-ons

| Add-on | ID | Purpose |
| --- | --- | --- |
| [HDMI Switcher](script.hdmi.switcher/README.md) | `script.hdmi.switcher` | Select the active HDMI display and restart Kodi. |
| MonteiroMedia Add-ons | `repository.monteiromedia` | Register this repository in Kodi for installation and updates. |

## Publish on GitHub

1. Upload the contents of this folder to a public GitHub repository using the `main` or `master` branch, including `.github`, `.gitignore`, and the generated `repository` directory.
2. Open **Actions** and wait for **Publish Kodi repository** to complete. The workflow generates package URLs from the actual GitHub owner, repository name, and branch.
3. If the workflow reports a permissions error, enable **Read and write permissions** under **Settings > Actions > General > Workflow permissions**. Branch protection must allow the workflow to push its generated commit.
4. Download the generated `repository/repository.monteiromedia/repository.monteiromedia-1.0.0.zip` after the workflow succeeds.

The initial generated files use `monteirohat/koid-addons` and the `main` branch. The first workflow run adjusts these values to the actual repository location before installation. GitHub Pages is optional; Kodi downloads files directly from GitHub Raw.

## Register the repository in Kodi

1. Enable **Settings > System > Add-ons > Unknown sources**.
2. Install `repository.monteiromedia-1.0.0.zip` through **Add-ons > Install from zip file** once.
3. Open **Install from repository > MonteiroMedia Add-ons > Program add-ons > HDMI Switcher**.
4. Select **Install**.

Further add-ons and updates are installed through **MonteiroMedia Add-ons**. Enable automatic updates for the add-on if desired. If an update is not visible yet, open the repository context menu and select **Check for updates**.

## Publish an add-on update

1. Modify its source code and increment its version in `addon.xml`.
2. Commit and push to `main` or `master`.
3. The workflow packages the add-ons, updates `addons.xml` and its checksum, and commits the generated files.
4. Kodi detects the updated catalog and offers the new version according to its update settings.

Add another self-contained top-level directory with its own `addon.xml` to publish another add-on. The folder name must match the add-on ID. The builder discovers these folders automatically and retains older installation packages.

## Repository layout

| Path | Purpose |
| --- | --- |
| `script.hdmi.switcher/` | HDMI Switcher source and documentation. |
| `repository.monteiromedia/` | Repository registration add-on. |
| `repository/addons.xml` | Generated Kodi add-on catalog. |
| `repository/addons.xml.md5` | Catalog change indicator used by Kodi. |
| `repository/<addon-id>/` | Versioned installation ZIPs and SHA-256 files. |
| `tools/build_repository.py` | Catalog and package generator using Python's standard library. |
| `.github/workflows/publish-repository.yml` | Build and publish workflow. |

Package hash headers are disabled in the Kodi repository definition because GitHub Raw does not provide Kodi's `content-sha256` headers. SHA-256 sidecars are provided for manual verification. Downloads use HTTPS.

## Build locally

From the repository root, run

```sh
python3 tools/build_repository.py --base-url https://raw.githubusercontent.com/monteirohat/koid-addons/main/repository
```

Replace the owner, repository name, and branch when building for another location. Commit the generated `repository` directory and the updated registration manifest. The GitHub workflow performs this step automatically on each push.

## HDMI Switcher setup

The target environment is LibreELEC 12.2.1 on Raspberry Pi 4 with Kodi 21 and Python 3. The menu maps the small display to `HDMI-A-1` and the external monitor to `HDMI-A-2`.

Complete the [one-time setup](script.hdmi.switcher/README.md#one-time-setup) to remove previously configured HDMI boot overrides. The add-on then updates the active profile's `advancedsettings.xml` and restarts Kodi when changing displays. One display is active at a time.

## Development conventions

- Use English for identifiers, comments, documentation, filenames, and interface text.
- Keep each add-on self-contained and match its directory name to its ID.
- Increment `addon.xml` versions before publishing changed packages.
- Preserve existing user settings when making configuration changes.
- Increase the repository add-on version when changing its public URLs or metadata.

## Validation

Local checks cover metadata, package structure, checksums, deterministic builds, and the previously tested HDMI configuration logic. Deployment to GitHub and end-to-end installation in Kodi remain pending. Display switching still requires hardware validation on the target Raspberry Pi.

## License

MIT. See [LICENSE](LICENSE).
