
class User:

    def __init__(self):
        print("User layer activated for the application")

    def register():
        pass

    def login(self, user_id, password):
        print("User login successfull")
        print(f"Hello ${user_id}")

    def logout():
        pass

    def profile():
        pass

    def changePassword():
        pass

    def forgotPassword():
        pass

    
    # def getPermitions(id):
    #     role = db.query("select role from users where id = ?", id).run()
    #     permitins = None

    #     if role == "admin":
    #         permissions = [
    #             "create",
    #             "read",
    #             "update",
    #             "delete"
    #         ]
    #     elif role == "manager":
    #         permissions = [
    #             "create",
    #             "read",
    #             "update"
    #         ]
    #     elif role == "employee":
    #         permissions = [
    #             "read"
    #             "create"
    #         ]
    #     else:
    #         permissions = [
    #             "read"
    #         ]
    #     return permissions
        


