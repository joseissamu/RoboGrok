"""
Script de teste específico para o Beat Schedule
Este script permite testar o comportamento do beat schedule de forma mais realista.
"""

import time
import json
import redis
import threading
from datetime import datetime
import os
import sys

# Adiciona o diretório atual ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class BeatScheduleSimulator:
    """Simula o comportamento do Celery Beat para testes"""
    
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=15, decode_responses=True)
        self.redis_client.flushdb()  # Limpa o banco de teste
        
        # Simula as constantes
        self.BATCH_SIZE = 12
        self.TEMPO_MEDIO_TASKS = 5
        self.THRESHOLD_CONTINUOS_QUEUE_FLUX = 2
        self.schedule_interval = 0.2 * self.BATCH_SIZE * self.TEMPO_MEDIO_TASKS  # 12 segundos
        
        # Estado do sistema
        self.main_queue_size = 0
        self.running = False
        self.transferred_tasks = []
        self.execution_log = []
        
        print(f"Simulador iniciado com intervalo de {self.schedule_interval} segundos")
        
    def get_buffer_queue_name(self, bot_id):
        return f"buffer_bot_{bot_id}"
        
    def add_task_to_buffer(self, task_data, priority, bot_id):
        """Simula adição de tarefa ao buffer"""
        buffer_queue = self.get_buffer_queue_name(bot_id)
        task_info = {
            'task_data': task_data,
            'priority': priority,
            'timestamp': time.time(),
            'bot_id': bot_id
        }
        
        self.redis_client.rpush(buffer_queue, json.dumps(task_info))
        
        # Transferência imediata se queue vazia
        if self.main_queue_size == 0:
            transferred = self.transfer_batch_from_buffer(bot_id)
            if transferred > 0:
                self.log(f"Transferência IMEDIATA: {transferred} tarefas do bot_{bot_id}")
        
    def transfer_batch_from_buffer(self, bot_id):
        """Simula transferência de lote do buffer para queue principal"""
        buffer_queue = self.get_buffer_queue_name(bot_id)
        buffer_size = self.redis_client.llen(buffer_queue)
        
        if buffer_size == 0:
            return 0
            
        transferred = 0
        for _ in range(min(self.BATCH_SIZE, buffer_size)):
            task_data = self.redis_client.lpop(buffer_queue)
            if task_data:
                task_info = json.loads(task_data)
                
                # Simula envio para queue principal
                self.main_queue_size += 1
                self.transferred_tasks.append({
                    'task': task_info,
                    'transferred_at': time.time()
                })
                transferred += 1
                
        return transferred
        
    def manage_buffer_transfer(self):
        """Simula a função manage_buffer_transfer"""
        execution_time = datetime.now().strftime('%H:%M:%S')
        
        if self.main_queue_size <= self.THRESHOLD_CONTINUOS_QUEUE_FLUX:
            total_transferred = 0
            
            for bot_id in range(4):  # bots 0-3
                transferred = self.transfer_batch_from_buffer(bot_id)
                total_transferred += transferred
                
                if transferred > 0:
                    self.log(f"[{execution_time}] Schedule: {transferred} tarefas transferidas do bot_{bot_id}")
            
            if total_transferred > 0:
                self.log(f"[{execution_time}] TOTAL Schedule: {total_transferred} tarefas transferidas")
            else:
                self.log(f"[{execution_time}] Schedule executado - nenhuma transferência (buffers vazios)")
        else:
            self.log(f"[{execution_time}] Schedule executado - queue muito cheia ({self.main_queue_size} tarefas)")
            
        return "Buffer management completed"
        
    def simulate_task_processing(self):
        """Simula o processamento de tarefas pelos workers"""
        while self.running:
            if self.main_queue_size > 0:
                # Simula processamento de uma tarefa
                processing_time = 2  # Simula 2 segundos por tarefa
                time.sleep(processing_time)
                self.main_queue_size -= 1
                
                # Log ocasional do processamento
                if self.main_queue_size % 5 == 0:
                    execution_time = datetime.now().strftime('%H:%M:%S')
                    self.log(f"[{execution_time}] Worker: Processou tarefa. Queue restante: {self.main_queue_size}")
            else:
                time.sleep(0.5)  # Aguarda se não há tarefas
                
    def simulate_beat_schedule(self):
        """Simula a execução periódica do beat schedule"""
        while self.running:
            time.sleep(self.schedule_interval)
            if self.running:  # Verifica novamente após o sleep
                self.manage_buffer_transfer()
                
    def log(self, message):
        """Log com timestamp"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        self.execution_log.append(log_message)
        
    def print_status(self):
        """Imprime status atual do sistema"""
        print(f"\n{'='*50}")
        print(f"STATUS DO SISTEMA - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*50}")
        print(f"Queue principal: {self.main_queue_size} tarefas")
        print(f"Schedule interval: {self.schedule_interval}s")
        print(f"Threshold: {self.THRESHOLD_CONTINUOS_QUEUE_FLUX}")
        
        # Status dos buffers
        for bot_id in range(4):
            buffer_size = self.redis_client.llen(self.get_buffer_queue_name(bot_id))
            if buffer_size > 0:
                print(f"Buffer bot_{bot_id}: {buffer_size} tarefas")
                
        print(f"Total transferido: {len(self.transferred_tasks)} tarefas")
        print(f"{'='*50}\n")
        
    def run_simulation(self, duration_minutes=2):
        """Executa simulação por um período específico"""
        print(f"Iniciando simulação por {duration_minutes} minutos...")
        print(f"Schedule executará a cada {self.schedule_interval} segundos")
        print("Pressione Ctrl+C para parar antes do tempo\n")
        
        self.running = True
        
        # Inicia threads
        beat_thread = threading.Thread(target=self.simulate_beat_schedule, daemon=True)
        worker_thread = threading.Thread(target=self.simulate_task_processing, daemon=True)
        
        beat_thread.start()
        worker_thread.start()
        
        try:
            start_time = time.time()
            status_interval = 30  # Status a cada 30 segundos
            last_status = start_time
            
            while time.time() - start_time < duration_minutes * 60:
                time.sleep(1)
                
                # Imprime status periodicamente
                if time.time() - last_status >= status_interval:
                    self.print_status()
                    last_status = time.time()
                    
        except KeyboardInterrupt:
            print("\nSimulação interrompida pelo usuário")
        finally:
            self.running = False
            print("\nParando simulação...")
            time.sleep(1)
            
        self.print_final_report()
        
    def print_final_report(self):
        """Imprime relatório final da simulação"""
        print(f"\n{'='*60}")
        print("RELATÓRIO FINAL DA SIMULAÇÃO")
        print(f"{'='*60}")
        
        print(f"Total de tarefas transferidas: {len(self.transferred_tasks)}")
        print(f"Queue principal final: {self.main_queue_size} tarefas")
        
        # Contagem por bot
        bot_counts = {}
        for task in self.transferred_tasks:
            bot_id = task['task']['bot_id']
            bot_counts[bot_id] = bot_counts.get(bot_id, 0) + 1
            
        for bot_id, count in bot_counts.items():
            print(f"Bot {bot_id}: {count} tarefas transferidas")
            
        print(f"\nTotal de execuções de log: {len(self.execution_log)}")
        print(f"Schedule interval usado: {self.schedule_interval}s")
        print(f"Threshold usado: {self.THRESHOLD_CONTINUOS_QUEUE_FLUX}")
        
        # Buffers restantes
        remaining_tasks = 0
        for bot_id in range(4):
            buffer_size = self.redis_client.llen(self.get_buffer_queue_name(bot_id))
            remaining_tasks += buffer_size
            
        if remaining_tasks > 0:
            print(f"\nTarefas restantes nos buffers: {remaining_tasks}")
            
        print(f"{'='*60}\n")


def create_test_scenario(simulator, scenario_name="default"):
    """Cria diferentes cenários de teste"""
    print(f"Criando cenário: {scenario_name}")
    
    if scenario_name == "burst":
        # Cenário de rajada: muitas tarefas de uma vez
        print("Adicionando 50 tarefas em rajada...")
        for i in range(50):
            bot_id = i % 3
            priority = i % 3
            simulator.add_task_to_buffer(
                f"burst_task_{i}",
                priority,
                bot_id
            )
            
    elif scenario_name == "gradual":
        # Cenário gradual: tarefas espaçadas no tempo
        print("Adicionando tarefas gradualmente...")
        def add_gradual_tasks():
            for i in range(30):
                if not simulator.running:
                    break
                bot_id = i % 3
                priority = i % 3
                simulator.add_task_to_buffer(
                    f"gradual_task_{i}",
                    priority,
                    bot_id
                )
                time.sleep(2)  # Espera 2 segundos entre tarefas
                
        threading.Thread(target=add_gradual_tasks, daemon=True).start()
        
    elif scenario_name == "mixed":
        # Cenário misto: rajada inicial + tarefas contínuas
        print("Adicionando tarefas em modo misto...")
        # Rajada inicial
        for i in range(20):
            bot_id = i % 3
            priority = i % 3
            simulator.add_task_to_buffer(
                f"initial_burst_{i}",
                priority,
                bot_id
            )
            
        # Tarefas contínuas
        def add_continuous_tasks():
            for i in range(40):
                if not simulator.running:
                    break
                bot_id = i % 3
                priority = i % 3
                simulator.add_task_to_buffer(
                    f"continuous_task_{i}",
                    priority,
                    bot_id
                )
                time.sleep(3)  # Espera 3 segundos entre tarefas
                
        threading.Thread(target=add_continuous_tasks, daemon=True).start()


def main():
    """Função principal para executar testes do beat schedule"""
    print("=== SIMULADOR DO BEAT SCHEDULE ===\n")
    
    # Cria simulador
    simulator = BeatScheduleSimulator()
    
    # Menu de opções
    print("Escolha um cenário:")
    print("1. Rajada (50 tarefas de uma vez)")
    print("2. Gradual (30 tarefas espaçadas)")
    print("3. Misto (rajada + contínuo)")
    print("4. Personalizado")
    
    choice = input("Digite sua escolha (1-4): ").strip()
    
    if choice == "1":
        create_test_scenario(simulator, "burst")
    elif choice == "2":
        create_test_scenario(simulator, "gradual")
    elif choice == "3":
        create_test_scenario(simulator, "mixed")
    elif choice == "4":
        num_tasks = int(input("Quantas tarefas adicionar? "))
        for i in range(num_tasks):
            bot_id = i % 3
            priority = i % 3
            simulator.add_task_to_buffer(
                f"custom_task_{i}",
                priority,
                bot_id
            )
    else:
        print("Opção inválida, usando cenário padrão (burst)")
        create_test_scenario(simulator, "burst")
    
    # Pergunta duração
    try:
        duration = float(input("Duração da simulação em minutos (padrão 2): ") or "2")
    except ValueError:
        duration = 2
        
    # Executa simulação
    simulator.run_simulation(duration)


if __name__ == "__main__":
    main()
