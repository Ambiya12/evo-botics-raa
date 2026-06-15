<?php

use App\Http\Controllers\ProfileController;
use App\Livewire\KioskManager;
use App\Livewire\Reservation;
use Illuminate\Foundation\Application;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use Inertia\Inertia;

Route::post('/locale', function (Request $request) {
    $validated = $request->validate([
        'locale' => 'required|in:en,fr,id,zh',
    ]);
    session(['locale' => $validated['locale']]);
    app()->setLocale($validated['locale']);
    return redirect()->back();
})->name('locale.switch');

Route::get('/', function () {
    return Inertia::render('Welcome', [
        'canLogin' => Route::has('login'),
        'canRegister' => Route::has('register'),
        'laravelVersion' => Application::VERSION,
        'phpVersion' => PHP_VERSION,
    ]);
});

Route::get('/kiosk', KioskManager::class);

Route::get('/reservation', Reservation::class)->middleware(['auth', 'verified'])->name('reservation');

Route::get('/dashboard', function () {
    return Inertia::render('Dashboard');
})->middleware(['auth', 'verified'])->name('dashboard');

Route::middleware('auth')->group(function () {
    Route::get('/profile', [ProfileController::class, 'edit'])->name('profile.edit');
    Route::patch('/profile', [ProfileController::class, 'update'])->name('profile.update');
    Route::delete('/profile', [ProfileController::class, 'destroy'])->name('profile.destroy');
});

require __DIR__.'/auth.php';
