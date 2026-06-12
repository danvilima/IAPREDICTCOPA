import io
import pandas as pd
from db import get_engine, get_raw_connection

def main():
    print("Conectando ao banco para consolidar gold_atributos...")
    engine = get_engine()
    
    # 1. Join SQL por ponderado_id e exclusão de amistosos
    query = """
        SELECT
            s.id AS ponderado_id,
            s.jogo_id,
            s.data,
            s.time_casa,
            s.time_visitante,
            e.elo_casa,
            e.elo_visitante,
            s.neutro,
            s.peso_torneio,
            s.peso_recencia,
            s.gols_casa,
            s.gols_visitante
        FROM silver_ponderado s
        JOIN silver_elo_pre_jogo e ON e.ponderado_id = s.id
        WHERE s.eh_amistoso = false
        ORDER BY s.data, s.id;
    """
    df = pd.read_sql(query, engine)
    
    # Garantir tipagens corretas do Pandas
    df['data'] = pd.to_datetime(df['data'])
    df['gols_casa'] = df['gols_casa'].astype('Int64')
    df['gols_visitante'] = df['gols_visitante'].astype('Int64')
    
    print("Engenharia de features (dif_elo e peso_amostra)...")
    # 2. Derivação
    df['dif_elo'] = df['elo_casa'] - df['elo_visitante']
    df['peso_amostra'] = df['peso_torneio'] * df['peso_recencia']
    
    # 3. Asserção Anti-nulos em TODOS os atributos vitais do ML
    print("Validando sanidade dos atributos...")
    COLUNAS_SEM_NULOS = [
        "ponderado_id", "jogo_id", "data", "time_casa", "time_visitante",
        "elo_casa", "elo_visitante", "dif_elo", "neutro", 
        "peso_torneio", "peso_recencia", "peso_amostra", 
        "gols_casa", "gols_visitante"
    ]
    nulos = df[COLUNAS_SEM_NULOS].isnull().sum().sum()
    assert nulos == 0, f"Falha de Asserção: Encontrados {nulos} valores nulos nos atributos."
    
    # Reordenar colunas para bater com o formato esperado de gravação
    df = df[COLUNAS_SEM_NULOS]
    
    # Ordenação extra por Pandas para garantir determinismo total
    df = df.sort_values(by=["data", "ponderado_id"]).reset_index(drop=True)
    
    print(f"\n--- Relatório Gold ---")
    print(f"Total de jogos competitivos filtrados: {len(df)}")
    print("Amostra das features construídas:")
    print(df[['time_casa', 'time_visitante', 'dif_elo', 'peso_amostra', 'gols_casa']].head(3))
    print("----------------------\n")
    
    # 4. Gravação idempotente no banco via psycopg2
    print("Gravando tabela gold_atributos...")
    conn = get_raw_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS gold_atributos;")
            cur.execute("""
                CREATE TABLE gold_atributos (
                    id bigint generated always as identity primary key,
                    ponderado_id bigint,
                    jogo_id bigint,
                    data date,
                    time_casa text,
                    time_visitante text,
                    elo_casa double precision,
                    elo_visitante double precision,
                    dif_elo double precision,
                    neutro boolean,
                    peso_torneio integer,
                    peso_recencia double precision,
                    peso_amostra double precision,
                    gols_casa integer,
                    gols_visitante integer
                );
            """)
            
            buffer = io.StringIO()
            df.to_csv(buffer, index=False, header=False, na_rep="")
            buffer.seek(0)
            
            cur.copy_expert(
                sql="COPY gold_atributos (ponderado_id, jogo_id, data, time_casa, time_visitante, elo_casa, elo_visitante, dif_elo, neutro, peso_torneio, peso_recencia, peso_amostra, gols_casa, gols_visitante) FROM STDIN WITH (FORMAT csv, NULL '')",
                file=buffer,
            )
            
        conn.commit()
        print("Dataset de ML gold_atributos gerado com sucesso!")
        
    except Exception as e:
        conn.rollback()
        print(f"Erro ao salvar gold_atributos: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    main()
