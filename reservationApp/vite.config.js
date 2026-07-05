import { defineConfig, loadEnv } from 'vite';
import laravel from 'laravel-vite-plugin';
import react from '@vitejs/plugin-react';

function hostFromUrl(url) {
    if (!url) {
        return undefined;
    }

    try {
        return new URL(url).hostname;
    } catch {
        return undefined;
    }
}

function unique(values) {
    return values.filter((value, index) => value && values.indexOf(value) === index);
}

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, process.cwd(), '');
    const appHost = env.VITE_HMR_HOST || env.APP_HOST || hostFromUrl(env.APP_URL);
    const vitePort = Number(env.VITE_PORT || 5173);
    const appPort = Number(env.APP_PORT || 8000);
    const appOrigins = unique([
        `http://localhost:${appPort}`,
        `http://127.0.0.1:${appPort}`,
        appHost ? `http://${appHost}:${appPort}` : undefined,
    ]);

    return {
        plugins: [
            laravel({
                input: [
                    'resources/js/app.tsx',
                    'resources/js/app.js',
                    'resources/css/app.css',
                ],
                refresh: true,
            }),
            react(),
        ],
        server: {
            host: '0.0.0.0',
            port: vitePort,
            strictPort: true,
            origin: appHost ? `http://${appHost}:${vitePort}` : undefined,
            cors: {
                origin: appOrigins,
            },
            hmr: appHost ? { host: appHost, port: vitePort } : undefined,
        },
    };
});
