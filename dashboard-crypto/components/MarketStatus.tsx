"use client";
import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, Activity } from "lucide-react";

export default function MarketStatus({ symbol }: { symbol: string }) {
  const [ticker, setTicker] = useState<any>(null);

  useEffect(() => {
    const fetchTicker = async () => {
      try {
        // V5: Converte o par (ex: BTC/BRL -> BTCBRL) para a API pública da Binance
        const binancePair = symbol.replace("/", "");
        const res = await fetch(`https://api.binance.com/api/v3/ticker/24hr?symbol=${binancePair}`);
        const data = await res.json();
        setTicker(data);
      } catch (error) {
        console.error("Erro ao procurar ticker da Binance:", error);
      }
    };

    fetchTicker();
    // Atualiza a cada 5 segundos para não sobrecarregar o limite da API
    const interval = setInterval(fetchTicker, 5000);
    return () => clearInterval(interval);
  }, [symbol]); // Recarrega os dados sempre que o símbolo mudar

  if (!ticker) return <div className="animate-pulse h-24 bg-zinc-900 rounded-2xl border border-zinc-800"></div>;

  const change = parseFloat(ticker.priceChangePercent);
  const isPositive = change >= 0;

  return (
    <div className="grid grid-cols-2 gap-3 mb-4">
      {/* CARD 1: VARIAÇÃO 24H (Contextual ao Ativo) */}
      <div className={`p-4 rounded-2xl border backdrop-blur-sm flex flex-col justify-center transition-colors duration-500 ${
        isPositive 
          ? "bg-emerald-500/5 border-emerald-500/20" 
          : "bg-red-500/5 border-red-500/20"
      }`}>
        <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mb-1">Variação 24h</span>
        <div className="flex items-center gap-2">
          {isPositive ? (
            <TrendingUp size={20} className="text-emerald-500" />
          ) : (
            <TrendingDown size={20} className="text-red-500" />
          )}
          <span className={`text-xl font-mono font-bold ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
            {isPositive ? "+" : ""}{change.toFixed(2)}%
          </span>
        </div>
      </div>

      {/* CARD 2: VOLUME (Contextual ao Ativo) */}
      <div className="bg-zinc-900/50 p-4 rounded-2xl border border-zinc-800 backdrop-blur-sm flex flex-col justify-center">
         <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest mb-1">Volume ({symbol.split('/')[1]})</span>
         <div className="flex items-center gap-2">
            <div className="p-1.5 bg-blue-500/10 rounded-lg">
                <Activity size={16} className="text-blue-400" />
            </div>
            <div className="flex items-baseline gap-1">
                <span className="text-lg font-mono font-bold text-zinc-200">
                {(parseFloat(ticker.quoteVolume) / 1000000).toFixed(1)}M
                </span>
                <span className="text-[9px] text-zinc-500 font-bold">MIL</span>
            </div>
         </div>
      </div>
    </div>
  );
}