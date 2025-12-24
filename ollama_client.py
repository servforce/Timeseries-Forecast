import asyncio
import json
import os

# =========================================================
# 🛑 强制修复：在导入任何网络库之前，屏蔽所有代理设置
# =========================================================
os.environ["NO_PROXY"] = "localhost,127.0.0.1,0.0.0.0"
os.environ["http_proxy"] = ""
os.environ["https_proxy"] = ""
os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""

import ollama
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.types import CallToolResult, GetPromptResult

# 配置你的服务地址
CHRONOS_MCP_URL = "http://localhost:5001/mcp/sse"
MODEL_NAME = "qwen2.5" 

async def run_agent():
    print(f"🔗 正在连接 Chronos MCP 服务: {CHRONOS_MCP_URL} ...")
    
    try:
        async with sse_client(CHRONOS_MCP_URL) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                print("✅ MCP 服务连接成功！")
                
                await session.initialize()
                
                # ====================================================
                # 🚀 步骤 1: 从服务端获取 Prompt (指令)
                # ====================================================
                print("\n📥 [1/3] 正在获取提示词模版 (Prompts)...")
                try:
                    prompt_name = "chronos_forecast_guide" 
                    prompt_result: GetPromptResult = await session.get_prompt(
                        name=prompt_name,
                        arguments={} 
                    )
                    server_system_prompt = prompt_result.messages[0].content.text
                    print(f"   ✅ 加载成功: {prompt_name} (长度: {len(server_system_prompt)})")
                except Exception as e:
                    print(f"   ⚠️ 获取失败，使用默认回退: {e}")
                    server_system_prompt = "你是预测助手，请使用 timestamp 和 target 字段。"

                # ====================================================
                # 📚 步骤 2: 从服务端拉取资源 (Resources)
                # 资源通常包含数据格式样例，这对于教会模型正确构造参数至关重要
                # ====================================================
                print("\n📥 [2/3] 正在拉取参考资源 (Resources)...")
                resource_context_str = ""
                try:
                    # A. 列出所有可用资源
                    resources_list = await session.list_resources()
                    if resources_list.resources:
                        print(f"   🔍 发现 {len(resources_list.resources)} 个资源")
                        
                        # B. 遍历并读取每个资源的内容
                        res_contents = []
                        for res in resources_list.resources:
                            print(f"   - 读取: {res.name} ({res.uri})")
                            try:
                                # 读取资源实体
                                read_res = await session.read_resource(res.uri)
                                # 提取文本内容
                                content = read_res.contents[0].text
                                res_contents.append(f"\n--- 参考资料: {res.name} ---\n{content}\n")
                            except Exception as e:
                                print(f"     ❌ 读取失败: {e}")
                        
                        # C. 拼接资源内容
                        resource_context_str = "\n".join(res_contents)
                    else:
                        print("   ⚠️ 服务端未提供任何资源")

                except Exception as e:
                    print(f"   ⚠️ 资源拉取过程出错: {e}")

                # ====================================================
                # 🛠️ 步骤 3: 获取工具定义 (Tools)
                # ====================================================
                print("\n📥 [3/3] 正在同步工具列表 (Tools)...")
                tools_result = await session.list_tools()
                mcp_tools = tools_result.tools
                ollama_tools = []
                for tool in mcp_tools:
                    ollama_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema
                        }
                    })
                print(f"   ✅ 已加载 {len(ollama_tools)} 个工具")

                # ====================================================
                # 🧠 构建最终的系统上下文
                # System Prompt = 指令 (Prompt) + 参考资料 (Resources)
                # ====================================================
                final_system_content = server_system_prompt
                if resource_context_str:
                    final_system_content += "\n\n【重要参考数据/格式样例】\n" + resource_context_str
                
                messages = [{"role": "system", "content": final_system_content}]
                
                print("\n" + "="*50)
                print("🤖 Agent 已就绪 (输入 'quit' 退出)")
                print("="*50)

                # ---------------------------------------------------------
                # 交互循环
                # ---------------------------------------------------------
                while True:
                    user_input = input("\n👤 你: ")
                    if user_input.lower() in ['quit', 'exit']:
                        break

                    messages.append({"role": "user", "content": user_input})

                    # A. 请求 Ollama
                    response = ollama.chat(
                        model=MODEL_NAME,
                        messages=messages,
                        tools=ollama_tools,
                    )
                    
                    # B. 处理工具调用
                    if response.message.tool_calls:
                        messages.append(response.message)
                        
                        for tool_call in response.message.tool_calls:
                            func_name = tool_call.function.name
                            func_args = tool_call.function.arguments
                            
                            print(f"⚙️  模型请求调用工具: {func_name} ...")
                            print(f"   参数: {json.dumps(func_args, ensure_ascii=False)[:100]}...")

                            try:
                                result: CallToolResult = await session.call_tool(
                                    name=func_name,
                                    arguments=func_args
                                )
                                
                                tool_output = result.content[0].text
                                print("✅ 工具调用成功")

                            except Exception as e:
                                tool_output = f"Error calling tool: {str(e)}"
                                print(f"❌ 工具调用失败: {e}")

                            messages.append({
                                "role": "tool",
                                "content": tool_output,
                            })

                        # C. 获取最终回答
                        final_response = ollama.chat(
                            model=MODEL_NAME,
                            messages=messages,
                        )
                        print(f"\n🤖 Agent: {final_response.message.content}")
                        messages.append(final_response.message)

                    else:
                        print(f"\n🤖 Agent: {response.message.content}")
                        messages.append(response.message)

    except Exception as e:
        print(f"\n❌ 运行错误: {e}")

if __name__ == "__main__":
    asyncio.run(run_agent())