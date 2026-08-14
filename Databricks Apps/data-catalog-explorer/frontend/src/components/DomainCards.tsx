import { useNavigate } from 'react-router-dom';
import { dataObjects } from '../data/catalog';
import { domainConfig } from '../data/catalog';
import type { Domain } from '../types';

export default function DomainCards() {
  const navigate = useNavigate();

  const domainCounts = dataObjects.reduce<Record<string, number>>((acc, obj) => {
    if (obj.status === 'ACTIVE') {
      acc[obj.domain] = (acc[obj.domain] || 0) + 1;
    }
    return acc;
  }, {});

  const domains = Object.entries(domainCounts).sort((a, b) => b[1] - a[1]);

  const handleClick = (domain: Domain) => {
    navigate(`/busca?q=&domain=${domain}`);
  };

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
      {domains.map(([domain, count]) => {
        const cfg = domainConfig[domain] || { icon: '\u{1F4CA}', color: 'bg-gray-100 text-gray-800' };
        return (
          <button
            key={domain}
            onClick={() => handleClick(domain as Domain)}
            className="card hover:shadow-md transition-all hover:border-indigo-200 text-left group"
          >
            <div className="text-2xl mb-2">{cfg.icon}</div>
            <div className="font-semibold text-gray-800 group-hover:text-indigo-600 transition-colors">{domain}</div>
            <div className="text-sm text-gray-500">{count} dataset{count !== 1 ? 's' : ''}</div>
          </button>
        );
      })}
    </div>
  );
}
