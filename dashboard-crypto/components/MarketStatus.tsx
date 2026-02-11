"use client";
import { useEffect, useState } from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

export default function MarketStatus() {
  const [ticker, setTicker] = useState<any>(null);

  useEffect(() => {
    const fetchTicker = async () => {
      try {
        // Pega dados de 24h da Binance
        const res = await fetch("https://api.binance.com/api/v3/ticker/24hr?symbol=BTCBRL");
        const data = await res.json();
        setTicker(data);
      } catch (error) {
        console.error(error);
      }
    };

    fetchTicker();
    const interval = setInterval(fetchTicker, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!ticker) return <div className="animate-pulse h-20 bg-zinc-900 rounded-xl"></div>;

  const change = parseFloat(ticker.priceChangePercent);
  const isPositive = change >= 0;

  return (
    <div className="grid grid-cols-2 gap-3 mb-4">
      {/* CARD 1: VARIAÇÃO 24H */}
      <div className={`p-4 rounded-xl border backdrop-blur-sm flex flex-col justify-center ${
        isPositive 
          ? "bg-emerald-500/10 border-emerald-500/20" 
          : "bg-red-500/10 border-red-500/20"
      }`}>
        <span className="text-xs text-zinc-400 font-medium uppercase tracking-wider mb-1">Variação 24h</span>
        <div className="flex items-center gap-2">
          {isPositive ? <TrendingUp size={24} className="text-emerald-500" /> : <TrendingDown size={24} className="text-red-500" />}
          <span className={`text-2xl font-bold ${isPositive ? "text-emerald-400" : "text-red-400"}`}>
            {change.toFixed(2)}%
          </span>
        </div>
      </div>

      {/* CARD 2: TERMÔMETRO (VOLUME) */}
      <div className="bg-zinc-900/80 p-4 rounded-xl border border-zinc-800 backdrop-blur-sm flex flex-col justify-center">
         <span className="text-xs text-zinc-400 font-medium uppercase tracking-wider mb-1">Volume (BRL)</span>
         <div className="flex items-end gap-1">
            <span className="text-xl font-bold text-zinc-200">
              {(parseFloat(ticker.quoteVolume) / 1000000).toFixed(1)}M
            </span>
            <span className="text-xs text-zinc-500 mb-1">milhões</span>
         </div>
      </div>
    </div>
  );
}