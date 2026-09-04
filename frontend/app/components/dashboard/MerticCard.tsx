type MetricCardProps = {
  label: string;
  value: string | number;
  description?: string;
};

export default function MetricCard({
  label,
  value,
  description,
}: MetricCardProps) {
  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-zinc-500">
        {label}
      </p>

      <p className="mt-2 text-2xl font-semibold text-zinc-900">
        {value}
      </p>

      {description && (
        <p className="mt-1 text-xs text-zinc-500">
          {description}
        </p>
      )}
    </div>
  );
}