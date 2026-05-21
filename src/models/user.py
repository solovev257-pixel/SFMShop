class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
    
    def get_info(self):
        return "Пользователь: " + self.name + ", Email: " + self.email
