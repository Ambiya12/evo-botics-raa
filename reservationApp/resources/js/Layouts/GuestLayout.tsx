import ApplicationLogo from '@/Components/ApplicationLogo';
import { Link, usePage, router } from '@inertiajs/react';
import { useTranslation } from '@/hooks/useTranslation';
import { useState, useRef, useEffect } from 'react';

const LOCALES: Record<string, { flag: string; label: string }> = {
    en: { flag: '\u{1F1EC}\u{1F1E7}', label: 'EN' },
    fr: { flag: '\u{1F1EB}\u{1F1F7}', label: 'FR' },
    id: { flag: '\u{1F1EE}\u{1F1E9}', label: 'ID' },
    zh: { flag: '\u{1F1E8}\u{1F1F3}', label: 'CN' },
};

export default function GuestLayout({ children }) {
    const { locale } = useTranslation();
    const [langOpen, setLangOpen] = useState(false);
    const langRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const onClick = (e: MouseEvent) => {
            if (langRef.current && !langRef.current.contains(e.target as Node)) {
                setLangOpen(false);
            }
        };
        document.addEventListener('mousedown', onClick);
        return () => document.removeEventListener('mousedown', onClick);
    }, []);

    const switchLocale = (loc: string) => {
        setLangOpen(false);
        router.post('/locale', { locale: loc });
    };

    return (
        <div className="flex min-h-screen flex-col items-center bg-gray-100 pt-6 sm:justify-center sm:pt-0">
            <div ref={langRef} className="relative mb-4 self-end mr-4">
                <button onClick={() => setLangOpen(!langOpen)} type="button"
                    className="flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-sm hover:bg-gray-50 transition">
                    <span className="text-lg">{LOCALES[locale]?.flag}</span>
                    <svg className="h-3 w-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                    </svg>
                </button>

                {langOpen && (
                    <div className="absolute right-0 z-50 mt-1 min-w-[120px] rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
                        {Object.entries(LOCALES).map(([code, { flag, label }]) => (
                            <button key={code} onClick={() => switchLocale(code)}
                                className={`flex w-full items-center gap-2 px-3 py-2 text-sm transition hover:bg-gray-100 ${locale === code ? 'bg-gray-50 font-medium' : ''
                                    }`}>
                                <span>{flag} {label}</span>
                            </button>
                        ))}
                    </div>
                )}
            </div>

            <div>
                <Link href="/">
                    <ApplicationLogo className="h-20 w-20 fill-current text-gray-500" />
                </Link>
            </div>

            <div className="mt-6 w-full overflow-hidden bg-white px-6 py-4 shadow-md sm:max-w-md sm:rounded-lg">
                {children}
            </div>
        </div>
    );
}
