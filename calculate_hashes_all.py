import json
import hashlib
import requests
from pathlib import Path
import time

CACHE_DIR = Path("tmp_downloads")
CACHE_DIR.mkdir(exist_ok=True)


def get_filename_from_url(url):
    return url.split("/")[-1]


def calculate_hash_and_size(url):
    filename = get_filename_from_url(url)
    cache_path = CACHE_DIR / filename

    if cache_path.exists():
        print(f"Using cached {filename}")
        sha256 = hashlib.sha256()
        size = 0
        with open(cache_path, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
                size += len(chunk)
        return sha256.hexdigest(), size / (1024 * 1024)

    print(f"Downloading {url}...")
    try:
        # Use stream=True and a timeout
        response = requests.get(url, stream=True, timeout=600)

        if response.status_code != 200:
            print(f"Error: Status {response.status_code} for {url}")
            return None, None

        sha256 = hashlib.sha256()
        size = 0
        last_print = time.time()

        with open(cache_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    sha256.update(chunk)
                    size += len(chunk)
                    if time.time() - last_print > 5:
                        print(f"  DL: {size / (1024*1024):.1f} MB", end="\r")
                        last_print = time.time()

        print()  # Newline
        return sha256.hexdigest(), size / (1024 * 1024)
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        # Clean up partial file to avoid corruption
        if cache_path.exists():
            cache_path.unlink()
        return None, None


def process_file(file_path):
    print(f"\nProcessing {file_path}")
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for tc_name, tc_data in data["toolchains"].items():
        if "versions" not in tc_data:
            continue

        for version, platforms in tc_data["versions"].items():
            for platform, info in platforms.items():
                current_hash = info.get("sha256")
                needs_update = False
                # Update if hash is TBD, placeholder, null, or missing
                if (
                    not current_hash
                    or current_hash == "null"
                    or "TBD" in current_hash
                    or "placeholder" in current_hash
                ):
                    needs_update = True

                if needs_update:
                    print(f"  Fixing {tc_name} {version} {platform}")
                    new_hash, new_size = calculate_hash_and_size(info["url"])

                    if new_hash:
                        info["sha256"] = new_hash
                        if new_size:
                            info["size_mb"] = round(new_size)

                        # Remove manual_install_required if we found a valid file
                        if info.get("manual_install_required"):
                            del info["manual_install_required"]

                        print(f"    -> Hash: {new_hash}")
                        print(f"    -> Size: {info['size_mb']} MB")

                        print(f"Saving incremental progress to {file_path}")
                        with open(file_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2)
                            # Ensure trailing newline
                            f.write("\n")
                    else:
                        print("    -> Failed to download. Leaving as is.")


if __name__ == "__main__":
    files = [
        # Process toolchains.json. Zig is already done, but no harm checking (it checks for TBD)
        r"d:\workplace\cpp\toolchainkit\toolchainkit\data\toolchains.json",
        r"d:\workplace\cpp\toolchainkit\examples\plugins\zig-compiler\toolchains.json",
    ]

    for f in files:
        if Path(f).exists():
            process_file(f)
        else:
            print(f"File not found: {f}")
