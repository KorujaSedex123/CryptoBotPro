"use client";
import { Play, Pause, AlertOctagon } from "lucide-react";
import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function DashboardControl() {
  const [isRunning, setIsRunning] = useState(true);
  const [isPanic, setIsPanic] = useState(false);

  const toggleBot = async () => {
    const newState = !isRunning;
    try {
      await fetch(`${API_URL}/bot-control?status=${newState}`);
      setIsRunning(newState);
    } catch (e) {
      console.error("Erro ao alternar bot");
    }
  };

  const handlePanicSell = async () => {
    if (!confirm("🚨 TEM CERTEZA? ISSO VENDERÁ TUDO AGORA!")) return;
    setIsPanic(true);
    try {
      await fetch(`${API_URL}/panic-sell`, { method: "POST" });
      alert("⚠️ PROTOCOLO DE EMERGÊNCIA ATIVADO!");
    } catch (e) {
      alert("Erro ao enviar comando de pânico.");
    } finally {
      setIsPanic(false);
    }
  };

  return (
    <div className="grid grid-cols-4 gap-3 mb-4">
      <button 
        onClick={toggleBot}
        className={`col-span-3 py-3 rounded-xl border flex items-center justify-center gap-2 font-black uppercase text-xs transition-all ${
          isRunning 
            ? "bg-emerald-500/10 border-emerald-500 text-emerald-400 hover:bg-emerald-500/20" 
            : "bg-orange-500/10 border-orange-500 text-orange-400 hover:bg-orange-500/20"
        }`}
      >
        {isRunning ? <><Pause size={16} /> Bot Operando (Pausar)</> : <><Play size={16} /> Bot Pausado (Iniciar)</>}
      </button>

      <button 
        onClick={handlePanicSell}
        disabled={isPanic}
        className="col-span-1 bg-red-500 text-white rounded-xl font-bold flex items-center justify-center hover:bg-red-600 active:scale-95 transition-all"
      >
        {isPanic ? <span className="animate-spin">...</span> : <AlertOctagon size={20} />}
      </button>
    </div>
  );
}