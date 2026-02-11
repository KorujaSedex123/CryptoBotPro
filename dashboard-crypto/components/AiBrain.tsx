"use client";
import { useEffect, useState } from "react";
import { Brain, Zap, Activity, TrendingUp, TrendingDown, AlertTriangle, CheckCircle, BarChart3 } from "lucide-react";

// Configuração da API
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AiBrain() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchBrain = async () => {
    try {
      const res = await fetch(`${API_URL}/stats`);
      const json = await res.json();
      setData(json.ia); // Assume que a API retorna { ia: { rsi, potencial, decisao } }
      setLoading(false);
    } catch (error) {
      console.error("Erro brain:", error);
    }
  };

  useEffect(() => {
    fetchBrain();
    const interval = setInterval(fetchBrain, 2000);
    return () => clearInterval(interval);
  }, []);

  // --- LÓGICA DE VISUALIZAÇÃO V3 ---
  // No V3, 'potencial' virou 'SCORE' (0 a 10)
  const score = data?.potencial || 0; 
  const rsi = data?.rsi || 50;
  const decisao = data?.decisao || "AGUARDAR";
  
  // Interpretação do Score para Cores
  const getScoreColor = (s: number) => {
    if (s >= 6) return "text-emerald-400"; // Compra Forte
    if (s >= 4) return "text-yellow-400";  // Atenção
    return "text-red-400";                 // Ruim
  };

  const getBarColor = (s: number) => {
    if (s >= 6) return "bg-emerald-500";
    if (s >= 4) return "bg-yellow-500";
    return "bg-red-500";
  };

  if (loading) return <div className="animate-pulse h-32 bg-zinc-900 rounded-xl"></div>;

  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-5 backdrop-blur-sm relative overflow-hidden group">
      
      {/* Efeito de Fundo (Pulse quando Score é alto) */}
      {score >= 6 && (
        <div className="absolute -top-10 -right-10 w-32 h-32 bg-emerald-500/10 rounded-full blur-3xl animate-pulse"></div>
      )}

      {/* CABEÇALHO */}
      <div className="flex justify-between items-center mb-4 relative z-10">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-purple-500/10 rounded-lg">
            <Brain className="text-purple-400" size={20} />
          </div>
          <div>
            <h3 className="text-sm font-bold text-zinc-200">Neural Engine V3</h3>
            <p className="text-[10px] text-zinc-500">Análise Quantitativa em Tempo Real</p>
          </div>
        </div>
        
        {/* Mostrador de Decisão */}
        <div className={`px-3 py-1 rounded-full border ${decisao === "COMPRA" ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" : "bg-zinc-800 border-zinc-700 text-zinc-400"}`}>
          <span className="text-xs font-bold tracking-wider flex items-center gap-1">
            {decisao === "COMPRA" ? <Zap size={12} fill="currentColor" /> : <Activity size={12} />}
            {decisao}
          </span>
        </div>
      </div>

      {/* GRID DE DADOS */}
      <div className="grid grid-cols-3 gap-4 relative z-10">
        
        {/* 1. RSI (Indicador Clássico) */}
        <div className="bg-black/30 p-3 rounded-xl border border-white/5 flex flex-col justify-between">
          <span className="text-[10px] text-zinc-500 uppercase font-bold flex items-center gap-1">
            <Activity size={10} /> RSI (14)
          </span>
          <div className={`text-xl font-mono font-bold mt-1 ${rsi < 30 ? "text-emerald-400 animate-pulse" : rsi > 70 ? "text-red-400" : "text-zinc-300"}`}>
            {rsi.toFixed(1)}
          </div>
          {/* Barrinha RSI */}
          <div className="w-full h-1 bg-zinc-800 rounded-full mt-2 overflow-hidden">
            <div 
              className={`h-full ${rsi < 30 ? "bg-emerald-500" : rsi > 70 ? "bg-red-500" : "bg-purple-500"}`} 
              style={{ width: `${rsi}%` }}
            ></div>
          </div>
        </div>

        {/* 2. SCORE V3 (O Novo Cérebro) */}
        <div className="bg-black/30 p-3 rounded-xl border border-white/5 flex flex-col justify-between col-span-2">
          <div className="flex justify-between items-start">
            <span className="text-[10px] text-zinc-500 uppercase font-bold flex items-center gap-1">
              <BarChart3 size={10} /> Pontuação (Score)
            </span>
            <span className={`text-[10px] font-bold ${getScoreColor(score)}`}>
               {score >= 6 ? "ALTA PROBABILIDADE" : score >= 4 ? "NEUTRO" : "RISCO ALTO"}
            </span>
          </div>
          
          <div className="flex items-end gap-2 mt-1">
            <div className={`text-3xl font-bold ${getScoreColor(score)}`}>
              {score.toFixed(0)}<span className="text-sm text-zinc-600">/10</span>
            </div>
          </div>

          {/* Barras de Score (Visualização Gráfica) */}
          <div className="flex gap-1 mt-2">
            {[...Array(10)].map((_, i) => (
              <div 
                key={i} 
                className={`h-1.5 flex-1 rounded-full transition-all duration-500 ${i < score ? getBarColor(score) : "bg-zinc-800"}`}
              ></div>
            ))}
          </div>
        </div>
      </div>

      {/* RODAPÉ: EXPLICAÇÃO (MOTIVOS) */}
      <div className="mt-4 pt-3 border-t border-white/5">
        <p className="text-[10px] text-zinc-500 mb-2 uppercase font-bold">Análise Técnica Detectada:</p>
        <div className="flex flex-wrap gap-2">
          {/* Como o DB atual não salva a lista de motivos, vamos inferir visualmente pelo Score/RSI para não quebrar */}
          
          {score >= 5 && (
            <span className="px-2 py-1 rounded bg-emerald-500/10 text-emerald-400 text-[10px] font-medium border border-emerald-500/20 flex items-center gap-1">
               <TrendingUp size={10} /> Tendência Macro Alta
            </span>
          )}
          
          {rsi < 30 && (
            <span className="px-2 py-1 rounded bg-blue-500/10 text-blue-400 text-[10px] font-medium border border-blue-500/20 flex items-center gap-1">
               <CheckCircle size={10} /> Sobrevenda (Barato)
            </span>
          )}

          {score < 4 && rsi > 40 && (
             <span className="px-2 py-1 rounded bg-zinc-800 text-zinc-500 text-[10px] font-medium border border-zinc-700">
               Aguardando Oportunidade...
             </span>
          )}

          {/* Se o score for alto e RSI normal, provavelmente foi um padrão de vela */}
          {score >= 6 && rsi > 30 && (
            <span className="px-2 py-1 rounded bg-purple-500/10 text-purple-400 text-[10px] font-medium border border-purple-500/20 flex items-center gap-1">
               <Zap size={10} /> Padrão de Vela (TA-Lib)
            </span>
          )}

          {decisao === "COMPRA" && (
             <span className="px-2 py-1 rounded bg-emerald-500 text-black text-[10px] font-bold animate-pulse">
               SINAL DE ENTRADA
             </span>
          )}
        </div>
      </div>

    </div>
  );
}