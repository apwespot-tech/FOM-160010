<?php

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Route;

Route::get('/', function () {
    return view('welcome');
});

// Проверка, что API живо и видит базу (слайды 22–23).
Route::get('/health', function () {
    try {
        DB::connection()->getPdo();
        $database = 'ok';
    } catch (\Throwable $e) {
        $database = 'unavailable';
    }

    return response()->json([
        'status' => 'ok',
        'database' => $database,
    ]);
});
