import os
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import openai, noise_cancellation

load_dotenv()

# Định nghĩa Voice Agent
class VietAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="Bạn là một trợ lý ảo hữu ích, nói chuyện tự nhiên bằng tiếng Việt.")

async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            voice="alloy",
        )
    )

    await session.start(
        room=ctx.room,
        agent=VietAssistant(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await session.generate_reply(
        instructions="Xin chào! Tôi có thể giúp gì cho bạn hôm nay?"
    )

# Khởi động Worker
if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
