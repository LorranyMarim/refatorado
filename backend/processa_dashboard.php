<?php
header('Content-Type: application/json');

function http_json($method, $url, $payload = null, $timeout = 10, $connectTimeout = 3)
{
    $ch = curl_init($url);
    $opts = [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CUSTOMREQUEST => $method,
        CURLOPT_CONNECTTIMEOUT => $connectTimeout,
        CURLOPT_TIMEOUT => $timeout,
        CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_MAXREDIRS => 0,
        CURLOPT_HTTPHEADER => ['Accept: application/json'],
    ];
    if ($payload !== null) {
        $opts[CURLOPT_HTTPHEADER][] = 'Content-Type: application/json';
        $opts[CURLOPT_POSTFIELDS] = json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    }
    if (isset($_COOKIE['session_token'])) {
        $opts[CURLOPT_COOKIE] = 'session_token=' . $_COOKIE['session_token'];
    }
    curl_setopt_array($ch, $opts);
    $body = curl_exec($ch);
    $err = curl_errno($ch);
    $info = curl_getinfo($ch);
    curl_close($ch);

    return [$err, $info['http_code'] ?? 0, $body];
}

function output($status, $data)
{
    http_response_code($status);
    echo is_string($data) ? $data : json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

function norm($s)
{
    $s = (string) ($s ?? '');
    $s = trim($s);
    if ($s === '')
        return '';
    $s = iconv('UTF-8', 'ASCII//TRANSLIT//IGNORE', $s);
    return strtolower($s);
}

function is_active($status)
{
    if (is_bool($status))
        return $status === true;
    $t = norm($status);
    return ($t === 'ativo' || $t === 'ativa' || $t === 'true' || $t === '1');
}

$FASTAPI_BASE = 'http://localhost:8000';
$ACTION = $_GET['action'] ?? 'metrics';


if ($_SERVER['REQUEST_METHOD'] !== 'GET') {
    output(405, ['error' => 'Método não suportado']);
}

switch ($ACTION) {
    case 'metrics': {
        list($e1, $code1, $body1) = http_json('GET', $FASTAPI_BASE . '/api/dashboard/metrics');
        if ($e1 === 0 && $code1 >= 200 && $code1 < 300 && $body1) {
            output($code1, $body1);
        }

        $total_turmas = 0;
        $total_alunos = 0;
        $turmas_ativas = 0;

        $page = 1;
        $page_size = 200;
        $limit = 10000;

        $somados = 0;
        while (true) {
            $url = sprintf('%s/api/turmas?page=%d&page_size=%d', $FASTAPI_BASE, $page, $page_size);
            list($e2, $code2, $body2) = http_json('GET', $url);
            if ($e2 !== 0 || $code2 < 200 || $code2 >= 300 || !$body2) {
                output(502, [
                    'error' => 'Falha ao obter turmas da API',
                    'status' => $code2,
                    'message' => 'Nem /api/dashboard/metrics nem /api/turmas retornaram com sucesso'
                ]);
            }

            $json = json_decode($body2, true);
            if (!is_array($json))
                $json = [];
            $items = $json['items'] ?? [];
            $total = (int) ($json['total'] ?? 0);

            foreach ($items as $t) {
                $total_turmas++;
                $num = isset($t['num_alunos']) ? (int) $t['num_alunos'] : 0;
                $total_alunos += $num;

                if (is_active($t['status'] ?? null)) {
                    $turmas_ativas++;
                }

                $somados++;
                if ($somados >= $limit)
                    break 2;
            }

            $trazidosAteAgora = $page * $page_size;
            if ($trazidosAteAgora >= $total || empty($items))
                break;
            $page++;
        }

        output(200, [
            'total_turmas' => $total_turmas,
            'total_alunos' => $total_alunos,
            'turmas_ativas' => $turmas_ativas,
        ]);
        break;
    }

    case 'alunos_por_turno': {
        list($e1, $code1, $body1) = http_json('GET', $FASTAPI_BASE . '/api/dashboard/alunos_por_turno');
        if ($e1 === 0 && $code1 >= 200 && $code1 < 300 && $body1) {
            output($code1, $body1);
        }

        $res = ['Manhã' => 0, 'Tarde' => 0, 'Noite' => 0];

        $page = 1;
        $page_size = 200;
        $limit = 10000;

        $somados = 0;
        while (true) {
            $url = sprintf('%s/api/turmas?page=%d&page_size=%d', $FASTAPI_BASE, $page, $page_size);
            list($e2, $code2, $body2) = http_json('GET', $url);
            if ($e2 !== 0 || $code2 < 200 || $code2 >= 300 || !$body2) {
                output(502, [
                    'error' => 'Falha ao obter turmas da API',
                    'status' => $code2,
                    'message' => 'Nem /api/dashboard/alunos_por_turno nem /api/turmas (fallback) retornaram com sucesso'
                ]);
            }

            $json = json_decode($body2, true);
            if (!is_array($json))
                $json = [];
            $items = $json['items'] ?? [];
            $total = (int) ($json['total'] ?? 0);

            foreach ($items as $t) {
                if (!is_active($t['status'] ?? null)) {
                    continue;
                }
                $n = isset($t['num_alunos']) ? (int) $t['num_alunos'] : 0;
                if ($n <= 0) {
                    continue;
                }

                $turno = norm($t['turno'] ?? '');
                if (strpos($turno, 'manh') !== false) {
                    $res['Manhã'] += $n;
                } elseif (strpos($turno, 'tarde') !== false) {
                    $res['Tarde'] += $n;
                } elseif (strpos($turno, 'noite') !== false || strpos($turno, 'noturn') !== false) {
                    $res['Noite'] += $n;
                }

                $somados++;
                if ($somados >= $limit)
                    break 2;
            }

            $trazidosAteAgora = $page * $page_size;
            if ($trazidosAteAgora >= $total || empty($items))
                break;
            $page++;
        }

        output(200, $res);
        break;
    }
    case 'areas_tecnologicas': {
        list($e1, $code1, $body1) = http_json('GET', $FASTAPI_BASE . '/api/dashboard/areas_tecnologicas_pie');
        if ($e1 === 0 && $code1 >= 200 && $code1 < 300 && $body1) {
            output($code1, $body1);
        }
        output(502, ['error' => 'Falha ao obter areas_tecnologicas da API']);
        break;
    }
    case 'areas_tecnologicas_pie': {
        list($e1, $code1, $body1) = http_json('GET', $FASTAPI_BASE . '/api/dashboard/areas_tecnologicas_pie');
        if ($e1 === 0 && $code1 >= 200 && $code1 < 300 && $body1) {
            output($code1, $body1);
        }
        output(502, ['error' => 'Falha ao obter areas_tecnologicas_pie da API']);
        break;
    }

    default:
        output(400, ['error' => 'Ação inválida']);
}
