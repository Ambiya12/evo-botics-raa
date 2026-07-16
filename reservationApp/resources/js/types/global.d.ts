export {};

declare global {
    function route(
        name?: string,
        params?: unknown,
        absolute?: boolean,
    ): string & {
        current(name?: string, params?: unknown): boolean;
    };
}
