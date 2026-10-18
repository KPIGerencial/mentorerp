-- Banco de dados: planejamento de colheita de cana-de-açúcar
-- SQLite (portável para PostgreSQL trocando INTEGER PRIMARY KEY por GENERATED ... AS IDENTITY)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS frente (
  id            INTEGER PRIMARY KEY,
  nome          TEXT NOT NULL UNIQUE,          -- ex.: FRENTE-01
  ton_media_dia REAL NOT NULL DEFAULT 0        -- TON MÉDIA da frente (t/dia)
);

CREATE TABLE IF NOT EXISTS fazenda (
  id               INTEGER PRIMARY KEY,
  cod_propriedade  TEXT NOT NULL,              -- código da Propriedade Rural
  nome             TEXT NOT NULL,
  tipo             TEXT,                       -- ACIONISTA / FORNECEDOR
  raio_km          REAL NOT NULL DEFAULT 0,    -- distância média até a usina
  UNIQUE (cod_propriedade, nome)
);

CREATE TABLE IF NOT EXISTS talhao (            -- estimativa de safra
  id                    INTEGER PRIMARY KEY,
  fazenda_id            INTEGER NOT NULL REFERENCES fazenda(id) ON DELETE CASCADE,
  codigo                TEXT NOT NULL,         -- Código TALHAO
  area_ha               REAL NOT NULL DEFAULT 0, -- Área Líquida (ha) = área prevista
  ativo                 INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0,1)),
  tipo                  TEXT,
  data_ultima_colheita  TEXT,                  -- AAAA-MM-DD
  frente_id             INTEGER REFERENCES frente(id),  -- FRENTE CORTE
  maturador             TEXT,                  -- APLICAÇÃO DE MATURADOR (dd-mm)
  fertirrigado          INTEGER NOT NULL DEFAULT 0 CHECK (fertirrigado IN (0,1)),
  tch_previsto          REAL NOT NULL DEFAULT 0, -- TON/ha
  ton_prevista          REAL NOT NULL DEFAULT 0  -- Produção (TON)
);
CREATE INDEX IF NOT EXISTS ix_talhao_fazenda ON talhao(fazenda_id);
CREATE INDEX IF NOT EXISTS ix_talhao_frente  ON talhao(frente_id);

CREATE TABLE IF NOT EXISTS atr (
  id         INTEGER PRIMARY KEY,
  fazenda_id INTEGER NOT NULL REFERENCES fazenda(id) ON DELETE CASCADE,
  data       TEXT NOT NULL,
  atr_kg_t   REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS frete (
  id            INTEGER PRIMARY KEY,
  transportador TEXT NOT NULL,
  frente_id     INTEGER REFERENCES frente(id),
  km_de         REAL NOT NULL DEFAULT 0,
  km_ate        REAL NOT NULL DEFAULT 0,
  valor_ton     REAL NOT NULL DEFAULT 0        -- R$/t
);

CREATE TABLE IF NOT EXISTS colhedora (
  id        INTEGER PRIMARY KEY,
  codigo    TEXT NOT NULL UNIQUE,
  modelo    TEXT,
  frente_id INTEGER REFERENCES frente(id),
  status    TEXT NOT NULL DEFAULT 'Ativa' CHECK (status IN ('Ativa','Manutenção','Inativa'))
);

CREATE TABLE IF NOT EXISTS transbordo (
  id        INTEGER PRIMARY KEY,
  codigo    TEXT NOT NULL UNIQUE,
  modelo    TEXT,
  frente_id INTEGER REFERENCES frente(id),
  status    TEXT NOT NULL DEFAULT 'Ativa' CHECK (status IN ('Ativa','Manutenção','Inativa'))
);

-- Produção real: cadastro somente da fazenda
CREATE TABLE IF NOT EXISTS producao_real (
  fazenda_id INTEGER PRIMARY KEY REFERENCES fazenda(id) ON DELETE CASCADE,
  ton_real   REAL NOT NULL DEFAULT 0,
  tch_real   REAL
);

-- Resumo por frente: raio médio ponderado pela produção prevista das fazendas da frente
CREATE VIEW IF NOT EXISTS v_frente_resumo AS
SELECT f.nome AS frente,
       f.ton_media_dia,
       COUNT(DISTINCT t.fazenda_id)                         AS fazendas,
       COUNT(t.id)                                          AS talhoes,
       ROUND(SUM(t.area_ha),1)                              AS area_ha,
       ROUND(SUM(t.ton_prevista),0)                         AS ton_prevista,
       ROUND(SUM(t.ton_prevista)/NULLIF(SUM(t.area_ha),0),1) AS tch_previsto,
       ROUND(SUM(t.ton_prevista*z.raio_km)/NULLIF(SUM(t.ton_prevista),0),1) AS raio_medio_km,
       ROUND(SUM(t.ton_prevista)/NULLIF(f.ton_media_dia,0),1) AS dias_de_corte,
       (SELECT COUNT(*) FROM colhedora  c WHERE c.frente_id=f.id AND c.status<>'Inativa') AS colhedoras,
       (SELECT COUNT(*) FROM transbordo b WHERE b.frente_id=f.id AND b.status<>'Inativa') AS transbordos
FROM frente f
LEFT JOIN talhao t ON t.frente_id=f.id AND t.ativo=1
LEFT JOIN fazenda z ON z.id=t.fazenda_id
GROUP BY f.id;
