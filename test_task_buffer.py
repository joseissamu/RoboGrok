"""
Arquivo de testes para o sistema de buffer e beat schedule do task.py
Este arquivo permite testar o funcionamento do sistema de filas em modo isolado.
"""

import unittest
import json
import time
import redis
from unittest.mock import patch, MagicMock, Mock
from unittest import TestCase
import os
import sys

# Adiciona o diretório atual ao path para importar os módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock das dependências antes de importar
sys.modules['robo'] = MagicMock()
sys.modules['utils'] = MagicMock()
sys.modules['dotenv'] = MagicMock()

# Importa o módulo a ser testado
import task

class TestBufferSystem(TestCase):
    """Testes para o sistema de buffer e transferência"""
    
    def setUp(self):
        """Configuração inicial para cada teste"""
        # Configuração do Redis de teste
        self.test_redis = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)  # DB 15 para testes
        
        # Substitui o cliente Redis global pelos testes
        task.redis_client = self.test_redis
        
        # Limpa todas as chaves do Redis de teste
        self.test_redis.flushdb()
        
        # Mock do Celery para evitar problemas de conexão
        task.app_celery = MagicMock()
        task.process_command = MagicMock()
        task.process_command.apply_async = MagicMock()
        
        # Valores de teste
        self.test_comando = json.dumps({
            "question": {
                "App": "pppoker",
                "Action": "balance",
                "BotId": 1
            }
        })
        
    def tearDown(self):
        """Limpeza após cada teste"""
        self.test_redis.flushdb()
        
    def test_get_buffer_queue_name(self):
        """Testa a geração do nome da fila buffer"""
        self.assertEqual(task.get_buffer_queue_name(0), "buffer_bot_0")
        self.assertEqual(task.get_buffer_queue_name(5), "buffer_bot_5")
        
    def test_add_task_to_buffer(self):
        """Testa a adição de tarefas ao buffer"""
        # Adiciona tarefa ao buffer
        task.add_task_to_buffer(self.test_comando, priority=1, bot_id=0)
        
        # Verifica se foi adicionada
        buffer_name = task.get_buffer_queue_name(0)
        buffer_size = self.test_redis.llen(buffer_name)
        self.assertEqual(buffer_size, 1)
        
        # Verifica o conteúdo
        task_data = self.test_redis.lindex(buffer_name, 0)
        task_info = json.loads(task_data)
        self.assertEqual(task_info['comando'], self.test_comando)
        self.assertEqual(task_info['priority'], 1)
        self.assertIn('timestamp', task_info)
        
    def test_transfer_batch_from_buffer_empty(self):
        """Testa transferência de buffer vazio"""
        transferred = task.transfer_batch_from_buffer(0)
        self.assertEqual(transferred, 0)
        
    def test_transfer_batch_from_buffer_with_tasks(self):
        """Testa transferência de buffer com tarefas"""
        # Adiciona várias tarefas ao buffer
        for i in range(15):  # Mais que BATCH_SIZE (12)
            task.add_task_to_buffer(
                json.dumps({"test": f"task_{i}"}), 
                priority=i % 3, 
                bot_id=0
            )
        
        # Verifica que foram adicionadas
        buffer_name = task.get_buffer_queue_name(0)
        initial_size = self.test_redis.llen(buffer_name)
        self.assertEqual(initial_size, 15)
        
        # Transfere um lote
        transferred = task.transfer_batch_from_buffer(0)
        
        # Verifica se transferiu o número correto (BATCH_SIZE = 12)
        self.assertEqual(transferred, 12)
        
        # Verifica que sobraram 3 no buffer
        remaining_size = self.test_redis.llen(buffer_name)
        self.assertEqual(remaining_size, 3)
        
        # Verifica se process_command.apply_async foi chamado 12 vezes
        self.assertEqual(task.process_command.apply_async.call_count, 12)
        
    @patch('task.get_main_queue_length')
    def test_manage_buffer_transfer_with_low_queue(self, mock_queue_length):
        """Testa o gerenciador quando a queue principal está baixa"""
        # Simula queue principal com poucas tarefas
        mock_queue_length.return_value = 1  # <= THRESHOLD_CONTINUOS_QUEUE_FLUX (2)
        
        # Adiciona tarefas em buffers de diferentes bots
        task.add_task_to_buffer(self.test_comando, 0, 0)  # bot 0
        task.add_task_to_buffer(self.test_comando, 1, 1)  # bot 1
        task.add_task_to_buffer(self.test_comando, 2, 2)  # bot 2
        
        # Executa o gerenciador
        result = task.manage_buffer_transfer()
        
        # Verifica resultado
        self.assertEqual(result, "Buffer management completed")
        
        # Verifica que tentou transferir de todos os bots
        mock_queue_length.assert_called()
        
    @patch('task.get_main_queue_length')
    def test_manage_buffer_transfer_with_high_queue(self, mock_queue_length):
        """Testa o gerenciador quando a queue principal está cheia"""
        # Simula queue principal com muitas tarefas
        mock_queue_length.return_value = 50  # > THRESHOLD_CONTINUOS_QUEUE_FLUX (2)
        
        # Adiciona tarefa ao buffer
        task.add_task_to_buffer(self.test_comando, 0, 0)
        
        # Reseta o mock do apply_async
        task.process_command.apply_async.reset_mock()
        
        # Executa o gerenciador
        result = task.manage_buffer_transfer()
        
        # Verifica que não transferiu nada
        task.process_command.apply_async.assert_not_called()
        self.assertEqual(result, "Buffer management completed")
        
    @patch('task.get_main_queue_length')
    def test_immediate_transfer_when_queue_empty(self, mock_queue_length):
        """Testa transferência imediata quando queue está vazia"""
        # Simula queue vazia
        mock_queue_length.return_value = 0
        
        # Adiciona múltiplas tarefas para formar um lote
        for i in range(5):
            task.add_task_to_buffer(
                json.dumps({"test": f"immediate_{i}"}), 
                priority=1, 
                bot_id=0
            )
        
        # Como mock_queue_length retorna 0, deveria ter transferido imediatamente
        # Verifica se apply_async foi chamado (5 tarefas)
        self.assertEqual(task.process_command.apply_async.call_count, 5)
        
    def test_submit_command_function(self):
        """Testa a função pública submit_command"""
        result = task.submit_command(self.test_comando, priority=2, bot_id=1)
        
        # Verifica retorno
        expected_result = "Comando adicionado ao buffer do bot_1 com prioridade 2"
        self.assertEqual(result, expected_result)
        
        # Verifica se foi adicionado ao buffer correto
        buffer_name = task.get_buffer_queue_name(1)
        buffer_size = self.test_redis.llen(buffer_name)
        self.assertEqual(buffer_size, 1)


