import { defineConfig, loadEnv } from 'vite';
import laravel from 'laravel-vite-plugin';
import react from '@vitejs/plugin-react';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig(({ mode }) => {
    const backendEnvDir = path.resolve(__dirname, '../backend');
    const env = loadEnv(mode, backendEnvDir, '');
    const appUrl = env.APP_URL || 'http://localhost';
    const adminUrl = new URL('/admin', appUrl).toString();

    return {
        envDir: '../backend',
        plugins: [
            laravel({
                input: 'src/app.tsx',
                publicDirectory: '../backend/public',
                refresh: [
                    '../backend/app/**',
                    '../backend/routes/**',
                    '../backend/resources/views/**',
                    './src/**',
                ],
            }),
            react(),
            {
                name: 'redirect-vite-root-to-laravel',
                configureServer(server) {
                    server.middlewares.use((req, res, next) => {
                        const pathname = req.url?.split('?')[0];
                        const acceptsHtml = req.headers.accept?.includes('text/html');

                        if (acceptsHtml && (pathname === '/' || pathname === '/admin')) {
                            res.statusCode = 302;
                            res.setHeader('Location', adminUrl);
                            res.end();
                            return;
                        }

                        next();
                    });
                },
            },
        ],
        resolve: {
            alias: {
                '@': path.resolve(__dirname, 'src'),
            },
        },
        server: {
            host: '0.0.0.0',
            port: 5173,
            hmr: {
                host: 'localhost',
            },
        },
    };
});
