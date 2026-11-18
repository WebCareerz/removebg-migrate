#!/usr/bin/env sh
# Before: remove.bg
curl -H "X-Api-Key: $REMOVE_BG_KEY" \
  -F 'image_file=@photo.jpg' \
  -F 'size=auto' \
  -f https://api.remove.bg/v1.0/removebg -o no-bg.png

# After: same request, new host and key
curl -H "X-Api-Key: $CLEARBG_API_KEY" \
  -F 'image_file=@photo.jpg' \
  -F 'size=auto' \
  -f https://api.clearbg.org/v1.0/removebg -o no-bg.png

# JSON instead of image bytes (same shape as remove.bg's JSON response)
curl -H "X-Api-Key: $CLEARBG_API_KEY" \
  -H 'Accept: application/json' \
  -F 'image_url=https://example.com/photo.jpg' \
  -F 'size=full' -F 'format=jpg' -F 'bg_color=ffffff' \
  https://api.clearbg.org/v1.0/removebg

# Balance and free calls (does not use a credit)
curl -H "X-Api-Key: $CLEARBG_API_KEY" https://api.clearbg.org/v1.0/account
