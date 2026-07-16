import { Head, router, useForm, usePage } from '@inertiajs/react';
import { FormEvent, useState, useMemo } from 'react';
import AuthenticatedLayout from '@/Layouts/AuthenticatedLayout';
import { useTranslation } from '@/hooks/useTranslation';

interface SessionRow {
    id: number;
    date: string;
    start_at: string;
    end_at: string;
    room_name: string;
    is_available: boolean;
}

interface RoomOption {
    id: number;
    name: string;
}

interface SessionsPageProps {
    sessions: SessionRow[];
    rooms: RoomOption[];
    flash?: { success?: string | null };
    [key: string]: unknown;
}

export default function Index() {
    const { t } = useTranslation();
    const { sessions, rooms, flash } = usePage<SessionsPageProps>().props;
    const { locale } = usePage<{ locale: string }>().props;

    const [filterRoom, setFilterRoom] = useState<string>('all');
    const [filterStatus, setFilterStatus] = useState<string>('all');
    const [sortBy, setSortBy] = useState<'date' | 'time'>('date');
    const [dateOrder, setDateOrder] = useState<'asc' | 'desc'>('asc');
    const [timeOrder, setTimeOrder] = useState<'asc' | 'desc'>('asc');

    const { data, setData, post, processing, reset, errors } = useForm({
        room_id: '',
        date: '',
        start_at: '09:00',
        end_at: '10:00',
    });

    const handleSubmit = (e: FormEvent) => {
        e.preventDefault();
        post(route('admin.sessions.store'), {
            onSuccess: () => reset(),
        });
    };

    const handleDelete = (id: number) => {
        if (confirm(t('Êtes-vous sûr de vouloir supprimer cette session ?'))) {
            router.delete(route('admin.sessions.destroy', id), {
                preserveScroll: true,
            });
        }
    };

    const processedSessions = useMemo(() => {
        let result = [...sessions];

        if (filterRoom !== 'all') {
            result = result.filter(session => session.room_name === filterRoom);
        }

        if (filterStatus === 'available') {
            result = result.filter(session => session.is_available === true);
        } else if (filterStatus === 'occupied') {
            result = result.filter(session => session.is_available === false);
        }

        result.sort((a, b) => {
            if (sortBy === 'date') {
                const dateA = new Date(a.date).getTime();
                const dateB = new Date(b.date).getTime();
                return dateOrder === 'asc' ? dateA - dateB : dateB - dateA;
            } else {
                return timeOrder === 'asc'
                    ? a.start_at.localeCompare(b.start_at)
                    : b.start_at.localeCompare(a.start_at);
            }
        });

        return result;
    }, [sessions, filterRoom, filterStatus, sortBy, dateOrder, timeOrder]);

    return (
        <AuthenticatedLayout
            header={<h2 className="text-xl font-semibold leading-tight text-gray-800">{t('Gestion des Sessions')}</h2>}>
            <Head title="Sessions de Réservation" />

            <div className="py-8">
                <div className="mx-auto max-w-7xl space-y-8 px-4 sm:px-6 lg:px-8">

                    {flash?.success && (
                        <div className="rounded-lg bg-emerald-50 px-4 py-3 text-sm text-emerald-800 ring-1 ring-emerald-200">
                            {flash.success}
                        </div>
                    )}

                    <div className="rounded-xl bg-white p-6 shadow-sm border border-gray-100">
                        <h3 className="text-lg font-bold text-gray-900 mb-4">{t('Créer un nouveau créneau de session')}</h3>
                        <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-4 items-end">
                            <div>
                                <label className="block text-sm font-medium text-gray-700">Salle</label>
                                <select value={data.room_id} onChange={(e) => setData('room_id', e.target.value)}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                                    required>
                                    <option value="">-- {t('Choisir une salle')} --</option>
                                    {rooms.map((room) => (
                                        <option key={room.id} value={room.id}>{room.name}</option>
                                    ))}
                                </select>
                                {errors.room_id && <p className="text-xs text-red-500 mt-1">{errors.room_id}</p>}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">{t('Date')}</label>
                                <input type="date" value={data.date} onChange={(e) => setData('date', e.target.value)}
                                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                                    required />
                                {errors.date && <p className="text-xs text-red-500 mt-1">{errors.date}</p>}
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-700">{t('Heure début / fin')}</label>
                                <div className="flex gap-2 items-center">
                                    <input type="time" value={data.start_at} onChange={(e) => setData('start_at', e.target.value)}
                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                                        required />
                                    <span>à</span>
                                    <input type="time" value={data.end_at} onChange={(e) => setData('end_at', e.target.value)}
                                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                                        required />
                                </div>
                                {(errors.start_at || errors.end_at) && (
                                    <p className="text-xs text-red-500 mt-1">{errors.start_at || errors.end_at}</p>
                                )}
                            </div>

                            <div>
                                <button type="submit" disabled={processing}
                                    className="w-full inline-flex justify-center rounded-md border border-transparent bg-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-400">
                                    {processing ? 'Ajout...' : t('Ajouter le créneau')}
                                </button>
                            </div>
                        </form>
                    </div>

                    <div className="flex flex-wrap items-center justify-between gap-4 bg-gray-50 p-4 rounded-xl border border-gray-200">
                        <div className="flex flex-wrap items-center gap-4">
                            <div>
                                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">{t('Filtrer par salle')}</label>
                                <select value={filterRoom} onChange={(e) => setFilterRoom(e.target.value)}
                                    className="block w-48 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm">
                                    <option value="all">{t('Toutes les salles')}</option>
                                    {rooms.map((room) => (
                                        <option key={room.id} value={room.name}>{room.name}</option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">{t('Filtrer par statut')}</label>
                                <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}
                                    className="block w-48 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm">
                                    <option value="all">{t('Tous les statuts')}</option>
                                    <option value="available">{t('Disponible')}</option>
                                    <option value="occupied">Occupée</option>
                                </select>
                            </div>
                        </div>

                        <div className="flex flex-wrap items-center gap-4">
                            <div>
                                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">{t('Trier par date')}</label>
                                <select
                                    value={sortBy === 'date' ? dateOrder : 'none'}
                                    onChange={(e) => {
                                        if (e.target.value !== 'none') {
                                            setSortBy('date');
                                            setDateOrder(e.target.value as 'asc' | 'desc');
                                        }
                                    }}
                                    className="block w-48 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm font-medium"
                                >
                                    <option value="none" disabled={sortBy === 'date'}>-- {t("Choisir l'ordre")} --</option>
                                    <option value="asc">{t('Du plus tôt au plus tard')} 📅</option>
                                    <option value="desc">{t('Du plus tard au plus tôt')} ➔</option>
                                </select>
                            </div>

                            <div>
                                <label className="block text-xs font-semibold uppercase tracking-wider text-gray-500 mb-1">{t('Trier par horaires')}</label>
                                <select value={sortBy === 'time' ? timeOrder : 'none'}
                                    onChange={(e) => {
                                        if (e.target.value !== 'none') {
                                            setSortBy('time');
                                            setTimeOrder(e.target.value as 'asc' | 'desc');
                                        }
                                    }}
                                    className="block w-48 rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm font-medium"
                                >
                                    <option value="none" disabled={sortBy === 'time'}>-- {t("Choisir l'ordre")} --</option>
                                    <option value="asc">{t("Le matin d'abord")} ⏰</option>
                                    <option value="desc">{t("L'après-midi d'abord")} ➔</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <div className="overflow-hidden rounded-xl bg-white shadow-sm border border-gray-100">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">{t('Salle')}</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">{t('Date')}</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">{t('Horaires')}</th>
                                    <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">{t('Statut')}</th>
                                    <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">{t('Action')}</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-gray-200 bg-white">
                                {processedSessions.length === 0 ? (
                                    <tr>
                                        <td colSpan={6} className="px-6 py-10 text-center text-sm text-gray-500">
                                            {t('Aucune session ne correspond à vos filtres')}.
                                        </td>
                                    </tr>
                                ) : (
                                    processedSessions.map((session) => (
                                        <tr key={session.id}>
                                            <td className="whitespace-nowrap px-6 py-4 text-sm font-semibold text-gray-900">{session.room_name}</td>
                                            <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                                                {new Date(session.date).toLocaleDateString(locale, { day: 'numeric', month: 'short', year: 'numeric' })}
                                            </td>
                                            <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-600">
                                                {session.start_at} — {session.end_at}
                                            </td>
                                            <td className="whitespace-nowrap px-6 py-4 text-sm">
                                                {session.is_available ? (
                                                    <span className="inline-flex rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-semibold text-green-800">
                                                        {t('Disponible')}
                                                    </span>
                                                ) : (
                                                    <span className="inline-flex rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800">
                                                        {t('Occupée')}
                                                    </span>
                                                )}
                                            </td>
                                            <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-medium">
                                                <button onClick={() => handleDelete(session.id)}
                                                    className="text-red-600 hover:text-red-900 transition">
                                                    {t('Supprimer')}
                                                </button>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>

                </div>
            </div>
        </AuthenticatedLayout>
    );
}