"""Importa a planilha AGR0190.xlsx para o banco SQLite.

Uso:  python importar_agr0190.py AGR0190.xlsx [--db colheita.db] [--reset]
"""
import argparse, sqlite3, sys
from pathlib import Path
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument("xlsx")
ap.add_argument("--db", default="colheita.db")
ap.add_argument("--reset", action="store_true", help="apaga o banco antes de importar")
a = ap.parse_args()

db = Path(a.db)
if a.reset and db.exists():
    db.unlink()

df = pd.read_excel(a.xlsx)
obrig = ["FAZENDA", "Propriedade Rural", "Código TALHAO", "Área Líquida (ha)", "Ativo Talhão",
         "FRENTE CORTE", "TON/ha", "Produção (TON)"]
falta = [c for c in obrig if c not in df.columns]
if falta:
    sys.exit(f"Colunas ausentes na planilha: {falta}")

txt = lambda s: s.fillna("").astype(str).str.strip()
df["cod"] = txt(df["Propriedade Rural"]).str.split(" - ").str[0].str.strip()
df["nome"] = txt(df["FAZENDA"])
df["frente"] = txt(df["FRENTE CORTE"])
df["ult"] = pd.to_datetime(df["Data da Última Colheita"], errors="coerce").dt.strftime("%Y-%m-%d")
num = lambda c: pd.to_numeric(df[c], errors="coerce").fillna(0)

con = sqlite3.connect(db)
con.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
con.execute("PRAGMA foreign_keys = ON")

with con:
    # frentes (mantém ton_media_dia já cadastrada)
    for f in sorted(x for x in df["frente"].unique() if x):
        con.execute("INSERT OR IGNORE INTO frente(nome) VALUES (?)", (f,))
    fr = dict(con.execute("SELECT nome, id FROM frente"))

    # fazendas
    for (cod, nome), g in df.groupby(["cod", "nome"]):
        km = pd.to_numeric(g["Média (Km)"], errors="coerce")
        raio = round(float(km[km > 0].mean()), 1) if (km > 0).any() else 0
        con.execute(
            "INSERT INTO fazenda(cod_propriedade,nome,tipo,raio_km) VALUES (?,?,?,?) "
            "ON CONFLICT(cod_propriedade,nome) DO UPDATE SET tipo=excluded.tipo, raio_km=excluded.raio_km",
            (cod, nome, str(g["Tipo"].iloc[0]), raio))
    fz = {(c, n): i for i, c, n in con.execute("SELECT id,cod_propriedade,nome FROM fazenda")}

    # talhões (recarrega as estimativas)
    con.execute("DELETE FROM talhao")
    rows = []
    for i, r in df.iterrows():
        rows.append((fz[(r["cod"], r["nome"])], str(r["Código TALHAO"]), float(num("Área Líquida (ha)")[i]),
                     1 if r["Ativo Talhão"] == "Sim" else 0, str(r.get("Tipo", "") or ""),
                     r["ult"] if isinstance(r["ult"], str) else None, fr.get(r["frente"]),
                     str(r.get("APLICAÇÃO DE MATURADOR", "") or "").replace("nan", ""),
                     1 if str(r.get("AREA FERTIRRIGADA", "")).strip().upper().startswith("AREA") else 0,
                     float(num("TON/ha")[i]), float(num("Produção (TON)")[i])))
    con.executemany("INSERT INTO talhao(fazenda_id,codigo,area_ha,ativo,tipo,data_ultima_colheita,frente_id,"
                    "maturador,fertirrigado,tch_previsto,ton_prevista) VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)

    # produção real (somente por fazenda)
    df["rt"], df["rh"] = num("Produção Real (TON)"), num("Área Colhida (ha)")
    for (cod, nome), g in df.groupby(["cod", "nome"]):
        t, h = g["rt"].sum(), g["rh"].sum()
        if t > 0:
            con.execute("INSERT INTO producao_real(fazenda_id,ton_real,tch_real) VALUES (?,?,?) "
                        "ON CONFLICT(fazenda_id) DO NOTHING",
                        (fz[(cod, nome)], round(t, 2), round(t / h, 2) if h else None))

for t in ("frente", "fazenda", "talhao", "producao_real"):
    print(f"{t:15s}", con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
con.close()
