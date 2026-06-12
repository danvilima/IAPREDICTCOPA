import io
import pickle
import numpy as np
import pandas as pd
import statsmodels.api as sm
from db import get_engine, get_raw_connection
from poisson import probabilidades_resultado

# Variáveis globais de Cache
_MODELO_CASA = None
_MODELO_VISITANTE = None
_COLUNAS_ATRIBUTOS = None
_ELO_ATUAL = None

def carregar_modelos():
    global _MODELO_CASA, _MODELO_VISITANTE, _COLUNAS_ATRIBUTOS, _ELO_ATUAL
    if _MODELO_CASA is None:
        with open('models/modelo_poisson_casa.pkl', 'rb') as f:
            _MODELO_CASA = pickle.load(f)
        with open('models/modelo_poisson_visitante.pkl', 'rb') as f:
            _MODELO_VISITANTE = pickle.load(f)
        with open('models/colunas_atributos.pkl', 'rb') as f:
            _COLUNAS_ATRIBUTOS = pickle.load(f)
            
        engine = get_engine()
        df_elo = pd.read_sql("SELECT selecao, elo FROM silver_elo_atual", engine)
        _ELO_ATUAL = dict(zip(df_elo['selecao'], df_elo['elo']))

def obter_elo(selecao):
    return _ELO_ATUAL.get(selecao, 1500.0)

def estimar_lambdas(elo_c, elo_v, neutro):
    df_inf = pd.DataFrame([{
        'elo_casa': elo_c,
        'elo_visitante': elo_v,
        'dif_elo': elo_c - elo_v,
        'neutro': int(neutro)
    }])
    
    # Criar matriz X garantindo as colunas exatas
    X = sm.add_constant(df_inf[_COLUNAS_ATRIBUTOS], has_constant='add')
    if 'const' not in X.columns:
        X.insert(0, 'const', 1.0)
        
    lam_c = _MODELO_CASA.predict(X).iloc[0]
    lam_v = _MODELO_VISITANTE.predict(X).iloc[0]
    return lam_c, lam_v

def prever_jogo(time_casa, time_visitante, neutro):
    carregar_modelos()
    
    elo_c = obter_elo(time_casa)
    elo_v = obter_elo(time_visitante)
    
    if neutro:
        # Simetrização obrigatória para campo neutro
        # Evita viés artificial de mandante que o Poisson possa ter absorvido
        lam_c1, lam_v1 = estimar_lambdas(elo_c, elo_v, True)
        lam_c2, lam_v2 = estimar_lambdas(elo_v, elo_c, True)
        lam_casa = (lam_c1 + lam_v2) / 2.0
        lam_visitante = (lam_v1 + lam_c2) / 2.0
    else:
        lam_casa, lam_visitante = estimar_lambdas(elo_c, elo_v, False)
        
    probs = probabilidades_resultado(lam_casa, lam_visitante)
    
    return {
        'time_casa': time_casa,
        'time_visitante': time_visitante,
        'gols_esperados_casa': lam_casa,
        'gols_esperados_visitante': lam_visitante,
        'prob_vitoria': probs['prob_vitoria'],
        'prob_empate': probs['prob_empate'],
        'prob_derrota': probs['prob_derrota']
    }

