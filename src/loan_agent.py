import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from livekit import agents
from ctnx import num_to_words
from dotenv import load_dotenv
from livekit.agents import UserInputTranscribedEvent
from google.genai.types import Modality
from livekit.agents import (
    Agent,
    AgentSession,
    ChatContext,
    JobContext,
    JobProcess,
    RoomInputOptions,
    RoomOutputOptions,
    WorkerOptions,
    cli,
    metrics,
    UserStateChangedEvent,
)
import asyncio
from livekit.agents.llm import function_tool
from livekit.agents.voice import MetricsCollectedEvent
from livekit.plugins import openai, noise_cancellation, deepgram, silero, assemblyai, google, elevenlabs

from utils.prompt_utils import load_prompt

logger = logging.getLogger("loan-agent")

load_dotenv()



@dataclass
class CustomerInfo:
    ten: str
    gioi_tinh: str
    so_hop_dong: str
    khoan_vay: str
    tien_thanh_toan: str
    han_thanh_toan: str
    trang_thai: str
    prefix: str

current_time = datetime.now().strftime("%H:%M:%S %d/%m/%Y")
class LoanCallAgent(Agent):
    def __init__(self, customer: CustomerInfo,ctx: JobContext, *, chat_ctx: Optional[ChatContext] = None) -> None:
        # instructions = f"""
        # You are Minh, a call center agent working for ABC Bank.
        # You must always speak naturally, concisely, and politely in Vietnamese, as if you were a real human agent.
        # Your goal is to inform the customer about their loan.
        # Current time: {current_time}
        #
        # Customer information:
        # - Name: {customer.ten}
        # - Sex: {customer.gioi_tinh}
        # - Contract number: {customer.so_hop_dong}
        # - Loan amount: {customer.khoan_vay}
        # - Payment due: {customer.tien_thanh_toan}
        # - Due date: {customer.han_thanh_toan}
        # - Status: {customer.trang_thai}
        # - Prefix: {customer.prefix}
        #
        # Conversation guidelines:
        # 1. On the very first turn, always start with a friendly greeting, introduce yourself as an agent from ABC Bank,
        #    and immediately confirm if you are speaking to {customer.ten}, the owner of contract number {customer.so_hop_dong}.
        #    - Use appropriate Vietnamese greetings like "Chào {customer.prefix}, em là Minh, nhân viên ngân hàng ABC".
        #    - Only proceed if the customer confirms their identity.
        # 2. Clearly inform the customer about the loan details above.
        # 3. If the customer asks about anything outside of this loan information
        #    (e.g. installment plan, early repayment, extension, penalty fees, interest rates, or other procedures), politely respond in Vietnamese:
        #    - "Dạ, để được hỗ trợ chi tiết về vấn đề này, anh chị vui lòng liên hệ tổng đài chăm sóc khách hàng 1-8-0-0-1-9-1-9 của ngân hàng ABC ạ."
        # 4. If the customer says they already paid → acknowledge it in Vietnamese, thank them,
        #    and suggest contacting the hotline 1800 119 to verify in case of mistakes.
        # 5. NEVER invent or make up any information outside of what is provided in the customer data above.
        # 6. If the customer speaks Vietnamese clearly but the topic is unrelated to the loan
        #    (e.g. asking for coffee, food, or other random requests), politely decline and steer
        #    the conversation back to the loan information. For example, say:
        #    - "Dạ, vấn đề này em không hỗ trợ được, anh chị vui lòng cho em xin phép quay lại nội dung khoản vay ạ."
        # 7. If the customer’s speech is unclear, nonsense, or in a foreign language,
        #    politely ask them to repeat in Vietnamese. For example, say:
        #    - "Dạ, em xin lỗi, em chưa nghe rõ. Anh chị có thể nhắc lại giúp em được không ạ?"
        #
        # Important: Always reply in Vietnamese, naturally, as if you are a real call center agent.
        # """
        instructions = load_prompt(
            "system_prompt.md",
            customer=customer,
        )
        super().__init__(
            instructions=instructions,
            # llm=openai.realtime.RealtimeModel(voice="alloy"),
            # stt=deepgram.STT(model="nova-3", language='multi'),
            # llm=openai.LLM(model="gpt-4.1"),
            # tts=openai.TTS(voice="alloy", speed=1.8),
            chat_ctx=chat_ctx,
        )
        self.customer = customer
        self.ctx = ctx
        self.call_ending = False
        self.is_processing = False

    @function_tool
    async def end_call(self):
        """
        Call this tool ONLY when ALL conditions below are satisfied:

        - The customer clearly confirms in **Vietnamese** that:
            * They have no more questions, OR
            * They are not the person you are looking for (ví dụ: 'gọi nhầm số rồi', 'sai số rồi'), OR
            * They say goodbye explicitly in Vietnamese (ví dụ: 'tạm biệt', 'chào em', 'cảm ơn, không cần nữa').

        - OR you have completed informing them of the loan details
          and they politely close the conversation in Vietnamese.

        IMPORTANT:
        - DO NOT call this tool if the speech is unclear, nonsense, or in a foreign language (English, French, Japanese, etc).
        """
        self.call_ending = True
        logger.info("Ending call with customer...")
        await asyncio.sleep(4)
        await self.session.interrupt()
        try:
            await asyncio.wait_for(self.session.aclose(), timeout=10)
        except asyncio.TimeoutError:
            logger.warning("session.aclose() timeout, force closing...")

        self.ctx.delete_room()
        logger.info("Call ended successfully.")

    # @function_tool
    # async def days_until_due(self):
    #     """
    #     Use this tool ONLY when the customer explicitly asks
    #     how many days are left until the payment due date.
    #     The question may be phrased in Vietnamese like:
    #     - "Còn mấy ngày nữa hết hạn?"
    #     - "Bao nhiêu ngày nữa thì đến hạn thanh toán?"
    #
    #     Do NOT call this tool for unrelated time questions (e.g., "Mấy giờ rồi?"),
    #     or if the customer is not asking about the due date.
    #
    #     When called, calculate the remaining days and then
    #     instruct the session to generate a natural Vietnamese reply.
    #     """
    #     logger.info("Call days_until_due() tool...")
    #     self.is_processing = True
    #     try:
    #         today = datetime.now()
    #         due_date = datetime.strptime(self.customer.han_thanh_toan, "%d/%m/%Y")
    #         delta = (due_date - today).days
    #
    #         if delta > 0:
    #             msg = f"Còn {delta} ngày nữa đến hạn thanh toán."
    #         elif delta == 0:
    #             msg = "Hôm nay là ngày đến hạn thanh toán."
    #         else:
    #             msg = f"Khoản vay đã quá hạn {abs(delta)} ngày."
    #         await self.session.generate_reply(
    #             instructions=f"Inform customers about remaining loan period: {msg}",
    #         )
    #         await asyncio.sleep(3)
    #     except Exception:
    #         await self.session.generate_reply(
    #             instructions="Xin lỗi, hiện tại em không tính được số ngày đến hạn."
    #         )
    #     finally:
    #         self.is_processing = False


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

