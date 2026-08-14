import { useState } from 'react';
import { X, AlertTriangle } from 'lucide-react';
import { useStore } from '../store/useStore';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  objectName: string;
}

export default function ReportProblemModal({ isOpen, onClose, objectName }: Props) {
  const { showToast } = useStore();
  const [form, setForm] = useState({ type: 'Dados incorretos', description: '', urgency: 'Media' });

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onClose();
    showToast('Problema reportado com sucesso! A equipe responsavel sera notificada.');
    setForm({ type: 'Dados incorretos', description: '', urgency: 'Media' });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-500" /> Reportar Problema
          </h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded"><X className="w-5 h-5" /></button>
        </div>

        <div className="p-5">
          <p className="text-sm text-gray-600 mb-4">Reportando problema em: <strong>{objectName}</strong></p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tipo de Problema</label>
              <select value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none">
                <option>Dados incorretos</option>
                <option>Dados desatualizados</option>
                <option>Descricao incompleta</option>
                <option>Problema de acesso</option>
                <option>Problema de performance</option>
                <option>Outro</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Descricao</label>
              <textarea required rows={3} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })}
                placeholder="Descreva o problema encontrado..."
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Urgencia</label>
              <select value={form.urgency} onChange={e => setForm({ ...form, urgency: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none">
                <option>Baixa</option>
                <option>Media</option>
                <option>Alta</option>
                <option>Critica</option>
              </select>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
              <button type="submit" className="btn-primary flex items-center gap-2">
                <AlertTriangle className="w-4 h-4" /> Enviar Report
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
