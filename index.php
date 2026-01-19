<?php
// Simple PHP Proxy to Python Uvicorn App
// Handles forwarding requests to localhost:8000 where the FastAPI app runs.

$port = 8000;
$host = "127.0.0.1";
$target_url = "http://{$host}:{$port}" . $_SERVER['REQUEST_URI'];

$ch = curl_init($target_url);

// Forward Method
curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $_SERVER['REQUEST_METHOD']);

// Forward Headers
$headers = [];
if (function_exists('getallheaders')) {
    foreach (getallheaders() as $name => $value) {
        if (strtolower($name) !== 'host') {
            $headers[] = "$name: $value";
        }
    }
} else {
    foreach ($_SERVER as $name => $value) {
        if (substr($name, 0, 5) == 'HTTP_') {
            $headerName = str_replace(' ', '-', ucwords(strtolower(str_replace('_', ' ', substr($name, 5)))));
            $headers[] = "$headerName: $value";
        }
    }
}
// Add content type/length if not caught by HTTP_ loop
if (isset($_SERVER['CONTENT_TYPE'])) $headers[] = "Content-Type: " . $_SERVER['CONTENT_TYPE'];
if (isset($_SERVER['CONTENT_LENGTH'])) $headers[] = "Content-Length: " . $_SERVER['CONTENT_LENGTH'];

curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);

// Forward Body (POST/PUT data)
$input_data = file_get_contents('php://input');
if (!empty($input_data)) {
    curl_setopt($ch, CURLOPT_POSTFIELDS, $input_data);
}

// Return headers and body
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HEADER, true);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, false); // Let the client handle redirects

$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);

if ($response === false) {
    http_response_code(502);
    echo "<h1>502 Bad Gateway</h1>";
    echo "<p>Could not connect to the application backend on port $port.</p>";
    echo "<p>Error: " . curl_error($ch) . "</p>";
    exit;
}

// Separate headers and body
$header_size = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
$response_headers = substr($response, 0, $header_size);
$response_body = substr($response, $header_size);

// Output Headers
$response_headers_lines = explode("\r\n", $response_headers);
foreach ($response_headers_lines as $header_line) {
    if (!empty($header_line)) {
        header($header_line);
    }
}

// Output Body
echo $response_body;

curl_close($ch);
?>
