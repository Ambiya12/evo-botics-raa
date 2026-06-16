import { Head, router, usePage } from '@inertiajs/react';
import { useState } from 'react';
import AuthenticatedLayout from '@/Layouts/AuthenticatedLayout';
import UserTable from '@/Components/Admin/Users/UserTable';
import ConfirmRoleChangeModal, { type PendingChange } from '@/Components/Admin/Users/ConfirmRoleChangeModal';
import { type AdminUserRow } from '@/Components/Admin/Users/UserRow';

interface UsersPageProps {
    users: AdminUserRow[];
    flash?: { success?: string | null };
    [key: string]: unknown;
}

export default function Index() {
    const { users, flash } = usePage<UsersPageProps>().props;
    const [pending, setPending] = useState<PendingChange | null>(null);
    const [processing, setProcessing] = useState(false);

    const requestChange = (user: AdminUserRow) => {
        setPending({
            userId: user.id,
            userName: user.name,
            nextRole: user.role === 'admin' ? 'user' : 'admin',
        });
    };

    const confirm = () => {
        if (!pending) return;
        setProcessing(true);
        router.patch(
            route('admin.users.role.update', pending.userId),
            { role: pending.nextRole },
            {
                preserveScroll: true,
                onFinish: () => {
                    setProcessing(false);
                    setPending(null);
                },
            },
        );
    };

    return (
        <AuthenticatedLayout
            header={<h2 className="text-xl font-semibold leading-tight text-gray-800">Utilisateurs</h2>}
        >
            <Head title="Utilisateurs" />

            <div className="py-8">
                <div className="mx-auto max-w-7xl space-y-4 px-4 sm:px-6 lg:px-8">
                    {flash?.success && (
                        <div className="rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-800 ring-1 ring-emerald-200">
                            {flash.success}
                        </div>
                    )}

                    <UserTable users={users} onRequestChange={requestChange} />
                </div>
            </div>

            <ConfirmRoleChangeModal
                pending={pending}
                processing={processing}
                onConfirm={confirm}
                onCancel={() => setPending(null)}
            />
        </AuthenticatedLayout>
    );
}
