# Feature 02 — Silver: limpeza + anti-leakage

## Contexto

A camada Silver transforma a Bronze em um dado confiável para modelagem.

Nesta etapa, o dado deixa de ser apenas uma cópia bruta e passa por limpeza controlada: nomes padronizados, tipos corretos, remoção de duplicatas, corte temporal e separação da Copa 2026 para evitar vazamento de informação.

O ponto mais importante desta feature é o **anti-leakage**: o modelo não pode treinar com jogos da própria Copa 2026, pois esses são exatamente os jogos que queremos prever/simular.

## Objetivo

Ler a tabela `bronze_jogos` e gerar duas tabelas Silver:

```text
silver_jogos
silver_copa2026
```

A tabela `silver_jogos` será o histórico limpo usado nas próximas features.

A tabela `silver_copa2026` será a base dos jogos da fase de grupos da Copa 2026, que serão previstos e simulados posteriormente.

## Entrada

Tabela:

```text
bronze_jogos
```

Colunas esperadas:

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

## Saída

### `silver_jogos`

Histórico limpo, com placar, sem jogos antigos demais e sem jogos da Copa 2026.

### `silver_copa2026`

Jogos da Copa do Mundo 2026 que serão previstos/simulados.

### Schema das duas tabelas

As duas tabelas devem ter o mesmo schema:

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
eh_amistoso
```

## Constantes da feature

Usar as seguintes constantes:

```python
DATA_CORTE_HISTORICO = "2006-01-01"
DATA_INICIO_COPA_2026 = "2026-06-11"
TORNEIO_COPA = "FIFA World Cup"
TORNEIO_AMISTOSO = "Friendly"
```

## Requisitos

### 1. Ler dados da Bronze

Ler todos os dados de:

```sql
SELECT *
FROM bronze_jogos;
```

A Feature 02 deve partir sempre da Bronze, mas as features seguintes devem usar a Silver.

### 2. Corrigir e garantir tipos

Garantir os tipos esperados:

```text
data → date/datetime
gols_casa → inteiro nullable
gols_visitante → inteiro nullable
neutro → boolean
campos de texto → string
```

No pandas:

```python
df["data"] = pd.to_datetime(df["data"]).dt.date
df["gols_casa"] = df["gols_casa"].astype("Int64")
df["gols_visitante"] = df["gols_visitante"].astype("Int64")
df["neutro"] = df["neutro"].astype(bool)
```

Atenção: não transformar placares nulos em zero.

Errado:

```python
df["gols_casa"] = df["gols_casa"].fillna(0)
df["gols_visitante"] = df["gols_visitante"].fillna(0)
```

### 3. Padronizar nomes de seleções

Aplicar `strip()` em:

```text
time_casa
time_visitante
```

Também aplicar um dicionário único de padronização, mesmo que inicialmente ele seja pequeno.

Exemplo:

```python
MAPA_SELECOES = {
    # manter vazio ou quase vazio no início
    # "USA": "United States",
    # "Ivory Coast": "Côte d'Ivoire",
}
```

Uso esperado:

```python
df["time_casa"] = df["time_casa"].str.strip().replace(MAPA_SELECOES)
df["time_visitante"] = df["time_visitante"].str.strip().replace(MAPA_SELECOES)
```

Os nomes das seleções devem permanecer em inglês, conforme o dataset.

Não traduzir:

```text
Brazil
France
Argentina
Morocco
United States
```

### 4. Padronizar textos básicos

Aplicar `strip()` também nas colunas de texto:

```text
torneio
cidade
pais
```

Não traduzir os valores.

Exemplo correto:

```text
FIFA World Cup
Friendly
Copa América
```

### 5. Remover duplicatas exatas

Remover apenas duplicatas exatas nas colunas de negócio.

Colunas de negócio:

```text
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

Exemplo:

```python
COLUNAS_NEGOCIO = [
    "data",
    "time_casa",
    "time_visitante",
    "gols_casa",
    "gols_visitante",
    "torneio",
    "cidade",
    "pais",
    "neutro",
]

df = df.drop_duplicates(subset=COLUNAS_NEGOCIO).copy()
```

