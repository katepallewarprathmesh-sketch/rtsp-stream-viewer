"""
Async wrapper around an FFmpeg subprocess that converts an RTSP stream
into a sequence of JPEG frames written to stdout (MJPEG over a pipe).
"""
import asyncio
import logging
from collections import deque

from django.conf import settings

logger = logging.getLogger(__name__)

JPEG_SOI = b"\xff\xd8"  # start of image
JPEG_EOI = b"\xff\xd9"  # end of image

# Hard cap so a corrupt stream can't grow the buffer unboundedly (8 MB).
MAX_BUFFER = 8 * 1024 * 1024


def build_ffmpeg_command(rtsp_url: str) -> list[str]:
    vf = (
        f"fps={settings.STREAM_FPS},"
        f"scale='min({settings.STREAM_MAX_WIDTH},iw)':-2"
    )
    return [
        settings.FFMPEG_BIN,
        "-hide_banner",
        "-loglevel", "error",
        "-rtsp_transport", "tcp",          # TCP is far more reliable than UDP
        "-timeout", "10000000",            # 10s socket I/O timeout (microseconds)
        "-analyzeduration", "2000000",
        "-probesize", "1000000",
        "-i", rtsp_url,
        "-an",                             # drop audio
        "-vf", vf,
        "-q:v", str(settings.STREAM_JPEG_QUALITY),
        "-f", "image2pipe",
        "-vcodec", "mjpeg",
        "pipe:1",
    ]


class FFmpegStream:
    """
    Manages one FFmpeg subprocess for one RTSP URL.

    Usage:
        stream = FFmpegStream(url)
        await stream.start()
        async for jpeg_bytes in stream.frames():
            ...
        await stream.stop()
    """

    def __init__(self, rtsp_url: str):
        self.rtsp_url = rtsp_url
        self.process: asyncio.subprocess.Process | None = None
        self._stderr_tail: deque[str] = deque(maxlen=12)
        self._stderr_task: asyncio.Task | None = None

    async def start(self):
        cmd = build_ffmpeg_command(self.rtsp_url)
        logger.info("Starting FFmpeg for %s", self.rtsp_url)
        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._stderr_task = asyncio.ensure_future(self._drain_stderr())

    async def _drain_stderr(self):
        assert self.process and self.process.stderr
        try:
            while True:
                line = await self.process.stderr.readline()
                if not line:
                    break
                text = line.decode(errors="replace").strip()
                if text:
                    self._stderr_tail.append(text)
                    logger.warning("[ffmpeg %s] %s", self.rtsp_url, text)
        except asyncio.CancelledError:
            pass

    @property
    def error_hint(self) -> str:
        """A short human-readable reason extracted from FFmpeg's stderr."""
        joined = " | ".join(self._stderr_tail).lower()
        if not joined:
            return "Could not connect to the stream."
        if "401" in joined or "unauthorized" in joined:
            return "Authentication failed (check username/password in the URL)."
        if "404" in joined or "no such stream" in joined:
            return "Stream path not found on the server (404)."
        if "connection refused" in joined:
            return "Connection refused — host is up but not serving RTSP on that port."
        if "timed out" in joined or "timeout" in joined:
            return "Connection timed out — camera unreachable or blocked by a firewall."
        if "name or service not known" in joined or "no route to host" in joined:
            return "Host could not be resolved / reached."
        if "invalid data" in joined:
            return "Received invalid data — is this really an RTSP stream?"
        # Fall back to the last raw stderr line.
        return self._stderr_tail[-1][:300]

    async def frames(self):
        """Async generator yielding complete JPEG frames as bytes."""
        assert self.process and self.process.stdout
        buffer = bytearray()
        stdout = self.process.stdout
        while True:
            chunk = await stdout.read(65536)
            if not chunk:
                break  # FFmpeg exited or closed stdout
            buffer.extend(chunk)
            if len(buffer) > MAX_BUFFER:
                logger.warning("Frame buffer overflow, resetting (%s)", self.rtsp_url)
                buffer.clear()
                continue
            # Extract every complete JPEG currently in the buffer.
            while True:
                start = buffer.find(JPEG_SOI)
                if start == -1:
                    buffer.clear()
                    break
                end = buffer.find(JPEG_EOI, start + 2)
                if end == -1:
                    if start > 0:
                        del buffer[:start]
                    break
                frame = bytes(buffer[start : end + 2])
                del buffer[: end + 2]
                yield frame

    async def stop(self):
        if self._stderr_task:
            self._stderr_task.cancel()
            self._stderr_task = None
        if self.process and self.process.returncode is None:
            try:
                self.process.kill()
            except ProcessLookupError:
                pass
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except asyncio.TimeoutError:
                logger.error("FFmpeg did not exit after kill (%s)", self.rtsp_url)
        self.process = None
