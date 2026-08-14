import { useState } from 'react';
import { X, Send } from 'lucide-react';
import { useStore } from '../store/useStore';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  objectName: string;
  owner: string;
  contactChannel: string;
}

export default function RequestAccessModal({ isOpen, onClose, objectName, owner, contactChannel }: Props) {
  const { showToast } = useStore();
  const [form, setForm] = useState({ name: '', email: '', justification: '', level: 'Leitura' });

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onClose();
    showToast('Solicitacao de acesso enviada com sucesso!');
    setForm({ name: '', email: '', justification: '', level: 'Leitura' });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="text-lg font-semibold text-gray-800">Solicitar Acesso</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded"><X className="w-5 h-5" /></button>
        </div>

        <div className="p-5">
          <div className="bg-indigo-50 rounded-lg p-3 mb-4">
            <p className="text-sm text-indigo-800">
              <strong>Dataset:</strong> {objectName}<br />
              <strong>Responsavel:</strong> {owner}<br />
              <strong>Canal:</strong> {contactChannel}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Seu Nome</label>
              <input type="text" required value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Seu Email</label>
              <input type="email" required value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Justificativa de Uso</label>
              <textarea required rows={3} value={form.justification} onChange={e => setForm({ ...form, justification: e.target.value })}
                placeholder="Descreva por que precisa acessar estes dados..."
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none resize-none" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nivel de Acesso Desejado</label>
              <select value={form.level} onChange={e => setForm({ ...form, level: e.target.value })}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none">
                <option>Leitura</option>
                <option>Escrita</option>
              </select>
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={onClose} className="btn-secondary">Cancelar</button>
              <button type="submit" className="btn-primary flex items-center gap-2">
                <Send className="w-4 h-4" /> Enviar Solicitacao
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
