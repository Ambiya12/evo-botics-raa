export interface AuthUser {
    id: number;
    name: string;
    email: string;
    role: 'user' | 'admin';
    email_verified_at: string | null;
}

export interface SharedPageProps {
    auth: { user: AuthUser | null };
    [key: string]: unknown;
}