Não remover jogos apenas porque possuem os mesmos times ou o mesmo placar. Só remover linhas idênticas.

### 6. Criar coluna `eh_amistoso`

Criar a coluna booleana:

```python
df["eh_amistoso"] = df["torneio"].eq("Friendly")
```

Resultado esperado:

```text
true  → amistoso
false → competição oficial ou torneio menor
```

O filtro de amistosos só será usado na Gold, não aqui.

### 7. Separação anti-leakage

Esta é a regra mais importante da Feature 02.

A Copa 2026 não deve entrar no histórico de treino.

#### `silver_copa2026`

Deve conter os jogos da Copa do Mundo 2026 vindos do CSV:

```text
torneio = "FIFA World Cup"
data >= "2026-06-11"
```

Regra:

```python
mask_copa2026 = (
    (df["torneio"] == TORNEIO_COPA)
    & (df["data"] >= DATA_INICIO_COPA_2026)
)
```

Essa regra é mais segura do que usar apenas `gols_casa IS NULL`, porque se o CSV for atualizado no futuro com placares da Copa, esses jogos continuarão separados e não vazarão para o treino.

#### `silver_jogos`

Deve conter apenas histórico válido para modelagem:

```text
data >= "2006-01-01"
gols_casa não nulo
gols_visitante não nulo
não ser jogo da Copa 2026
```

Regra:

```python
mask_historico = (
    (df["data"] >= DATA_CORTE_HISTORICO)
    & df["gols_casa"].notna()
    & df["gols_visitante"].notna()
    & (~mask_copa2026)
)
```

Assim, jogos anteriores a 2006 são ignorados pelo modelo, mas permanecem preservados na Bronze.

### 8. Importante sobre jogos de 2026

Jogos de 2026 com placar podem entrar em `silver_jogos` somente se forem antes da Copa e não forem parte da Copa 2026.

Exemplos que podem entrar no histórico:

```text
amistosos de 2026 antes da Copa
eliminatórias de 2026 antes da Copa
outros jogos oficiais antes da Copa
```

Exemplos que não podem entrar no histórico:

```text
jogos da Copa do Mundo 2026
qualquer jogo de FIFA World Cup com data >= 2026-06-11
```

### 9. Nomes de países e coluna `pais`

A coluna `pais` representa o país onde o jogo aconteceu, não a seleção.

Ela deve permanecer na tabela, mas não deve ser usada como se fosse o país da equipe.

Exemplo:

```text
time_casa = Brazil
time_visitante = Argentina
pais = United States
```

Nesse caso, `pais` é local da partida, não a seleção.

### 10. Gravação idempotente

As tabelas devem ser recriadas do zero a cada execução:

```sql
DROP TABLE IF EXISTS silver_jogos;
DROP TABLE IF EXISTS silver_copa2026;
CREATE TABLE ...
COPY ...
```

Rodar a Feature 02 várias vezes deve produzir o mesmo resultado.

## Schema das tabelas

```sql
CREATE TABLE silver_jogos (
    id bigint generated always as identity primary key,
    data date,
    time_casa text,
    time_visitante text,
    gols_casa integer,
    gols_visitante integer,
    torneio text,
    cidade text,
    pais text,
    neutro boolean,
    eh_amistoso boolean
);
```

```sql
CREATE TABLE silver_copa2026 (
    id bigint generated always as identity primary key,
    data date,
    time_casa text,
    time_visitante text,
    gols_casa integer,
    gols_visitante integer,
    torneio text,
    cidade text,
    pais text,
    neutro boolean,
    eh_amistoso boolean
);
```

## Critérios de aceite

A Feature 02 será considerada correta quando:

1. `silver_jogos` não tiver jogos anteriores a 2006.
2. `silver_jogos` não tiver placares nulos.
3. `silver_jogos` não tiver jogos da Copa 2026.
4. `silver_copa2026` tiver os jogos da Copa 2026 usados na simulação.
5. `silver_copa2026` tiver aproximadamente 72 jogos, conforme o arquivo atual.
6. A coluna `eh_amistoso` existir nas duas tabelas.
7. Os nomes das seleções estiverem sem espaços extras.
8. As tabelas não tiverem duplicatas exatas.
9. Os nomes de seleções, torneios, cidades e países permanecerem no idioma original.
10. As próximas features deverão usar `silver_jogos`, não `bronze_jogos`.

