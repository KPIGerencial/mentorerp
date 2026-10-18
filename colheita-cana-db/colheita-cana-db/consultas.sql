-- Resumo por frente (raio médio, dias de corte, equipamentos)
SELECT * FROM v_frente_resumo;

-- Fazendas com maior produção prevista
SELECT z.nome, z.raio_km, ROUND(SUM(t.area_ha),1) AS ha, ROUND(SUM(t.ton_prevista)) AS ton
FROM fazenda z JOIN talhao t ON t.fazenda_id=z.id AND t.ativo=1
GROUP BY z.id ORDER BY ton DESC LIMIT 20;

-- Previsto x real por fazenda
SELECT z.nome, ROUND(SUM(t.ton_prevista)) AS ton_prevista, p.ton_real, p.tch_real,
       ROUND((p.ton_real/NULLIF(SUM(t.ton_prevista),0)-1)*100,1) AS dif_pct
FROM producao_real p JOIN fazenda z ON z.id=p.fazenda_id
JOIN talhao t ON t.fazenda_id=z.id AND t.ativo=1
GROUP BY z.id ORDER BY dif_pct;
