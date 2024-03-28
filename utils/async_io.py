import asyncio
import aiofiles

async def async_write_file(file_path, contents):
    async with aiofiles.open(file_path, "w") as file:
        await file.writelines(contents)

async def write_files_async(save_path, contents):
    await async_write_file(save_path, contents)