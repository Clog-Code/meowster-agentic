"""Example agent that queries weather for a city."""

# Install:
# pip install deepagents python-dotenv langchain-fireworks


from deepagents import create_deep_agent
from dotenv import load_dotenv

load_dotenv()


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


agent = create_deep_agent(
    model="fireworks:accounts/fireworks/models/qwen3p7-plus",
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)

# Run the agent
# agent.invoke(
#   {"messages": [{"role": "user", "content": "what is the weather in sf"}]}
# )

# Output
result = agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather in Kuala Lumpur"}]}
)

# 1. Print the final textual answer from the agent
print("\n--- Final Agent Response ---")
print(result["messages"][-1].content)

# 2. Look under the hood to see the tool-calling path
print("\n--- Complete Step-by-Step Message History ---")
for msg in result["messages"]:
    print(f"[{msg.type.upper()}]: {msg.content or msg.tool_calls}")
