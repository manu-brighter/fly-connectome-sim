import { startGuest } from '../../market/web/image-main.ts';
import '../../market/web/style.css';

const root = document.getElementById('market-image-root');
if (root) startGuest(root);
