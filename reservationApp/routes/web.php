<?php

use App\Http\Controllers\Admin\UserManagementController;
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

Route::middleware(['auth', 'verified', 'admin'])->prefix('admin')->name('admin.')->group(function () {
    Route::prefix('robot')->name('robot.')->group(function () {
        Route::get('/', fn () => Inertia::render('Admin/Robot/Overview'))->name('overview');
        Route::get('/navigation', fn () => Inertia::render('Admin/Robot/Navigation'))->name('navigation');
        Route::get('/teleop', fn () => Inertia::render('Admin/Robot/Teleop'))->name('teleop');
        Route::get('/arm', fn () => Inertia::render('Admin/Robot/Arm'))->name('arm');
        Route::get('/diagnostics', fn () => Inertia::render('Admin/Robot/Diagnostics'))->name('diagnostics');
        Route::get('/connection', fn () => Inertia::render('Admin/Robot/Connection'))->name('connection');
    });

    Route::get('users', [UserManagementController::class, 'index'])->name('users.index');
    Route::patch('users/{user}/role', [UserManagementController::class, 'updateRole'])->name('users.role.update');
});

Route::middleware('auth')->group(function () {
    Route::get('/profile', [ProfileController::class, 'edit'])->name('profile.edit');
    Route::patch('/profile', [ProfileController::class, 'update'])->name('profile.update');
    Route::delete('/profile', [ProfileController::class, 'destroy'])->name('profile.destroy');
});

require __DIR__.'/auth.php';