## Verificação SQL

### Verificar corte temporal

```sql
SELECT MIN(data) AS primeira_data,
       MAX(data) AS ultima_data,
       COUNT(*) AS linhas
FROM silver_jogos;
```

Resultado esperado:

```text
primeira_data >= 2006-01-01
```

### Verificar que não há jogos anteriores a 2006

```sql
SELECT COUNT(*)
FROM silver_jogos
WHERE data < '2006-01-01';
```

Resultado esperado:

```text
0
```

### Verificar que não há placares nulos no histórico

```sql
SELECT COUNT(*)
FROM silver_jogos
WHERE gols_casa IS NULL
   OR gols_visitante IS NULL;
```

Resultado esperado:

```text
0
```

### Verificar que não há Copa 2026 no histórico

```sql
SELECT COUNT(*)
FROM silver_jogos
WHERE torneio = 'FIFA World Cup'
  AND data >= '2026-06-11';
```

Resultado esperado:

```text
0
```

### Verificar jogos da Copa 2026 separados

```sql
SELECT COUNT(*)
FROM silver_copa2026;
```

Resultado esperado aproximado:

```text
72
```

### Conferir os jogos da Copa 2026

```sql
SELECT data, time_casa, time_visitante, gols_casa, gols_visitante, torneio
FROM silver_copa2026
ORDER BY data, id
LIMIT 10;
```

### Verificar amistosos

```sql
SELECT eh_amistoso, COUNT(*)
FROM silver_jogos
GROUP BY eh_amistoso
ORDER BY eh_amistoso;
```

### Verificar duplicatas exatas no histórico

```sql
SELECT data,
       time_casa,
       time_visitante,
       gols_casa,
       gols_visitante,
       torneio,
       cidade,
       pais,
       neutro,
       COUNT(*)
FROM silver_jogos
GROUP BY data,
         time_casa,
         time_visitante,
         gols_casa,
         gols_visitante,
         torneio,
         cidade,
         pais,
         neutro
HAVING COUNT(*) > 1;
```

Resultado esperado:

```text
nenhuma linha
```

### Verificar duplicatas exatas na Copa 2026

```sql
SELECT data,
       time_casa,
       time_visitante,
       torneio,
       cidade,
       pais,
       neutro,
       COUNT(*)
FROM silver_copa2026
GROUP BY data,
         time_casa,
         time_visitante,
         torneio,
         cidade,
         pais,
         neutro
HAVING COUNT(*) > 1;
```

Resultado esperado:

```text
nenhuma linha
```

## Plano de implementação

1. Ler `bronze_jogos`.

2. Garantir tipos corretos.

3. Aplicar `strip()` nas colunas de texto.

4. Aplicar o dicionário único de padronização de seleções.

5. Remover duplicatas exatas pelas colunas de negócio.

6. Criar `eh_amistoso`.

7. Criar `mask_copa2026` com:

   * `torneio = 'FIFA World Cup'`;
   * `data >= '2026-06-11'`.

8. Criar `silver_copa2026` usando `mask_copa2026`.

9. Criar `silver_jogos` usando:

   * `data >= '2006-01-01'`;
   * placares não nulos;
   * não Copa 2026.

10. Validar quantidades, nulos e duplicatas.

11. Gravar `silver_jogos` e `silver_copa2026` no banco com `DROP + CREATE + COPY`.

## Para explicar enquanto desenvolve

* A camada Silver transforma dado bruto em dado confiável.
* O corte em 2006 evita que partidas muito antigas influenciem o modelo.
* A Copa 2026 precisa ficar separada para evitar data leakage.
* Usar apenas `gols_casa IS NULL` para identificar a Copa é frágil, porque o CSV pode ser atualizado no futuro.
* `silver_jogos` será usado para aprender com o passado.
* `silver_copa2026` será usado para prever o futuro.
* A coluna `pais` é local da partida, não a seleção.
