import PrimaryButton from '@/Components/PrimaryButton';
import DangerButton from '@/Components/DangerButton';
import RoleBadge from './RoleBadge';

export interface AdminUserRow {
    id: number;
    name: string;
    email: string;
    role: 'user' | 'admin';
    isSelf: boolean;
    isLastAdmin: boolean;
}

interface UserRowProps {
    user: AdminUserRow;
    onRequestChange: (user: AdminUserRow) => void;
}

export default function UserRow({ user, onRequestChange }: UserRowProps) {
    const isAdmin = user.role === 'admin';
    const disabled = user.isSelf || user.isLastAdmin;
    const tooltip = user.isSelf
        ? 'Vous ne pouvez pas modifier votre propre rôle.'
        : user.isLastAdmin
          ? 'Vous êtes le dernier admin.'
          : undefined;

    return (
        <tr className="border-b border-gray-100">
            <td className="px-4 py-3 text-sm text-gray-900">{user.name}</td>
            <td className="px-4 py-3 text-sm text-gray-600">{user.email}</td>
            <td className="px-4 py-3">
                <RoleBadge role={user.role} />
            </td>
            <td className="px-4 py-3 text-right">
                <span title={tooltip}>
                    {isAdmin ? (
                        <DangerButton disabled={disabled} onClick={() => onRequestChange(user)}>
                            Rétrograder
                        </DangerButton>
                    ) : (
                        <PrimaryButton disabled={disabled} onClick={() => onRequestChange(user)}>
                            Promouvoir
                        </PrimaryButton>
                    )}
                </span>
            </td>
        </tr>
    );
}
