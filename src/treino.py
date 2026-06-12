import os
import io
import pickle
import numpy as np
import pandas as pd
import statsmodels.api as sm
from db import get_engine, get_raw_connection
from poisson import resultado_previsto, resultado_real

# Constantes Restritivas de Input
COLUNAS_ATRIBUTOS = [
    "elo_casa",
    "elo_visitante",
    "dif_elo",
    "neutro",
]

COLUNAS_OBRIGATORIAS = [
    "data",
    "elo_casa",
    "elo_visitante",
    "dif_elo",
    "neutro",
    "peso_amostra",
    "gols_casa",
    "gols_visitante",
]

def montar_X(df):
    """
    Função padronizada para montagem da matriz de features preditivas.
    Exclui pesos e alvos garantindo bloqueio contra vazamentos.
    """
    X = df[COLUNAS_ATRIBUTOS].copy()
    X["neutro"] = X["neutro"].astype(int)
    X = sm.add_constant(X, has_constant="add")
    return X

def main():
    print("Conectando ao banco para ler gold_atributos...")
    engine = get_engine()
    
    query = """
        SELECT *
        FROM gold_atributos
        ORDER BY data, ponderado_id;
    """
    df = pd.read_sql(query, engine)
    
    # Garantir datetime puro para o split
    df['data'] = pd.to_datetime(df['data'])
    
    print("Validando entradas e restrições obrigatórias...")
    # Asserts Obrigatórios
    assert df[COLUNAS_OBRIGATORIAS].isna().sum().sum() == 0, "Falha: Dados nulos detectados no dataframe."
    assert (df["peso_amostra"] > 0).all(), "Falha: Existência de peso_amostra nulo ou negativo."
    assert (df["gols_casa"] >= 0).all(), "Falha: Gols negativos na casa."
    assert (df["gols_visitante"] >= 0).all(), "Falha: Gols negativos no visitante."
    
    print("Realizando split temporal de dados...")
    DATA_SPLIT = pd.Timestamp("2024-01-01")
    
    treino = df[df["data"] < DATA_SPLIT].copy()
    teste = df[df["data"] >= DATA_SPLIT].copy()
    
    n_treino = len(treino)
    n_teste = len(teste)
    print(f"Volume do Treino (Validação): {n_treino}")
    print(f"Volume do Teste (Validação): {n_teste}")
    
    # Alvos de Validação
    y_casa_treino = treino["gols_casa"].astype(float)
    y_visit_treino = treino["gols_visitante"].astype(float)
    
    y_casa_teste = teste["gols_casa"].astype(float)
    y_visit_teste = teste["gols_visitante"].astype(float)
    
    # Features e Pesos de Validação
    X_treino = montar_X(treino)
    X_teste = montar_X(teste)
    
    peso_treino = treino["peso_amostra"]
    
    print("\n--- Fase de Validação ---")
    print("Treinando modelos Poisson GLM (Casa e Visitante)...")
    modelo_casa_validacao = sm.GLM(
        y_casa_treino,
        X_treino,
        family=sm.families.Poisson(),
        freq_weights=peso_treino
    ).fit()
    
    modelo_visitante_validacao = sm.GLM(
        y_visit_treino,
        X_treino,
        family=sm.families.Poisson(),
        freq_weights=peso_treino
    ).fit()
    
    print("Predizendo Lambdas no conjunto de Teste...")
    lambda_casa_teste = modelo_casa_validacao.predict(X_teste)
    lambda_visitante_teste = modelo_visitante_validacao.predict(X_teste)
    
    print("Calculando Métricas...")
    mae_casa = abs(lambda_casa_teste - y_casa_teste).mean()
    mae_visitante = abs(lambda_visitante_teste - y_visit_teste).mean()
    
    previstos = []
    reais = []
    
    for lc, lv, gc, gv in zip(
        lambda_casa_teste,
        lambda_visitante_teste,
        y_casa_teste,
        y_visit_teste
    ):
        previstos.append(resultado_previsto(lc, lv))
        reais.append(resultado_real(gc, gv))
        
    acuracia = np.mean(np.array(previstos) == np.array(reais))
    
    print(f"MAE Estimado Casa: {mae_casa:.4f}")
    print(f"MAE Estimado Visitante: {mae_visitante:.4f}")
    print(f"Acurácia Absoluta (Resultado): {acuracia:.4f}")
    
    print("\nGravando tabela de metricas_validacao...")
    conn = get_raw_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS metricas_validacao;")
            cur.execute("""
                CREATE TABLE metricas_validacao (
                    id bigint generated always as identity primary key,
                    data_execucao timestamp default now(),
                    mae_casa double precision,
                    mae_visitante double precision,
                    acuracia double precision,
                    n_treino integer,
                    n_teste integer
                );
            """)
            
            df_metricas = pd.DataFrame([{
                'mae_casa': mae_casa,
                'mae_visitante': mae_visitante,
                'acuracia': acuracia,
                'n_treino': n_treino,
                'n_teste': n_teste
            }])
            
            buffer = io.StringIO()
            df_metricas.to_csv(buffer, index=False, header=False, na_rep="")
            buffer.seek(0)
            
            cur.copy_expert(
                sql="COPY metricas_validacao (mae_casa, mae_visitante, acuracia, n_treino, n_teste) FROM STDIN WITH (FORMAT csv, NULL '')",
                file=buffer,
            )
            
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Erro ao salvar métricas: {e}")
        raise
    finally:
        conn.close()

    print("\n--- Fase de Treinamento de Produção ---")
    print("Retreinando Modelos Finais em toda a base (gold_atributos)...")
    
    X_final = montar_X(df)
    peso_final = df["peso_amostra"]
    
    modelo_casa_final = sm.GLM(
        df["gols_casa"].astype(float),
        X_final,
        family=sm.families.Poisson(),
        freq_weights=peso_final
    ).fit()
    
    modelo_visitante_final = sm.GLM(
        df["gols_visitante"].astype(float),
        X_final,
        family=sm.families.Poisson(),
        freq_weights=peso_final
    ).fit()
    
    print("Arquivando modelos para produção (.pkl)...")
    os.makedirs('models', exist_ok=True)
    with open('models/modelo_poisson_casa.pkl', 'wb') as f:
        pickle.dump(modelo_casa_final, f)
        
    with open('models/modelo_poisson_visitante.pkl', 'wb') as f:
        pickle.dump(modelo_visitante_final, f)
        
    with open('models/colunas_atributos.pkl', 'wb') as f:
        pickle.dump(COLUNAS_ATRIBUTOS, f)
        
    print("Pipeline de Machine Learning concluída com sucesso!")

if __name__ == '__main__':
    main()
