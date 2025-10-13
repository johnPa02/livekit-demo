# --------------------------------------------------------------------
# LiveKit OpenAI-Compatible TTS (for Orpheus-FASTAPI)
# --------------------------------------------------------------------
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Literal, Union

import httpx
import openai

from livekit.agents import (
    APIConnectionError,
    APIConnectOptions,
    APIStatusError,
    APITimeoutError,
    DEFAULT_API_CONNECT_OPTIONS,
    tts,
    utils,
)

# --------------------------------------------------------------------
# Audio constants
# --------------------------------------------------------------------
SAMPLE_RATE = 24000
NUM_CHANNELS = 1
RESPONSE_FORMATS = Union[Literal["mp3", "wav", "opus", "aac", "flac", "pcm"], str]


# --------------------------------------------------------------------
# Options Dataclass
# --------------------------------------------------------------------
@dataclass
class _TTSOptions:
    model: str
    voice: str
    speed: float
    response_format: RESPONSE_FORMATS


# --------------------------------------------------------------------
# Main TTS Class
# --------------------------------------------------------------------
class TTS(tts.TTS):
    """
    Orpheus/OpenAI-compatible Text-to-Speech adapter for LiveKit.
    """

    def __init__(
        self,
        *,
        model: str = "orpheus",
        voice: str = "tara",
        speed: float = 1.0,
        response_format: RESPONSE_FORMATS = "mp3",
        base_url: str = "http://localhost:5005/v1",
        api_key: str = "not-needed",
        client: openai.AsyncClient | None = None,
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
        )

        self._opts = _TTSOptions(
            model=model,
            voice=voice,
            speed=speed,
            response_format=response_format,
        )

        # Build AsyncClient
        self._client = client or openai.AsyncClient(
            api_key=api_key,
            base_url=base_url,
            max_retries=0,
            http_client=httpx.AsyncClient(
                timeout=httpx.Timeout(15.0),
                follow_redirects=True,
                limits=httpx.Limits(
                    max_connections=50,
                    max_keepalive_connections=50,
                    keepalive_expiry=120,
                ),
            ),
        )

    # ----------------------------------------------------------------
    # Helper factory for Orpheus TTS
    # ----------------------------------------------------------------
    @staticmethod
    def create_orpheus_client(
        *,
        voice: str = "tara",
        base_url: str = "http://localhost:5005/v1",
        response_format: RESPONSE_FORMATS = "mp3",
    ) -> "TTS":
        """
        Create a TTS client pointing to Orpheus-FASTAPI endpoint.
        """
        return TTS(
            model="orpheus",
            voice=voice,
            speed=1.0,
            response_format=response_format,
            base_url=base_url,
            api_key="not-needed",
        )

    # ----------------------------------------------------------------
    # Update runtime parameters
    # ----------------------------------------------------------------
    def update_options(
        self,
        *,
        voice: str | None = None,
        speed: float | None = None,
        response_format: RESPONSE_FORMATS | None = None,
    ) -> None:
        if voice:
            self._opts.voice = voice
        if speed:
            self._opts.speed = speed
        if response_format:
            self._opts.response_format = response_format

    # ----------------------------------------------------------------
    # Main Synthesize Entry Point
    # ----------------------------------------------------------------
    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> "ChunkedStream":
        return ChunkedStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
            opts=self._opts,
            client=self._client,
        )


# --------------------------------------------------------------------
# Chunked Stream (Orpheus-compatible)
# --------------------------------------------------------------------
class ChunkedStream(tts.ChunkedStream):
    """
    Handles downloading & decoding Orpheus/OpenAI-compatible TTS audio.
    Compatible with LiveKit's tts.AudioEmitter interface.
    """

    def __init__(
        self,
        *,
        tts: TTS,
        input_text: str,
        conn_options: APIConnectOptions,
        opts: _TTSOptions,
        client: openai.AsyncClient,
    ):
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._client = client
        self._opts = opts

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        """
        Fetch TTS output from Orpheus using OpenAI-compatible /v1/audio/speech.
        This version matches LiveKit's expected signature (_run(self, output_emitter)).
        """
        # Build OpenAI-compatible streaming request
        oai_stream = self._client.audio.speech.with_streaming_response.create(
            input=self.input_text,
            model=self._opts.model,
            voice=self._opts.voice,
            response_format=self._opts.response_format,
            speed=self._opts.speed,
            timeout=httpx.Timeout(30.0),
        )

        request_id = utils.shortuuid()

        # Initialize audio emitter before streaming
        output_emitter.initialize(
            request_id=request_id,
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
            mime_type=f"audio/{self._opts.response_format}",
        )

        try:
            async with oai_stream as stream:
                async for data in stream.iter_bytes():
                    # Push raw bytes directly into emitter
                    output_emitter.push(data)

            # Flush remaining data
            output_emitter.flush()

        except openai.APITimeoutError:
            raise APITimeoutError()
        except openai.APIStatusError as e:
            raise APIStatusError(
                e.message,
                status_code=e.status_code,
                request_id=e.request_id,
                body=e.body,
            )
        except Exception as e:
            raise APIConnectionError() from e

