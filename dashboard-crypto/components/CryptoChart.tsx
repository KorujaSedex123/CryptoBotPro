"use client";
import { useEffect, useRef } from "react";
import { 
  createChart, 
  ColorType, 
  IChartApi, 
  ISeriesApi, 
  CandlestickSeries, 
  Time,
  SeriesMarker 
} from "lightweight-charts";

interface CryptoChartProps {
  symbol: string;
  trades: any[];
}

export default function CryptoChart({ symbol, trades }: CryptoChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartApiRef = useRef<IChartApi | null>(null);
  const seriesApiRef = useRef<ISeriesApi<"Candlestick"> | null>(null);

  // 1. EFEITO MESTRE: Criação e Gerenciamento do Gráfico
  useEffect(() => {
    if (!chartContainerRef.current) return;

    // --- SETUP DO GRÁFICO ---
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#71717a",
      },
      grid: {
        vertLines: { color: "rgba(42, 46, 57, 0.1)" },
        horzLines: { color: "rgba(42, 46, 57, 0.1)" },
      },
      width: chartContainerRef.current.clientWidth,
      height: 300,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderColor: "#27272a",
      },
      rightPriceScale: {
        borderColor: "#27272a",
      },
    });

    // Cria a Série usando a classe da V4
    const newSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#10b981",
      downColor: "#ef4444",
      borderUpColor: "#10b981",
      borderDownColor: "#ef4444",
      wickUpColor: "#10b981",
      wickDownColor: "#ef4444",
    });

    // Salva nas Refs
    chartApiRef.current = chart;
    seriesApiRef.current = newSeries;

    // --- CARREGAMENTO DE DADOS (CANDLES) ---
    const fetchCandles = async () => {
      try {
        const res = await fetch(`https://api.binance.com/api/v3/klines?symbol=${symbol.replace('/', '')}&interval=15m&limit=100`);
        const data = await res.json();
        
        const candles = data.map((d: any) => ({
          time: (d[0] / 1000) as Time,
          open: parseFloat(d[1]),
          high: parseFloat(d[2]),
          low: parseFloat(d[3]),
          close: parseFloat(d[4]),
        }));

        // Verifica se a série ainda existe antes de setar dados
        if (seriesApiRef.current) {
          seriesApiRef.current.setData(candles);
        }
      } catch (e) {
        console.error("Erro chart:", e);
      }
    };

    fetchCandles();

    // --- RESPONSIVIDADE ---
    const resizeObserver = new ResizeObserver((entries) => {
      if (entries.length === 0 || !entries[0].target || !chartApiRef.current) return;
      const { width } = entries[0].contentRect;
      chartApiRef.current.applyOptions({ width });
    });
    resizeObserver.observe(chartContainerRef.current);

    // --- CLEANUP ---
    return () => {
      resizeObserver.disconnect();
      if (chartApiRef.current) {
        chartApiRef.current.remove();
        chartApiRef.current = null;
        seriesApiRef.current = null;
      }
    };
  }, [symbol]);

  // 2. EFEITO SECUNDÁRIO: Atualização dos Marcadores (Trades)
  useEffect(() => {
    // Verificação de Segurança
    if (!seriesApiRef.current || !trades) return;

    try {
      // Ordena os trades por data (Obrigatório na V4)
      const sortedTrades = [...trades].sort((a, b) => new Date(a.data_hora).getTime() - new Date(b.data_hora).getTime());

      // Tipagem explícita dos marcadores
      const markers: SeriesMarker<Time>[] = sortedTrades.map((t) => ({
        time: (new Date(t.data_hora).getTime() / 1000) as Time,
        position: t.tipo === 'COMPRA' ? 'belowBar' : 'aboveBar',
        color: t.tipo === 'COMPRA' ? '#10b981' : '#ef4444',
        shape: t.tipo === 'COMPRA' ? 'arrowUp' : 'arrowDown',
        text: t.tipo === 'COMPRA' ? 'Buy' : `Sell (${t.lucro > 0 ? '+' : ''}${t.lucro.toFixed(2)})`,
      }));

      // AQUI ESTÁ A CORREÇÃO: Usamos 'as any' para o TypeScript parar de reclamar
      // A função existe no objeto, mas a tipagem ISeriesApi às vezes não a expõe corretamente.
      (seriesApiRef.current as any).setMarkers(markers);
      
    } catch (error) {
      console.warn("Erro ao plotar markers:", error);
    }
  }, [trades, symbol]);

  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-4 backdrop-blur-sm">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-widest">Gráfico {symbol} (15m)</h3>
        <span className="text-[9px] text-zinc-600 bg-zinc-800 px-2 py-1 rounded">Live Binance Data</span>
      </div>
      <div ref={chartContainerRef} className="w-full h-[300px]" />
    </div>
  );
}