import { useState } from 'react';
import AuthenticatedLayout from '@/Layouts/AuthenticatedLayout';
import Modal from '@/Components/Modal';
import PrimaryButton from '@/Components/PrimaryButton';
import SecondaryButton from '@/Components/SecondaryButton';
import { Head, usePage, router, Link } from '@inertiajs/react';
import { useTranslation } from '@/hooks/useTranslation';

interface Reservation {
    id: number;
    uuid: string;
    status: 'pending' | 'confirmed' | 'validated' | 'cancelled' | 'expired';
    booking_session?: {
        date: string;
        start_at: string;
        end_at: string;
        room?: {
            name: string;
        }
    };
}

const STATUS_STYLES: Record<string, { circle: string; icon: string; badge: string }> = {
    confirmed: { circle: 'bg-green-100', icon: 'text-green-600', badge: 'bg-green-100 text-green-700' },
    validated: { circle: 'bg-green-100', icon: 'text-green-600', badge: 'bg-green-100 text-green-700' },
    pending:   { circle: 'bg-yellow-100', icon: 'text-yellow-600', badge: 'bg-yellow-100 text-yellow-700' },
    cancelled: { circle: 'bg-red-100', icon: 'text-red-600', badge: 'bg-red-100 text-red-700' },
    expired:   { circle: 'bg-gray-100', icon: 'text-gray-400', badge: 'bg-gray-100 text-gray-500' },
};

export default function Dashboard() {
    const { t } = useTranslation();
    const { reservations } = usePage<{ reservations: any }>().props;
    const [confirmCancelUuid, setConfirmCancelUuid] = useState<string | null>(null);

    const cancelReservation = (uuid: string) => {
        router.delete(`/reservations/${uuid}`, {
            onSuccess: () => setConfirmCancelUuid(null),
        });
    };

    return (
        <AuthenticatedLayout
            header={
                <div className="flex w-full items-center justify-between">
                    <h2 className="text-xl font-semibold leading-tight text-gray-800">
                        {t('Dashboard')}
                    </h2>
                    <a href="/reservation" className="rounded-lg bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-300">
                        {t('Book a meeting room')}
                    </a>
                </div>
            }
        >
            <Head title={t('Dashboard')} />

            {reservations.data.length === 0 ? (
                <div className="py-12 text-center text-gray-500">
                    {t('You do not have any bookings yet.')}
                </div>
            ) : (
                reservations.data.map((item: Reservation) => (
                    <div key={item.id} className="py-3">
                        <div className="mx-auto max-w-7xl sm:px-6 lg:px-8">
                            <div className="overflow-hidden bg-white shadow-sm sm:rounded-lg">
                                <div className="p-6 text-gray-900">
                                    <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                                        <div className="flex items-center gap-4">
                                            <div className={`flex h-12 w-12 items-center justify-center rounded-full ${(STATUS_STYLES[item.status] ?? STATUS_STYLES.expired).circle}`}>
                                                <svg className={`h-6 w-6 ${(STATUS_STYLES[item.status] ?? STATUS_STYLES.expired).icon}`} fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                                    <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
                                                </svg>
                                            </div>
                                            <div>
                                                <div className="flex items-center gap-3">
                                                    <p className="text-base font-semibold text-gray-900">
                                                        {item.booking_session?.date
                                                            ? item.booking_session.date.split('T')[0]
                                                            : t('No date')}
                                                    </p>
                                                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${(STATUS_STYLES[item.status] ?? STATUS_STYLES.expired).badge}`}>
                                                        {t(item.status.charAt(0).toUpperCase() + item.status.slice(1))}
                                                    </span>
                                                </div>
                                                <p className="mt-0.5 text-sm text-gray-500 flex items-center gap-1">
                                                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth="1.5" stroke="currentColor">
                                                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                    </svg>
                                                    {item.booking_session?.start_at} — {item.booking_session?.end_at}
                                                    {item.booking_session?.room?.name && (
                                                        <span className="ml-2 text-gray-400">({item.booking_session.room.name})</span>
                                                    )}
                                                </p>
                                            </div>
                                        </div>
                                        {(item.status === 'confirmed' || item.status === 'pending') && (
                                            <PrimaryButton disabled={false} onClick={() => setConfirmCancelUuid(item.uuid)}>
                                                {t('Cancel')}
                                            </PrimaryButton>
                                        )}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                ))
            )}

            {reservations.last_page > 1 && (
                <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-center gap-2">
                        {reservations.links.map((link: { url: string | null; label: string; active: boolean }, i: number) => (
                            link.url ? (
                                <Link
                                    key={i}
                                    href={link.url}
                                    preserveState
                                    preserveScroll
                                    className={`px-3 py-1.5 text-sm rounded-md border transition ${
                                        link.active
                                            ? 'bg-blue-600 text-white border-blue-600'
                                            : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                                    }`}
                                    dangerouslySetInnerHTML={{ __html: link.label }}
                                />
                            ) : (
                                <span
                                    key={i}
                                    className="px-3 py-1.5 text-sm rounded-md border border-gray-200 bg-gray-100 text-gray-400 cursor-not-allowed"
                                    dangerouslySetInnerHTML={{ __html: link.label }}
                                />
                            )
                        ))}
                    </div>
                </div>
            )}

            <Modal show={confirmCancelUuid !== null} onClose={() => setConfirmCancelUuid(null)}>
                <div className="p-6">
                    <h2 className="text-lg font-medium text-gray-900">
                        {t('Cancel this booking?')}
                    </h2>
                    <p className="mt-1 text-sm text-gray-600">
                        {t('This action cannot be undone.')}
                    </p>
                    <div className="mt-6 flex justify-end gap-3">
                        <SecondaryButton onClick={() => setConfirmCancelUuid(null)}>
                            {t('No')}
                        </SecondaryButton>
                        <PrimaryButton
                            disabled={false}
                            onClick={() => confirmCancelUuid !== null && cancelReservation(confirmCancelUuid)}
                        >
                            {t('Yes, cancel')}
                        </PrimaryButton>
                    </div>
                </div>
            </Modal>
        </AuthenticatedLayout>
    );
}