async def entrypoint(ctx: JobContext):
    khoan_vay = num_to_words(20000000)
    tien_thanh_toan = num_to_words(2000000)
    customer = CustomerInfo(
        ten="Hoàng Anh",
        gioi_tinh="Nữ",
        so_hop_dong="1 9 2 7 3 7",
        khoan_vay=khoan_vay,
        tien_thanh_toan=tien_thanh_toan,
        han_thanh_toan="30/08/2025",
        trang_thai="Chưa thanh toán",
        prefix="chị",
    )

    session = AgentSession[CustomerInfo](
        # llm=openai.realtime.RealtimeModel(
        #     modalities=["text"],
        #     model='gpt-4o-realtime-preview-2025-06-03',
        # ),
        llm=google.beta.realtime.RealtimeModel(
            vertexai=True,
            modalities=[Modality.TEXT],
            model="gemini-2.0-flash-exp",
        ),
        # stt=openai.STT(model="gpt-4o-mini-transcribe", language="vi"),
        # stt=google.STT(
        #     languages='vi-VN',
        #     model='latest_long',
        #     spoken_punctuation=False,
        # ),
        # vad=ctx.proc.userdata["vad"],
        # llm=openai.LLM(model="gpt-4.1"),
        tts=elevenlabs.TTS(
            voice_id="BUPPIXeDaJWBz696iXRS",
            model="eleven_flash_v2_5",
            # voice_settings=elevenlabs.VoiceSettings(
            #     stability=0.75,
            #     similarity_boost=0.75,
            #     speed=1.0,
            # )
        ),
        # tts=openai.TTS(voice="alloy", speed=1.2),
        # tts=google.TTS(
        #     gender='male',
        #     voice_name='vi-VN-Chirp3-HD-Iapetus',
        #     language='vi-VN',
        # ),
        userdata=customer,
        user_away_timeout=9,
    )

    inactivity_task: asyncio.Task | None = None

    async def user_presence_task():
        try:
            if session.agent.call_ending or session.agent.is_processing:
                return
            logger.info("User is away, starting inactivity task...")

            await session.generate_reply(
                instructions="User is away, say goodbye and say that the call will be ended."
            )
            await asyncio.sleep(5)
            # Ngắt và đóng session
            await session.interrupt()
            try:
                await asyncio.wait_for(session.aclose(), timeout=8)
            except asyncio.TimeoutError:
                logger.warning("session.aclose() timeout, force closing...")

            ctx.delete_room()
            logger.info("Session closed due to inactivity (with goodbye message)")
        except asyncio.CancelledError:
            logger.info("Inactivity task cancelled (user returned)")

            async def resume_conversation():
                await session.generate_reply(
                    instructions="Dạ vâng, em vẫn đang lắng nghe anh chị ạ."
                )

            asyncio.create_task(resume_conversation())

    @session.on("user_state_changed")
    def _user_state_changed(ev: UserStateChangedEvent):
        nonlocal inactivity_task
        if ev.new_state == "away":
            if inactivity_task is None or inactivity_task.done():
                inactivity_task = asyncio.create_task(user_presence_task())
        elif ev.new_state == "speaking":
            async def delayed_cancel():
                await asyncio.sleep(1)  # đợi 2 giây xem user có thực sự active không
                if ev.new_state == "speaking":
                    if inactivity_task and not inactivity_task.done():
                        inactivity_task.cancel()

            asyncio.create_task(delayed_cancel())

    usage_collector = metrics.UsageCollector()
    latencies = []

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

        if "latency_ms" in ev.metrics:
            latencies.append(ev.metrics["latency_ms"])

    async def log_usage():
        summary = usage_collector.get_summary()
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        logger.info(f"Usage: {summary}")
        logger.info(f"Average latency: {avg_latency:.2f} ms")

    ctx.add_shutdown_callback(log_usage)

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event: UserInputTranscribedEvent):
        logger.info(
            f"[STT] transcript='{event.transcript}', final={event.is_final}, speaker={event.speaker_id}"
        )

    agent = LoanCallAgent(customer=customer, ctx=ctx)
    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            noise_cancellation=noise_cancellation.BVC(),
        ),
        room_output_options=RoomOutputOptions(transcription_enabled=True),
    )
    session.agent = agent
    await session.generate_reply()

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
