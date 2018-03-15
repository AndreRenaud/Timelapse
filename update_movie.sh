#!/bin/sh

#SIZE=960x720

echo "Resizing & morphing into png @ $SIZE"
#convert -scale $SIZE -delay 20 -loop 0 cropped-*.png -morph 20 result-%04d.png -monitor
#convert -scale $SIZE alpha-*.png result-%04d.png
#convert -resize 1280x720 -delay 20 -loop 0 warped-*.png result.gif
echo "Converting to mp4"
#ffmpeg -v 24 -y -r 15 -f image2 -s $SIZE -i result-%04d.png -vcodec libx264 -crf 24 -pix_fmt yuv420p result.mp4
#rm result-*.png

# TODO: This could be done automatically inside the application - no need to cache the alpha
# images, just write them directly to the FFMPEG pipe
#cat alpha-*.png | ffmpeg -v 24 -y -framerate 15 -f image2pipe -i - -vf scale=1920:-2 -c:v h264_nvenc -pix_fmt yuv420p result.mp4
cat alpha-*.png | ffmpeg -v 24 -y -framerate 15 -f image2pipe -i - -vf scale=1920:-2 -vcodec libx264 -crf 24 -pix_fmt yuv420p result.mp4
