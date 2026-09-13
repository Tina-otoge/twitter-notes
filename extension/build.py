import json
import shutil
import zipfile
from pathlib import Path
from zipfile import ZipFile

SOURCE = Path(__file__).resolve().parent
OUTPUT = SOURCE.parent / "dist"
ASSETS = [
    "background.js",
    "bridge.js",
    "content.js",
    "popup.html",
    "popup.css",
    "popup.js",
]


def build():
    for browser in ("chrome", "firefox"):
        destination = OUTPUT / browser
        destination.mkdir(parents=True, exist_ok=True)
        manifest = json.loads((SOURCE / "manifest.json").read_text())
        if browser == "firefox":
            manifest.pop("minimum_chrome_version")
            manifest["background"] = {"scripts": ["background.js"]}
            manifest["browser_specific_settings"] = {
                "gecko": {
                    "id": "twitter-notes@local.invalid",
                    "strict_min_version": "142.0",
                    "data_collection_permissions": {
                        "required": [
                            "authenticationInfo",
                            "personalCommunications",
                            "websiteContent",
                        ]
                    },
                }
            }
        (destination / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n"
        )
        for asset in ASSETS:
            shutil.copy2(SOURCE / asset, destination / asset)
        archive_path = OUTPUT / f"twitter-notes-{browser}.zip"
        with ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for asset in ["manifest.json", *ASSETS]:
                archive.write(destination / asset, asset)
        print(f"Built {archive_path}")


if __name__ == "__main__":
    build()
