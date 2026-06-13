from abc import ABC, abstractmethod

class UserInterface(ABC):

    @abstractmethod
    def login(self, user_id, password):
        pass

    @abstractmethod
    def updateLastLogin(self, user_id):
        pass

    
    def setLiveStatus(self, user_id):
        print("Livestatus is updated to LIVE")
        
