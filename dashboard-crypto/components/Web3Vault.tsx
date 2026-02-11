"use client";
import { ConnectButton } from '@rainbow-me/rainbowkit';
import { useAccount, useBalance } from 'wagmi';
import { ShieldCheck, Wallet } from 'lucide-react';

export default function Web3Vault() {
  const { address, isConnected } = useAccount();
  const { data: balance } = useBalance({
    address: address,
  });

  return (
    <div className="bg-zinc-900/50 border border-purple-500/20 rounded-2xl p-6 backdrop-blur-sm mb-6">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
            <ShieldCheck className="text-purple-500" />
            Cofre DeFi (Web3)
          </h2>
          <p className="text-xs text-zinc-400">Sua custódia pessoal, fora da Binance.</p>
        </div>
        {/* O botão mágico do RainbowKit faz tudo sozinho */}
        <ConnectButton label="Conectar Carteira" accountStatus="avatar" chainStatus="icon" />
      </div>

      {isConnected ? (
        <div className="grid grid-cols-2 gap-4 mt-4">
          <div className="bg-black/40 p-3 rounded-xl border border-zinc-800">
            <span className="text-[10px] text-zinc-500 uppercase font-bold">Endereço</span>
            <div className="text-sm text-zinc-300 font-mono truncate">
              {address}
            </div>
          </div>
          
          <div className="bg-gradient-to-br from-purple-900/20 to-blue-900/20 p-3 rounded-xl border border-purple-500/30">
            <span className="text-[10px] text-purple-300 uppercase font-bold flex items-center gap-1">
              <Wallet size={10} /> Saldo em Carteira
            </span>
            <div className="text-xl font-bold text-white mt-1">
              {balance?.formatted.slice(0, 6)} <span className="text-xs">{balance?.symbol}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center py-4 bg-zinc-800/30 rounded-xl border border-dashed border-zinc-700">
          <p className="text-sm text-zinc-500">Conecte sua MetaMask ou Ledger para visualizar.</p>
        </div>
      )}
    </div>
  );
}