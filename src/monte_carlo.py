import io
import re
import numpy as np
import pandas as pd
from collections import defaultdict
from scipy.optimize import linear_sum_assignment
from db import get_engine, get_raw_connection
from previsao import prever_jogo

np.random.seed(42)

NOMES_RODADA = {
    'R32': 'prob_grupo',
    'R16': 'prob_oitavas',
    'QF': 'prob_quartas',
    'SF': 'prob_semi',
    'FINAL': 'prob_final',
    'CHAMP': 'prob_campea'
}

_CACHE_LAMBDA = {}

def get_lambdas(t1, t2, neutro):
    key = tuple(sorted([t1, t2])) + (neutro,)
    if key not in _CACHE_LAMBDA:
        res = prever_jogo(key[0], key[1], neutro)
        # Sempre guarda na ordem de key[0], key[1]
        _CACHE_LAMBDA[key] = (res['gols_esperados_casa'], res['gols_esperados_visitante'])
            
    lam1, lam2 = _CACHE_LAMBDA[key]
    if key[0] != t1:
        return lam2, lam1
    return lam1, lam2

def slots_terceiros(terceiros, slot_names):
    """
    terceiros: lista de tuplas (time, grupo_de_origem)
    slot_names: lista de strings identificando os slots ex: "3A", "3B", etc.
    O calendário original aponta: "3rd A/B/C/D/E/F" que a carga filtra no silver.
    Assumimos que o slot_names vem como as strings puras do 'home_slot' ou 'away_slot'.
    """
    n = len(terceiros)
    m = len(slot_names)
    
    cost_matrix = np.full((n, m), 9999.0)
    
    for j, slot in enumerate(slot_names):
        valid_groups = [c for c in slot if c.isalpha() and c.isupper()]
            
        for i, (time, grupo) in enumerate(terceiros):
            if grupo in valid_groups:
                cost_matrix[i, j] = i
                
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    
    mapping = {}
    for i, j in zip(row_ind, col_ind):
        if cost_matrix[i, j] < 9999.0:
            mapping[slot_names[j]] = terceiros[i][0]
    
    return mapping

def preparar():
    engine = get_engine()
    df_jogos = pd.read_sql("SELECT id as match_id, time_casa, time_visitante, neutro FROM silver_copa2026 ORDER BY id", engine)
    
    df_grupos = pd.read_csv("data/grupos_copa2026.csv")
    df_calendario = pd.read_csv("data/calendario_copa2026.csv")
    df_calendario_mata = df_calendario[df_calendario['match_id'].str.startswith('M7') | 
                                      df_calendario['match_id'].str.startswith('M8') | 
                                      df_calendario['match_id'].str.startswith('M9') | 
                                      df_calendario['match_id'].str.startswith('M10')].copy()
    
    # Pré-aquecer cache com todos os jogos da fase de grupos para performance extrema (Evitando o overhead da chamadas sequenciais Pandas dentro do GLM predict)
    print("Pré-aquecendo Lambdas para fase de grupos...")
    for row in df_jogos.itertuples():
        get_lambdas(row.time_casa, row.time_visitante, row.neutro)
        
    return df_jogos, df_grupos, df_calendario_mata

def simular_uma_vez(df_jogos, df_grupos, df_calendario_mata):
    pontos = defaultdict(int)
    gols_pro = defaultdict(int)
    saldo_gols = defaultdict(int)
    
    # 1. Fase de Grupos
    for row in df_jogos.itertuples():
        t1, t2 = row.time_casa, row.time_visitante
        lam1, lam2 = get_lambdas(t1, t2, row.neutro)
        
        g1 = np.random.poisson(lam1)
        g2 = np.random.poisson(lam2)
        
        gols_pro[t1] += g1
        gols_pro[t2] += g2
        saldo_gols[t1] += (g1 - g2)
        saldo_gols[t2] += (g2 - g1)
        
        if g1 > g2:
            pontos[t1] += 3
        elif g1 < g2:
            pontos[t2] += 3
        else:
            pontos[t1] += 1
            pontos[t2] += 1
            
    # Classificar por grupo
    classificados_1 = {}
    classificados_2 = {}
    terceiros_list = []
    
    fases_alcancadas = defaultdict(lambda: 'OUT')
    
    for g, df_g in df_grupos.groupby('group'):
        times = df_g['nation'].tolist()
        
        # Sorteio (Tie-breaker)
        rands = np.random.rand(len(times))
        
        dados_grupo = []
        for i, t in enumerate(times):
            dados_grupo.append((pontos[t], saldo_gols[t], gols_pro[t], rands[i], t))
            
        dados_grupo.sort(reverse=True)
        
        classificados_1[f'1{g}'] = dados_grupo[0][4]
        classificados_2[f'2{g}'] = dados_grupo[1][4]
        terceiros_list.append((pontos[dados_grupo[2][4]], saldo_gols[dados_grupo[2][4]], gols_pro[dados_grupo[2][4]], np.random.rand(), dados_grupo[2][4], g))
    
    terceiros_list.sort(reverse=True)
    top_8_terceiros = [(t[4], t[5]) for t in terceiros_list[:8]]
    
    slots_3 = [s for s in df_calendario_mata['home_slot'].tolist() + df_calendario_mata['away_slot'].tolist() if s.startswith('3')]
    slots_3 = list(set(slots_3))
    
    mapa_terceiros = slots_terceiros(top_8_terceiros, slots_3)
    slots = {**classificados_1, **classificados_2, **mapa_terceiros}
    
    # 2. Mata-Mata
    for row in df_calendario_mata.itertuples():
        match_id = row.match_id
        
        h_slot = row.home_slot
        a_slot = row.away_slot
        
        t1 = slots.get(h_slot, h_slot)
        t2 = slots.get(a_slot, a_slot)
        
        # Tratamento emergencial se falhar mapeamento de slot
        if not t1 or not t2 or t1.startswith('1') or t1.startswith('2') or t1.startswith('3') or t1.startswith('W') or t1.startswith('RU') or t2.startswith('1') or t2.startswith('2') or t2.startswith('3') or t2.startswith('W') or t2.startswith('RU'):
            # Ignora placar limpo se der miss de bracket
            continue
            
        lam1, lam2 = get_lambdas(t1, t2, True)
        
        g1 = np.random.poisson(lam1)
        g2 = np.random.poisson(lam2)
        
        vencedor = t1
        perdedor = t2
        
        if g1 < g2:
            vencedor = t2
            perdedor = t1
        elif g1 == g2:
            if np.random.rand() < 0.5:
                vencedor = t1
                perdedor = t2
            else:
                vencedor = t2
                perdedor = t1
                
        slots[f'W{match_id[1:]}'] = vencedor
        slots[f'RU{match_id[1:]}'] = perdedor
        
        fases_alcancadas[t1] = match_id
        fases_alcancadas[t2] = match_id
        if match_id == 'M104':
            fases_alcancadas[vencedor] = 'CHAMP'
            
    for t, m in fases_alcancadas.items():
        if m == 'CHAMP':
            nivel = 6
        elif m == 'M104':
            nivel = 5
        elif m in ['M101', 'M102', 'M103']:
            nivel = 4
        elif m.startswith('M97') or m.startswith('M98') or m.startswith('M99') or m.startswith('M100'):
            nivel = 3
        elif m.startswith('M89') or m.startswith('M90') or m.startswith('M91') or m.startswith('M92') or m.startswith('M93') or m.startswith('M94') or m.startswith('M95') or m.startswith('M96'):
            nivel = 2
        elif m.startswith('M7') or m.startswith('M8'):
            nivel = 1
        else:
            nivel = 0
            
        fases_alcancadas[t] = nivel
        
    return fases_alcancadas

