import UserRow, { type AdminUserRow } from './UserRow';

interface UserTableProps {
    users: AdminUserRow[];
    onRequestChange: (user: AdminUserRow) => void;
}

export default function UserTable({ users, onRequestChange }: UserTableProps) {
    return (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
            <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                    <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Nom</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Email</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">Rôle</th>
                        <th className="px-4 py-3" />
                    </tr>
                </thead>
                <tbody>
                    {users.map((user) => (
                        <UserRow key={user.id} user={user} onRequestChange={onRequestChange} />
                    ))}
                </tbody>
            </table>
        </div>
    );
}
