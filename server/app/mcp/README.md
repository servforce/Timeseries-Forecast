## 🤖 MCP (Model Context Protocol)
本项目实现了MCP Server，LLM客户端可通过以下配置连接：
- Tools：`chronos_zeroshot_forecast`（零样本预测）、`chronos_finetune_forecast`（微调+预测）
- Resources：`chronos://overview`（服务说明）、`chronos://sample_markdown`（Markdown 输入模版）、`chronos://error_codes`（错误码）
- Prompts：`chronos_zeroshot_guide`（zeroshot 指南）、`chronos_finetune_guide`（finetune 指南）

接入地址：
- SSE：`http://localhost:5001/mcp/sse`
- SSH（如启用）：`http://localhost:5001/mcp/ssh`

典型流程：
1) `list_tools` 获取工具列表  
2) `list_resources` / `read_resource` 获取输入格式  
3) `get_prompt` 获取指令模板  
4) `call_tool` 执行预测

示例客户端：`ollama_client.py`
