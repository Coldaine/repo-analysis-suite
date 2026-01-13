import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def inspect_fs_server():
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "mcp_server_filesystem", "."],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            print("--- Tools ---")
            tools = await session.list_tools()
            for tool in tools.tools:
                print(f"Tool: {tool.name}")
                print(f"Description: {tool.description}")
                print(f"Schema: {tool.inputSchema}")
                print("-" * 20)

if __name__ == "__main__":
    asyncio.run(inspect_fs_server())
