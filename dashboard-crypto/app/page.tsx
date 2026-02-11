"use client";
import { useEffect, useState } from "react";
import { 
  ArrowUpRight, ArrowDownRight, RefreshCcw, Wallet, 
  Activity, TrendingUp, History, Zap, BarChart3 
} from "lucide-react";
import CryptoChart from "@/components/CryptoChart";
import MarketStatus from "@/components/MarketStatus";
import AiBrain from "@/components/AiBrain";
import EquityChart from "@/components/EquityChart";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  const [stats, setStats] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [botStatus, setBotStatus] = useState<any>(null);
  const [marketPrice, setMarketPrice] = useState<number>(0);
  
  // Tabs: 'dash', 'wallet', 'trades'
  const [activeTab, setActiveTab] = useState("dash");

  const fetchData = async () => {
    try {
      const [resStats, resHistory, resBot, resBinance] = await Promise.all([
        fetch(`${API_URL}/stats`),
        fetch(`${API_URL}/history`),
        fetch(`${API_URL}/status-bot`),
        fetch("https://api.binance.com/api/v3/ticker/price?symbol=BTCBRL")
      ]);
      
      setStats(await resStats.json());
      setHistory(await resHistory.json());
      setBotStatus(await resBot.json());
      const jsonBinance = await resBinance.json();
      setMarketPrice(parseFloat(jsonBinance.price));
    } catch (error) {
      console.log("Conectando...", error);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-black text-zinc-100 font-sans pb-28 selection:bg-emerald-500/30">

      {/* HEADER */}
      <header className="sticky top-0 z-50 bg-black/80 backdrop-blur-md border-b border-zinc-800 px-4 py-4 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-500 bg-clip-text text-transparent">
            TraderBot Pro <span className="text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded ml-1">V4.0</span>
          </h1>
        </div>
        <button onClick={fetchData} className="p-2 bg-zinc-900 rounded-full border border-zinc-800 active:scale-90 transition">
          <RefreshCcw size={18} className="text-zinc-400" />
        </button>
      </header>

      <main className="p-4 space-y-4 max-w-5xl mx-auto">

        {/* --- ABA 1: DASHBOARD PRINCIPAL --- */}
        {activeTab === "dash" && (
          <div className="space-y-4 animate-in fade-in duration-500">
             {/* Card de Operação em Tempo Real (Só aparece se estiver posicionado) */}
             {botStatus?.posicionado && (
                <div className="bg-blue-600/10 border border-blue-500/30 p-4 rounded-2xl">
                    <div className="flex justify-between items-center mb-2">
                        <span className="text-[10px] font-bold text-blue-400 flex items-center gap-1">
                            <Zap size={12} fill="currentColor" /> EM OPERAÇÃO
                        </span>
                        <span className="text-xs font-mono text-zinc-400">
                            Preço Médio: R$ {botStatus.preco_compra.toLocaleString()}
                        </span>
                    </div>
                    <div className="text-2xl font-bold">
                        {(((marketPrice - botStatus.preco_compra) / botStatus.preco_compra) * 100 - 0.2).toFixed(2)}%
                        <span className="text-xs text-zinc-500 font-normal ml-2">Líquido</span>
                    </div>
                </div>
             )}
            
            <AiBrain />
            <CryptoChart trades={history} />
            <MarketStatus />
          </div>
        )}

        {/* --- ABA 2: PATRIMÔNIO (NOVA) --- */}
        {activeTab === "wallet" && (
          <div className="space-y-4 animate-in slide-in-from-right-4 duration-500">
            {/* Cards de Saldo */}
            <div className="grid grid-cols-1 gap-3">
              <div className="bg-zinc-900/50 border border-zinc-800 p-6 rounded-3xl backdrop-blur-sm relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-10">
                    <Wallet size={80} />
                </div>
                <span className="text-[10px] text-zinc-500 uppercase font-black tracking-widest">Saldo em Carteira</span>
                <div className="text-4xl font-bold text-white mt-1">
                  R$ {botStatus?.saldo_disponivel?.toFixed(2) || "0.00"}
                </div>
                <div className="flex items-center gap-2 mt-4">
                    <div className={`flex items-center text-xs font-bold ${stats?.lucro_total >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {stats?.lucro_total >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                        {stats?.lucro_total.toFixed(2)} R$ acumulados
                    </div>
                </div>
              </div>

              <div className="bg-zinc-900/50 border border-zinc-800 p-4 rounded-2xl flex justify-between items-center">
                 <div className="flex items-center gap-2">
                    <Activity className="text-blue-400" size={16} />
                    <span className="text-xs font-medium text-zinc-400">Taxa de Assertividade</span>
                 </div>
                 <span className="text-lg font-bold text-blue-400">{stats?.win_rate}%</span>
              </div>
            </div>

            {/* Gráfico de Evolução */}
            <EquityChart />
          </div>
        )}

        {/* --- ABA 3: HISTÓRICO --- */}
        {activeTab === "trades" && (
          <div className="animate-in slide-in-from-right-4 duration-500">
            <div className="flex items-center justify-between mb-4 px-1">
                <h3 className="text-xs font-black text-zinc-500 uppercase">Journal de Operações</h3>
            </div>
            <div className="space-y-2">
              {history.map((trade: any) => (
                <div key={trade.id} className="bg-zinc-900/40 p-4 rounded-2xl border border-zinc-800/50 flex justify-between items-center">
                  <div className="flex items-center gap-4">
                    <div className={`p-2 rounded-lg ${trade.tipo === 'COMPRA' ? 'bg-blue-500/10 text-blue-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                      {trade.tipo === 'COMPRA' ? <ArrowDownRight size={20} /> : <ArrowUpRight size={20} />}
                    </div>
                    <div>
                      <p className="font-bold text-sm">{trade.tipo}</p>
                      <p className="text-[10px] text-zinc-500">{new Date(trade.data_hora).toLocaleString('pt-BR')}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-sm">R$ {trade.preco.toLocaleString()}</p>
                    {trade.tipo === 'VENDA' && (
                      <span className={`text-[10px] font-bold ${trade.lucro > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {trade.lucro > 0 ? '+' : ''}{trade.lucro.toFixed(2)} R$
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* NAVEGAÇÃO INFERIOR ATUALIZADA (3 BOTÕES) */}
      <nav className="fixed bottom-0 w-full bg-black/80 backdrop-blur-2xl border-t border-zinc-800/50 flex justify-around py-4 pb-8 z-50">
        <button
          onClick={() => setActiveTab("dash")}
          className={`flex flex-col items-center gap-1.5 transition-all ${activeTab === "dash" ? "text-emerald-400 scale-110" : "text-zinc-600"}`}
        >
          <BarChart3 size={24} />
          <span className="text-[9px] font-black uppercase tracking-widest">Mercado</span>
        </button>

        <button
          onClick={() => setActiveTab("wallet")}
          className={`flex flex-col items-center gap-1.5 transition-all ${activeTab === "wallet" ? "text-emerald-400 scale-110" : "text-zinc-600"}`}
        >
          <Wallet size={24} />
          <span className="text-[9px] font-black uppercase tracking-widest">Carteira</span>
        </button>

        <button
          onClick={() => setActiveTab("trades")}
          className={`flex flex-col items-center gap-1.5 transition-all ${activeTab === "trades" ? "text-emerald-400 scale-110" : "text-zinc-600"}`}
        >
          <History size={24} />
          <span className="text-[9px] font-black uppercase tracking-widest">Logs</span>
        </button>
      </nav>
      
    </div>
  );
}