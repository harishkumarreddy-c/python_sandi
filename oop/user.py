'''
    class dicluration
    intiation
    properties
    methods:
        Constructor: __init__()
        Logical Methods: getProfile()

    access modifiers: 
        public, 
        private: _Variable 
        protected: __Variable

    Magic Methods/ Dunder Methods/ Special Methods: __MethodName__
        __init__(): constructor
        __str__(): string representation of the object
        

'''

class User:
    __name = None
    __email = None
    __password = None

    

    def __str__(self):
        return f"User object with the Name: {self.__name}, Email: {self.__email}"
    
    def __json__(self):
        return {
            "name": self.__name,
            "email": self.__email,
            "password": self.__password
        }
    
    def __init__(self, name, email, password):
        self.__name = name
        self.__email = email
        self.__password = password

    def json(self):
        return self.__json__()

    # def getProfile(self):
    #     return f"Name: {self.__name}, Email: {self.__email}"
    
    # def setName(self, name):
    #     self.__name = name

    # def getName(self):
    #     return self.__name





u1 = User("John Doe", "john.doe@example.com", "123456")
print(u1)
print(u1.json())

# # u2 = User("Jane Smith", "jane.smith@example.com", "654321")

# # u1.name = "Harish Kumar"
# # u1.email = "john.doe@example.com"
# # u1.password = "123456"

# u1.setName("Harish Kumar")

# print(u1.getProfile())
# print(u1)


# u1 = User("John Doe", "john.doe@example.com", "123456")
# print(u1.getProfile())
# print(u1)

# # u2.name = "Jane Smith"
# # u2.email = "jane.smith@example.com"
# # u2.password = "654321"

# # print(u2.getProfile())

