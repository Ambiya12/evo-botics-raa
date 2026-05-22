<?php

return [

    /*
    |--------------------------------------------------------------------------
    | Third Party Services
    |--------------------------------------------------------------------------
    |
    | This file is for storing the credentials for third party services such
    | as Mailgun, Postmark, AWS and more. This file provides the de facto
    | location for this type of information, allowing packages to have
    | a conventional file to locate the various service credentials.
    |
    */

    'postmark' => [
        'key' => env('POSTMARK_API_KEY'),
    ],

    'resend' => [
        'key' => env('RESEND_API_KEY'),
    ],

    'ses' => [
        'key' => env('AWS_ACCESS_KEY_ID'),
        'secret' => env('AWS_SECRET_ACCESS_KEY'),
        'region' => env('AWS_DEFAULT_REGION', 'us-east-1'),
    ],

    'slack' => [
        'notifications' => [
            'bot_user_oauth_token' => env('SLACK_BOT_USER_OAUTH_TOKEN'),
            'channel' => env('SLACK_BOT_USER_DEFAULT_CHANNEL'),
        ],
    ],

    'rosbridge' => [
        'url' => env('ROSBRIDGE_URL', 'ws://10.10.221.115:9090'),
    ],

    'influxdb' => [
        'url'    => env('INFLUXDB_URL', 'http://influxdb:8086'),
        'token'  => env('INFLUXDB_TOKEN', 'dev-token-local'),
        'org'    => env('INFLUXDB_ORG', 'evo-botics'),
        'bucket' => env('INFLUXDB_BUCKET', 'robot_metrics'),
    ],

];
