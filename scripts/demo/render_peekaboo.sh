#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${ROOT_DIR}/Demo-Assets/peekaboo-demo/work"
OUTPUT="${ROOT_DIR}/Demo-Assets/peekaboo-demo/renders/codexify-peekaboo-16x9.mp4"
FFMPEG_BIN="${FFMPEG_BIN:-ffmpeg}"

for frame in 01-primary 04-gallery 03-documents 05-secondary 06-final; do
  test -s "${WORK_DIR}/${frame}.jpg" || {
    echo "Missing capture: ${WORK_DIR}/${frame}.jpg" >&2
    exit 1
  }
done

mkdir -p "$(dirname "${OUTPUT}")"

"${FFMPEG_BIN}" -y \
  -loop 1 -t 9.7 -i "${WORK_DIR}/01-primary.jpg" \
  -loop 1 -t 5.7 -i "${WORK_DIR}/04-gallery.jpg" \
  -loop 1 -t 5.7 -i "${WORK_DIR}/03-documents.jpg" \
  -loop 1 -t 11.7 -i "${WORK_DIR}/05-secondary.jpg" \
  -loop 1 -t 5.0 -i "${WORK_DIR}/06-final.jpg" \
  -filter_complex "\
    [0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[v0];\
    [1:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[v1];\
    [2:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[v2];\
    [3:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[v3];\
    [4:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p[v4];\
    [v0][v1]xfade=transition=fade:duration=0.7:offset=9.0[x1];\
    [x1][v2]xfade=transition=fade:duration=0.7:offset=14.0[x2];\
    [x2][v3]xfade=transition=fade:duration=0.7:offset=19.0[x3];\
    [x3][v4]xfade=transition=fade:duration=0.7:offset=30.0[vout]" \
  -map "[vout]" -an -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
  -movflags +faststart "${OUTPUT}"

echo "${OUTPUT}"
