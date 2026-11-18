const form = new FormData();
form.append('image_url', url);
form.append('size', 'preview');
form.append('bg_image_url', 'https://example.com/beach.jpg');
form.append('position', 'center');
form.append('scale', 'original');

const res = await fetch('https://api.remove.bg/v1.0/removebg', {
  method: 'POST',
  headers: { 'X-Api-Key': process.env.REMOVE_BG_KEY },
  body: form,
});
console.log(res.headers.get('X-Credits-Charged'));
