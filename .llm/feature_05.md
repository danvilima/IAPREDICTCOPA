# Feature 05 — Gold: tabela de treino para o Poisson

## Contexto

A camada Gold monta a tabela larga que será usada pelo modelo Poisson.

Cada linha representa uma partida histórica válida para treino. A tabela junta informações do jogo, ELO pré-jogo, pesos de treino e placares reais.

O ponto mais importante desta feature é separar corretamente:

```text
features preditivas
pesos de treino
alvos do modelo
identificadores
```

Essa separação evita vazamento de informação e evita que o modelo use colunas que não deveria usar na previsão.

## Objetivo

Montar a tabela:

```text
gold_atributos
```

Essa tabela será usada na Feature 06 para treinar dois modelos Poisson:

```text
modelo_poisson_casa
modelo_poisson_visitante
```

## Entrada

Tabelas:

```text
silver_ponderado
silver_elo_pre_jogo
```

## Saída

Tabela:

```text
gold_atributos
```

Com uma linha por jogo competitivo do histórico.

## Regras principais

A tabela deve conter:

### 1. Identificadores

```text
id
ponderado_id
jogo_id
data
time_casa
time_visitante
```

### 2. Features preditivas

Essas são as colunas que poderão entrar no `X` do modelo:

```text
elo_casa
elo_visitante
dif_elo
neutro
```

### 3. Pesos de treino

Essas colunas não são features de previsão. Elas servem para ponderar o treino:

```text
peso_torneio
peso_recencia
peso_amostra
```

Onde:

```text
peso_amostra = peso_torneio × peso_recencia
```

### 4. Alvos do modelo

Essas são as respostas que o modelo tentará aprender:

```text
gols_casa
gols_visitante
```

Essas colunas não podem ser usadas como features de entrada.

## Entrada esperada de `silver_ponderado`

Colunas esperadas:

```text
id
jogo_id
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
peso_torneio
peso_recencia
```

Onde:

```text
silver_ponderado.id = id próprio da tabela ponderada
silver_ponderado.jogo_id = id original vindo de silver_jogos
```

## Entrada esperada de `silver_elo_pre_jogo`

Colunas esperadas:

```text
id
ponderado_id
jogo_id
data
time_casa
time_visitante
elo_casa
elo_visitante
```

Onde:

```text
silver_elo_pre_jogo.ponderado_id = silver_ponderado.id
```

## Requisitos

### 1. Fazer o join correto

O join deve ser feito por:

```sql
e.ponderado_id = s.id
```

Exemplo:

```sql
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
JOIN silver_elo_pre_jogo e
  ON e.ponderado_id = s.id
WHERE s.eh_amistoso = false
ORDER BY s.data, s.id;
```

Não fazer join por:

```sql
e.id = s.id
```

Isso pode juntar o ELO de uma partida com outra partida errada.

### 2. Filtrar apenas jogos competitivos

A tabela `gold_atributos` deve excluir amistosos.

O filtro correto é:

```sql
WHERE s.eh_amistoso = false
```

Não filtrar por `peso_torneio`.

Motivo:

```text
torneios menores não-amistosos podem ter peso_torneio = 1,
mas ainda são jogos competitivos e devem entrar no treino.
```

### 3. Não incluir confederação

Não incluir coluna de confederação.

Não criar colunas como:

```text
confederacao_casa
confederacao_visitante
continente_casa
continente_visitante
regiao
```

Motivo:

```text
confederação pode introduzir viés no modelo e distorcer probabilidades.
```

### 4. Garantir anti-leakage

A tabela `gold_atributos` não pode conter jogos da Copa 2026 futura.

Como a Feature 02 já separou a Copa 2026 em `silver_copa2026`, isso deve estar garantido por construção.

Mesmo assim, validar:

```sql
SELECT COUNT(*)
FROM gold_atributos
WHERE data >= '2026-06-11';
```

Idealmente deve retornar zero para jogos da Copa 2026 futura.

Se existir algum jogo depois dessa data por atualização do dataset, verificar se não é `FIFA World Cup`.

Validação mais específica:

```sql
SELECT COUNT(*)
FROM gold_atributos g
JOIN silver_ponderado s
  ON s.id = g.ponderado_id
WHERE s.torneio = 'FIFA World Cup'
  AND s.data >= '2026-06-11';
```

