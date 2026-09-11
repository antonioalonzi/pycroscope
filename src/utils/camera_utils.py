import glob
import os
import re
import subprocess


def get_available_cameras() -> list[dict]:
    available_cameras = []

    devices = sorted(glob.glob("/dev/video*"))
    if devices:
        for dev in devices:
            dev_name = os.path.basename(dev)
            sys_path = f"/sys/class/video4linux/{dev_name}/name"

            camera_name = dev
            if os.path.exists(sys_path):
                try:
                    with open(sys_path, "r") as f:
                        camera_name = f.read().strip()
                except IOError:
                    print(f"Error reading camera name from {sys_path}")
                    pass

            available_cameras.append({
                'camera_name': camera_name,
                'dev': dev
            })

    return available_cameras

def get_preferred_camera(dev: str | None) -> dict:
    cameras = get_available_cameras()
    for camera in cameras:
        if camera['dev'] == dev:
            return camera

    return cameras[0]

def get_camera_resolutions(device: str | None) -> list[tuple]:
    if not isinstance(device, str):
        return []

    try:
        result = subprocess.run(
            ["v4l2-ctl", "--device", device, "--list-formats-ext"],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        print("v4l2-ctl not found... run `sudo apt install -y v4l-utils` (or install it according to your Linux distribution)")
        return []

    if result.returncode != 0:
        print(f"Error running v4l2-ctl: {result.stderr}")
        return []

    resolutions = set()
    for line in result.stdout.splitlines():
        match = re.search(r"(\d+)x(\d+)", line)
        if match:
            width = int(match.group(1))
            height = int(match.group(2))
            resolutions.add((width, height))

    return sorted(resolutions, key=lambda res: (res[0] * res[1], res[0], res[1]))

def get_preferred_resolution(last_device: str | None, camera_resolution: str | None) -> tuple:
    camera = get_preferred_camera(last_device)
    resolutions = get_camera_resolutions(camera['dev'])
    for resolution in resolutions:
        if resolution == camera_resolution:
            return resolution

    return resolutions[0]