"use client";
import { useEffect, useRef } from "react";
import { createChart, ColorType, CandlestickSeries } from "lightweight-charts";

export default function CryptoChart({ trades }: { trades?: any[] }) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const seriesRef = useRef<any>(null); // Usamos REF para garantir que o objeto fique intacto

  // 1. Criação do Gráfico
  useEffect(() => {
    if (!chartContainerRef.current) return;

    // Cria o gráfico
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#A1A1AA",
      },
      width: chartContainerRef.current.clientWidth,
      height: 300,
      grid: {
        vertLines: { color: "#27272a" },
        horzLines: { color: "#27272a" },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
    });

    chartRef.current = chart;

    // Adiciona a Série (V5 Syntax)
    const newSeries = chart.addSeries(CandlestickSeries, {
      upColor: "#4ade80", 
      downColor: "#f87171",
      borderVisible: false, 
      wickUpColor: "#4ade80", 
      wickDownColor: "#f87171",
    });

    // Guarda na referência (isso não causa re-render, mas guarda o objeto real)
    seriesRef.current = newSeries;

    // Busca dados iniciais
    const fetchBinanceData = async () => {
      try {
        const res = await fetch("https://api.binance.com/api/v3/klines?symbol=BTCBRL&interval=1m&limit=100");
        const data = await res.json();
        const candles = data.map((d: any) => ({
          time: d[0] / 1000,
          open: parseFloat(d[1]),
          high: parseFloat(d[2]),
          low: parseFloat(d[3]),
          close: parseFloat(d[4]),
        }));
        newSeries.setData(candles);
      } catch (error) { console.error(error); }
    };

    fetchBinanceData();
    const interval = setInterval(fetchBinanceData, 2000);

    const handleResize = () => {
        if (chartRef.current && chartContainerRef.current) {
            chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
        }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      clearInterval(interval);
      window.removeEventListener("resize", handleResize);
      chart.remove();
      seriesRef.current = null; // Limpa a referência
    };
  }, []);

  // 2. Atualização dos Marcadores (Roda sempre que 'trades' mudar)
  useEffect(() => {
    // Verifica se a série existe e se tem o método setMarkers
    if (!seriesRef.current || !trades) return;

    try {
        const markers = trades.map((t: any) => {
            const time = new Date(t.data_hora).getTime() / 1000; 
            return {
                time: time,
                position: t.tipo === 'COMPRA' ? 'belowBar' : 'aboveBar',
                color: t.tipo === 'COMPRA' ? '#4ade80' : '#f87171',
                shape: t.tipo === 'COMPRA' ? 'arrowUp' : 'arrowDown',
                text: t.tipo === 'COMPRA' ? 'C' : 'V',
                size: 2,
            };
        });
        
        // Ordena por tempo (Obrigatório)
        markers.sort((a: any, b: any) => a.time - b.time);

        // Chama o método direto na referência
        if (typeof seriesRef.current.setMarkers === 'function') {
            seriesRef.current.setMarkers(markers);
        }

    } catch (e) {
        console.error("Erro markers:", e);
    }
  }, [trades]);

  return (
    <div className="w-full bg-zinc-900/50 border border-zinc-800 rounded-2xl p-4 backdrop-blur-sm shadow-xl">
      <div className="flex justify-between items-center mb-4">
         <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
            <h3 className="text-sm font-semibold text-zinc-300">BTC/BRL</h3>
         </div>
         <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-1 rounded-full animate-pulse">● Ao Vivo</span>
      </div>
      <div ref={chartContainerRef} className="w-full h-[300px]" />
    </div>
  );
}