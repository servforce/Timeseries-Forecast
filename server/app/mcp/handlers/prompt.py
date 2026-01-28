from pathlib import Path
import logging

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent / "prompt_templates"


def _load_prompt_file(filename: str) -> str:
    file_path = PROMPTS_DIR / filename
    if not file_path.exists():
        logger.warning("Prompt markdown 文件不存在: %s", file_path)
        return f"# Missing prompt file: {filename}\n\n请检查服务端提示词配置。"
    return file_path.read_text(encoding="utf-8")


def register_prompts(mcp) -> None:
    """
    注册 MCP 提示模版到服务器（按 CDD：zeroshot / finetune 拆分）。
    """

    @mcp.prompt()
    async def chronos_zeroshot_guide() -> str:
        return _load_prompt_file("zero-shot_guide.md")

    @mcp.prompt()
    async def chronos_finetune_guide() -> str:
        return _load_prompt_file("finetune_guide.md")

    
