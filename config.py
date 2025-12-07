from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class SimulationParams:
    totalTime: int
    arrivalInterval: Tuple[int, int]
    probChatty: float
    serviceTime: Tuple[int, int]
    networkLatency: int
    numServers: int
    bufferSize: int
    chattyMin: int
    chattyMax: int

@dataclass
class SimulationStats:
    generatedTotal: int = 0
    generatedChatty: int = 0
    generatedOptimized: int = 0
    processedTotal: int = 0
    rejectedTotal: int = 0
    utilizationServers: List[float] = None