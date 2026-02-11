"use client";
import { useEffect, useState } from "react";
import { ArrowUpRight, ArrowDownRight, RefreshCcw, Wallet, Activity, TrendingUp, History } from "lucide-react";
import CryptoChart from "@/components/CryptoChart";
import MarketStatus from "@/components/MarketStatus";
import AiBrain from "@/components/AiBrain";

// Configuração da API
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function Home() {
  // Estados de Dados
  const [stats, setStats] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [botStatus, setBotStatus] = useState<any>(null);
  const [marketPrice, setMarketPrice] = useState<number>(0);
  
  // Controle de Interface
  const [activeTab, setActiveTab] = useState("dash"); // 'dash' ou 'trades'

  // --- BUSCA DE DADOS ---
  const fetchData = async () => {
    try {
      // 1. Dados do Bot (Backend)
      const resStats = await fetch(`${API_URL}/stats`);
      const resHistory = await fetch(`${API_URL}/history`);
      const resBot = await fetch(`${API_URL}/status-bot`);
      
      const jsonStats = await resStats.json();
      const jsonHistory = await resHistory.json();
      const jsonBot = await resBot.json();

      setStats(jsonStats);
      setHistory(jsonHistory.reverse());
      setBotStatus(jsonBot);

      // 2. Preço ao Vivo (Binance) - Para cálculo instantâneo na tela
      const resBinance = await fetch("https://api.binance.com/api/v3/ticker/price?symbol=BTCBRL");
      const jsonBinance = await resBinance.json();
      setMarketPrice(parseFloat(jsonBinance.price));

    } catch (error) {
      console.log("Aguardando conexão...", error);
    }
  };

  // Loop de atualização (A cada 2 segundos)
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-black text-zinc-100 font-sans pb-24 selection:bg-emerald-500/30">

      {/* 1. HEADER */}
      <header className="sticky top-0 z-50 bg-black/80 backdrop-blur-md border-b border-zinc-800 px-4 py-4 flex justify-between items-center">
        <div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-500 bg-clip-text text-transparent">
            TraderBot V2
          </h1>
          <p className="text-xs text-zinc-500 flex items-center gap-1">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
            Sistema Online
          </p>
        </div>
        <button onClick={fetchData} className="p-2 bg-zinc-900 rounded-full border border-zinc-800 active:scale-90 transition hover:bg-zinc-800">
          <RefreshCcw size={18} className="text-zinc-400" />
        </button>
      </header>

      <main className="p-4 space-y-4">

        {activeTab === "dash" && (
          <>
            {/* 2. GRID DE STATUS GERAL (Lucro Total e Win Rate) */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              {/* Card Lucro */}
              <div className="bg-zinc-900/50 border border-zinc-800 p-4 rounded-2xl backdrop-blur-sm">
                <div className="flex items-center gap-2 text-zinc-400 mb-2">
                  <Wallet size={16} />
                  <span className="text-xs font-medium uppercase">Lucro Total</span>
                </div>
                <div className={`text-2xl font-bold ${stats?.lucro_total >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {stats ? `R$ ${stats.lucro_total.toFixed(2)}` : <span className="animate-pulse">...</span>}
                </div>
              </div>

              {/* Card Win Rate */}
              <div className="bg-zinc-900/50 border border-zinc-800 p-4 rounded-2xl backdrop-blur-sm">
                <div className="flex items-center gap-2 text-zinc-400 mb-2">
                  <Activity size={16} />
                  <span className="text-xs font-medium uppercase">Win Rate</span>
                </div>
                <div className="text-2xl font-bold text-blue-400">
                  {stats ? `${stats.win_rate}%` : <span className="animate-pulse">...</span>}
                </div>
              </div>
            </div>

            {/* 3. CARD DE OPERAÇÃO EM ANDAMENTO (Live Profit & Trailing Stop) */}
            {botStatus && botStatus.posicionado && (
              <div className="bg-gradient-to-r from-blue-900/40 to-purple-900/40 border border-blue-500/30 p-4 rounded-xl mb-4 relative overflow-hidden group">
                
                {/* Efeito de fundo */}
                <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl -mr-10 -mt-10"></div>

                <div className="relative z-10">
                  {/* Cabeçalho do Card */}
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="text-sm font-bold text-blue-200 flex items-center gap-2">
                        <span className="animate-pulse w-2 h-2 bg-blue-400 rounded-full"></span>
                        Operação em Curso
                      </h3>
                      <p className="text-[10px] text-zinc-400">
                        Entrada: R$ {botStatus.preco_compra.toFixed(2)}
                      </p>
                    </div>
                    <span className="text-[10px] bg-blue-500 text-white px-2 py-1 rounded-full font-bold shadow-lg shadow-blue-500/20">
                      HOLDING
                    </span>
                  </div>

                  {/* CÁLCULOS AO VIVO */}
                  {(() => {
                    // Usamos o preço ao vivo da Binance ou o preço do bot
                    const precoAtual = marketPrice > 0 ? marketPrice : botStatus.preco_maximo;
                    const precoCompra = botStatus.preco_compra;
                    const qtd = botStatus.qtd_btc;
                    const topoHistorico = botStatus.preco_maximo;
                    
                    // Lucro em Reais (R$) e Porcentagem (%)
                    const lucroReais = (precoAtual - precoCompra) * qtd;
                    const lucroPct = ((precoAtual - precoCompra) / precoCompra) * 100;
                    
                    // ONDE O BOT VAI VENDER? (Trailing Stop de 1%)
                    const gatilhoVenda = topoHistorico * (1 - 0.01); 
                    const distanciaDoStop = ((precoAtual - gatilhoVenda) / gatilhoVenda) * 100;

                    return (
                      <div className="grid grid-cols-2 gap-4">
                        
                        {/* LADO ESQUERDO: LUCRO AGORA */}
                        <div className="bg-black/30 p-2 rounded-lg border border-white/5">
                          <span className="text-[10px] text-zinc-400 uppercase font-bold block mb-1">Lucro (PnL)</span>
                          <div className={`text-xl font-mono font-bold ${lucroReais >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                            {lucroReais >= 0 ? "+" : ""}R$ {lucroReais.toFixed(2)}
                          </div>
                          <div className={`text-xs ${lucroPct >= 0 ? "text-emerald-500/80" : "text-red-500/80"}`}>
                            {lucroPct >= 0 ? "▲" : "▼"} {lucroPct.toFixed(2)}%
                          </div>
                        </div>

                        {/* LADO DIREITO: GATILHO DE SAÍDA */}
                        <div className="bg-black/30 p-2 rounded-lg border border-white/5 relative">
                          <span className="text-[10px] text-zinc-400 uppercase font-bold block mb-1">Stop (Venda em)</span>
                          <div className="text-lg font-mono font-bold text-yellow-400">
                            R$ {gatilhoVenda.toFixed(2)}
                          </div>
                          <div className="text-[10px] text-zinc-500 mt-1">
                            Distância: <span className="text-zinc-300">{distanciaDoStop.toFixed(2)}%</span>
                          </div>
                        </div>

                      </div>
                    );
                  })()}
                </div>
              </div>
            )}

            {/* 4. COMPONENTES PRINCIPAIS */}
            <MarketStatus />
            <AiBrain />
            <CryptoChart trades={[...history].reverse()} />
          </>
        )}

        {/* 5. ABA HISTÓRICO */}
        {activeTab === "trades" && (
          <div className="mt-2">
            <h3 className="text-sm font-semibold text-zinc-500 mb-3 px-1 uppercase tracking-wider">
              Histórico Completo
            </h3>

            <div className="space-y-2">
              {history.length === 0 ? (
                <div className="text-center py-12 text-zinc-600 text-sm bg-zinc-900/30 rounded-xl border border-dashed border-zinc-800">
                  Nenhum trade registrado ainda.
                </div>
              ) : (
                history.map((trade: any) => (
                  <div key={trade.id} className="bg-zinc-900/60 p-3 rounded-xl border border-zinc-800/50 flex justify-between items-center hover:border-zinc-700 transition">
                    <div className="flex items-center gap-3">
                      <div className={`p-2.5 rounded-full ${trade.tipo === 'COMPRA' ? 'bg-blue-500/10 text-blue-400' : 'bg-emerald-500/10 text-emerald-400'}`}>
                        {trade.tipo === 'COMPRA' ? <ArrowDownRight size={18} /> : <ArrowUpRight size={18} />}
                      </div>
                      <div>
                        <p className={`font-bold text-sm ${trade.tipo === 'COMPRA' ? 'text-blue-200' : 'text-emerald-200'}`}>{trade.tipo}</p>
                        <p className="text-[10px] text-zinc-500">{trade.data_hora}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="font-mono text-sm text-zinc-300">R$ {trade.preco.toFixed(2)}</p>
                      {trade.lucro !== 0 && (
                        <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${trade.lucro > 0 ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                          {trade.lucro > 0 ? '+' : ''}{trade.lucro.toFixed(2)} R$
                        </span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </main>

      {/* 6. NAVEGAÇÃO INFERIOR */}
      <nav className="fixed bottom-0 w-full bg-black/80 backdrop-blur-xl border-t border-zinc-800 flex justify-around py-3 pb-6 z-50">
        <button
          onClick={() => setActiveTab("dash")}
          className={`flex flex-col items-center gap-1 transition-colors ${activeTab === "dash" ? "text-emerald-400" : "text-zinc-600 hover:text-zinc-400"}`}
        >
          <TrendingUp size={24} />
          <span className="text-[10px] font-medium">Dashboard</span>
        </button>

        <button
          onClick={() => setActiveTab("trades")}
          className={`flex flex-col items-center gap-1 transition-colors ${activeTab === "trades" ? "text-emerald-400" : "text-zinc-600 hover:text-zinc-400"}`}
        >
          <History size={24} />
          <span className="text-[10px] font-medium">Histórico</span>
        </button>
      </nav>
      
    </div>
  );
}