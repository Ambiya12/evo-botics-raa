import { useState } from 'react';
import AuthenticatedLayout from '@/Layouts/AuthenticatedLayout';
import Modal from '@/Components/Modal';
import PrimaryButton from '@/Components/PrimaryButton';
import SecondaryButton from '@/Components/SecondaryButton';
import { Head } from '@inertiajs/react';
import { useTranslation } from '@/hooks/useTranslation';

/*
TODO: Replace mock data with BDD
  1. php artisan make:model Reservation -m
     - table: user_id, date, heure_debut, heure_fin, status (pending/confirmed/cancelled/expired)
     - Model: Reservation belongsTo User, User hasMany Reservation
  2. routes/web.php — pass real data:
       Route::get('/dashboard', function () {
           return Inertia::render('Dashboard', [
               'reservations' => auth()->user()->reservations,
           ]);
       })->middleware(['auth', 'verified'])->name('dashboard');
  3. Dashboard.tsx:
     - Remove useState mock & cancelReservation (local filter)
     - Import usePage from @inertiajs/react
     - Use: const { reservations } = usePage().props
     - Wire Cancel button to: router.patch(route('reservations.cancel', id))
  4. app/Livewire/Reservation.php — persist on book:
       auth()->user()->reservations()->create([...])
  5. Create PATCH /reservations/{id}/cancel route + Controller
*/

export default function Dashboard() {
    const { t } = useTranslation();
    const [reservations, setReservations] = useState([
        { id: 1, date: '07/13/26', heure_debut: '10:00', heure_fin: '15:00', status: 'confirmed' },
        { id: 2, date: '07/14/26', heure_debut: '14:00', heure_fin: '17:00', status: 'pending' },
        { id: 3, date: '06/28/26', heure_debut: '09:00', heure_fin: '11:00', status: 'cancelled' },
        { id: 4, date: '05/20/26', heure_debut: '13:00', heure_fin: '14:00', status: 'expired' },
    ]);
    const [confirmCancelId, setConfirmCancelId] = useState<number | null>(null);

    const cancelReservation = (id: number) => {
        setReservations((prev) => prev.filter((r) => r.id !== id));
        setConfirmCancelId(null);
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

            {reservations.map((item) => (
                <div key={item.id} className="py-3">
                    <div className="mx-auto max-w-7xl sm:px-6 lg:px-8">
                        <div className="overflow-hidden bg-white shadow-sm sm:rounded-lg">
                            <div className="p-6 text-gray-900">
                                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                                    <div className="flex items-center gap-4">
                                        <div className={`flex h-12 w-12 items-center justify-center rounded-full ${
                                            item.status === 'confirmed' ? 'bg-green-100' :
                                            item.status === 'pending' ? 'bg-yellow-100' :
                                            item.status === 'cancelled' ? 'bg-red-100' : 'bg-gray-100'
                                        }`}>
                                            <svg className={`h-6 w-6 ${
                                                item.status === 'confirmed' ? 'text-green-600' :
                                                item.status === 'pending' ? 'text-yellow-600' :
                                                item.status === 'cancelled' ? 'text-red-600' : 'text-gray-400'
                                            }`} fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                                <path stroke-linecap="round" stroke-linejoin="round" d="M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 012.25-2.25h13.5A2.25 2.25 0 0121 7.5v11.25m-18 0A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75m-18 0v-7.5A2.25 2.25 0 015.25 9h13.5A2.25 2.25 0 0121 11.25v7.5" />
                                            </svg>
                                        </div>
                                        <div>
                                            <div className="flex items-center gap-3">
                                                <p className="text-base font-semibold text-gray-900">{item.date}</p>
                                                <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                                                    item.status === 'confirmed'
                                                        ? 'bg-green-100 text-green-700'
                                                        : item.status === 'pending'
                                                        ? 'bg-yellow-100 text-yellow-700'
                                                        : item.status === 'cancelled'
                                                        ? 'bg-red-100 text-red-700'
                                                        : 'bg-gray-100 text-gray-500'
                                                }`}>
                                                    {t(item.status === 'confirmed' ? 'Confirmed' :
                                                       item.status === 'pending' ? 'Pending' :
                                                       item.status === 'cancelled' ? 'Cancelled' : 'Expired')}
                                                </span>
                                            </div>
                                            <p className="mt-0.5 text-sm text-gray-500">
                                                <svg className="mr-1 inline h-4 w-4" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                                                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                </svg>
                                                {item.heure_debut} — {item.heure_fin}
                                            </p>
                                        </div>
                                    </div>
                                    {(item.status === 'confirmed' || item.status === 'pending') && (
                                        <PrimaryButton disabled={false} onClick={() => setConfirmCancelId(item.id)}>
                                            {t('Cancel')}
                                        </PrimaryButton>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            ))}

            <Modal show={confirmCancelId !== null} onClose={() => setConfirmCancelId(null)}>
                <div className="p-6">
                    <h2 className="text-lg font-medium text-gray-900">
                        {t('Cancel this booking?')}
                    </h2>
                    <p className="mt-1 text-sm text-gray-600">
                        {t('This action cannot be undone.')}
                    </p>
                    <div className="mt-6 flex justify-end gap-3">
                        <SecondaryButton onClick={() => setConfirmCancelId(null)}>
                            {t('No')}
                        </SecondaryButton>
                        <PrimaryButton
                            disabled={false}
                            onClick={() => confirmCancelId !== null && cancelReservation(confirmCancelId)}
                        >
                            {t('Yes, cancel')}
                        </PrimaryButton>
                    </div>
                </div>
            </Modal>
        </AuthenticatedLayout>
    );
}
