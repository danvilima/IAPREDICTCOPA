# Feature 01 — Bronze: ingestão do `results.csv`

## Contexto

Primeira camada do padrão Medallion. A camada Bronze deve guardar o dado cru de `data/results.csv`, sem limpeza analítica, sem filtro temporal e sem remoção de jogos.

A única padronização permitida nesta etapa é estrutural: renomear as colunas para português e aplicar conversões mínimas de tipo para que o dado possa ser gravado corretamente no banco.

## Objetivo

Ler `data/results.csv` e gravar a tabela `bronze_jogos` no banco de dados, mantendo o mesmo número de linhas do CSV original.

As colunas devem ser renomeadas para português conforme o dicionário definido no `prd.md`.

## Entrada

Arquivo:

```text
data/results.csv
```

Colunas originais esperadas:

```text
date, home_team, away_team, home_score, away_score, tournament, city, country, neutral
```

Volume esperado:

```text
aproximadamente 49.450 linhas
```

Período esperado:

```text
1872 até jogos agendados de 2026
```

## Saída

Tabela no banco:

```text
bronze_jogos
```

Colunas:

```text
id
data
time_casa
time_visitante
gols_casa
gols_visitante
torneio
cidade
pais
neutro
```

## Requisitos

### 1. Leitura do CSV

O caminho do CSV deve ser lido nesta ordem de prioridade:

1. argumento de linha de comando;
2. variável de ambiente `CAMINHO_CSV`;
3. valor padrão `data/results.csv`.

Exemplo de uso:

```bash
python src/feature_01_bronze.py
```

ou:

```bash
python src/feature_01_bronze.py data/results.csv
```

### 2. Renomear colunas para português

Aplicar o seguinte mapeamento:

```python
{
    "date": "data",
    "home_team": "time_casa",
    "away_team": "time_visitante",
    "home_score": "gols_casa",
    "away_score": "gols_visitante",
    "tournament": "torneio",
    "city": "cidade",
    "country": "pais",
    "neutral": "neutro"
}
```

Nenhuma coluna original em inglês deve permanecer na tabela final.

### 3. Não limpar, não filtrar e não remover linhas

A camada Bronze deve preservar o dado como chegou.

Não fazer:

```text
filtro por data
remoção de amistosos
remoção de jogos antigos
remoção da Copa 2026
padronização de nomes de seleções
tradução de nomes de seleções
tradução de torneios, cidades ou países
remoção de duplicatas
```

Essas etapas pertencem às camadas Silver e Gold.

### 4. Conversões mínimas de tipo

Aplicar somente as conversões necessárias para armazenamento correto:

#### `data`

Converter para tipo `date`.

No pandas, pode ser lido com:

```python
parse_dates=["date"]
```

Depois de renomear, gravar no banco como `date`.

#### `gols_casa` e `gols_visitante`

Converter para inteiro nullable:

```python
Int64
```

Isso é necessário porque os jogos futuros da Copa 2026 possuem valores nulos.

Os `NA` do CSV devem virar `NULL` no banco.

Não substituir nulos por zero.

Errado:

```python
df["gols_casa"] = df["gols_casa"].fillna(0)
df["gols_visitante"] = df["gols_visitante"].fillna(0)
```

Certo:

```python
df["gols_casa"] = df["gols_casa"].astype("Int64")
df["gols_visitante"] = df["gols_visitante"].astype("Int64")
```

#### `neutro`

Converter para booleano de forma explícita e segura.

Não usar conversão direta perigosa caso a coluna venha como texto:

```python
astype(bool)
```

A conversão deve aceitar valores booleanos reais e strings como `"TRUE"`/`"FALSE"`.

Exemplo seguro:

```python
df["neutro"] = df["neutro"].map({
    True: True,
    False: False,
    "TRUE": True,
    "FALSE": False,
    "True": True,
    "False": False,
    "true": True,
    "false": False
})
```

Após a conversão, validar que não existem nulos em `neutro`.

### 5. Textos permanecem no idioma original

As seguintes colunas devem permanecer exatamente como vieram no CSV, sem tradução:

```text
time_casa
time_visitante
torneio
cidade
pais
```

Exemplo:

```text
Brazil
France
FIFA World Cup
Washington, D.C.
United States
```

