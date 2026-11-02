"""Build the Kodi catalog and installation packages using the standard library."""

import argparse
import copy
import hashlib
import io
from pathlib import Path
import shutil
import tempfile
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parent.parent
REPOSITORY_ID = "repository.monteiromedia"


def build(base_url):
    base_url = base_url.rstrip("/")
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        raise ValueError("The repository base URL must be an absolute HTTPS URL.")

    repository_manifest = ROOT / REPOSITORY_ID / "addon.xml"
    repository = ET.parse(repository_manifest).getroot()
    directory = repository.find("extension[@point='xbmc.addon.repository']/dir")
    directory.find("info").text = base_url + "/addons.xml"
    directory.find("checksum").text = base_url + "/addons.xml.md5"
    directory.find("datadir").text = base_url + "/"
    ET.indent(repository, space="  ")
    repository_bytes = ET.tostring(repository, encoding="utf-8", xml_declaration=True) + b"\n"

    catalog = ET.Element("addons")
    packages = []
    asset_files = []
    for manifest_path in sorted(ROOT.glob("*/addon.xml")):
        addon_directory = manifest_path.parent
        manifest_bytes = repository_bytes if addon_directory.name == REPOSITORY_ID else manifest_path.read_bytes()
        addon = ET.fromstring(manifest_bytes)
        addon_id, version = addon.get("id"), addon.get("version")
        if addon_id != addon_directory.name or not version:
            raise ValueError("The folder must match the add-on ID and its version must be set.")
        if any(character in version for character in "/\\"):
            raise ValueError("Invalid add-on version.")
        for asset in addon.findall("extension[@point='xbmc.addon.metadata']/assets/*"):
            relative_path = Path(asset.text or "")
            source = addon_directory / relative_path
            if relative_path.is_absolute() or not source.resolve().is_relative_to(addon_directory.resolve()):
                raise ValueError("Artwork must be located inside the add-on directory.")
            if not source.is_file():
                raise ValueError("Missing artwork for " + addon_id + ": " + str(relative_path))
            asset_files.append((addon_id, relative_path, source.read_bytes()))
        catalog.append(copy.deepcopy(addon))
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for source in sorted(addon_directory.rglob("*")):
                relative = source.relative_to(addon_directory)
                if not source.is_file() or "__pycache__" in relative.parts or source.suffix in {".pyc", ".zip"}:
                    continue
                # Stable timestamps keep packages identical across unchanged builds.
                info = zipfile.ZipInfo(str(source.relative_to(ROOT)), date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                data = manifest_bytes if source == manifest_path else source.read_bytes()
                archive.writestr(info, data)
        packages.append((addon_id, version, buffer.getvalue()))

    ET.indent(catalog, space="  ")
    catalog_bytes = ET.tostring(catalog, encoding="utf-8", xml_declaration=True) + b"\n"
    output = ROOT / "repository"
    # Stage a complete build before replacing the catalog. Keep previous releases.
    with tempfile.TemporaryDirectory(prefix="kodi-repository-") as temporary:
        staging = Path(temporary)
        # Kodi downloads artwork before installing add-ons, using the catalog paths.
        for addon_id, relative_path, data in asset_files:
            asset_path = staging / addon_id / relative_path
            asset_path.parent.mkdir(parents=True, exist_ok=True)
            asset_path.write_bytes(data)
        for addon_id, version, package in packages:
            destination = staging / addon_id / (addon_id + "-" + version + ".zip")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(package)
            with zipfile.ZipFile(destination) as archive:
                if archive.testzip() is not None:
                    raise ValueError("Invalid package for " + addon_id)
            digest = hashlib.sha256(package).hexdigest()
            destination.with_suffix(".zip.sha256").write_text(digest + "\n")
        (staging / "addons.xml").write_bytes(catalog_bytes)
        (staging / "addons.xml.md5").write_text(hashlib.md5(catalog_bytes).hexdigest() + "\n")
        shutil.copytree(staging, output, dirs_exist_ok=True)
    repository_manifest.write_bytes(repository_bytes)
    print("Built " + str(len(packages)) + " add-ons in " + str(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="Public HTTPS URL of the generated repository directory")
    arguments = parser.parse_args()
    build(arguments.base_url)
