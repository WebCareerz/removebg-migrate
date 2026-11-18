<?php
// $apiBase = 'https://api.remove.bg';   // before
$apiBase = getenv('BG_API_BASE') ?: 'https://api.clearbg.org'; // after

$ch = curl_init($apiBase . '/v1.0/removebg');
curl_setopt_array($ch, [
    CURLOPT_POST => true,
    CURLOPT_HTTPHEADER => ['X-Api-Key: ' . getenv('BG_API_KEY')],
    CURLOPT_POSTFIELDS => [
        'image_file' => new CURLFile('photo.jpg'),
        'size' => 'full',
    ],
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_TIMEOUT => 150,
]);
$body = curl_exec($ch);
$status = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($status === 200) {
    file_put_contents('photo-no-bg.png', $body);
} else {
    echo $body; // {"errors":[{"title":...,"code":...}]}, same shape as remove.bg
}
