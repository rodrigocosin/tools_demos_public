"""File operations for Unity Catalog Volumes via Databricks Files API."""
import aiohttp
from server.config import get_workspace_host, get_token, VOLUME_PATH


async def upload_to_volume(file_content: bytes, filename: str) -> str:
    """Upload a file to Unity Catalog Volume. Returns the volume path."""
    host = get_workspace_host()
    token = get_token()

    volume_file_path = f"{VOLUME_PATH}/{filename}"
    api_path = volume_file_path  # /Volumes/catalog/schema/volume/filename

    url = f"{host}/api/2.0/fs/files{api_path}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
    }

    async with aiohttp.ClientSession() as session:
        async with session.put(url, data=file_content, headers=headers) as resp:
            if resp.status not in (200, 201, 204):
                error = await resp.text()
                raise Exception(f"Volume upload error ({resp.status}): {error[:500]}")

    return volume_file_path


async def read_from_volume(volume_path: str) -> bytes:
    """Read a file from Unity Catalog Volume."""
    host = get_workspace_host()
    token = get_token()

    url = f"{host}/api/2.0/fs/files{volume_path}"
    headers = {"Authorization": f"Bearer {token}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise Exception(f"Volume read error ({resp.status}): {error[:500]}")
            return await resp.read()
