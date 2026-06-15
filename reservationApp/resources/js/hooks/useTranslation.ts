import { usePage } from '@inertiajs/react';

interface PageProps {
    auth: { user: any };
    locale: string;
    translations: Record<string, Record<string, string>>;
    [key: string]: any;
}

export function useTranslation() {
    const { locale, translations } = usePage<PageProps>().props;

    const t = (key: string, replace?: Record<string, string | number>): string => {
        const dict = translations?.[locale] ?? {};
        let str = dict[key] ?? key;
        if (replace) {
            for (const [k, v] of Object.entries(replace)) {
                str = str.replace(`:${k}`, String(v));
            }
        }
        return str;
    };

    return { t, locale };
}
