<?php

namespace App\Console\Commands;

use App\Events\RobotStatusUpdated;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Http;
use WebSocket\Client;
use WebSocket\Message\Message;

class RobotListenCommand extends Command
{
    protected $signature = 'robot:listen';
    protected $description = 'Connect to rosbridge and broadcast robot telemetry via Reverb';

    private array $state = [
        'id'                      => 'robot-01',
        'name'                    => 'EvoRobot',
        'mode'                    => 'rosbridge',
        'connectionStatus'        => 'connected_ros',
        'state'                   => 'IDLE',
        'battery'                 => 0,
        'location'                => '',
        'currentWaypoint'         => '',
        'destination'             => '',
        'currentMissionSessionId' => null,
        'lastIncidentSummary'     => '',
        'lastUpdate'              => '',
        'emergencyStop'           => false,
        'services'                => [],
    ];

    private const NAV_STATE_INDEX = [
        'IDLE'                   => 0,
        'WAITING_FOR_QR'         => 1,
        'VALIDATING_RESERVATION' => 2,
        'GUIDING'                => 3,
        'ARRIVED'                => 4,
        'RETURNING_HOME'         => 5,
        'ERROR'                  => 6,
        'EMERGENCY_STOP'         => 7,
    ];

    public function handle(): never
    {
        $url = config('services.rosbridge.url');

        while (true) {
            try {
                $this->info("Connecting to rosbridge at {$url}…");
                $client = new Client($url, ['timeout' => 30]);

                $this->subscribeTo($client, '/battery');
                $this->subscribeTo($client, '/odom_raw');
                $this->subscribeTo($client, '/JoyState');
                // TODO: confirmer avec l'équipe robot un topic pour l'état de navigation (IDLE, GUIDING…)
                // TODO: confirmer avec l'équipe robot un topic pour l'arrêt d'urgence

                $this->info('Connected — listening for robot topics.');

                while (true) {
                    try {
                        $received = $client->receive();
                    } catch (\WebSocket\TimeoutException) {
                        // Pas de message depuis 30 s — le robot est silencieux, on continue d'attendre
                        continue;
                    }

                    $raw = $received instanceof Message ? $received->getContent() : (string) $received;
                    $msg = json_decode($raw, true);

                    if (($msg['op'] ?? '') !== 'publish') {
                        continue;
                    }

                    $this->handleTopic($msg['topic'], $msg['msg'] ?? []);
                }
            } catch (\Throwable $e) {
                $this->error("rosbridge error: {$e->getMessage()} — retry in 5s");
                sleep(5);
            }
        }
    }

    private function subscribeTo(Client $client, string $topic): void
    {
        $client->text(json_encode(['op' => 'subscribe', 'topic' => $topic]));
    }

    private function handleTopic(string $topic, array $msg): void
    {
        match ($topic) {
            // 3S LiPo: 9.0 V (vide) → 12.6 V (plein)
            '/battery'   => $this->state['battery'] = (int) round(
                min(100, max(0, (($msg['data'] ?? 9.0) - 9.0) / 3.6 * 100))
            ),
            '/odom_raw'  => $this->state['location'] = sprintf(
                'x=%.2f y=%.2f',
                $msg['pose']['pose']['position']['x'] ?? 0.0,
                $msg['pose']['pose']['position']['y'] ?? 0.0,
            ),
            '/JoyState'  => $this->state['emergencyStop'] = ($msg['emergency_stop'] ?? false) === true,
            default      => null,
        };

        $this->state['lastUpdate'] = now()->format('H:i:s');

        $payload = array_merge($this->state, ['sentAt' => now()->toIso8601String()]);

        broadcast(new RobotStatusUpdated($payload));

        $this->writeToInfluxDB($payload);
    }

    private function writeToInfluxDB(array $payload): void
    {
        $navIndex = self::NAV_STATE_INDEX[$payload['state']] ?? 0;
        $timestamp = (int) (microtime(true) * 1_000_000_000);

        $line = "robot_metrics,robot={$payload['id']}"
            . " battery={$payload['battery']}i"
            . ",nav_state={$navIndex}i"
            . " {$timestamp}";

        Http::withHeaders([
            'Authorization' => 'Token ' . config('services.influxdb.token'),
        ])
        ->withBody($line, 'text/plain')
        ->post(config('services.influxdb.url') . '/api/v2/write?' . http_build_query([
            'org'       => config('services.influxdb.org'),
            'bucket'    => config('services.influxdb.bucket'),
            'precision' => 'ns',
        ]));
    }
}
