<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\ReservationController;
use App\Http\Controllers\BookingSessionController;

Route::get('/user', function (Request $request) {
    return $request->user();
})->middleware('auth:sanctum');

Route::post('/reservations/validate', [ReservationController::class, 'validateQRCode']);
Route::post('/sessions/book', [BookingSessionController::class, 'bookSession']);