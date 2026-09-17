export default function EmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="max-w-md text-center p-6">
      <h3 className="text-sm font-semibold text-[var(--text)]">{title}</h3>
      <p className="mt-2 text-sm text-[var(--text-3)]">{description}</p>
    </div>
  );
}
