import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_server_git", "--repository", "."],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool('git_log', {'repo_path': '.', 'max_count': 1})
            print(result)

if __name__ == "__main__":
    asyncio.run(run())
