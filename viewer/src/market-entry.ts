import { startBoard } from '../../market/web/main.ts';
import { createMarketTrader } from './market-trader.ts';
import '../../market/web/style.css';
import '../../market/web/trader.css';

const root = document.getElementById('market-root');
if (root) {
  const trader = createMarketTrader(root);
  const stop = startBoard(trader.board, trader.presentation);
  window.addEventListener('pagehide', () => { stop(); trader.dispose(); }, { once: true });
}
