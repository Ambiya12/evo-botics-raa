import Modal from '@/Components/Modal';
import PrimaryButton from '@/Components/PrimaryButton';
import DangerButton from '@/Components/DangerButton';
import SecondaryButton from '@/Components/SecondaryButton';

export interface PendingChange {
    userId: number;
    userName: string;
    nextRole: 'user' | 'admin';
}

interface ConfirmRoleChangeModalProps {
    pending: PendingChange | null;
    processing: boolean;
    onConfirm: () => void;
    onCancel: () => void;
}

export default function ConfirmRoleChangeModal({
    pending,
    processing,
    onConfirm,
    onCancel,
}: ConfirmRoleChangeModalProps) {
    const promoting = pending?.nextRole === 'admin';

    return (
        <Modal show={pending !== null} onClose={onCancel} maxWidth="md">
            <div className="p-6">
                <h2 className="text-lg font-semibold text-gray-900">
                    {promoting ? 'Promouvoir en administrateur' : 'Retirer les droits admin'}
                </h2>
                <p className="mt-2 text-sm text-gray-600">
                    {promoting
                        ? `Donner les droits administrateur à ${pending?.userName} ?`
                        : `Retirer les droits administrateur à ${pending?.userName} ?`}
                </p>
                <div className="mt-6 flex justify-end gap-3">
                    <SecondaryButton onClick={onCancel} disabled={processing}>
                        Annuler
                    </SecondaryButton>
                    {promoting ? (
                        <PrimaryButton onClick={onConfirm} disabled={processing}>
                            Promouvoir
                        </PrimaryButton>
                    ) : (
                        <DangerButton onClick={onConfirm} disabled={processing}>
                            Rétrograder
                        </DangerButton>
                    )}
                </div>
            </div>
        </Modal>
    );
}
