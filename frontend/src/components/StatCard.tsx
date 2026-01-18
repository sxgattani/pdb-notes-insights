interface StatCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  onClick?: () => void;
}

export function StatCard({ title, value, subtitle, onClick }: StatCardProps) {
  return (
    <div
      className={`bg-white rounded-lg shadow p-6 ${onClick ? 'cursor-pointer hover:shadow-lg transition-shadow' : ''}`}
      onClick={onClick}
    >
      <h3 className="text-sm font-medium text-gray-500">{title}</h3>
      <p className="mt-2 text-3xl font-semibold text-gray-900">{value}</p>
      {subtitle && <p className="mt-1 text-sm text-gray-500">{subtitle}</p>}
    </div>
  );
}
