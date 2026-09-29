"""
WebSocket consumer: one connection == one RTSP stream viewer.

Protocol (client -> server), JSON text frames:
    {"action": "play",  "url": "rtsp://..."}   start (or resume) streaming
    {"action": "pause"}                        stop sending frames, keep socket
    {"action": "stop"}                         tear down the ffmpeg process

Protocol (server -> client):
    binary frames                              JPEG images (render directly)
    {"type": "status", "state": "connecting"|"live"|"paused"|"stopped"}
    {"type": "error",  "message": "..."}       human-readable failure reason
"""
import asyncio
import json
import logging
from urllib.parse import urlparse

from channels.generic.websocket import AsyncWebsocketConsumer
from django.conf import settings

from .ffmpeg import FFmpegStream

logger = logging.getLogger(__name__)


def validate_rtsp_url(url: str) -> str | None:
    """Return an error message if the URL is not an acceptable RTSP URL."""
    if not url or not isinstance(url, str):
        return "No URL provided."
    if len(url) > 2048:
        return "URL is too long."
    parsed = urlparse(url)
    if parsed.scheme not in ("rtsp", "rtsps"):
        return "URL must start with rtsp:// or rtsps://"
    if not parsed.hostname:
        return "URL is missing a host."
    return None


class StreamConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.stream: FFmpegStream | None = None
        self.pump_task: asyncio.Task | None = None
        self.paused = False
        await self.accept()

    async def disconnect(self, code):
        await self._teardown()

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            message = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON message.")
            return

        action = message.get("action")
        if action == "play":
            await self.handle_play(message.get("url", ""))
        elif action == "pause":
            await self.handle_pause()
        elif action == "stop":
            await self._teardown()
            await self.send_status("stopped")
        else:
            await self.send_error(f"Unknown action: {action!r}")

    # ------------------------------------------------------------------ #

    async def handle_play(self, url: str):
        # Resume from pause: same URL, ffmpeg still running.
        if (
            self.paused
            and self.stream
            and self.stream.rtsp_url == url
            and self.stream.process
            and self.stream.process.returncode is None
        ):
            self.paused = False
            await self.send_status("live")
            return

        error = validate_rtsp_url(url)
        if error:
            await self.send_error(error)
            return

        await self._teardown()
        await self.send_status("connecting")

        self.stream = FFmpegStream(url)
        try:
            await self.stream.start()
        except FileNotFoundError:
            await self.send_error("FFmpeg is not installed on the server.")
            return
        except Exception as exc:  # pragma: no cover
            logger.exception("Failed to start FFmpeg")
            await self.send_error(f"Failed to start stream: {exc}")
            return

        self.paused = False
        self.pump_task = asyncio.ensure_future(self._pump_frames(self.stream))

    async def handle_pause(self):
        if self.stream:
            self.paused = True
            await self.send_status("paused")
        else:
            await self.send_error("Nothing is playing.")

    async def _pump_frames(self, stream: FFmpegStream):
        """Read JPEG frames from FFmpeg and push them over the WebSocket."""
        frames_sent = 0
        try:
            connect_deadline = asyncio.get_event_loop().time() + settings.STREAM_CONNECT_TIMEOUT
            frame_iter = stream.frames().__aiter__()
            while True:
                if frames_sent == 0:
                    remaining = connect_deadline - asyncio.get_event_loop().time()
                    if remaining <= 0:
                        raise asyncio.TimeoutError
                    frame = await asyncio.wait_for(frame_iter.__anext__(), timeout=remaining)
                else:
                    frame = await asyncio.wait_for(frame_iter.__anext__(), timeout=20)

                if frames_sent == 0:
                    await self.send_status("live")
                frames_sent += 1
                if not self.paused:
                    await self.send(bytes_data=frame)
        except StopAsyncIteration:
            # FFmpeg exited (stream ended or connection failed).
            if frames_sent == 0:
                await self.send_error(stream.error_hint)
            else:
                await self.send_error("Stream ended: " + stream.error_hint)
        except asyncio.TimeoutError:
            if frames_sent == 0:
                await self.send_error(
                    "Timed out connecting to the stream. " + stream.error_hint
                )
            else:
                await self.send_error("Stream stalled — no frames received for 20s.")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Frame pump crashed")
            try:
                await self.send_error("Internal streaming error.")
            except Exception:
                pass
        finally:
            await stream.stop()

    async def _teardown(self):
        if self.pump_task:
            self.pump_task.cancel()
            try:
                await self.pump_task
            except (asyncio.CancelledError, Exception):
                pass
            self.pump_task = None
        if self.stream:
            await self.stream.stop()
            self.stream = None
        self.paused = False

    # ------------------------------------------------------------------ #

    async def send_status(self, state: str):
        try:
            await self.send(text_data=json.dumps({"type": "status", "state": state}))
        except Exception:
            pass

    async def send_error(self, message: str):
        logger.info("Stream error sent to client: %s", message)
        try:
            await self.send(text_data=json.dumps({"type": "error", "message": message}))
        except Exception:
            pass
