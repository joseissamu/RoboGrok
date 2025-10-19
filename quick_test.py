#!/usr/bin/env python3
"""
Script rápido para testar o sistema de buffer
Execute: python quick_test.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import redis
import json
import time
from unittest.mock import patch, MagicMock

# Mock das dependências
sys.modules['robo'] = MagicMock()
sys.modules['utils'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

# Importa o task
import task

def quick_test():
    """Teste rápido do sistema de buffer"""
    print("=== TESTE RÁPIDO DO SISTEMA DE BUFFER ===\n")
    
    # Configura Redis de teste
    test_redis = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
    test_redis.flushdb()
    task.redis_client = test_redis
    
    # Mock do Celery
    task.app_celery = MagicMock()
    task.process_command = MagicMock()
    task.process_command.apply_async = MagicMock()
    
    print("1. Testando adição de tarefas ao buffer...")
    
    # Adiciona tarefas
    for i in range(5):
        task_data = json.dumps({
            "task_id": i,
            "app": "pppoker",
            "action": "balance"
        })
        task.submit_command(task_data, priority=i % 3, bot_id=0)
        print(f"   Tarefa {i} adicionada (prioridade {i % 3})")
    
    # Verifica buffer
    buffer_name = task.get_buffer_queue_name(0)
    buffer_size = test_redis.llen(buffer_name)
    print(f"   Buffer bot_0 tem {buffer_size} tarefas\n")
    
    print("2. Testando transferência manual...")
    
    # Mock para queue baixa
    with patch('task.get_main_queue_length') as mock_queue:
        mock_queue.return_value = 1  # Queue baixa
        
        # Executa gerenciador
        result = task.manage_buffer_transfer()
        print(f"   Resultado: {result}")
        print(f"   apply_async chamado {task.process_command.apply_async.call_count} vezes")
        
        # Verifica buffer após transferência
        remaining = test_redis.llen(buffer_name)
        print(f"   Buffer restante: {remaining} tarefas\n")
    
    print("3. Testando configuração do beat schedule...")
    
    # Verifica configuração
    beat_config = task.app_celery.conf.beat_schedule
    transfer_config = beat_config['manage-buffer-transfer']
    print(f"   Task: {transfer_config['task']}")
    print(f"   Schedule: {transfer_config['schedule']} segundos")
    
    expected_schedule = 0.2 * 12 * 5  # 0.2 * BATCH_SIZE * TEMPO_MEDIO_TASKS
    print(f"   Schedule esperado: {expected_schedule} segundos")
    print(f"   ✅ Configuração {'correta' if transfer_config['schedule'] == expected_schedule else 'incorreta'}\n")
    
    print("4. Testando cenário de queue vazia...")
    
    # Reset mock
    task.process_command.apply_async.reset_mock()
    
    # Mock para queue vazia
    with patch('task.get_main_queue_length') as mock_queue:
        mock_queue.return_value = 0  # Queue vazia
        
        # Adiciona nova tarefa (deveria transferir imediatamente)
        task.submit_command('{"immediate": true}', priority=0, bot_id=1)
        
        # Como queue estava vazia, deveria ter transferido imediatamente
        immediate_calls = task.process_command.apply_async.call_count
        print(f"   Transferência imediata: {immediate_calls} chamadas")
    
    print("\n=== TESTE CONCLUÍDO ===")
    print("Para teste mais detalhado, execute:")
    print("  python test_task_buffer.py --unit")
    print("  python beat_schedule_test.py")
    
    # Limpeza
    test_redis.flushdb()

if __name__ == "__main__":
    try:
        quick_test()
    except Exception as e:
        print(f"Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
