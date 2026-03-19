interface Props {
  score: number;
  label?: string;
  showBar?: boolean;
}

function getColor(score: number) {
  if (score >= 80) return { bg: 'bg-green-500', text: 'text-green-700', badge: 'bg-green-100 text-green-800', label: 'Excelente' };
  if (score >= 60) return { bg: 'bg-yellow-500', text: 'text-yellow-700', badge: 'bg-yellow-100 text-yellow-800', label: 'Bom' };
  if (score >= 40) return { bg: 'bg-orange-500', text: 'text-orange-700', badge: 'bg-orange-100 text-orange-800', label: 'Atencao' };
  return { bg: 'bg-red-500', text: 'text-red-700', badge: 'bg-red-100 text-red-800', label: 'Critico' };
}

export default function QualityBadge({ score, label, showBar = false }: Props) {
  const c = getColor(score);

  if (showBar) {
    return (
      <div className="w-full">
        {label && (
          <div className="flex justify-between items-center mb-1">
            <span className="text-sm text-gray-600">{label}</span>
            <span className={`text-sm font-semibold ${c.text}`}>{score}%</span>
          </div>
        )}
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div className={`h-2.5 rounded-full ${c.bg} transition-all duration-500`} style={{ width: `${score}%` }} />
        </div>
      </div>
    );
  }

  return (
    <span className={`badge ${c.badge}`}>
      {score}% - {c.label}
    </span>
  );
}
