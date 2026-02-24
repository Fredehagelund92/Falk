"""Demo tool — example custom extension for falk projects."""

from pydantic_ai import FunctionToolset, RunContext

from falk.agent import DataAgent

toolset = FunctionToolset()


@toolset.tool
def ping(ctx: RunContext[DataAgent]) -> str:
    """Return a simple greeting to verify custom tools are loaded."""
    return "pong"
