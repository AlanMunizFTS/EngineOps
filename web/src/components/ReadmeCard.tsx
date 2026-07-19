import { BookIcon } from "./icons";

export default function ReadmeCard({
  projectName,
  description,
}: {
  projectName: string;
  description: string | null;
}) {
  return (
    <section className="rounded-md border border-ink-800 bg-ink-900">
      <div className="flex items-center gap-2 border-b border-ink-800 px-4 py-2.5">
        <BookIcon className="h-4 w-4 text-slate-500" />
        <span className="text-sm font-medium text-slate-200">README.md</span>
      </div>
      <div className="px-5 py-4">
        <h1 className="border-b border-ink-800 pb-2 text-xl font-semibold text-slate-100">
          {projectName}
        </h1>
        <p className="mt-3 text-sm text-slate-400">
          {description || "No description yet."}
        </p>
      </div>
    </section>
  );
}