Resultado esperado:

```text
0
```

### 5. Calcular `dif_elo`

Criar a coluna:

```text
dif_elo
```

Regra:

```python
df["dif_elo"] = df["elo_casa"] - df["elo_visitante"]
```

A diferença deve ser sempre:

```text
ELO do time da casa − ELO do time visitante
```

### 6. Calcular `peso_amostra`

Criar a coluna:

```text
peso_amostra
```

Regra:

```python
df["peso_amostra"] = df["peso_torneio"] * df["peso_recencia"]
```

Essa coluna será usada na Feature 06 como peso do treino.

Uso correto na Feature 06:

```python
sample_weight = df["peso_amostra"]
```

Uso incorreto:

```python
X = df[["peso_torneio", "peso_recencia", "peso_amostra"]]
```

### 7. Converter `neutro` para booleano

A coluna `neutro` deve permanecer como booleano na tabela.

Na Feature 06, ela será convertida para inteiro 0/1 na montagem do `X`.

Exemplo:

```python
X["neutro"] = X["neutro"].astype(int)
```

### 8. Não usar placares como features

As colunas:

```text
gols_casa
gols_visitante
```

devem estar na tabela porque são os alvos do modelo.

Mas elas não podem entrar como variáveis explicativas no treino.

Correto:

```python
X = df[["elo_casa", "elo_visitante", "dif_elo", "neutro"]]

y_casa = df["gols_casa"]
y_visitante = df["gols_visitante"]
```

Errado:

```python
X = df[[
    "elo_casa",
    "elo_visitante",
    "dif_elo",
    "neutro",
    "gols_casa",
    "gols_visitante"
]]
```

Isso seria vazamento total, porque o modelo estaria recebendo a resposta.

### 9. Não usar pesos como features

As colunas:

```text
peso_torneio
peso_recencia
peso_amostra
```

não devem entrar como features preditivas.

Elas servem apenas para definir a importância de cada linha no treino.

Correto:

```python
X = df[["elo_casa", "elo_visitante", "dif_elo", "neutro"]]
peso = df["peso_amostra"]
```

Errado:

```python
X = df[[
    "elo_casa",
    "elo_visitante",
    "dif_elo",
    "neutro",
    "peso_torneio",
    "peso_recencia"
]]
```

### 10. Validar nulos

A tabela final não pode ter nulos nas colunas usadas no treino e nos alvos.

Validar:

```python
COLUNAS_SEM_NULOS = [
    "ponderado_id",
    "jogo_id",
    "data",
    "time_casa",
    "time_visitante",
    "elo_casa",
    "elo_visitante",
    "dif_elo",
    "neutro",
    "peso_torneio",
    "peso_recencia",
    "peso_amostra",
    "gols_casa",
    "gols_visitante",
]

assert df[COLUNAS_SEM_NULOS].isna().sum().sum() == 0
```

### 11. Validar duplicidade

Cada jogo de `silver_ponderado` deve aparecer no máximo uma vez em `gold_atributos`.

Validar por:

```text
ponderado_id
```

Não pode haver duplicidade.

### 12. Ordenação

Gravar os dados ordenados por:

```text
data
ponderado_id
```

Isso ajuda a manter rastreabilidade e facilita o split temporal da Feature 06.

## Schema da tabela

```sql
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
```

## Critérios de aceite

A Feature 05 será considerada correta quando:

1. `gold_atributos` tiver apenas jogos competitivos.
2. Nenhum amistoso estiver presente.
3. Nenhum jogo da Copa 2026 futura estiver presente.
4. O join entre `silver_ponderado` e `silver_elo_pre_jogo` for feito por `ponderado_id`.
5. `dif_elo` estiver correto.
6. `peso_amostra` estiver correto.
7. Não houver nulos nas colunas necessárias.
8. Não houver duplicidade por `ponderado_id`.
9. `gols_casa` e `gols_visitante` forem mantidos apenas como alvos.
10. `peso_torneio`, `peso_recencia` e `peso_amostra` forem mantidos como pesos de treino, não como features preditivas.
11. Nenhuma coluna de confederação existir na tabela.
12. A coluna `data` existir, pois será usada no split temporal da Feature 06.

## Verificação SQL

### Verificar primeiras linhas

