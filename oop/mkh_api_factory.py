class MKHApiRepo:
    def __init__(self):
        print("MKH API Layer Intiated")

class MKHmsazRepo:
    def __init__(self):
        print("MKH Azure Layer Intiated")

class MKHAwsRepo:
    def __init__(self):
        print("MKH AWS Layer Intiated")

class MKHApiFactory:
    def __init__(self, source=None):
        match source:
            case "azure":
                self.repo = MKHmsazRepo()
            case "aws":
                self.repo = MKHAwsRepo()
            case _:
                self.repo = MKHApiRepo()

    def getRepo(self):
        return self.repo
    

MKHFactory = MKHApiFactory("azure")
MKHClient = MKHFactory.getRepo()

MKHFactory = MKHApiFactory("aws")
MKHClient = MKHFactory.getRepo()

MKHFactory = MKHApiFactory()
MKHClient = MKHFactory.getRepo()