"use client";
import { useEffect, useRef } from "react";
import { createChart, ColorType, AreaSeries } from "lightweight-charts";

export default function EquityChart() {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    // 1. Configura o Gráfico
    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#71717a", // Zinc 500
      },
      width: chartContainerRef.current.clientWidth,
      height: 200, // Um pouco menor que o principal
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

    // 2. Adiciona a Série de ÁREA (Patrimônio)
    const areaSeries = chart.addSeries(AreaSeries, {
      lineColor: "#10b981", // Emerald 500
      topColor: "#10b98120", // Transparente
      bottomColor: "#10b98100",
      lineWidth: 2,
    });

    // 3. Busca Dados da API
    const fetchEquity = async () => {
      try {
        const res = await fetch("http://localhost:8000/equity");
        const data = await res.json();
        
        // Se tiver dados, atualiza
        if (data && data.length > 0) {
            // Garante ordenação e unicidade de tempo (Lightweight charts é chato com isso)
            const uniqueData = Array.from(new Map(data.map((item:any) => [item.time, item])).values());
            // @ts-ignore
            areaSeries.setData(uniqueData);
            chart.timeScale().fitContent();
        }
      } catch (error) {
        console.error("Erro Equity:", error);
      }
    };

    fetchEquity();
    // Atualiza a cada 5 segundos (não precisa ser real-time igual preço)
    const interval = setInterval(fetchEquity, 5000);

    // Responsividade
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
  }, []);

  return (
    <div className="w-full bg-zinc-900/50 border border-zinc-800 rounded-2xl p-4 backdrop-blur-sm shadow-xl mt-4">
      <div className="flex items-center gap-2 mb-4">
        <div className="p-1.5 bg-emerald-500/10 rounded-md">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#10b981" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" x2="12" y1="2" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
        </div>
        <h3 className="text-sm font-semibold text-zinc-300">Crescimento de Patrimônio (R$)</h3>
      </div>
      <div ref={chartContainerRef} className="w-full h-[200px]" />
    </div>
  );
}