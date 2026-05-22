# Frontend

React, TypeScript, Vite, and Tailwind source for the reservation app.

The frontend is connected to Laravel through `laravel-vite-plugin` in `vite.config.js`. In development, Laravel loads assets from the Vite dev server. In production, `npm run build` writes the manifest and compiled assets to `../backend/public/build`.

Do not open the Vite URL directly (`http://localhost:5173`). It only serves frontend assets and hot reload. Open the Laravel route instead:

```text
http://localhost:8000/admin
```

With Docker/Sail, use:

```text
http://localhost/admin
```

## Commands

```bash
npm install
npm run dev
npm run build
npm run test
```
