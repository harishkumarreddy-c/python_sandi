from user import User
from user_interface import UserInterface

class Use(User, UserInterface):

    def __init__(self):
        super().__init__()


class Admin(Use):

    def __init__(self):
        super().__init__()
        print("Admin user initiated")

    def updateLastLogin(self, user_id):
        pass



admin = Admin();
admin.login("Harish", "12345")
admin.setLiveStatus("Harish")