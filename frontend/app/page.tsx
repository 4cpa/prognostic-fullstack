import HomeForm from "./HomeForm";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default function HomePage() {
  return (
    <main
      id="main-content"
      className="flex min-h-screen flex-col items-center justify-center bg-slate-50 px-4"
    >
      <div className="w-full max-w-2xl">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold tracking-tight text-slate-950">
            4cpa Prognostic
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            Frage stellen — Forecast erhalten
          </p>
        </div>

        {/* Formular */}
        <HomeForm />
      </div>
    </main>
  );
}
