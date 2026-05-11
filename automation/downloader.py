import requests
from pathlib import Path
from datetime import datetime

# ====================== CONFIG ======================
URL = "https://recapo.plugintheworld.com/data_exports/1569"

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
SNAPSHOT_DIR = BASE_DIR / "data" / "snapshots"

# ====================== CREATE FOLDERS ======================
RAW_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# ====================== DOWNLOAD FILE ======================
def download_file():
    try:
        print("🔄 Downloading latest RECAPO export...")

        response = requests.get(URL, timeout=60)
        response.raise_for_status()

        # Timestamped snapshot
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        snapshot_file = SNAPSHOT_DIR / f"export_{timestamp}.xlsx"
        latest_file = RAW_DIR / "latest_export.xlsx"

        # Save snapshot
        with open(snapshot_file, "wb") as f:
            f.write(response.content)

        # Save latest copy (for dashboard)
        with open(latest_file, "wb") as f:
            f.write(response.content)

        print(f"✅ Download complete!")
        print(f"📁 Latest file: {latest_file}")
        print(f"🗂 Snapshot saved: {snapshot_file}")

    except requests.exceptions.RequestException as e:
        print("❌ Download failed:", e)

    except Exception as e:
        print("❌ Unexpected error:", e)


# ====================== RUN ======================
if __name__ == "__main__":
    download_file()