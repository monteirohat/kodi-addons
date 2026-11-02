![Monteiro repository icon](repository.monteiromedia/resources/icon.png)


# Monteiro

Monteiro is a collection of practical, open-source Kodi add-ons for LibreELEC and Raspberry Pi. It provides a single place to install and update utilities that simplify your media-center setup. The collection currently includes HDMI Switcher, which lets you choose the active HDMI display directly from Kodi. New tools and updates are published through this repository.


## Artwork

The repository and HDMI Switcher share a navy, cyan, and blue M monogram. The opaque PNG icon is 512 by 512 pixels. The fanart background is a 1280 by 720 JPEG under 1 MB. Both assets are declared in each add-on's `addon.xml` and published at their catalog paths so Kodi can display them before installation.

The artwork was created with OpenAI image generation. The icon brief specified a simple M monogram with a subtle play-shaped cutout on a dark navy background. The companion fanart brief requested quiet angular ribbons and a small M monogram on the right, leaving room for Kodi's interface.

After publishing, open the Monteiro repository context menu in Kodi and select **Check for updates**. Update the repository add-on and HDMI Switcher to version 1.0.3. If artwork remains cached, restart Kodi after the update.

## Available add-ons

| Add-on | ID | Purpose |
| --- | --- | --- |
| [HDMI Switcher](script.hdmi.switcher/README.md) | `script.hdmi.switcher` | Select the active HDMI display and restart Kodi. |
| Monteiro | `repository.monteiromedia` | Register this repository in Kodi for installation and updates. |

## Repository identity

The name shown in Kodi is **Monteiro**. The technical ID remains `repository.monteiromedia` so existing installations can receive this rename through a normal repository update. Version 1.0.3 adds repository artwork and detailed metadata. HDMI Switcher keeps its `script.hdmi.switcher` ID and is also versioned 1.0.3 for its artwork and metadata update.

## Publish on GitHub

1. Upload the contents of this folder to a public GitHub repository using the `main` or `master` branch, including `.github`, `.gitignore`, and the generated `repository` directory.
2. Open **Actions** and wait for **Publish Kodi repository** to complete. The workflow generates package URLs from the actual GitHub owner, repository name, and branch.
3. If the workflow reports a permissions error, enable **Read and write permissions** under **Settings > Actions > General > Workflow permissions**. Branch protection must allow the workflow to push its generated commit.
4. In GitHub, open the **Code** tab and download the generated `repository/repository.monteiromedia/repository.monteiromedia-1.0.3.zip` after the workflow succeeds. The ZIP is committed to the repository; it is listed under **Code**, rather than as an Actions artifact.

The initial generated files use `monteirohat/kodi-addons` and the `main` branch. The first workflow run adjusts these values to the actual repository location before installation. GitHub Pages is optional; Kodi downloads files directly from GitHub Raw.

## Register the repository in Kodi

1. On GitHub, open this repository's **Code** tab and select the branch where **Publish Kodi repository** completed successfully.
2. Open **repository > repository.monteiromedia** and select **repository.monteiromedia-1.0.3.zip**. You can also open the [repository installation ZIP](repository/repository.monteiromedia/repository.monteiromedia-1.0.3.zip) directly from this README.
3. On the file page, click **Download raw file** to download the ZIP. The full path from the repository root is `repository/repository.monteiromedia/repository.monteiromedia-1.0.3.zip`.
4. Copy the downloaded ZIP to a USB drive or a folder accessible from your Kodi device.
5. In Kodi, enable **Settings > System > Add-ons > Unknown sources**.
6. Open **Add-ons > Install from zip file**, browse to the location used in step 4, and select **repository.monteiromedia-1.0.3.zip**. Wait for the **Monteiro** repository installation notification. Registering the repository is a one-time step.
7. Open **Add-ons > Install from repository > Monteiro > Program add-ons > HDMI Switcher**.
8. Select **Install** and wait for installation to finish.

Further add-ons and updates are installed through **Monteiro**. Enable automatic updates for the add-on if desired. If an update is not visible yet, open the repository context menu and select **Check for updates**.

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
| `repository/<addon-id>/` | Versioned installation ZIPs, SHA-256 files, and published artwork. |
| `tools/build_repository.py` | Catalog and package generator using Python's standard library. |
| `.github/workflows/publish-repository.yml` | Build and publish workflow. |

Package hash headers are disabled in the Kodi repository definition because GitHub Raw does not provide Kodi's `content-sha256` headers. SHA-256 sidecars are provided for manual verification. Downloads use HTTPS.

## Build locally

From the repository root, run

```sh
python3 tools/build_repository.py --base-url https://raw.githubusercontent.com/monteirohat/kodi-addons/main/repository
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

Local checks cover metadata, package structure, checksums, deterministic builds, and the previously tested HDMI configuration logic. The user confirmed installation and HDMI display switching on the target Raspberry Pi. The artwork and metadata update still requires confirmation in Kodi.

## License

MIT. See [LICENSE](LICENSE).
