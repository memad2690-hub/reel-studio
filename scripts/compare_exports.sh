#!/usr/bin/env bash
# Side-by-side comparison export (360x640 per panel, label on top, audio from the last panel).
# bash scripts/compare_exports.sh out.mp4 "V1" a.mp4 "V2" b.mp4 ["V2 b" c.mp4]
# cmp.sh OUT "label1" file1 "label2" file2 ["label3" file3]   (audio from the last panel)
set -e
OUT=$1; shift
FONT="$(cd "$(dirname "$0")/.." && pwd)/fonts/Cairo-Variable.ttf"
ins=(); fl=""; n=0
while [ $# -gt 0 ]; do lab=$1; f=$2; shift 2
  ins+=(-i "$f")
  fl+="[$n:v]scale=360:640,setsar=1,pad=360:700:0:60:color=0x1b1b1b,drawtext=fontfile=$FONT:text='$lab':fontcolor=white:fontsize=26:x=(w-text_w)/2:y=16[v$n];"
  n=$((n+1)); done
st=""; for i in $(seq 0 $((n-1))); do st+="[v$i]"; done
ffmpeg -v error -y "${ins[@]}" -filter_complex "${fl}${st}hstack=inputs=$n[v]" -map "[v]" -map $((n-1)):a -c:v libx264 -preset veryfast -crf 22 -pix_fmt yuv420p -c:a aac -b:a 128k -shortest -movflags +faststart "$OUT"
echo "$OUT $(ffprobe -v error -show_entries format=duration:stream=width,height -of csv=p=0 "$OUT" | tr '\n' ' ')"
