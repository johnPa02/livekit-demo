import os
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, function_tool, RunContext, UserInputTranscribedEvent
from livekit.plugins import openai, noise_cancellation, silero, google
import openai as openai_sdk
from utils.prompt_utils import load_prompt
import logging

load_dotenv()

client = openai_sdk.OpenAI()
logger = logging.getLogger("loan-agent")
instructions = load_prompt("booking/intake.md", customer=None)



class BookingIntake(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=instructions)

    @function_tool
    async def venueSearch(
            context: RunContext,
            venue_name: str,
    ):
        """
        Use this tool to look up venue details by name for a reservation request.
        The assistant should extract the name of the venue provided by the user. This value will be used to search for venue details such as address, hours, hotline, and booking requirements.
        Args:
            venue_name (str): Name of the venue to search for.
        """
        logger.info(f"Searching for venue: {venue_name}")
        # await context.session.generate_reply(
        #     instructions="Inform the guest that you are looking for reservation information at {venue_name}, please wait a moment.",
        # )
        query = f"How How to book a table at {venue_name}, including hotline, exact name of the restaurant, required information to book a table, opening and closing hours, priority for a few branches near the waterfront building 1A Ton Duc Thang, Saigon, District 1."
        response = client.responses.create(
            model="gpt-4.1",
            tools=[{"type": "web_search"}],
            input=query,
        )

        return response.output_text

async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-realtime-2025-08-28",
            voice="ballad",
            speed=1.2,
            modalities=["text"],
        ),
        # tts=openai.TTS(voice="alloy", speed=1.2),
        tts=google.TTS(
            gender='male',
            voice_name='vi-VN-Chirp3-HD-Iapetus',
            language='vi-VN',
        ),
    )
    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event: UserInputTranscribedEvent):
        logger.info(
            f"[STT] transcript='{event.transcript}', final={event.is_final}, speaker={event.speaker_id}"
        )

    await session.start(
        room=ctx.room,
        agent=BookingIntake(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )
    import asyncio
    await asyncio.sleep(1)

    await session.generate_reply(
        instructions="You are a reservation support staff, ask the customer which restaurant they want to order from in Vietnamese"
    )

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
