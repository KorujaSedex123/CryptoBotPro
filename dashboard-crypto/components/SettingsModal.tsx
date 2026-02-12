"use client";
import { Brain, RefreshCcw, X } from "lucide-react";
import { useState } from "react";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  configs: any;
  onSave: (key: string, val: string) => void;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SettingsModal({ isOpen, onClose, configs, onSave }: SettingsModalProps) {
  const [aiRec, setAiRec] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const runSim = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/ai-simulation`);
      setAiRec(await res.json());
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-lg p-6 overflow-y-auto animate-in fade-in zoom-in-95 flex items-center justify-center">
      <div className="w-full max-w-md bg-zinc-900 border border-zinc-800 rounded-3xl p-6 shadow-2xl">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Brain className="text-purple-500" /> Configurações
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-white/5 rounded-full"><X size={20} /></button>
        </div>

        <div className="space-y-6">
          <div>
            <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2 block">Perfil de Risco</label>
            <div className="grid grid-cols-3 gap-2 mb-3">
              {['conservador', 'moderado', 'agressivo'].map(p => (
                <button
                  key={p}
                  onClick={() => onSave('perfil_risco', p)}
                  className={`py-3 rounded-xl border text-[10px] font-black uppercase transition-all ${
                    configs.perfil_risco === p 
                      ? 'bg-purple-500 text-white border-purple-500 shadow-lg shadow-purple-500/20' 
                      : 'bg-black border-zinc-800 text-zinc-500 hover:border-zinc-700'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
            
            <button 
              onClick={runSim} 
              disabled={loading}
              className="w-full py-3 border border-dashed border-zinc-700 text-zinc-400 rounded-xl text-xs font-bold hover:bg-white/5 flex items-center justify-center gap-2"
            >
              {loading ? <RefreshCcw className="animate-spin" size={14} /> : "IA: Qual o melhor perfil hoje?"}
            </button>

            {aiRec && (
              <div className="mt-3 p-4 bg-gradient-to-br from-purple-500/10 to-blue-500/10 border border-purple-500/20 rounded-xl">
                <div className="flex justify-between text-[10px] font-black text-purple-400 uppercase mb-1">
                  <span>Recomendação: {aiRec.recomendacao}</span>
                  <span>Volatilidade: {aiRec.volatilidade_detectada}</span>
                </div>
                <p className="text-[11px] text-zinc-400">{aiRec.analise}</p>
                <button 
                  onClick={() => onSave('perfil_risco', aiRec.recomendacao.toLowerCase())}
                  className="w-full mt-3 py-2 bg-purple-500 text-white text-[10px] font-black rounded-lg"
                >
                  Aplicar {aiRec.recomendacao}
                </button>
              </div>
            )}
          </div>

          <div className="pt-6 border-t border-zinc-800">
             <label className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-2 block">Produção (API Keys)</label>
             <input type="password" placeholder="Binance API Key" className="w-full bg-black border border-zinc-800 rounded-xl p-3 text-xs mb-2 focus:border-purple-500 outline-none transition-colors" />
             <input type="password" placeholder="Binance Secret" className="w-full bg-black border border-zinc-800 rounded-xl p-3 text-xs mb-4 focus:border-purple-500 outline-none transition-colors" />
             
             <div className="flex items-center justify-between p-3 bg-red-500/10 border border-red-500/20 rounded-xl">
               <span className="text-[10px] font-black text-red-400 uppercase">Modo Dinheiro Real</span>
               <div className="relative inline-block w-10 mr-2 align-middle select-none transition duration-200 ease-in">
                  <input type="checkbox" name="toggle" id="toggle" className="toggle-checkbox absolute block w-5 h-5 rounded-full bg-white border-4 appearance-none cursor-pointer"/>
                  <label htmlFor="toggle" className="toggle-label block overflow-hidden h-5 rounded-full bg-gray-300 cursor-pointer"></label>
               </div>
             </div>
          </div>
        </div>
      </div>
    </div>
  );
}