### 6. Parser CSV

Usar o parser padrão do pandas.

O CSV possui cidades com vírgula interna entre aspas, por exemplo:

```text
"Washington, D.C."
```

O pandas trata esse caso corretamente com `read_csv`.

### 7. Inventário da ingestão

Após carregar e converter os dados, imprimir um inventário com:

```text
número de linhas
nomes das colunas
tipos das colunas
quantidade de nulos por coluna
percentual de nulos por coluna
```

Esse inventário serve para validar a qualidade inicial do dado antes de qualquer transformação.

### 8. Gravação idempotente no banco

A gravação deve ser idempotente:

```sql
DROP TABLE IF EXISTS bronze_jogos;
CREATE TABLE bronze_jogos (...);
COPY ...
```

Ou seja, rodar a Feature 01 várias vezes deve recriar a tabela do zero com o mesmo resultado.

## Schema da tabela

```sql
CREATE TABLE bronze_jogos (
    id bigint generated always as identity primary key,
    data date,
    time_casa text,
    time_visitante text,
    gols_casa integer,
    gols_visitante integer,
    torneio text,
    cidade text,
    pais text,
    neutro boolean
);
```

## Critérios de aceite

A Feature 01 será considerada correta quando:

1. `bronze_jogos` tiver o mesmo número de linhas do CSV original.
2. Todas as colunas estiverem em português.
3. Nenhuma coluna original em inglês permanecer.
4. Os jogos futuros da Copa 2026 estiverem preservados.
5. Os jogos futuros com placar ausente tiverem `gols_casa` e `gols_visitante` como `NULL`.
6. A coluna `neutro` estiver corretamente gravada como boolean.
7. Nenhum filtro temporal tiver sido aplicado.
8. Nenhuma seleção, torneio, cidade ou país tiver sido traduzido.

## Verificação SQL

```sql
SELECT COUNT(*) AS linhas
FROM bronze_jogos;
```

Resultado esperado:

```text
aproximadamente 49.450 linhas
```

```sql
SELECT data, time_casa, time_visitante, gols_casa, gols_visitante
FROM bronze_jogos
ORDER BY data
LIMIT 5;
```

```sql
SELECT MIN(data) AS mais_antigo,
       MAX(data) AS mais_recente
FROM bronze_jogos;
```

Resultado esperado aproximado:

```text
1872-11-30 até 2026
```

```sql
SELECT COUNT(*)
FROM bronze_jogos
WHERE gols_casa IS NULL
   OR gols_visitante IS NULL;
```

Resultado esperado:

```text
72 jogos futuros da Copa 2026
```

```sql
SELECT neutro, COUNT(*)
FROM bronze_jogos
GROUP BY neutro
ORDER BY neutro;
```

Esse resultado deve mostrar distribuição entre `true` e `false`, não apenas um único valor.

```sql
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'bronze_jogos'
ORDER BY ordinal_position;
```

As colunas devem aparecer em português.

## Plano de implementação

1. Criar infraestrutura compartilhada do projeto:

   * `requirements.txt`
   * `.env.example`
   * `.gitignore`
   * `src/db.py`

2. Implementar em `src/db.py`:

   * `get_engine()`
   * `get_raw_connection()`

3. Ler o CSV com pandas:

   * caminho por argumento, `CAMINHO_CSV` ou padrão `data/results.csv`;
   * usar `parse_dates=["date"]`.

4. Validar se todas as colunas esperadas existem.

5. Aplicar o mapeamento de nomes para português.

6. Converter:

   * `data` para `date`;
   * `gols_casa` e `gols_visitante` para `Int64`;
   * `neutro` para booleano seguro.

7. Imprimir inventário da tabela.

8. Criar a tabela `bronze_jogos` no banco.

9. Gravar os dados usando `COPY`.

10. Rodar as queries de validação.

## Para explicar enquanto desenvolve

* A camada Bronze é a cópia confiável do dado original.
* A Bronze não deve tentar “melhorar” o dado, porque isso pode esconder problemas.
* Renomear colunas para português já na entrada ajuda a manter consistência no projeto.
* Os placares nulos da Copa 2026 são importantes e não podem virar zero.
* O inventário inicial ajuda a enxergar nulos, tipos e possíveis problemas antes das transformações.