def main():
    print("Lendo parâmetros e preparando Monte Carlo...")
    df_jogos, df_grupos, df_calendario_mata = preparar()
    
    agregado = defaultdict(lambda: [0,0,0,0,0,0])
    
    N_SIMULACOES = 60000
    print(f"\nIniciando execução iterativa maciça: {N_SIMULACOES} Copas...")
    
    import time
    start = time.time()
    
    for i in range(N_SIMULACOES):
        if (i+1) % 5000 == 0:
            print(f"Progresso: {i+1} iterações...")
        fases = simular_uma_vez(df_jogos, df_grupos, df_calendario_mata)
        for t, nivel in fases.items():
            for lvl in range(1, nivel + 1):
                agregado[t][lvl-1] += 1
                
    end = time.time()
    print(f"\nSimulação finalizada em {end - start:.2f} segundos!")
                
    print("Calculando espaço probabilístico definitivo [0, 1]...")
    records = []
    for t, contagens in agregado.items():
        records.append({
            'selecao': t,
            'prob_grupo': contagens[0] / N_SIMULACOES,
            'prob_oitavas': contagens[1] / N_SIMULACOES,
            'prob_quartas': contagens[2] / N_SIMULACOES,
            'prob_semi': contagens[3] / N_SIMULACOES,
            'prob_final': contagens[4] / N_SIMULACOES,
            'prob_campea': contagens[5] / N_SIMULACOES
        })
        
    todas_selecoes = df_grupos['nation'].tolist()
    inseridas = [r['selecao'] for r in records]
    for t in todas_selecoes:
        if t not in inseridas:
            records.append({
                'selecao': t,
                'prob_grupo': 0.0,
                'prob_oitavas': 0.0,
                'prob_quartas': 0.0,
                'prob_semi': 0.0,
                'prob_final': 0.0,
                'prob_campea': 0.0
            })
            
    df_res = pd.DataFrame(records)
    
    print("\n--- Top 10 Favoritos à Taça (Copa 2026) ---")
    print(df_res.sort_values('prob_campea', ascending=False).head(10)[['selecao', 'prob_campea']])
    print("-------------------------------------------\n")
    
    print("Persistindo ouro em gold_probabilidades_copa...")
    conn = get_raw_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS gold_probabilidades_copa;")
            cur.execute("""
                CREATE TABLE gold_probabilidades_copa (
                    id bigint generated always as identity primary key,
                    selecao text,
                    prob_grupo double precision,
                    prob_oitavas double precision,
                    prob_quartas double precision,
                    prob_semi double precision,
                    prob_final double precision,
                    prob_campea double precision
                );
            """)
            
            buffer = io.StringIO()
            df_res.to_csv(buffer, index=False, header=False, na_rep="")
            buffer.seek(0)
            
            cur.copy_expert(
                sql="COPY gold_probabilidades_copa (selecao, prob_grupo, prob_oitavas, prob_quartas, prob_semi, prob_final, prob_campea) FROM STDIN WITH (FORMAT csv, NULL '')",
                file=buffer,
            )
            
        conn.commit()
        print("Mesa de Palpites Fechada e gravada com sucesso!")
        
    except Exception as e:
        conn.rollback()
        print(f"Erro ao salvar probabilidades: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    main()