```sql
SELECT
    ponderado_id,
    jogo_id,
    data,
    time_casa,
    time_visitante,
    ROUND(elo_casa::numeric, 1) AS elo_casa,
    ROUND(elo_visitante::numeric, 1) AS elo_visitante,
    ROUND(dif_elo::numeric, 1) AS dif_elo,
    neutro,
    peso_torneio,
    ROUND(peso_recencia::numeric, 4) AS peso_recencia,
    ROUND(peso_amostra::numeric, 4) AS peso_amostra,
    gols_casa,
    gols_visitante
FROM gold_atributos
ORDER BY data, ponderado_id
LIMIT 10;
```

### Verificar quantidade esperada

```sql
SELECT COUNT(*)
FROM gold_atributos;
```

Resultado esperado aproximado:

```text
cerca de 13.000 jogos, dependendo do dataset
```

### Verificar se não há amistosos

```sql
SELECT COUNT(*)
FROM gold_atributos g
JOIN silver_ponderado s
  ON s.id = g.ponderado_id
WHERE s.eh_amistoso = true;
```

Resultado esperado:

```text
0
```

### Verificar se não há Copa 2026 futura

```sql
SELECT COUNT(*)
FROM gold_atributos g
JOIN silver_ponderado s
  ON s.id = g.ponderado_id
WHERE s.torneio = 'FIFA World Cup'
  AND s.data >= '2026-06-11';
```

Resultado esperado:

```text
0
```

### Verificar nulos

```sql
SELECT COUNT(*)
FROM gold_atributos
WHERE ponderado_id IS NULL
   OR jogo_id IS NULL
   OR data IS NULL
   OR time_casa IS NULL
   OR time_visitante IS NULL
   OR elo_casa IS NULL
   OR elo_visitante IS NULL
   OR dif_elo IS NULL
   OR neutro IS NULL
   OR peso_torneio IS NULL
   OR peso_recencia IS NULL
   OR peso_amostra IS NULL
   OR gols_casa IS NULL
   OR gols_visitante IS NULL;
```

Resultado esperado:

```text
0
```

### Verificar `dif_elo`

```sql
SELECT COUNT(*)
FROM gold_atributos
WHERE ABS(dif_elo - (elo_casa - elo_visitante)) > 0.000001;
```

Resultado esperado:

```text
0
```

### Verificar `peso_amostra`

```sql
SELECT COUNT(*)
FROM gold_atributos
WHERE ABS(peso_amostra - (peso_torneio * peso_recencia)) > 0.000001;
```

Resultado esperado:

```text
0
```

### Verificar duplicidade por jogo ponderado

```sql
SELECT ponderado_id, COUNT(*)
FROM gold_atributos
GROUP BY ponderado_id
HAVING COUNT(*) > 1;
```

Resultado esperado:

```text
nenhuma linha
```

### Verificar se não existe coluna de confederação

```sql
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'gold_atributos'
  AND (
      column_name ILIKE '%confed%'
      OR column_name ILIKE '%continente%'
      OR column_name ILIKE '%regiao%'
  );
```

Resultado esperado:

```text
nenhuma linha
```

## Plano de implementação

1. Ler `silver_ponderado` junto com `silver_elo_pre_jogo`.
2. Fazer join por:

```sql
e.ponderado_id = s.id
```

3. Filtrar:

```sql
s.eh_amistoso = false
```

4. Selecionar identificadores, ELOs, pesos, neutralidade e placares.
5. Calcular:

```python
df["dif_elo"] = df["elo_casa"] - df["elo_visitante"]
df["peso_amostra"] = df["peso_torneio"] * df["peso_recencia"]
```

6. Validar ausência de nulos.
7. Validar ausência de duplicidade por `ponderado_id`.
8. Validar que não há Copa 2026 futura.
9. Ordenar por `data, ponderado_id`.
10. Gravar `gold_atributos` com `DROP + CREATE + COPY`.

## Para explicar enquanto desenvolve

* Feature engineering é transformar dados limpos em variáveis úteis para o modelo.
* `dif_elo` ajuda o modelo a entender a diferença de força entre as seleções.
* `gols_casa` e `gols_visitante` são os alvos, não atributos de entrada.
* `peso_torneio` e `peso_recencia` dizem quanto cada jogo pesa no treino.
* A tabela Gold precisa ser clara para evitar vazamento de informação.
* A coluna `data` será usada para separar treino e teste de forma temporal.
