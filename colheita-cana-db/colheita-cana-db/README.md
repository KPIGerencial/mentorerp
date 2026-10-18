# Banco de dados: colheita de cana

SQLite local, sem servidor. Tabelas: `frente`, `fazenda`, `talhao` (estimativa), `atr`, `frete`,
`colhedora`, `transbordo`, `producao_real` (somente por fazenda) e a view `v_frente_resumo`
(raio médio ponderado, dias de corte, equipamentos por frente).

## Passo a passo no VS Code
1. Abra esta pasta (Arquivo > Abrir Pasta) e coloque `AGR0190.xlsx` dentro dela.
2. Extensões: **Python** e **SQLite Viewer** (ou **SQLite**, de alexcvzz).
3. Terminal (Ctrl+`):
   ```
   python -m venv .venv
   .venv\Scripts\activate        # Linux/macOS: source .venv/bin/activate
   pip install -r requirements.txt
   python importar_agr0190.py AGR0190.xlsx --reset
   ```
4. Clique em `colheita.db` para navegar nas tabelas. Rode `consultas.sql` com a extensão SQLite.

Reimportar sem `--reset` recarrega os talhões e mantém ton média das frentes, ATR, fretes,
colhedoras, transbordos e produção real já cadastrados.