def executar_experimentos():
    print("\nIniciando bateria de experimentos de MAE com decaimento temporal...")
    engine = get_engine()
    df = pd.read_sql("SELECT * FROM gold_atributos ORDER BY data, ponderado_id", engine)
    df['data'] = pd.to_datetime(df['data'])
    df['neutro'] = df['neutro'].astype(int)
    
    # Split estrito igual a Validação da Feature 06
    df_treino = df[df['data'] < '2024-01-01'].copy()
    df_teste = df[df['data'] >= '2024-01-01'].copy()
    
    DATA_REF = pd.to_datetime('2026-06-11')
    idade_anos_treino = ((DATA_REF - df_treino['data']).dt.days / 365.25).clip(lower=0)
    idade_anos_teste = ((DATA_REF - df_teste['data']).dt.days / 365.25).clip(lower=0)
    
    colunas_preditivas = ['elo_casa', 'elo_visitante', 'dif_elo', 'neutro']
    
    configs = {
        'sem_recencia': None,
        'meia_vida_3': 3,
        'meia_vida_5': 5,
        'meia_vida_10': 10
    }
    
    resultados_mae = []
    
    for nome, h in configs.items():
        print(f"Treinando config: {nome}...")
        df_tr_exp = df_treino.copy()
        
        if h is None:
            df_tr_exp['peso_recencia_temp'] = 1.0
        else:
            df_tr_exp['peso_recencia_temp'] = 0.5 ** (idade_anos_treino / h)
            
        # Matriz X limpa
        X_tr = sm.add_constant(df_tr_exp[colunas_preditivas], has_constant='add')
        X_te = sm.add_constant(df_teste[colunas_preditivas], has_constant='add')
        if 'const' not in X_tr.columns:
            X_tr.insert(0, 'const', 1.0)
            X_te.insert(0, 'const', 1.0)
            
        y_c = df_tr_exp['gols_casa'].astype(float)
        y_v = df_tr_exp['gols_visitante'].astype(float)
        
        y_c_te = df_teste['gols_casa'].astype(float)
        y_v_te = df_teste['gols_visitante'].astype(float)
        
        # Ponderação de amostra sem vazar como feature preditiva
        pesos = df_tr_exp['peso_torneio'] * df_tr_exp['peso_recencia_temp']
        
        # Uso obrigatório de freq_weights
        mod_c = sm.GLM(y_c, X_tr, family=sm.families.Poisson(), freq_weights=pesos).fit()
        mod_v = sm.GLM(y_v, X_tr, family=sm.families.Poisson(), freq_weights=pesos).fit()
        
        lam_c = mod_c.predict(X_te)
        lam_v = mod_v.predict(X_te)
        
        mae_c = np.mean(np.abs(lam_c - y_c_te))
        mae_v = np.mean(np.abs(lam_v - y_v_te))
        
        resultados_mae.append({
            'config': nome,
            'mae_casa': mae_c,
            'mae_visitante': mae_v
        })
        
    return pd.DataFrame(resultados_mae)

def main():
    print("Gerando previsões oficiais para a Copa 2026...")
    engine = get_engine()
    df_copa = pd.read_sql("SELECT time_casa, time_visitante, neutro FROM silver_copa2026 ORDER BY id", engine)
    
    previsoes = []
    for row in df_copa.itertuples():
        p = prever_jogo(row.time_casa, row.time_visitante, row.neutro)
        previsoes.append(p)
        
    df_previsoes = pd.DataFrame(previsoes)
    
    df_experimentos = executar_experimentos()
    
    print("\n--- Relatório Experimentos MAE ---")
    print(df_experimentos.sort_values('mae_casa'))
    print("----------------------------------\n")
    
    print("Gravando tabelas (previsoes, experimentos_mae) no banco...")
    conn = get_raw_connection()
    try:
        with conn.cursor() as cur:
            # Tabela de previsoes
            cur.execute("DROP TABLE IF EXISTS previsoes;")
            cur.execute("""
                CREATE TABLE previsoes (
                    id bigint generated always as identity primary key,
                    time_casa text,
                    time_visitante text,
                    gols_esperados_casa double precision,
                    gols_esperados_visitante double precision,
                    prob_vitoria double precision,
                    prob_empate double precision,
                    prob_derrota double precision
                );
            """)
            
            buffer_prev = io.StringIO()
            df_previsoes.to_csv(buffer_prev, index=False, header=False, na_rep="")
            buffer_prev.seek(0)
            
            cur.copy_expert(
                sql="COPY previsoes (time_casa, time_visitante, gols_esperados_casa, gols_esperados_visitante, prob_vitoria, prob_empate, prob_derrota) FROM STDIN WITH (FORMAT csv, NULL '')",
                file=buffer_prev,
            )
            
            # Tabela de experimentos
            cur.execute("DROP TABLE IF EXISTS experimentos_mae;")
            cur.execute("""
                CREATE TABLE experimentos_mae (
                    id bigint generated always as identity primary key,
                    config text,
                    mae_casa double precision,
                    mae_visitante double precision
                );
            """)
            
            buffer_exp = io.StringIO()
            df_experimentos.to_csv(buffer_exp, index=False, header=False, na_rep="")
            buffer_exp.seek(0)
            
            cur.copy_expert(
                sql="COPY experimentos_mae (config, mae_casa, mae_visitante) FROM STDIN WITH (FORMAT csv, NULL '')",
                file=buffer_exp,
            )
            
        conn.commit()
        print("Previsões e Experimentos salvos com sucesso!")
        
    except Exception as e:
        conn.rollback()
        print(f"Erro na gravação: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    main()
