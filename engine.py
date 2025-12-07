import random
from typing import List, Dict, Any, Tuple
from config import SimulationParams, SimulationStats

class Worker:
    def __init__(self, nameId: str):
        self.id = nameId
        self.busyTimeRemaining = 0
        self.totalBusyTime = 0
        self.currentTask = None

    @property
    def isFree(self) -> bool:
        return self.busyTimeRemaining <= 0

    def assignTask(self, duration: int, taskType: str):
        self.busyTimeRemaining = duration
        self.totalBusyTime += duration
        self.currentTask = taskType

    def tick(self) -> bool:
        if not self.isFree:
            self.busyTimeRemaining -= 1
            if self.busyTimeRemaining <= 0:
                self.currentTask = None
                return True
        return False

class ChattyEngine:
    def __init__(self, params: SimulationParams):
        self.params = params
        self.stats = SimulationStats()
        self.stats.utilizationServers = [0.0] * params.numServers
        self.currentTime = 0
        self.nextArrivalTime = self.getRandomInterval(params.arrivalInterval)
        # Буферы
        self.ioQueue: List[int] = []
        # Серверы
        self.servers = [Worker(f'Server-{i+1}') for i in range(params.numServers)]

    def getRandomInterval(self, interval: Tuple[int, int]) -> int:
        return random.randint(interval[0], interval[1])

    def step(self) -> bool:
        if self.currentTime >= self.params.totalTime:
            return False
        # 1. Генерация трафика
        if self.currentTime >= self.nextArrivalTime:
            self.stats.generatedTotal += 1
            isChatty = random.random() < self.params.probChatty
            numSubRequests = random.randint(self.params.chattyMin, self.params.chattyMax) if isChatty else 1
            self.stats.generatedChatty += 1 if isChatty else 0
            self.stats.generatedOptimized += 1 if not isChatty else 0
            for _ in range(numSubRequests):
                if len(self.ioQueue) < self.params.bufferSize:
                    self.ioQueue.append(self.currentTime)
                else:
                    self.stats.rejectedTotal += 1
            self.nextArrivalTime = self.currentTime + self.getRandomInterval(self.params.arrivalInterval)
        # 2. Обработка
        for server in self.servers:
            if server.isFree and self.ioQueue:
                _ = self.ioQueue.pop(0)
                serviceTime = self.getRandomInterval(self.params.serviceTime) + self.params.networkLatency
                server.assignTask(serviceTime, 'IO')
                self.stats.processedTotal += 1
            server.tick()
        self.currentTime += 1
        return True

    def getResults(self) -> Dict[str, Any]:
        t = self.currentTime if self.currentTime > 0 else 1
        kServers = [(r.totalBusyTime / t) * 100 for r in self.servers]
        rejProb = 0
        if self.stats.generatedTotal > 0:
            rejProb = (self.stats.rejectedTotal / (self.stats.generatedTotal + self.stats.generatedChatty * (self.params.chattyMax - 1))) * 100  # Учет субзапросов
        kAvg = sum(kServers) / len(kServers) if kServers else 0
        return {
            'totalReq': self.stats.generatedTotal,
            'processed': self.stats.processedTotal,
            'rejected': self.stats.rejectedTotal,
            'rejProb': rejProb,
            'kAvg': kAvg
        }