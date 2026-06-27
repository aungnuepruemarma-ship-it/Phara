import nextDynamic from 'next/dynamic';
const Page = nextDynamic(() => import('./page-client'), { ssr: false });
export const dynamic = 'force-static';
export function generateStaticParams() { return [{ id: '_' }]; }
export default Page;
