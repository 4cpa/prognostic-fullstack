import Link from "next/link";
import HomeForm from "./HomeForm";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default function HomePage() {
  return (
    <main className="min-h-screen bg-slate-50">
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-6 lg:px-8">
        <div className="mb-8">
          <Link href="/" className="text-sm font-medium text-slate-600 hover:text-slate-900">
            4cpa Prognostic
          </Link>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-slate-950">
            Neue Prognosefrage anlegen
          </h1>
          <p className="mt-2 text-sm leading-6 text-slate-600">
            Frage erfassen, dann direkt einen Forecast erzeugen und zur Detailseite springen.
          </p>
        </div>

        <HomeForm />
      </div>
    </main>
  );
}
