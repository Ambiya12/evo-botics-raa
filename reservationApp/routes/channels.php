<?php

use Illuminate\Support\Facades\Broadcast;

// Canal public : le backend diffuse les données robot vers tous les clients dashboard
Broadcast::channel('robot-dashboard', fn() => true);
