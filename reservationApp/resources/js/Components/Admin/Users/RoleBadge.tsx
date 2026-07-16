interface RoleBadgeProps {
    role: 'user' | 'admin';
}

export default function RoleBadge({ role }: RoleBadgeProps) {
    const isAdmin = role === 'admin';
    const classes = isAdmin
        ? 'bg-emerald-100 text-emerald-800 ring-emerald-200'
        : 'bg-gray-100 text-gray-700 ring-gray-200';

    return (
        <span className={`rounded-full px-2 py-1 text-xs font-semibold ring-1 ${classes}`}>
            {isAdmin ? 'Admin' : 'User'}
        </span>
    );
}