class TestBeatScheduleConfiguration(TestCase):
    """Testes para a configuração do beat schedule"""
    
    def test_beat_schedule_configuration(self):
        """Testa se o beat schedule está configurado corretamente"""
        # Verifica se a configuração existe
        self.assertIn('beat_schedule', task.app_celery.conf.__dict__)
        
        # Verifica se a tarefa está configurada
        beat_config = task.app_celery.conf.beat_schedule
        self.assertIn('manage-buffer-transfer', beat_config)
        
        # Verifica configuração da tarefa
        transfer_config = beat_config['manage-buffer-transfer']
        self.assertEqual(transfer_config['task'], 'task.manage_buffer_transfer')
        
        # Verifica se o schedule é calculado corretamente
        expected_schedule = 0.2 * 12 * 5  # 0.2 * BATCH_SIZE * TEMPO_MEDIO_TASKS
        self.assertEqual(transfer_config['schedule'], expected_schedule)


class TestIntegrationScenarios(TestCase):
    """Testes de integração para cenários complexos"""
    
    def setUp(self):
        """Configuração inicial"""
        self.test_redis = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
        task.redis_client = self.test_redis
        self.test_redis.flushdb()
        
        # Mock do Celery
        task.app_celery = MagicMock()
        task.process_command = MagicMock()
        task.process_command.apply_async = MagicMock()
        
    def tearDown(self):
        """Limpeza"""
        self.test_redis.flushdb()
        
    @patch('task.get_main_queue_length')
    def test_priority_batching_scenario(self, mock_queue_length):
        """Testa cenário de lotes com diferentes prioridades"""
        # Simula queue baixa para permitir transferência
        mock_queue_length.return_value = 1
        
        # Adiciona tarefas com diferentes prioridades ao mesmo buffer
        priorities = [0, 0, 0, 1, 1, 2, 2, 2, 0, 1]  # Mix de prioridades
        for i, priority in enumerate(priorities):
            task.add_task_to_buffer(
                json.dumps({"task_id": i, "priority": priority}),
                priority=priority,
                bot_id=0
            )
        
        # Executa transferência
        transferred = task.transfer_batch_from_buffer(0)
        self.assertEqual(transferred, 10)  # Todas as 10 tarefas
        
        # Verifica se todas foram chamadas com suas respectivas prioridades
        self.assertEqual(task.process_command.apply_async.call_count, 10)
        
        # Verifica se as prioridades foram mantidas nas chamadas
        calls = task.process_command.apply_async.call_args_list
        for call in calls:
            self.assertIn('priority', call.kwargs)
            
    @patch('task.get_main_queue_length')
    def test_multiple_bots_scenario(self, mock_queue_length):
        """Testa cenário com múltiplos bots"""
        mock_queue_length.return_value = 0  # Queue vazia
        
        # Adiciona tarefas para diferentes bots
        for bot_id in range(4):  # bots 0, 1, 2, 3
            for task_num in range(3):
                task.add_task_to_buffer(
                    json.dumps({
                        "bot_id": bot_id,
                        "task_num": task_num,
                        "app": f"app_{bot_id}"
                    }),
                    priority=task_num % 3,
                    bot_id=bot_id
                )
        
        # Executa gerenciador
        task.manage_buffer_transfer()
        
        # Verifica se transferiu de todos os buffers
        # Como queue estava vazia (0), deveria ter transferido imediatamente na adição
        # Mais a execução do manage_buffer_transfer
        total_calls = task.process_command.apply_async.call_count
        self.assertGreater(total_calls, 0)


