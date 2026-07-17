<?php
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Content-Type: application/json');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

$UPLOAD_DIR = '/volume1/web/nas_uploads/';
$MAX_BYTES  = 100 * 1024 * 1024; // 100MB

if (!is_dir($UPLOAD_DIR)) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Upload directory not found: ' . $UPLOAD_DIR]);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['ok' => false, 'error' => 'Method not allowed']);
    exit;
}

// ── Sanitize a relative path component (folder name or filename)
// Prevents path traversal: strips slashes, dots, and unsafe characters
function sanitizeName($s) {
    $s = str_replace(['..', '/', '\\', "\0"], '', $s);
    $s = preg_replace('/[^a-zA-Z0-9가-힣_\-. ]/', '', $s);
    return trim($s);
}

// ── Delete action ─────────────────────────────────────────────
if (isset($_POST['action']) && $_POST['action'] === 'delete') {
    $raw = isset($_POST['filename']) ? $_POST['filename'] : '';

    // Allow one level of folder: "folder/filename" or just "filename"
    $parts    = explode('/', $raw, 2);
    $folder   = count($parts) === 2 ? sanitizeName($parts[0]) : '';
    $filename = sanitizeName(count($parts) === 2 ? $parts[1] : $parts[0]);

    if (!$filename) {
        http_response_code(400);
        echo json_encode(['ok' => false, 'error' => 'filename required']);
        exit;
    }

    $path = $UPLOAD_DIR . ($folder ? $folder . '/' : '') . $filename;
    if (file_exists($path)) unlink($path);

    // Remove folder dir if now empty
    if ($folder) {
        $dir = $UPLOAD_DIR . $folder;
        if (is_dir($dir) && count(glob($dir . '/*')) === 0) rmdir($dir);
    }

    echo json_encode(['ok' => true]);
    exit;
}

// ── Upload action ─────────────────────────────────────────────
// $_FILES empty + Content-Length > 0 means post_max_size exceeded
if (!isset($_FILES['file'])) {
    $cl = isset($_SERVER['CONTENT_LENGTH']) ? (int)$_SERVER['CONTENT_LENGTH'] : 0;
    if ($cl > 0) {
        http_response_code(413);
        echo json_encode(['ok' => false, 'error' => 'PHP post_max_size 초과 — Web Station에서 php.ini 설정 필요 (upload_max_filesize=100M, post_max_size=110M)']);
    } else {
        http_response_code(400);
        echo json_encode(['ok' => false, 'error' => 'No file in request']);
    }
    exit;
}

$file = $_FILES['file'];

if ($file['size'] > $MAX_BYTES) {
    http_response_code(413);
    echo json_encode(['ok' => false, 'error' => '100MB 초과 — NAS 드라이브를 직접 이용하세요.']);
    exit;
}

if ($file['error'] !== UPLOAD_ERR_OK) {
    $errors = [
        UPLOAD_ERR_INI_SIZE   => 'File too large (php.ini limit)',
        UPLOAD_ERR_FORM_SIZE  => 'File too large (form limit)',
        UPLOAD_ERR_PARTIAL    => 'Partial upload',
        UPLOAD_ERR_NO_FILE    => 'No file',
        UPLOAD_ERR_NO_TMP_DIR => 'No temp directory',
        UPLOAD_ERR_CANT_WRITE => 'Cannot write to disk',
    ];
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => $errors[$file['error']] ?? 'Upload error ' . $file['error']]);
    exit;
}

$filename = sanitizeName(basename($file['name']));
if (!$filename) {
    http_response_code(400);
    echo json_encode(['ok' => false, 'error' => 'Invalid filename']);
    exit;
}

// Folder support (1-level flat only)
$folder  = isset($_POST['folder']) ? sanitizeName($_POST['folder']) : '';
$subDir  = $UPLOAD_DIR . ($folder ? $folder . '/' : '');

if ($folder && !is_dir($subDir)) {
    if (!mkdir($subDir, 0755, true)) {
        http_response_code(500);
        echo json_encode(['ok' => false, 'error' => 'Cannot create folder: ' . $folder]);
        exit;
    }
    // Ensure the http user can write (best-effort — chown may fail without sudo)
    @chown($subDir, 'http');
}

$destination = $subDir . $filename;
$nasPath     = $folder ? $folder . '/' . $filename : $filename;

if (!move_uploaded_file($file['tmp_name'], $destination)) {
    http_response_code(500);
    echo json_encode(['ok' => false, 'error' => 'Failed to save file to NAS']);
    exit;
}

echo json_encode([
    'ok'       => true,
    'name'     => $filename,
    'nas_path' => $nasPath,
    'size'     => $file['size'],
    'type'     => $file['type'],
]);
