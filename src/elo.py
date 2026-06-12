import io
import pandas as pd
from collections import defaultdict
from db import get_engine, get_raw_connection

ELO_INICIAL = 1500.0
HFA_VALUE = 100

K_POR_TORNEIO = {
    1: 20,
    2: 40,
    3: 60,
}

def main():
    print("Conectando ao banco para ler silver_ponderado...")
    engine = get_engine()
    
    # 1. Leitura cronológica estrita
    query = """
        SELECT id AS ponderado_id, jogo_id, data, time_casa, time_visitante, 
               gols_casa, gols_visitante, neutro, peso_torneio, torneio
        FROM silver_ponderado
        ORDER BY data, id
    """
    df = pd.read_sql(query, engine)
    
    # Validações de segurança
    assert df["gols_casa"].notna().all(), "Erro: Existem gols nulos em gols_casa na silver_ponderado."
    assert df["gols_visitante"].notna().all(), "Erro: Existem gols nulos em gols_visitante na silver_ponderado."
    
    # Sort determinístico do pandas para garantir redundância do Order By
    df = df.sort_values(["data", "ponderado_id"]).reset_index(drop=True)
    
    elos = defaultdict(lambda: ELO_INICIAL)
    pre_jogo_records = []
    
    print("Calculando ELO jogo a jogo...")
    
    for row in df.itertuples():
        casa = row.time_casa
        visitante = row.time_visitante
        
        # 1. Buscar ELO atual pré-jogo
        elo_casa = elos[casa]
        elo_visitante = elos[visitante]
        
        # 2. Gravar pré-jogo
        pre_jogo_records.append({
            'ponderado_id': row.ponderado_id,
            'jogo_id': row.jogo_id,
            'data': row.data,
            'time_casa': casa,
            'time_visitante': visitante,
            'elo_casa': elo_casa,
            'elo_visitante': elo_visitante
        })
        
        # 3. Definir HFA
        hfa = 0 if row.neutro else HFA_VALUE
        
        # 4. Calcular expectativa (com - hfa para o time da casa)
        e_casa = 1 / (1 + 10 ** ((elo_visitante - elo_casa - hfa) / 400))
        e_visitante = 1 - e_casa
        
        # 5. Resultado Real
        if row.gols_casa > row.gols_visitante:
            s_casa = 1.0
        elif row.gols_casa == row.gols_visitante:
            s_casa = 0.5
        else:
            s_casa = 0.0
            
        s_visitante = 1.0 - s_casa
        
        # 6. K-Factor
        K = K_POR_TORNEIO.get(row.peso_torneio, 20)
        
        # 7. Atualizar ELO
        elos[casa] += K * (s_casa - e_casa)
        elos[visitante] += K * (s_visitante - e_visitante)

    df_pre_jogo = pd.DataFrame(pre_jogo_records)
    df_atual = pd.DataFrame([
        {'selecao': selecao, 'elo': elo}
        for selecao, elo in elos.items()
    ])
    
    print(f"\n--- Relatório ELO ---")
    print(f"Jogos processados (pre_jogo): {len(df_pre_jogo)}")
    print(f"Seleções ativas no banco (atual): {len(df_atual)}")
    print("Top 10 Forças no momento:")
    print(df_atual.sort_values('elo', ascending=False).head(10))
    print("---------------------\n")
    
    print("Gravando tabelas no banco de dados...")
    conn = get_raw_connection()
    try:
        with conn.cursor() as cur:
            # silver_elo_pre_jogo
            print("Recriando silver_elo_pre_jogo...")
            cur.execute("DROP TABLE IF EXISTS silver_elo_pre_jogo;")
            cur.execute("""
                CREATE TABLE silver_elo_pre_jogo (
                    id bigint generated always as identity primary key,
                    ponderado_id bigint,
                    jogo_id bigint,
                    data date,
                    time_casa text,
                    time_visitante text,
                    elo_casa double precision,
                    elo_visitante double precision
                );
            """)
            
            buffer_pre = io.StringIO()
            df_pre_jogo.to_csv(buffer_pre, index=False, header=False, na_rep="")
            buffer_pre.seek(0)
            cur.copy_expert(
                sql="COPY silver_elo_pre_jogo (ponderado_id, jogo_id, data, time_casa, time_visitante, elo_casa, elo_visitante) FROM STDIN WITH (FORMAT csv, NULL '')",
                file=buffer_pre,
            )
            
            # silver_elo_atual
            print("Recriando silver_elo_atual...")
            cur.execute("DROP TABLE IF EXISTS silver_elo_atual;")
            cur.execute("""
                CREATE TABLE silver_elo_atual (
                    id bigint generated always as identity primary key,
                    selecao text,
                    elo double precision
                );
            """)
            
            buffer_atual = io.StringIO()
            df_atual.to_csv(buffer_atual, index=False, header=False, na_rep="")
            buffer_atual.seek(0)
            cur.copy_expert(
                sql="COPY silver_elo_atual (selecao, elo) FROM STDIN WITH (FORMAT csv, NULL '')",
                file=buffer_atual,
            )
            
        conn.commit()
        print("Tabelas de ELO criadas e carregadas com sucesso!")
        
    except Exception as e:
        conn.rollback()
        print(f"Erro ao salvar tabelas ELO: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    main()