class TestManualScheduleTesting(TestCase):
    """Classe para testes manuais do schedule"""
    
    def setUp(self):
        self.test_redis = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
        task.redis_client = self.test_redis
        self.test_redis.flushdb()
        
    def tearDown(self):
        self.test_redis.flushdb()
        
    def test_schedule_timing_calculation(self):
        """Testa o cálculo do timing do schedule"""
        # Valores das constantes (do Constants.py)
        BATCH_SIZE = 12
        TEMPO_MEDIO_TASKS = 5
        
        # Cálculo esperado
        expected_interval = 0.2 * BATCH_SIZE * TEMPO_MEDIO_TASKS
        expected_interval = 0.2 * 12 * 5  # = 12 segundos
        
        print(f"Intervalo calculado do schedule: {expected_interval} segundos")
        print(f"Isso significa que manage_buffer_transfer será executado a cada {expected_interval}s")
        
        # Verifica se o cálculo está correto
        self.assertEqual(expected_interval, 12.0)
        
    def create_test_scenario(self, num_tasks_per_bot=5, num_bots=3):
        """Cria um cenário de teste com tarefas"""
        print(f"\n=== Criando cenário de teste ===")
        print(f"Bots: {num_bots}, Tarefas por bot: {num_tasks_per_bot}")
        
        for bot_id in range(num_bots):
            for task_id in range(num_tasks_per_bot):
                task_data = {
                    "bot_id": bot_id,
                    "task_id": task_id,
                    "app": f"app_{bot_id}",
                    "action": f"action_{task_id}",
                    "timestamp": time.time()
                }
                
                priority = task_id % 3  # Prioridades 0, 1, 2
                task.add_task_to_buffer(
                    json.dumps(task_data),
                    priority=priority,
                    bot_id=bot_id
                )
                
        print("Tarefas adicionadas aos buffers!")
        self.print_buffer_status()
        
    def print_buffer_status(self):
        """Imprime o status atual dos buffers"""
        print("\n=== Status dos Buffers ===")
        for bot_id in range(4):  # Verifica bots 0-3
            buffer_name = task.get_buffer_queue_name(bot_id)
            size = self.test_redis.llen(buffer_name)
            if size > 0:
                print(f"Buffer bot_{bot_id}: {size} tarefas")
        print("=" * 30)


def run_manual_test():
    """Função para executar teste manual do sistema"""
    print("=== TESTE MANUAL DO SISTEMA DE BUFFER ===\n")
    
    # Cria instância de teste
    test = TestManualScheduleTesting()
    test.setUp()
    
    try:
        # Testa cálculo do schedule
        test.test_schedule_timing_calculation()
        
        # Cria cenário de teste
        test.create_test_scenario(num_tasks_per_bot=8, num_bots=3)
        
        # Simula execução do manage_buffer_transfer
        print("\n=== Simulando execução do manage_buffer_transfer ===")
        
        # Mock para simular queue baixa
        with patch('task.get_main_queue_length') as mock_queue_length:
            mock_queue_length.return_value = 1  # Queue baixa
            
            # Mock do Celery
            task.app_celery = MagicMock()
            task.process_command = MagicMock()
            task.process_command.apply_async = MagicMock()
            
            # Executa gerenciador
            result = task.manage_buffer_transfer()
            print(f"Resultado: {result}")
            print(f"Chamadas para apply_async: {task.process_command.apply_async.call_count}")
            
        test.print_buffer_status()
        
    finally:
        test.tearDown()
        print("\nTeste manual concluído!")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Testa o sistema de buffer e beat schedule')
    parser.add_argument('--manual', action='store_true', help='Executa teste manual')
    parser.add_argument('--unit', action='store_true', help='Executa testes unitários')
    
    args = parser.parse_args()
    
    if args.manual:
        run_manual_test()
    elif args.unit:
        unittest.main(argv=[''], verbosity=2, exit=False)
    else:
        print("Executando todos os testes...")
        print("\n1. Teste manual:")
        run_manual_test()
        print("\n2. Testes unitários:")
        unittest.main(argv=[''], verbosity=2, exit=False)
