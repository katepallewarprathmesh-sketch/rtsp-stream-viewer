#!/bin/sh
# Container entrypoint.
#
# DEMO_MODE=1 (default): starts a local MediaMTX RTSP server and publishes
# two synthetic test-pattern cameras, so the deployed demo always has live
# streams to show even when no public RTSP camera is reachable.
# Set DEMO_MODE=0 to run the viewer alone.
set -e

if [ "${DEMO_MODE:-1}" = "1" ]; then
    cat > /tmp/mediamtx.yml <<'EOF'
logLevel: warn
rtsp: yes
rtspAddress: :8554
rtmp: no
hls: no
webrtc: no
srt: no
api: no
metrics: no
pprof: no
paths:
  all_others:
EOF
    mediamtx /tmp/mediamtx.yml &
    sleep 2

    publish_cam() {
        # $1 = path name, $2 = lavfi source, $3 = label, $4 = color
        while true; do
            ffmpeg -hide_banner -loglevel error -re \
                -f lavfi -i "$2" \
                -vf "drawtext=text='$3  %{localtime}':fontcolor=$4:fontsize=32:box=1:boxcolor=black@0.6:boxborderw=8:x=20:y=20" \
                -c:v libx264 -preset ultrafast -tune zerolatency -pix_fmt yuv420p \
                -g 30 -b:v 700k \
                -f rtsp -rtsp_transport tcp "rtsp://127.0.0.1:8554/$1" \
                || true
            sleep 2
        done
    }

    publish_cam demo1 "testsrc2=size=960x540:rate=15"     "DEMO CAM 1" white  &
    publish_cam demo2 "smptehdbars=size=960x540:rate=15"  "DEMO CAM 2" yellow &

    export DEMO_RTSP_URLS="${DEMO_RTSP_URLS:-rtsp://127.0.0.1:8554/demo1,rtsp://127.0.0.1:8554/demo2}"
fi

exec python -m daphne -b 0.0.0.0 -p "${PORT:-8000}" core.asgi:application
