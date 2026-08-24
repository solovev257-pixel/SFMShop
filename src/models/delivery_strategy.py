from abc import ABC, abstractmethod

class DeliveryStrategy(ABC):
    @abstractmethod
    def calculate_cost(self, distance):
        pass

class StandardDelivery(DeliveryStrategy):
    def calculate_cost(self, distance):
        return distance * 10

class ExpressDelivery(DeliveryStrategy):
    def calculate_cost(self, distance):
        return distance * 20