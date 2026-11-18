curl -H 'X-Api-Key: KEY' -F 'image_file=@photo.jpg' -F 'size=auto' -F 'shadow_type=car' \
  -f https://api.remove.bg/v1.0/removebg -o no-bg.png
curl -H 'Authorization: Bearer TOKEN' https://api.remove.bg/v1.0/improve
