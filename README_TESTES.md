# Testes do Sistema de Buffer e Beat Schedule

Este conjunto de arquivos permite testar a funcionalidade do sistema de buffer e beat schedule implementado no `task.py`.

## Arquivos de Teste

### 1. `quick_test.py` - Teste Rápido
Teste básico para verificar se o sistema está funcionando.

**Uso:**
```bash
python quick_test.py
```

**O que testa:**
- Adição de tarefas ao buffer
- Transferência manual de lotes
- Configuração do beat schedule
- Transferência imediata quando queue vazia

### 2. `test_task_buffer.py` - Testes Unitários Completos
Testes unitários abrangentes usando unittest.

**Uso:**
```bash
# Todos os testes
python test_task_buffer.py

# Apenas testes unitários
python test_task_buffer.py --unit

# Apenas teste manual
python test_task_buffer.py --manual
```

**Classes de teste:**
- `TestBufferSystem`: Testa sistema de buffer
- `TestBeatScheduleConfiguration`: Testa configuração do schedule
- `TestIntegrationScenarios`: Testes de integração
- `TestManualScheduleTesting`: Testes manuais com output detalhado

### 3. `beat_schedule_test.py` - Simulador Realista
Simula o comportamento completo do beat schedule em tempo real.

**Uso:**
```bash
python beat_schedule_test.py
```

**Cenários disponíveis:**
1. **Rajada**: 50 tarefas adicionadas de uma vez
2. **Gradual**: 30 tarefas espaçadas no tempo
3. **Misto**: Rajada inicial + tarefas contínuas
4. **Personalizado**: Você define quantas tarefas

**Características:**
- Simula workers processando tarefas
- Executa beat schedule em intervalo real (12s)
- Mostra logs em tempo real
- Relatório final com estatísticas

## Pré-requisitos

### Redis
Certifique-se de que o Redis está rodando:
```bash
redis-server
```

Os testes usam a database 15 do Redis para não interferir com dados reais.

### Dependências Python
```bash
pip install redis
```

## Como Usar

### Teste Rápido (2 minutos)
```bash
python quick_test.py
```

### Teste Completo (5 minutos)
```bash
python test_task_buffer.py --unit
```

### Simulação Realista (tempo variável)
```bash
python beat_schedule_test.py
```
Escolha um cenário e defina a duração da simulação.

## Interpretando os Resultados

### Beat Schedule
- **Intervalo**: Calculado como `0.2 * BATCH_SIZE * TEMPO_MEDIO_TASKS`
- **Valor atual**: 0.2 * 12 * 5 = 12 segundos
- **Transfere quando**: `queue_size <= THRESHOLD_CONTINUOS_QUEUE_FLUX` (2)

### Transferência Imediata
- Acontece quando `queue_size == 0` e nova tarefa é adicionada
- Transfere apenas do buffer específico do bot

### Logs Importantes
```
[12:34:56] Schedule executado - queue muito cheia (15 tarefas)
[12:35:08] Schedule: 12 tarefas transferidas do bot_0
[12:35:08] Transferência IMEDIATA: 3 tarefas do bot_1
```

## Troubleshooting

### Erro de Conexão Redis
```
redis.exceptions.ConnectionError: Error connecting to Redis
```
**Solução**: Inicie o Redis server: `redis-server`

### Import Error
```
ModuleNotFoundError: No module named 'task'
```
**Solução**: Execute os testes do diretório correto (onde está o `task.py`)

### Mock Warnings
Warnings sobre mocks são normais durante os testes, pois simulamos o Celery.

## Configurações de Teste

### Constantes Testadas
- `BATCH_SIZE`: 12 (tamanhas do lote)
- `TEMPO_MEDIO_TASKS`: 5 (tempo médio por tarefa)
- `THRESHOLD_CONTINUOS_QUEUE_FLUX`: 2 (threshold da queue)
- `NUMERO_DE_FILAS_DE_PRIORIDADE_POR_ROBO`: 3 (níveis de prioridade)

### Cenários Testados
1. **Buffer vazio**: Nenhuma transferência
2. **Queue vazia**: Transferência imediata
3. **Queue baixa**: Transferência por schedule
4. **Queue cheia**: Nenhuma transferência
5. **Múltiplos bots**: Transferência de todos os buffers
6. **Prioridades mistas**: Manutenção da ordem de prioridade

## Próximos Passos

Após os testes passarem, você pode:

1. **Testar com Celery real**:
   ```bash
   # Terminal 1
   celery -A task worker --loglevel=info --pool=solo
   
   # Terminal 2  
   celery -A task beat --loglevel=info
   ```

2. **Monitorar em produção**:
   - Usar Flower para monitorar: `pip install flower && celery -A task flower`
   - Verificar logs do Redis: `redis-cli monitor`

3. **Ajustar parâmetros**:
   - Modificar `BATCH_SIZE` se necessário
   - Ajustar `THRESHOLD_CONTINUOS_QUEUE_FLUX`
   - Alterar intervalo do schedule se preciso
