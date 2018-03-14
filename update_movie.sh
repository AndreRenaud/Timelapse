#!/bin/sh

SIZE=960x720

echo "Resizing & morphing into png @ $SIZE"
convert -scale $SIZE -delay 20 -loop 0 cropped-*.png -morph 20 result-%04d.png -monitor
#convert -resize 1280x720 -delay 20 -loop 0 warped-*.png result.gif
echo "Converting to mp4"
ffmpeg -v 24 -y -r 15 -f image2 -s $SIZE -i result-%04d.png -vcodec libx264 -crf 24 -pix_fmt yuv420p result.mp4
rm result-*.png
