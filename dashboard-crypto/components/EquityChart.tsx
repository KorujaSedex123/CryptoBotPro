"use client";
import { useEffect, useRef } from "react";
import { createChart, ColorType, AreaSeries } from "lightweight-charts";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function EquityChart({ symbol }: { symbol: string }) {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // 1. Configura o Gráfico de Área
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#71717a", 
      },
      width: chartContainerRef.current.clientWidth,
      height: 200,
      grid: {
        vertLines: { visible: false },
        horzLines: { color: "#27272a" },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
        borderVisible: false,
      },
      rightPriceScale: {
        borderVisible: false,
      },
    });

    const areaSeries = chart.addSeries(AreaSeries, {
      lineColor: "#10b981", 
      topColor: "#10b98120", 
      bottomColor: "#10b98100",
      lineWidth: 2,
    });

    // 2. Busca Dados Filtrados por Símbolo
    const fetchEquity = async () => {
      try {
        // V5: Adiciona o parâmetro de símbolo na requisição
        const res = await fetch(`${API_URL}/equity?symbol=${symbol}`);
        const data = await res.json();
        
        if (data && data.length > 0) {
            // Remove duplicatas de tempo para evitar erros no Lightweight Charts
            const uniqueData = Array.from(new Map(data.map((item:any) => [item.time, item])).values());
            // @ts-ignore
            areaSeries.setData(uniqueData);
            chart.timeScale().fitContent();
        }
      } catch (error) {
        console.error(`Erro Equity (${symbol}):`, error);
      }
    };

    fetchEquity();
    const interval = setInterval(fetchEquity, 5000);

    const handleResize = () => {
        if(chartContainerRef.current) {
            chart.applyOptions({ width: chartContainerRef.current.clientWidth });
        }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      clearInterval(interval);
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [symbol]); // O gráfico reinicia ao trocar de moeda

  return (
    <div className="w-full bg-zinc-900/50 border border-zinc-800 rounded-2xl p-4 backdrop-blur-sm shadow-xl mt-4">
      <div className="flex items-center gap-2 mb-4">
        <div className="p-1.5 bg-emerald-500/10 rounded-md">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" x2="12" y1="2" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
        </div>
        <h3 className="text-sm font-semibold text-zinc-300">Desempenho de {symbol} (R$)</h3>
      </div>
      <div ref={chartContainerRef} className="w-full h-[200px]" />
    </div>
  );
}