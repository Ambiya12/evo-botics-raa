import type { ReactElement, ReactNode } from 'react';

export type LayoutComponent = ((props: Record<string, unknown>) => ReactElement) & {
    layout?: (page: ReactElement) => ReactNode;
};
