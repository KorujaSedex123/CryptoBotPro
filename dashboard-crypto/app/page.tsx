"use client";
import { useEffect, useState } from "react";
import {
  ArrowUpRight, ArrowDownRight, RefreshCcw, Wallet,
  Activity, TrendingUp, History, Zap, BarChart3, Star, ShieldAlert, PieChart
} from "lucide-react";
import CryptoChart from "@/components/CryptoChart";
import MarketStatus from "@/components/MarketStatus";
import AiBrain from "@/components/AiBrain";
import EquityChart from "@/components/EquityChart";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  // --- ESTADOS DE DADOS ---
  const [eliteSymbols, setEliteSymbols] = useState<string[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState("");
  const [scanResults, setScanResults] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [botStatus, setBotStatus] = useState<any>(null);
  const [marketPrice, setMarketPrice] = useState<number>(0);

  const handleTriggerReport = async () => {
    console.log("Disparando relatório diário...");
    try {
      const res = await fetch(`${API_URL}/trigger-report`);
      const data = await res.json();
      if (data.status === "sucesso") {
        alert("🚀 Relatório enviado com sucesso para o Discord!");
      }
    } catch (error) {
      alert("❌ Erro ao disparar relatório.");
    }
  };

  // --- CONTROLE DE INTERFACE ---
  const [activeTab, setActiveTab] = useState("dash");

  const fetchData = async () => {
    try {
      // 1. Busca Global: Elite e Resultados do Escaneamento
      const [resElite, resScan] = await Promise.all([
        fetch(`${API_URL}/elite`),
        fetch(`${API_URL}/scan-results`)
      ]);

      const eliteList = await resElite.json();
      const scanList = await resScan.json();

      setEliteSymbols(eliteList);
      setScanResults(scanList);

      // Define a primeira moeda da elite como padrão no primeiro carregamento
      if (!selectedSymbol && eliteList.length > 0) {
        setSelectedSymbol(eliteList[0]);
      } else if (!selectedSymbol && scanList.length > 0) {
        setSelectedSymbol(scanList[0].symbol); // Fallback para qualquer uma scaneada
      }

      // 2. Busca Específica do Ativo Selecionado
      if (selectedSymbol) {
        const [resStats, resHistory, resBot, resBinance] = await Promise.all([
          fetch(`${API_URL}/stats?symbol=${selectedSymbol}`),
          fetch(`${API_URL}/history?symbol=${selectedSymbol}`),
          fetch(`${API_URL}/status-bot?symbol=${selectedSymbol}`),
          fetch(`https://api.binance.com/api/v3/ticker/price?symbol=${selectedSymbol.replace('/', '')}`)
        ]);

        setStats(await resStats.json());
        setHistory(await resHistory.json());
        setBotStatus(await resBot.json());
        const jsonBinance = await resBinance.json();
        setMarketPrice(parseFloat(jsonBinance.price));
      }
    } catch (error) {
      console.log("Conectando ao bot...", error);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, [selectedSymbol]);

  return (
    <div className="min-h-screen bg-black text-zinc-100 font-sans pb-28 selection:bg-emerald-500/30">

      {/* HEADER FIXO */}
      <header className="sticky top-0 z-50 bg-black/80 backdrop-blur-md border-b border-zinc-800 px-4 py-4 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-500 bg-clip-text text-transparent">
            TraderBot Pro <span className="text-[10px] bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded ml-1">V5.2</span>
          </h1>
          <p className="text-[9px] text-zinc-500 flex items-center gap-1 mt-0.5 uppercase tracking-widest font-black">
            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span>
            Screener Quantitativo Ativo
          </p>
        </div>
        <button onClick={fetchData} className="p-2 bg-zinc-900 rounded-full border border-zinc-800 active:scale-90 transition">
          <RefreshCcw size={18} className="text-zinc-400" />
        </button>
      </header>

      <main className="p-4 space-y-6 max-w-5xl mx-auto">

        {/* SEÇÃO 1: RANKING DE ELITE (TOP 3) */}
        <div className="space-y-2">
          <h3 className="text-[10px] font-black text-zinc-500 uppercase tracking-widest flex items-center gap-2 px-1">
            <Star size={12} className="text-yellow-500" /> Elite Selecionada
          </h3>
          <div className="grid grid-cols-3 gap-2">
            {eliteSymbols.map((sym) => (
              <button
                key={sym}
                onClick={() => setSelectedSymbol(sym)}
                className={`p-3 rounded-2xl border transition-all flex flex-col items-center gap-1 ${selectedSymbol === sym
                    ? "bg-emerald-500/10 border-emerald-500/50 shadow-[0_0_20px_rgba(16,185,129,0.1)]"
                    : "bg-zinc-900/50 border-zinc-800 opacity-50"
                  }`}
              >
                <span className={`text-[11px] font-black ${selectedSymbol === sym ? "text-emerald-400" : "text-zinc-400"}`}>
                  {sym.split('/')[0]}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* SEÇÃO 2: RELATÓRIO DE ESCANEAMENTO (TRANSPARÊNCIA DO BACKTEST) */}
        <div className="bg-zinc-900/30 border border-zinc-800/50 rounded-2xl p-4">
          <h3 className="text-[10px] font-black text-zinc-500 uppercase tracking-widest mb-3 flex items-center gap-2">
            <PieChart size={12} /> Placar de Calibração (Backtest 24h)
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-2">
            {scanResults.map((res) => (
              <button
                key={res.symbol}
                onClick={() => setSelectedSymbol(res.symbol)}
                className={`flex justify-between items-center p-2 rounded-lg transition-colors ${selectedSymbol === res.symbol ? 'bg-zinc-800/40' : 'hover:bg-zinc-900/50'}`}
              >
                <span className="text-[11px] font-bold text-zinc-400">{res.symbol}</span>
                <div className="flex items-center gap-3">
                  <span className={`text-[11px] font-mono font-bold ${res.lucro > 0 ? 'text-emerald-400' : 'text-red-500'}`}>
                    {res.lucro > 0 ? '+' : ''}{res.lucro.toFixed(2)}%
                  </span>
                  <span className={`px-1.5 py-0.5 rounded-[4px] text-[8px] font-black uppercase ${res.decisao === 'ELITE' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-zinc-800 text-zinc-500'
                    }`}>
                    {res.decisao}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* --- ABA 1: OPERAÇÃO --- */}
        {activeTab === "dash" && selectedSymbol && (
          <div className="space-y-4 animate-in fade-in duration-500">

            {/* AVISO DE MODO OBSERVAÇÃO */}
            {botStatus?.posicionado === false && stats?.ultimo_trade?.decisao === "OBSERVAÇÃO" && (
              <div className="bg-orange-500/10 border border-orange-500/30 p-4 rounded-2xl flex items-center gap-3 border-l-4">
                <ShieldAlert className="text-orange-400" size={24} />
                <div>
                  <p className="text-xs font-black text-orange-400 uppercase tracking-tighter">Modo Observação Ativo</p>
                  <p className="text-[10px] text-zinc-500">Backtest negativo ({stats?.lucro_total.toFixed(2)}%). A IA não operará {selectedSymbol} agora.</p>
                </div>
              </div>
            )}

            {/* CARD DE POSIÇÃO ATIVA */}
            {botStatus?.posicionado && (
              <div className="bg-gradient-to-br from-blue-600/20 to-zinc-900 border border-blue-500/30 p-5 rounded-2xl relative overflow-hidden">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-[10px] font-black text-blue-400 flex items-center gap-1 mb-1">
                      <Zap size={14} fill="currentColor" /> TRADE EM ANDAMENTO
                    </span>
                    <div className="text-4xl font-mono font-bold text-white">
                      {(((marketPrice - botStatus.preco_compra) / botStatus.preco_compra) * 100 - 0.2).toFixed(2)}%
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-zinc-500 font-bold uppercase">Preço Entrada</p>
                    <p className="text-sm font-mono text-zinc-300">R$ {botStatus.preco_compra.toLocaleString()}</p>
                  </div>
                </div>
              </div>
            )}

            <AiBrain symbol={selectedSymbol} marketPrice={marketPrice} />
            <CryptoChart symbol={selectedSymbol} trades={history} />
            <MarketStatus symbol={selectedSymbol} />
          </div>
        )}

        {/* --- ABA 2: CARTEIRA & MÉTRICAS QUANT --- */}
        {activeTab === "wallet" && (
          <div className="space-y-4 animate-in slide-in-from-right-4 duration-500">

            <div className="bg-zinc-900/50 border border-zinc-800 p-6 rounded-3xl backdrop-blur-sm relative overflow-hidden">
              <div className="absolute top-0 right-0 p-4 opacity-5"><Wallet size={100} /></div>
              <span className="text-[10px] text-zinc-500 uppercase font-black tracking-widest">Patrimônio {selectedSymbol}</span>
              <div className="text-4xl font-bold text-white mt-1">
                R$ {botStatus?.saldo_disponivel?.toFixed(2) || "0.00"}
              </div>
              <div className={`flex items-center text-xs font-bold mt-4 ${stats?.lucro_total >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                {stats?.lucro_total >= 0 ? <ArrowUpRight size={14} /> : <ArrowDownRight size={14} />}
                R$ {stats?.lucro_total.toFixed(2)} (Lucro Real Acumulado)
              </div>
            </div>

            {/* MÉTRICAS DE RISCO (O CORAÇÃO DO QUANT) */}
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-zinc-900/50 border border-zinc-800 p-4 rounded-2xl text-center">
                <span className="text-[9px] text-zinc-500 font-bold uppercase block mb-1">Profit Factor</span>
                <div className={`text-xl font-bold ${stats?.profit_factor >= 1.5 ? 'text-emerald-400' : 'text-zinc-100'}`}>
                  {stats?.profit_factor}x
                </div>
                <p className="text-[7px] text-zinc-600 mt-1 uppercase font-bold tracking-tighter">Eficiência</p>
              </div>

              <div className="bg-zinc-900/50 border border-zinc-800 p-4 rounded-2xl text-center">
                <span className="text-[9px] text-zinc-500 font-bold uppercase block mb-1">Sharpe Ratio</span>
                <div className="text-xl font-bold text-blue-400">{stats?.sharpe_ratio}</div>
                <p className="text-[7px] text-zinc-600 mt-1 uppercase font-bold tracking-tighter">Estabilidade</p>
              </div>

              <div className="bg-zinc-900/50 border border-zinc-800 p-4 rounded-2xl text-center">
                <span className="text-[9px] text-zinc-500 font-bold uppercase block mb-1">Max DD</span>
                <div className="text-xl font-bold text-red-400">-{stats?.max_drawdown}%</div>
                <p className="text-[7px] text-zinc-600 mt-1 uppercase font-bold tracking-tighter">Risco Max</p>
              </div>
            </div>

            <EquityChart symbol={selectedSymbol} />
          </div>
        )}

        {/* --- ABA 3: HISTÓRICO DE LOGS --- */}
        {activeTab === "trades" && (
          <div className="space-y-2 animate-in slide-in-from-right-4 duration-500">
            <button
              onClick={handleTriggerReport}
              className="w-full mb-4 py-3 bg-zinc-900 border border-zinc-800 rounded-2xl text-[10px] font-black uppercase tracking-widest text-zinc-400 hover:text-emerald-400 hover:border-emerald-500/50 transition-all flex items-center justify-center gap-2"
            >
              <Zap size={14} /> Gerar Relatório Diário Agora
            </button>
            {history.length > 0 ? (
              history.map((trade: any) => (
                <div key={trade.id} className="bg-zinc-900/40 p-4 rounded-2xl border border-zinc-800/50 flex justify-between items-center group transition-all hover:bg-zinc-900/80">
                  <div className="flex items-center gap-4">
                    <div className={`p-2 rounded-lg ${trade.tipo === 'COMPRA' ? 'bg-blue-500/10 text-blue-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                      {trade.tipo === 'COMPRA' ? <ArrowDownRight size={20} /> : <ArrowUpRight size={20} />}
                    </div>
                    <div>
                      <p className="font-black text-xs text-zinc-200 uppercase tracking-tight">{trade.tipo} - {trade.symbol}</p>
                      <p className="text-[10px] text-zinc-600 font-mono">{new Date(trade.data_hora).toLocaleString('pt-BR')}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-xs font-bold text-zinc-300">R$ {trade.preco.toLocaleString()}</p>
                    {trade.tipo === 'VENDA' && (
                      <span className={`text-[10px] font-black ${trade.lucro > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                        {trade.lucro > 0 ? '+' : ''}{trade.lucro.toFixed(2)} R$
                      </span>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-20 opacity-20"><History size={48} className="mx-auto" /></div>
            )}
          </div>
        )}
      </main>

      {/* NAVEGAÇÃO INFERIOR */}
      <nav className="fixed bottom-0 w-full bg-black/60 backdrop-blur-2xl border-t border-zinc-800/50 flex justify-around py-4 pb-8 z-50">
        <button onClick={() => setActiveTab("dash")} className={`flex flex-col items-center gap-1.5 transition-all ${activeTab === "dash" ? "text-emerald-400 scale-110" : "text-zinc-600"}`}>
          <BarChart3 size={24} /><span className="text-[9px] font-black uppercase tracking-widest">Mercado</span>
        </button>
        <button onClick={() => setActiveTab("wallet")} className={`flex flex-col items-center gap-1.5 transition-all ${activeTab === "wallet" ? "text-emerald-400 scale-110" : "text-zinc-600"}`}>
          <Wallet size={24} /><span className="text-[9px] font-black uppercase tracking-widest">Carteira</span>
        </button>
        <button onClick={() => setActiveTab("trades")} className={`flex flex-col items-center gap-1.5 transition-all ${activeTab === "trades" ? "text-emerald-400 scale-110" : "text-zinc-600"}`}>
          <History size={24} /><span className="text-[9px] font-black uppercase tracking-widest">Logs</span>
        </button>
      </nav>

    </div>
  );
}