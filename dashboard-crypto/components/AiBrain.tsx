"use client";
import { useEffect, useState } from "react";
import { Brain, Zap, Activity, TrendingUp, BarChart3, CheckCircle, ShieldAlert } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Interface para receber o marketPrice do page.tsx
interface AiBrainProps {
  symbol: string;
  marketPrice: number;
}

export default function AiBrain({ symbol, marketPrice }: AiBrainProps) {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [botInfo, setBotInfo] = useState<any>(null);

  const fetchBrain = async () => {
    try {
      const res = await fetch(`${API_URL}/ia-status?symbol=${symbol}`);
      const json = await res.json();
      setData(json);
      setLoading(false);
    } catch (error) {
      console.error("Erro ao procurar dados da IA:", error);
    }
  };

  const fetchBotInfo = async () => {
    try {
      const resBot = await fetch(`${API_URL}/status-bot?symbol=${symbol}`);
      const jsonBot = await resBot.json();
      setBotInfo(jsonBot);
    } catch (error) {
      console.error("Erro ao buscar status do bot:", error);
    }
  }

  useEffect(() => {
    fetchBrain();
    fetchBotInfo();
    const interval = setInterval(() => {
      fetchBrain();
      fetchBotInfo();
    }, 2000);
    return () => clearInterval(interval);
  }, [symbol]);

  // Constantes de Análise
  const score = data?.potencial || 0;
  const rsi = data?.rsi || 50;
  const decisao = data?.decisao || "AGUARDAR";

  // Lógica da Barra de Risco
  const precoStop = botInfo?.preco_stop || 0;
  const distanciaStop = marketPrice > 0 && precoStop > 0 
    ? ((marketPrice - precoStop) / marketPrice) * 100 
    : 0;

  const getScoreColor = (s: number) => {
    if (s >= 6) return "text-emerald-400";
    if (s >= 4) return "text-yellow-400";
    return "text-red-400";
  };

  const getBarColor = (s: number) => {
    if (s >= 6) return "bg-emerald-500";
    if (s >= 4) return "bg-yellow-500";
    return "bg-red-500";
  };

  if (loading) return <div className="animate-pulse h-48 bg-zinc-900 rounded-2xl border border-zinc-800"></div>;

  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-5 backdrop-blur-sm relative overflow-hidden group">
      
      {/* Efeito Visual de Score Alto */}
      {score >= 6 && (
        <div className="absolute -top-10 -right-10 w-32 h-32 bg-emerald-500/10 rounded-full blur-3xl animate-pulse"></div>
      )}

      {/* HEADER */}
      <div className="flex justify-between items-center mb-6 relative z-10">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-purple-500/10 rounded-lg">
            <Brain className="text-purple-400" size={20} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-zinc-200 uppercase tracking-tighter">Neural Engine V5.3</h3>
            <p className="text-[10px] text-zinc-500 font-mono">{symbol}</p>
          </div>
        </div>

        <div className={`px-3 py-1 rounded-full border text-[10px] font-black tracking-widest ${
          decisao === "COMPRA" ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" : 
          decisao === "OBSERVAÇÃO" ? "bg-orange-500/10 border-orange-500/30 text-orange-400" :
          "bg-zinc-800 border-zinc-700 text-zinc-500"
        }`}>
          <span className="flex items-center gap-1">
            {decisao === "COMPRA" ? <Zap size={12} fill="currentColor" /> : <Activity size={12} />}
            {decisao}
          </span>
        </div>
      </div>

      {/* GRID DE INDICADORES */}
      <div className="grid grid-cols-3 gap-4 relative z-10 mb-6">
        <div className="bg-black/30 p-3 rounded-xl border border-white/5 flex flex-col justify-between">
          <span className="text-[9px] text-zinc-500 uppercase font-black flex items-center gap-1">
            <Activity size={10} /> RSI (1M)
          </span>
          <div className={`text-xl font-mono font-bold mt-1 ${rsi < 35 ? "text-emerald-400" : rsi > 70 ? "text-red-400" : "text-zinc-300"}`}>
            {rsi.toFixed(1)}
          </div>
          <div className="w-full h-1 bg-zinc-800 rounded-full mt-2 overflow-hidden">
            <div className={`h-full ${rsi < 35 ? "bg-emerald-500" : "bg-purple-500"}`} style={{ width: `${rsi}%` }}></div>
          </div>
        </div>

        <div className="bg-black/30 p-3 rounded-xl border border-white/5 col-span-2 flex flex-col justify-between">
          <span className="text-[9px] text-zinc-500 uppercase font-black flex items-center gap-1">
            <BarChart3 size={10} /> Score de Potencial
          </span>
          <div className="flex items-end gap-2 mt-1">
            <div className={`text-3xl font-bold ${getScoreColor(score)}`}>
              {score.toFixed(0)}<span className="text-sm text-zinc-600">/10</span>
            </div>
            <div className="flex-1 flex gap-1 mb-2">
              {[...Array(10)].map((_, i) => (
                <div key={i} className={`h-1.5 flex-1 rounded-full transition-all duration-500 ${i < score ? getBarColor(score) : "bg-zinc-800"}`}></div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* --- MONITOR DE RISCO (EXIBIDO APENAS QUANDO POSICIONADO) --- */}
      {botInfo?.posicionado && (
        <div className="mt-4 pt-4 border-t border-white/5 animate-in slide-in-from-bottom-2 duration-500">
          <div className="flex justify-between items-end mb-2">
            <div>
              <span className="text-[9px] text-zinc-500 uppercase font-black tracking-widest flex items-center gap-1">
                <ShieldAlert size={10} className="text-red-500" /> Gatilho de Saída
              </span>
              <div className="text-xs font-bold text-zinc-300">
                Stop em: <span className="text-red-400 font-mono">R$ {precoStop.toLocaleString()}</span>
              </div>
            </div>
            <div className="text-right">
              <span className="text-[9px] text-zinc-500 uppercase font-black tracking-widest">Margem</span>
              <div className={`text-xs font-bold ${distanciaStop < 0.3 ? 'text-red-500 animate-pulse' : 'text-emerald-400'}`}>
                {distanciaStop.toFixed(2)}%
              </div>
            </div>
          </div>

          <div className="relative h-2 w-full bg-zinc-800 rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-700 rounded-full ${
                distanciaStop < 0.3 ? "bg-red-500 shadow-[0_0_10px_#ef4444]" : "bg-gradient-to-r from-red-500 via-yellow-500 to-emerald-500"
              }`}
              style={{ width: `${Math.min(distanciaStop * 50, 100)}%` }} 
            />
          </div>
          <div className="flex justify-between mt-1 px-1">
            <span className="text-[7px] text-zinc-600 font-bold uppercase tracking-tighter">Liquidando</span>
            <span className="text-[7px] text-zinc-600 font-bold uppercase tracking-tighter">Zona Segura</span>
          </div>
        </div>
      )}

      {/* TAGS DE STATUS FINAL */}
      <div className="mt-4 flex flex-wrap gap-2">
        {score >= 6 && (
          <span className="px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-black border border-emerald-500/20 flex items-center gap-1 uppercase tracking-tighter">
            <TrendingUp size={10} /> Alta Confluência
          </span>
        )}
        {decisao === "OBSERVAÇÃO" && (
          <span className="px-2 py-1 rounded bg-orange-500/10 text-orange-400 text-[10px] font-black border border-orange-500/20 flex items-center gap-1 uppercase tracking-tighter">
            <Activity size={10} /> Aguardando Recuperação
          </span>
        )}
      </div>
    </div>
  );
}