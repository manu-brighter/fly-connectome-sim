import { startBoard } from '../../market/web/main.ts';
import '../../market/web/style.css';

const root = document.getElementById('market-root');
if (root) startBoard(root);
