<?php
// Погода для сайта: сервер сам берёт её у Open-Meteo и отдаёт браузеру.
// Зачем: у части российских провайдеров api.open-meteo.com из браузера не открывается без VPN.
// Запрос фиксированный (координаты отеля) — это не открытый прокси. Ответ кэшируется на 10 минут,
// при сбое Open-Meteo отдаётся последний удачный ответ (до 3 часов).
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: public, max-age=300');
header('X-Content-Type-Options: nosniff');

$url = 'https://api.open-meteo.com/v1/forecast?latitude=43.246012&longitude=42.526408&elevation=2150&cell_selection=nearest'
  . '&current=temperature_2m,weather_code,is_day,wind_speed_10m,cloud_cover,wind_direction_10m'
  . '&daily=sunrise,sunset,weather_code,temperature_2m_max,temperature_2m_min'
  . '&hourly=temperature_2m,weather_code,cloud_cover,wind_speed_10m&timezone=Europe%2FMoscow&forecast_days=5';
$cache = __DIR__ . '/.wx-cache.json';
$age = is_file($cache) ? time() - filemtime($cache) : PHP_INT_MAX;

if ($age < 600) { readfile($cache); exit; }

$body = false;
if (function_exists('curl_init')) {
  $ch = curl_init($url);
  curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 8, CURLOPT_CONNECTTIMEOUT => 5, CURLOPT_USERAGENT => 'hotellegenda.ru weather']);
  $body = curl_exec($ch);
  if (curl_getinfo($ch, CURLINFO_HTTP_CODE) !== 200) $body = false;
  curl_close($ch);
} else {
  $ctx = stream_context_create(['http' => ['timeout' => 8, 'user_agent' => 'hotellegenda.ru weather']]);
  $body = @file_get_contents($url, false, $ctx);
}

$ok = $body !== false && ($j = json_decode($body, true)) && isset($j['current']);
if ($ok) { @file_put_contents($cache, $body, LOCK_EX); echo $body; exit; }
if ($age < 3 * 3600) { header('X-Wx-Stale: 1'); readfile($cache); exit; }
http_response_code(502);
echo '{"error":"weather unavailable"}';
