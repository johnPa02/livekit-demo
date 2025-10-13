import os
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import openai, noise_cancellation, google
from google.genai.types import Modality
from utils.prompt_utils import load_prompt

load_dotenv()

# instructions = load_prompt("english.md", customer=None)

class BookingAction(Agent):
    def __init__(self) -> None:
        super().__init__(instructions="You are an AI with a humorous and concise English answering style.")

async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-realtime",
            modalities=["text"],
            speed=1.2
        ),
        # tts=openai.TTS(
        #     base_url="http://54.255.219.98:5005/v1",
        #     voice="tara",
        #     speed=1.2,
        #     response_format="mp3"
        # ),
        tts=openai.TTS.create_orpheus_client(
            voice="tara",
            base_url="http://54.255.219.98:5005/v1",
            response_format="wav"
        ),
    )

    await session.start(
        room=ctx.room,
        agent=BookingAction(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await session.generate_reply(
        instructions="How can I help you today?"
    )

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
