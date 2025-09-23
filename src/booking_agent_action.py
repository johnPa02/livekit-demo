import os
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import openai, noise_cancellation

from utils.prompt_utils import load_prompt

load_dotenv()

customer = {
            "booking_info": """{
                "date": "2025-09-12",
                "time": "19:00",
                "guests": 2,
                "name": "Vũ Hùng Cường",
                "phone": "0933-725-681",
                "notes": "Prefer window seat"
            }"""
        }
instructions = load_prompt("booking/action.md", customer=customer)

class BookingAction(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=instructions)

async def entrypoint(ctx: agents.JobContext):
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            model="gpt-realtime-2025-08-28",
            voice="ballad",
            speed=1.2
        )
    )

    await session.start(
        room=ctx.room,
        agent=BookingAction(),
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await session.generate_reply(
        instructions="Pretend to be a customer and only imitate the customer's greeting when calling to make a reservation, do not mention the reservation details, use Vietnamese. For example: 'Hello, I'm calling to make a reservation at your restaurant.'"
    )

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
