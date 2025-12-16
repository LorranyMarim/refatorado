<?php
if (!isset($_POST['username']) || !isset($_POST['password']) || !isset($_POST['instituicao_id'])) {
    header("Location: ../views/index.php?erro=1");
    exit();
}

$user = trim($_POST['username']); 
$pass = $_POST['password'];       
$inst = $_POST['instituicao_id'];

if (strlen($user) < 4 || strlen($user) > 50 || strlen($pass) < 4 || strlen($pass) > 50) {
    header("Location: ../views/index.php?erro=1");
    exit();
}

$api_url = "http://localhost:8000/api/login";
$dados = ["user_name" => $user, "senha" => $pass, "instituicao_id" => $inst];

$ch = curl_init($api_url);
curl_setopt_array($ch, [
    CURLOPT_POST            => true,
    CURLOPT_HTTPHEADER      => ['Content-Type: application/json', 'Accept: application/json'],
    CURLOPT_POSTFIELDS      => json_encode($dados, JSON_UNESCAPED_UNICODE),
    CURLOPT_RETURNTRANSFER  => true,
    CURLOPT_HEADER          => true, 
    CURLOPT_TIMEOUT         => 10,
    CURLOPT_CONNECTTIMEOUT  => 5,
]);

$response = curl_exec($ch);

if ($response === false) {
    header("Location: ../views/index.php?erro=1");
    exit();
}

$header_size = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
$http_code   = curl_getinfo($ch, CURLINFO_HTTP_CODE);
$body        = substr($response, $header_size);
curl_close($ch);

if ($http_code === 422) {
    header("Location: ../views/index.php?erro=valid");
    exit();
}
if ($http_code === 429) {
    header("Location: ../views/index.php?erro=limite"); 
    exit();
}
if ($http_code === 401) {
    header("Location: ../views/index.php?erro=auth");
    exit();
}
if ($http_code === 403) {
    header("Location: ../views/index.php?erro=inst");  
    exit();
}
if ($http_code === 400) {
    header("Location: ../views/index.php?erro=inst_invalida"); 
    exit();
}
if ($http_code !== 200) {
    header("Location: ../views/index.php?erro=1");
    exit();
}

$user_data = json_decode($body, true);

if (!is_array($user_data) || !isset($user_data['id'])) {
    header("Location: ../views/index.php?erro=1");
    exit();
}

if (!empty($user_data['token'])) {
    setcookie(
        'session_token',
        $user_data['token'],
        [
            'expires'  => time() + (30 * 60), 
            'path'     => '/',                
            'secure'   => false, 
            'httponly' => true,  
            'samesite' => 'Lax',         
        ]
    );
}

header("Location: ../views/dashboard.php");
exit();
?>