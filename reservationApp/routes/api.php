<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use Illuminate\Support\Facades\Hash;
use Illuminate\Validation\ValidationException;
use App\Http\Controllers\ReservationController;
use App\Http\Controllers\BookingSessionController;
use App\Models\ActivityLog;
use App\Models\User;

Route::get('/user', function (Request $request) {
    return $request->user();
})->middleware('auth:sanctum');

Route::post('/register', function (Request $request) {
    $request->validate([
        'name' => 'required|string|max:255',
        'email' => 'required|string|email|max:255|unique:users',
        'password' => 'required|string|min:8|confirmed',
    ]);

    $user = User::create([
        'name' => $request->name,
        'email' => $request->email,
        'password' => Hash::make($request->password),
    ]);

    $token = $user->createToken('auth_token')->plainTextToken;

    return response()->json([
        'access_token' => $token,
        'token_type' => 'Bearer',
    ], 201);
});

Route::post('/login', function (Request $request) {
    $request->validate([
        'email' => 'required|email',
        'password' => 'required',
    ]);

    $user = User::where('email', $request->email)->first();

    if (! $user || ! Hash::check($request->password, $user->password)) {
        throw ValidationException::withMessages([
            'email' => ['Les identifiants sont incorrects.'],
        ]);
    }

    $token = $user->createToken('auth_token')->plainTextToken;

    return response()->json([
        'access_token' => $token,
        'token_type' => 'Bearer',
    ]);
});

Route::post('/reservations/validate', [ReservationController::class, 'validateQRCode']);
Route::get('/logs', function() {return ActivityLog::latest()->get();});

Route::get('/sessions', [BookingSessionController::class, 'index']);

Route::middleware('auth:sanctum')->group(function () {
    Route::post('/sessions/book', [BookingSessionController::class, 'bookSession']);
    Route::get('/my-reservations', [ReservationController::class, 'myReservations']);
    Route::delete('/reservations/{uuid}', [ReservationController::class, 'cancel']);
});