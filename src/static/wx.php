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
$multi = 'https://api.open-meteo.com/v1/forecast?latitude=43.246012&longitude=42.526408&elevation=2150&cell_selection=nearest'
  . '&hourly=cloud_cover&timezone=Europe%2FMoscow&forecast_days=5'
  . '&models=ecmwf_ifs025,icon_seamless,gfs_seamless,meteofrance_seamless,gem_seamless,ukmo_seamless';
$cache = __DIR__ . '/.wx-cache.json';
$age = is_file($cache) ? time() - filemtime($cache) : PHP_INT_MAX;

if ($age < 600) { readfile($cache); exit; }

function get($url) {
  if (function_exists('curl_init')) {
    $ch = curl_init($url);
    curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 8, CURLOPT_CONNECTTIMEOUT => 5, CURLOPT_USERAGENT => 'hotellegenda.ru weather']);
    $b = curl_exec($ch);
    if (curl_getinfo($ch, CURLINFO_HTTP_CODE) !== 200) $b = false;
    curl_close($ch);
    return $b;
  }
  $ctx = stream_context_create(['http' => ['timeout' => 8, 'user_agent' => 'hotellegenda.ru weather']]);
  return @file_get_contents($url, false, $ctx);
}

// Облачность — по середине (медиане) шести моделей: одна модель часто «видит» ясное небо, когда остальные — сплошные облака
// (08.11.2026: основная давала 21 %, большинство — 75–100 %, Яндекс и iPhone — пасмурно). Температура — из основной модели.
// Код погоды меняется, только если он «без осадков и тумана» (0–3): тогда он пересчитывается по медиане облачности.
function median($a) { $a = array_values(array_filter($a, function ($v) { return $v !== null; })); $n = count($a);
  if (!$n) return null; sort($a); return $n % 2 ? $a[intdiv($n, 2)] : ($a[$n / 2 - 1] + $a[$n / 2]) / 2; }
function skyCode($cloud) { return $cloud < 20 ? 0 : ($cloud < 45 ? 1 : ($cloud < 75 ? 2 : 3)); }
function blendClouds($body, $multi) {
  $d = json_decode($body, true); $m = $multi ? json_decode($multi, true) : null;
  if (!$d || !$m || empty($m['hourly']['time']) || empty($d['hourly']['time'])) return $body;
  $idx = array_flip($m['hourly']['time']); $keys = [];
  foreach ($m['hourly'] as $k => $v) if (strpos($k, 'cloud_cover_') === 0) $keys[] = $k;
  if (count($keys) < 3) return $body;
  $at = function ($t) use ($m, $idx, $keys) { if (!isset($idx[$t])) return null; $i = $idx[$t]; $v = [];
    foreach ($keys as $k) $v[] = $m['hourly'][$k][$i] ?? null; $md = median($v); return $md === null ? null : (int) round($md); };
  foreach ($d['hourly']['time'] as $i => $t) { $c = $at($t); if ($c === null) continue;
    $d['hourly']['cloud_cover'][$i] = $c;
    if (isset($d['hourly']['weather_code'][$i]) && $d['hourly']['weather_code'][$i] <= 3) $d['hourly']['weather_code'][$i] = skyCode($c); }
  if (!empty($d['current']['time'])) { $c = $at(substr($d['current']['time'], 0, 13) . ':00');
    if ($c !== null) { $d['current']['cloud_cover'] = $c; $d['current']['cloud_models'] = count($keys);
      if ($d['current']['weather_code'] <= 3) $d['current']['weather_code'] = skyCode($c); } }
  return json_encode($d, JSON_UNESCAPED_UNICODE | JSON_PRESERVE_ZERO_FRACTION);
}

$body = get($url);
$ok = $body !== false && ($j = json_decode($body, true)) && isset($j['current']);
if ($ok) { $body = blendClouds($body, get($multi)); @file_put_contents($cache, $body, LOCK_EX); echo $body; exit; }
if ($age < 3 * 3600) { header('X-Wx-Stale: 1'); readfile($cache); exit; }
http_response_code(502);
echo '{"error":"weather unavailable"}';
